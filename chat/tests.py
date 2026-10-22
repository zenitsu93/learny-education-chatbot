import datetime
import io
from unittest import mock

from django import forms
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import ai, retrieval
from .forms import normaliser_telephone
from .models import Chat, CourseChunk, Session
from .rendering import markdown_sur
from .seance import seance_du_jour
from .subjects import MATIERES

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class TelephoneTests(TestCase):
    def test_formats_acceptes(self):
        for brut in ["70 12 34 56", "70123456", "+226 70 12 34 56", "0022670123456", "226-70-12-34-56"]:
            self.assertEqual(normaliser_telephone(brut), "+22670123456", brut)

    def test_numero_trop_court(self):
        with self.assertRaises(forms.ValidationError):
            normaliser_telephone("70 12 34")


class RenduTests(TestCase):
    def test_pas_de_script(self):
        html = markdown_sur("Bonjour <script>alert(1)</script> [lien](javascript:alert(1)) **gras**")
        self.assertNotIn("<script", html)
        self.assertNotIn("href=\"javascript", html)
        self.assertIn("<strong>gras</strong>", html)

    def test_titres_ramenes_a_h3(self):
        self.assertIn("<h3>", markdown_sur("# Titre"))


class ComptesTests(TestCase):
    def test_inscription_puis_connexion(self):
        r = self.client.post(reverse("inscription"), {"prenom": "awa", "telephone": "70 12 34 56", "password": "cahier-bleu-26"})
        self.assertRedirects(r, reverse("accueil"))
        u = User.objects.get(username="+22670123456")
        self.assertEqual(u.first_name, "Awa")
        self.assertEqual(u.profile.niveau, "3eme")

        self.client.post(reverse("deconnexion"))
        r = self.client.post(reverse("connexion"), {"identifiant": "70123456", "password": "cahier-bleu-26"})
        self.assertRedirects(r, reverse("accueil"))

    def test_numero_deja_pris(self):
        User.objects.create_user("+22670123456", password="x")
        r = self.client.post(reverse("inscription"), {"prenom": "Awa", "telephone": "70123456", "password": "cahier-bleu-26"})
        self.assertContains(r, "Ce numéro a déjà un compte")

    def test_ancien_compte_email(self):
        User.objects.create_user("eleve@exemple.bf", password="cahier-bleu-26")
        r = self.client.post(reverse("connexion"), {"identifiant": "eleve@exemple.bf", "password": "cahier-bleu-26"})
        self.assertRedirects(r, reverse("accueil"))

    def test_pages_protegees(self):
        r = self.client.get(reverse("accueil"))
        self.assertEqual(r.status_code, 302)


@override_settings(GEMINI_API_KEY="", LEARNY_QUOTA_JOUR=2)
class DiscussionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("+22670000001", password="x", first_name="Awa")
        self.client.force_login(self.user)
        self.s = Session.objects.create(user=self.user, cours_name="maths", title="Nouvelle discussion")
        self.url = reverse("question", args=[self.s.pk])

    def poser(self, texte="Comment utiliser Thalès ?"):
        return self.client.post(self.url, {"question": texte, "guide": "1"}, HTTP_HX_REQUEST="true")

    def test_pages_s_affichent(self):
        for nom, args in [("accueil", []), ("reglages", []), ("discussion", [self.s.pk])]:
            self.assertEqual(self.client.get(reverse(nom, args=args)).status_code, 200, nom)

    def test_question_en_mode_demo(self):
        r = self.poser()
        self.assertContains(r, "Mode démonstration")
        self.assertContains(r, 'id="quota" hx-swap-oob="true"')
        self.s.refresh_from_db()
        self.assertEqual(self.s.title, "Comment utiliser Thalès ?")
        self.assertEqual(Chat.objects.count(), 1)

    def test_question_vide(self):
        r = self.poser("   ")
        self.assertContains(r, "Ta question est vide")
        self.assertEqual(Chat.objects.count(), 0)

    def test_quota(self):
        self.poser()
        self.poser()
        r = self.poser()
        self.assertContains(r, "Tu as posé tes 2 questions du jour")
        self.assertEqual(Chat.objects.count(), 2)

    def test_gemini_indisponible_garde_la_question(self):
        with mock.patch.object(ai, "repondre", side_effect=ai.LearnyIndisponible):
            r = self.poser("Question gardée")
        self.assertContains(r, "Renvoyer la question")
        self.assertContains(r, 'value="Question gardée"')
        self.assertEqual(Chat.objects.count(), 0)

    def test_reponse_echappe_le_html(self):
        rep = ai.Reponse(texte="<img src=x onerror=alert(1)> **ok**", sources=[{"source": "Maths 3e", "page": 12}])
        with mock.patch.object(ai, "repondre", return_value=rep):
            r = self.poser()
        self.assertNotContains(r, "<img")
        self.assertContains(r, "Maths 3e · p. 12")

    def test_discussion_d_un_autre_eleve(self):
        autre = User.objects.create_user("+22670000002", password="x")
        s2 = Session.objects.create(user=autre, cours_name="maths", title="Privé")
        self.assertEqual(self.client.get(reverse("discussion", args=[s2.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("question", args=[s2.pk]), {"question": "x"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("supprimer_discussion", args=[s2.pk])).status_code, 404)

    def test_matiere_inconnue(self):
        self.assertEqual(self.client.get(reverse("matiere", args=["latin"])).status_code, 404)

    def test_reglages_appliques_a_la_page(self):
        self.client.post(reverse("reglages"), {"taille_texte": "130", "theme": "sombre", "reduire_animations": "on"})
        r = self.client.get(reverse("accueil"))
        self.assertContains(r, 'data-theme="dark"')
        self.assertContains(r, "data-reduce")
        self.assertContains(r, "calc(130 / 100)")


class RechercheTests(TestCase):
    def test_decoupage_garde_la_page(self):
        pages = [(3, "Phrase. " * 400)]
        morceaux = list(retrieval.decouper(pages))
        self.assertGreater(len(morceaux), 1)
        self.assertTrue(all(p == 3 and len(t) <= 1200 for p, t in morceaux))

    def test_recherche_par_similarite(self):
        CourseChunk.objects.create(matiere="maths", source="Maths 3e", page=1, texte="Thalès", embedding=[1.0, 0.0])
        CourseChunk.objects.create(matiere="maths", source="Maths 3e", page=2, texte="Pythagore", embedding=[0.0, 1.0])
        CourseChunk.objects.create(matiere="svt", source="SVT 3e", page=1, texte="Gène", embedding=[1.0, 0.0])
        with mock.patch.object(ai, "embed", return_value=[[0.9, 0.1]]):
            res = retrieval.rechercher("maths", "Thalès ?")
        self.assertEqual([c.texte for c in res], ["Thalès"])

    def test_sans_cle_pas_de_recherche(self):
        CourseChunk.objects.create(matiere="maths", source="Maths 3e", page=1, texte="Thalès", embedding=[1.0, 0.0])
        with mock.patch.object(ai, "embed", return_value=None):
            self.assertEqual(retrieval.rechercher("maths", "x"), [])

    def test_import_cite_les_pages_du_livre(self):
        pages = [mock.Mock(extract_text=mock.Mock(return_value=t)) for t in ["Couverture du cours. " * 10, "Les nombres réels. " * 10]]
        with mock.patch("chat.management.commands.import_cours.PdfReader", return_value=mock.Mock(pages=pages)), \
                mock.patch.object(ai, "embed", side_effect=lambda textes: [[1.0, 0.0]] * len(textes)):
            call_command("import_cours", "cours.pdf", matiere="maths", titre="Maths 3e", decalage=1, stdout=io.StringIO())
        self.assertEqual(list(CourseChunk.objects.order_by("id").values_list("page", flat=True)), [None, 1])


@override_settings(GEMINI_API_KEY="", LEARNY_QUOTA_JOUR=2)
class PhotoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("+22670000001", password="x")
        self.client.force_login(self.user)
        self.s = Session.objects.create(user=self.user, cours_name="maths", title="Nouvelle discussion")

    def envoyer(self, contenu=JPEG):
        return self.client.post(reverse("photo", args=[self.s.pk]), {"photo": SimpleUploadedFile("exo.jpg", contenu)})

    def test_lecture_en_mode_demo(self):
        r = self.envoyer()
        self.assertContains(r, "J'ai lu ceci")
        self.assertContains(r, "Mode démonstration")
        self.assertContains(r, f'hx-post="{reverse("question", args=[self.s.pk])}"')
        self.assertEqual(Chat.objects.count(), 0)  # lire la photo ne coûte pas de question

    def test_texte_lu_renvoye_a_l_eleve(self):
        with mock.patch.object(ai, "lire_enonce", return_value="ABC est un triangle. Calcule AN.") as lire:
            r = self.envoyer()
        self.assertContains(r, "ABC est un triangle. Calcule AN.")
        self.assertEqual(lire.call_args.args[2], "image/jpeg")

    def test_photo_illisible(self):
        with mock.patch.object(ai, "lire_enonce", return_value=""):
            self.assertContains(self.envoyer(), "Je n'arrive pas à lire la photo")

    def test_gemini_indisponible(self):
        with mock.patch.object(ai, "lire_enonce", side_effect=ai.LearnyIndisponible):
            self.assertContains(self.envoyer(), "La photo n'a pas pu être lue")

    def test_fichier_qui_n_est_pas_une_photo(self):
        with mock.patch.object(ai, "lire_enonce") as lire:
            self.assertContains(self.envoyer(b"%PDF-1.7 pas une photo"), "Je ne sais pas lire ce fichier")
            self.assertContains(self.client.post(reverse("photo", args=[self.s.pk])), "Je ne sais pas lire ce fichier")
        lire.assert_not_called()

    def test_quota_atteint(self):
        for _ in range(2):
            Chat.objects.create(session=self.s, message="q", response="r")
        self.assertContains(self.envoyer(), "Tu as posé tes 2 questions du jour")

    def test_photo_dans_la_discussion_d_un_autre_eleve(self):
        autre = User.objects.create_user("+22670000002", password="x")
        s2 = Session.objects.create(user=autre, cours_name="maths", title="Privé")
        r = self.client.post(reverse("photo", args=[s2.pk]), {"photo": SimpleUploadedFile("exo.jpg", JPEG)})
        self.assertEqual(r.status_code, 404)


class LecturePhotoTests(TestCase):
    def test_type_image(self):
        self.assertEqual(ai.type_image(JPEG[:16]), "image/jpeg")
        self.assertEqual(ai.type_image(b"\x89PNG\r\n\x1a\n\x00\x00"), "image/png")
        self.assertEqual(ai.type_image(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image/webp")
        self.assertEqual(ai.type_image(b"\x00\x00\x00\x18ftypheic\x00\x00"), "image/heic")
        self.assertIsNone(ai.type_image(b"%PDF-1.7"))
        self.assertIsNone(ai.type_image(b"<svg xmlns="))

    @override_settings(GEMINI_API_KEY="cle-de-test")
    def test_reponse_de_gemini(self):
        faux = mock.Mock()
        with mock.patch.object(ai, "client", return_value=faux):
            faux.models.generate_content.return_value = mock.Mock(text="ILLISIBLE.")
            self.assertEqual(ai.lire_enonce(MATIERES["maths"], JPEG, "image/jpeg"), "")
            faux.models.generate_content.return_value = mock.Mock(text="  Calcule AN.  ")
            self.assertEqual(ai.lire_enonce(MATIERES["maths"], JPEG, "image/jpeg"), "Calcule AN.")
            faux.models.generate_content.side_effect = RuntimeError("503")
            with self.assertRaises(ai.LearnyIndisponible):
                ai.lire_enonce(MATIERES["maths"], JPEG, "image/jpeg")


@override_settings(GEMINI_API_KEY="")
class SeanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("+22670000003", password="x")
        self.client.force_login(self.user)

    def travailler(self, slug, n, jours=1):
        """n questions posées dans la matière il y a `jours` jours."""
        s = Session.objects.create(user=self.user, cours_name=slug, title="x")
        for _ in range(n):
            Chat.objects.create(session=s, message="q", response="r")
        Chat.objects.filter(session=s).update(created=timezone.now() - datetime.timedelta(days=jours))

    def seance_passee(self, slug, chapitre, jours):
        s = Session.objects.create(user=self.user, cours_name=slug, title="x", chapitre=chapitre)
        Chat.objects.create(session=s, message="q", response="r")
        Session.objects.filter(pk=s.pk).update(created=timezone.now() - datetime.timedelta(days=jours))

    def test_matiere_la_moins_travaillee(self):
        self.travailler("maths", 3)
        self.travailler("svt", 2)
        seance = seance_du_jour(self.user)
        self.assertEqual(seance.matiere.slug, "physique-chimie")
        self.assertEqual(seance.chapitre, MATIERES["physique-chimie"].chapitres[0])
        self.assertFalse(seance.faite)

    def test_chapitre_suivant_dans_l_ordre_du_cours(self):
        self.travailler("physique-chimie", 3)
        self.travailler("svt", 3)
        maths = MATIERES["maths"]
        self.seance_passee("maths", maths.chapitres[0], jours=2)
        seance = seance_du_jour(self.user)
        self.assertEqual((seance.matiere.slug, seance.chapitre), ("maths", maths.chapitres[1]))

    def test_programme_fini_on_reprend_le_plus_ancien(self):
        self.travailler("maths", 5)
        self.travailler("physique-chimie", 5)
        svt = MATIERES["svt"]
        for i, chapitre in enumerate(svt.chapitres):
            self.seance_passee("svt", chapitre, jours=30 if i == 2 else 10 + i)
        self.assertEqual(seance_du_jour(self.user).chapitre, svt.chapitres[2])

    def test_commencer_puis_faire_la_seance(self):
        self.travailler("maths", 3)
        self.travailler("svt", 2)
        self.assertContains(self.client.get(reverse("accueil")), "Commencer la séance")

        r = self.client.post(reverse("commencer_seance"))
        s = Session.objects.exclude(chapitre="").get()
        self.assertRedirects(r, reverse("discussion", args=[s.pk]))
        self.assertEqual((s.cours_name, s.title, s.guide), ("physique-chimie", "Séance : Résistance et loi d'Ohm", True))
        self.assertContains(self.client.get(s.get_absolute_url()), 'data-suggest="envoyer"')

        # Un second clic reprend la même séance.
        self.client.post(reverse("commencer_seance"))
        self.assertEqual(Session.objects.exclude(chapitre="").count(), 1)
        self.assertContains(self.client.get(reverse("accueil")), "Continuer la séance")

        self.client.post(reverse("question", args=[s.pk]), {"question": "Séance du jour : loi d'Ohm."}, HTTP_HX_REQUEST="true")
        s.refresh_from_db()
        self.assertEqual(s.title, "Séance : Résistance et loi d'Ohm")
        self.assertContains(self.client.get(reverse("accueil")), "Séance du jour faite")

    def test_nouvelle_discussion_ne_reprend_pas_la_seance(self):
        Session.objects.create(user=self.user, cours_name="maths", title="Séance : x", chapitre="Les nombres réels")
        r = self.client.post(reverse("nouvelle_discussion", args=["maths"]))
        nouvelle = Session.objects.get(chapitre="")
        self.assertRedirects(r, reverse("discussion", args=[nouvelle.pk]))
