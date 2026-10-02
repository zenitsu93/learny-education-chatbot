from unittest import mock

from django import forms
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from . import ai, retrieval
from .forms import normaliser_telephone
from .models import Chat, CourseChunk, Session
from .rendering import markdown_sur


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
