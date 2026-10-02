from django.conf import settings

from .subjects import MATIERES


def preferences(request):
    profil = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    return {
        "prefs": profil,
        "aide_whatsapp": settings.LEARNY_AIDE_WHATSAPP,
        "nav_matieres": MATIERES.values(),
    }
