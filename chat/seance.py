"""Séance du jour : un chapitre à réviser, proposé sur l'accueil.

La matière est celle que l'élève a le moins travaillée les 7 jours précédents ;
le chapitre est le premier qu'il n'a pas encore révisé en séance, dans l'ordre du cours.
Le choix ne dépend que des jours passés, il ne change donc pas au fil de la journée.
"""
import datetime
from dataclasses import dataclass

from django.db.models import Count, Max
from django.utils import timezone

from .models import Chat, Session
from .subjects import MATIERES, Matiere


@dataclass
class Seance:
    matiere: Matiere
    chapitre: str
    session: Session = None  # la discussion de la séance, une fois commencée

    @property
    def faite(self):
        return self.session is not None and self.session.chats.exists()


def seance_du_jour(user) -> Seance:
    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    s = Session.objects.filter(user=user, created__gte=debut, cours_name__in=MATIERES).exclude(chapitre="").first()
    if s is not None:
        return Seance(MATIERES[s.cours_name], s.chapitre, s)
    m = _matiere_a_travailler(user, debut)
    return Seance(m, _prochain_chapitre(user, m))


def _matiere_a_travailler(user, debut):
    compte = dict(
        Chat.objects.filter(session__user=user, created__gte=debut - datetime.timedelta(days=7), created__lt=debut)
        .values_list("session__cours_name")
        .annotate(n=Count("id"))
    )
    # À égalité, l'ordre tourne chaque jour pour ne pas toujours proposer la même matière.
    slugs = list(MATIERES)
    r = debut.date().toordinal() % len(slugs)
    slugs = slugs[r:] + slugs[:r]
    return MATIERES[min(slugs, key=lambda slug: compte.get(slug, 0))]


def _prochain_chapitre(user, m):
    revises = dict(
        Session.objects.filter(user=user, cours_name=m.slug, chats__isnull=False)
        .exclude(chapitre="")
        .values_list("chapitre")
        .annotate(d=Max("created"))
    )
    for c in m.chapitres:
        if c not in revises:
            return c
    # Programme fait en entier : on reprend le chapitre révisé il y a le plus longtemps.
    return min(m.chapitres, key=lambda c: revises[c])
