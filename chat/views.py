import datetime
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from . import ai, retrieval
from .forms import ConnexionForm, InscriptionForm, ReglagesForm
from .models import Chat, Session, UserProfile
from .seance import seance_du_jour
from .subjects import MATIERES


def _matiere(slug):
    m = MATIERES.get(slug)
    if m is None:
        raise Http404("Matière inconnue")
    return m


def _profil(user):
    profil, _ = UserProfile.objects.get_or_create(user=user)
    return profil


def questions_restantes(user):
    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    faites = Chat.objects.filter(session__user=user, created__gte=debut).count()
    return max(0, settings.LEARNY_QUOTA_JOUR - faites)


def jours_avant_bepc():
    if not settings.LEARNY_DATE_BEPC:
        return None
    try:
        date = datetime.date.fromisoformat(settings.LEARNY_DATE_BEPC)
    except ValueError:
        return None
    jours = (date - timezone.localdate()).days
    return jours if jours >= 0 else None


# --- Comptes ------------------------------------------------------------------

def racine(request):
    return redirect("accueil" if request.user.is_authenticated else "connexion")


def connexion(request):
    if request.user.is_authenticated:
        return redirect("accueil")
    form = ConnexionForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        if not request.POST.get("rester"):
            request.session.set_expiry(0)  # téléphone partagé : session fermée avec le navigateur
        return redirect(request.GET.get("next") or "accueil")
    return render(request, "chat/connexion.html", {"form": form, "mode": "connexion"})


def inscription(request):
    if request.user.is_authenticated:
        return redirect("accueil")
    form = InscriptionForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Bienvenue {user.first_name}. Choisis une matière pour poser ta première question.")
        return redirect("accueil")
    return render(request, "chat/inscription.html", {"form": form, "mode": "inscription"})


@require_POST
def deconnexion(request):
    logout(request)
    messages.info(request, "Tu es déconnecté. Ce téléphone ne garde plus ton compte ouvert.")
    return redirect("connexion")


# --- Accueil et matières ------------------------------------------------------

@login_required
def accueil(request):
    sessions = Session.objects.filter(user=request.user)
    derniere = sessions.filter(chats__isnull=False).distinct().first()
    compte = {s: 0 for s in MATIERES}
    for s in sessions.filter(chats__isnull=False).distinct():
        if s.cours_name in compte:
            compte[s.cours_name] += 1
    return render(
        request,
        "chat/accueil.html",
        {
            "matieres": [(m, compte[m.slug]) for m in MATIERES.values()],
            "derniere": derniere,
            "derniere_matiere": MATIERES.get(derniere.cours_name) if derniere else None,
            "restantes": questions_restantes(request.user),
            "quota": settings.LEARNY_QUOTA_JOUR,
            "jours_bepc": jours_avant_bepc(),
            "seance": seance_du_jour(request.user),
            "nav": "accueil",
        },
    )


@login_required
@require_POST
def commencer_seance(request):
    seance = seance_du_jour(request.user)
    s = seance.session or Session.objects.create(
        user=request.user,
        cours_name=seance.matiere.slug,
        title=f"Séance : {seance.chapitre}"[:80],
        chapitre=seance.chapitre,
        guide=True,
    )
    return redirect("discussion", pk=s.pk)


@login_required
def matiere(request, slug):
    _matiere(slug)
    s = Session.objects.filter(user=request.user, cours_name=slug).first()
    if s is None:
        s = Session.objects.create(user=request.user, cours_name=slug, title="Nouvelle discussion")
    return redirect("discussion", pk=s.pk)


@login_required
@require_POST
def nouvelle_discussion(request, slug):
    _matiere(slug)
    vide = Session.objects.filter(user=request.user, cours_name=slug, chapitre="", chats__isnull=True).first()
    s = vide or Session.objects.create(user=request.user, cours_name=slug, title="Nouvelle discussion")
    return redirect("discussion", pk=s.pk)


@login_required
@never_cache
def discussion(request, pk):
    s = get_object_or_404(Session, pk=pk, user=request.user)
    m = _matiere(s.cours_name)
    historique = Session.objects.filter(user=request.user, cours_name=s.cours_name, chats__isnull=False).distinct()
    return render(
        request,
        "chat/discussion.html",
        {
            "s": s,
            "m": m,
            "matieres": MATIERES.values(),
            "echanges": s.chats.all(),
            "historique": historique,
            "nb_historique": historique.count(),
            "restantes": questions_restantes(request.user),
            "nav": m.slug,
        },
    )


@login_required
@require_POST
def question(request, pk):
    s = get_object_or_404(Session, pk=pk, user=request.user)
    m = _matiere(s.cours_name)
    texte = (request.POST.get("question") or "").strip()[:2000]
    htmx = request.headers.get("HX-Request") == "true"
    ctx = {"s": s, "m": m, "question_texte": texte}

    def rendu(template, status=200):
        if htmx:
            return render(request, template, ctx, status=status)
        return redirect("discussion", pk=s.pk)

    if "guide" in request.POST:
        s.guide = request.POST.get("guide") == "1"

    if not texte:
        ctx["erreur"] = "vide"
        return rendu("partials/erreur.html", 200)

    if questions_restantes(request.user) <= 0:
        ctx["erreur"] = "quota"
        ctx["quota"] = settings.LEARNY_QUOTA_JOUR
        return rendu("partials/erreur.html", 200)

    historique = [(c.message, c.response) for c in s.chats.all()]
    try:
        extraits = retrieval.rechercher(m.slug, texte)
    except Exception:
        extraits = []  # la recherche ne doit jamais bloquer une réponse
    try:
        rep = ai.repondre(m, texte, historique, extraits, s.guide)
    except ai.LearnyIndisponible:
        ctx["erreur"] = "reseau"
        return rendu("partials/erreur.html", 200)

    chat = Chat.objects.create(session=s, message=texte, response=rep.texte, sources=rep.sources)
    if s.title == "Nouvelle discussion":
        s.title = ai.titre_depuis(texte)
    s.save()
    ctx.update({"c": chat, "restantes": questions_restantes(request.user), "nouveau": True})
    return rendu("partials/echange.html")


@login_required
@require_POST
def photo(request, pk):
    """Lit l'énoncé photographié et le renvoie à l'élève pour vérification.

    La lecture ne compte pas dans le quota : c'est la question envoyée ensuite qui compte.
    """
    s = get_object_or_404(Session, pk=pk, user=request.user)
    m = _matiere(s.cours_name)
    return render(request, "partials/photo.html", {"s": s, "m": m, **_lire_photo(request, m)})


def _lire_photo(request, m):
    if questions_restantes(request.user) <= 0:
        return {"erreur": "quota", "quota": settings.LEARNY_QUOTA_JOUR}
    f = request.FILES.get("photo")
    if f is None or f.size > ai.PHOTO_MAX:
        return {"erreur": "format"}
    image = f.read()
    mime = ai.type_image(image[:16])
    if mime is None:
        return {"erreur": "format"}
    try:
        enonce = ai.lire_enonce(m, image, mime)
    except ai.LearnyIndisponible:
        return {"erreur": "reseau"}
    if not enonce:
        return {"erreur": "illisible"}
    return {"enonce": enonce, "cle": uuid.uuid4().hex[:8]}


@login_required
@require_POST
def supprimer_discussion(request, pk):
    s = get_object_or_404(Session, pk=pk, user=request.user)
    slug = s.cours_name
    s.delete()
    messages.success(request, "Discussion supprimée.")
    return redirect("matiere", slug=slug)


@login_required
@require_POST
def supprimer_tout(request, slug):
    m = _matiere(slug)
    n, _ = Session.objects.filter(user=request.user, cours_name=slug).delete()
    messages.success(request, f"Discussions de {m.nom} supprimées. Tes réglages sont gardés.")
    return redirect("accueil")


# --- Réglages -----------------------------------------------------------------

@login_required
def reglages(request):
    profil = _profil(request.user)
    form = ReglagesForm(data=request.POST or None, instance=profil)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Réglages enregistrés.")
        return redirect("reglages")
    return render(request, "chat/reglages.html", {"form": form, "nav": "reglages"})


# --- PWA ----------------------------------------------------------------------

def hors_ligne(request):
    return render(request, "chat/hors_ligne.html")


def service_worker(request):
    resp = render(
        request,
        "chat/sw.js",
        {
            "version": "v1.1-2026-10-22",
            "static_prefix": static(""),
            "fichiers": [
                reverse("hors_ligne"),
                static("learny/css/learny.css"),
                static("learny/js/learny.js"),
                static("learny/vendor/htmx-2.0.4.min.js"),
                static("learny/fonts/atkinson-hyperlegible-latin-400-normal.woff2"),
                static("learny/fonts/atkinson-hyperlegible-latin-700-normal.woff2"),
                static("learny/fonts/bricolage-grotesque-latin-700-normal.woff2"),
                static("learny/img/icone.svg"),
            ],
        },
        content_type="application/javascript",
    )
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def manifeste(request):
    return render(request, "chat/manifest.webmanifest", content_type="application/manifest+json")


def erreur_404(request, exception=None):
    return render(request, "chat/404.html", status=404)
