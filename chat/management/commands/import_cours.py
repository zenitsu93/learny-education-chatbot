"""Importe un cours PDF : découpe par page, calcule les embeddings, enregistre en base.

À lancer sur sa machine (ou une fois sur le serveur), jamais pendant une requête :
    python manage.py import_cours "context/Cours de Maths 3ème Burkina Faso.pdf" --matiere maths --titre "Cours de Maths 3e"
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pypdf import PdfReader

from chat import ai
from chat.models import CourseChunk
from chat.retrieval import decouper
from chat.subjects import MATIERES

LOT = 50


class Command(BaseCommand):
    help = "Importe un cours PDF dans l'index de recherche d'une matière."

    def add_arguments(self, parser):
        parser.add_argument("pdf")
        parser.add_argument("--matiere", required=True, choices=sorted(MATIERES))
        parser.add_argument("--titre", required=True, help="Nom affiché dans les sources, ex. « Cours de Maths 3e ».")
        parser.add_argument("--remplacer", action="store_true", help="Supprime d'abord les passages de ce titre.")

    def handle(self, pdf, matiere, titre, remplacer, **opts):
        try:
            lecteur = PdfReader(pdf)
        except Exception as exc:
            raise CommandError(f"Impossible de lire {pdf} : {exc}")

        pages = [(i, p.extract_text() or "") for i, p in enumerate(lecteur.pages, 1)]
        passages = list(decouper(pages))
        if not passages:
            raise CommandError("Aucun texte trouvé : le PDF est peut-être scanné (image seule).")

        vecteurs = []
        for i in range(0, len(passages), LOT):
            lot = [t for _, t in passages[i : i + LOT]]
            v = ai.embed(lot)
            if v is None:
                raise CommandError("GEMINI_API_KEY est vide : impossible de calculer les embeddings.")
            vecteurs.extend(v)
            self.stdout.write(f"  {min(i + LOT, len(passages))}/{len(passages)} passages")

        with transaction.atomic():
            if remplacer:
                CourseChunk.objects.filter(matiere=matiere, source=titre).delete()
            CourseChunk.objects.bulk_create(
                CourseChunk(matiere=matiere, source=titre, page=page, texte=texte, embedding=list(vec))
                for (page, texte), vec in zip(passages, vecteurs)
            )
        self.stdout.write(self.style.SUCCESS(f"{len(passages)} passages importés pour {matiere} ({titre})."))
