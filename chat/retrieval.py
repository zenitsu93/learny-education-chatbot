"""Recherche dans les cours officiels.

Les passages et leurs embeddings sont calculés une fois (commande import_cours)
et stockés en base. À chaque question, on calcule un seul embedding et on compare
en mémoire avec numpy : pas de base vectorielle, ce qui tient sur un hébergement mutualisé.
"""
import numpy as np

from . import ai
from .models import CourseChunk

SEUIL = 0.55  # similarité cosinus minimale pour citer un passage
TOP_K = 4


def decouper(pages, taille=1200, chevauchement=150):
    """Découpe une liste de (numéro de page, texte) en passages qui gardent leur page."""
    for num, texte in pages:
        texte = " ".join((texte or "").split())
        debut = 0
        while debut < len(texte):
            fin = min(len(texte), debut + taille)
            if fin < len(texte):
                coupe = texte.rfind(". ", debut + taille // 2, fin)
                if coupe != -1:
                    fin = coupe + 1
            morceau = texte[debut:fin].strip()
            if len(morceau) > 80:
                yield num, morceau
            if fin >= len(texte):
                break
            debut = max(fin - chevauchement, debut + 1)


def rechercher(matiere: str, question: str, k=TOP_K, seuil=SEUIL):
    chunks = list(CourseChunk.objects.filter(matiere=matiere).exclude(embedding=[]))
    if not chunks:
        return []
    vq = ai.embed([question], tache="RETRIEVAL_QUERY")
    if not vq:
        return []
    q = np.asarray(vq[0], dtype=np.float32)
    m = np.asarray([c.embedding for c in chunks], dtype=np.float32)
    scores = (m @ q) / (np.linalg.norm(m, axis=1) * np.linalg.norm(q) + 1e-9)
    ordre = np.argsort(-scores)[:k]
    return [chunks[i] for i in ordre if scores[i] >= seuil]
