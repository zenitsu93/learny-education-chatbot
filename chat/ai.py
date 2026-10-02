"""Accès à Gemini via le SDK google-genai.

Sans clé (GEMINI_API_KEY vide), Learny reste utilisable en développement :
les réponses sont un message de démonstration et la recherche dans les cours est désactivée.
"""
import logging
from dataclasses import dataclass, field

from django.conf import settings

from .subjects import Matiere, consigne_systeme

log = logging.getLogger(__name__)

HISTORIQUE_MAX = 6  # derniers échanges renvoyés au modèle


class LearnyIndisponible(Exception):
    """Gemini n'a pas répondu (réseau, quota, clé invalide…)."""


@dataclass
class Reponse:
    texte: str
    sources: list = field(default_factory=list)


_client = None


def client():
    global _client
    if not settings.GEMINI_API_KEY:
        return None
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def embed(textes, tache="RETRIEVAL_DOCUMENT"):
    """Renvoie un vecteur par texte, ou None sans clé."""
    c = client()
    if c is None:
        return None
    from google.genai import types

    res = c.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents=list(textes),
        config=types.EmbedContentConfig(task_type=tache, output_dimensionality=settings.GEMINI_EMBED_DIM),
    )
    return [e.values for e in res.embeddings]


def repondre(matiere: Matiere, question: str, historique, extraits, guide: bool) -> Reponse:
    """Génère la réponse de Learny.

    historique : liste de (question, réponse) des derniers échanges, du plus ancien au plus récent.
    extraits : passages de cours retrouvés (CourseChunk), déjà triés par pertinence.
    """
    sources = [{"source": e.source, "page": e.page} for e in extraits]
    c = client()
    if c is None:
        return Reponse(texte=_demo(matiere, question), sources=sources)

    from google.genai import types

    contents = []
    for q, r in list(historique)[-HISTORIQUE_MAX:]:
        contents.append(types.Content(role="user", parts=[types.Part(text=q)]))
        contents.append(types.Content(role="model", parts=[types.Part(text=r)]))

    prompt = question
    if extraits:
        bloc = "\n\n".join(f"[{i}] {e.source}, page {e.page} :\n{e.texte}" for i, e in enumerate(extraits, 1))
        prompt = (
            f"Extraits du cours officiel (cite-les avec leur numéro entre crochets, par exemple [1]) :\n\n{bloc}"
            f"\n\nQuestion de l'élève : {question}"
        )
    contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

    try:
        res = c.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=consigne_systeme(matiere, guide),
                temperature=0.4,
                max_output_tokens=1200,
            ),
        )
    except Exception as exc:  # le SDK lève des erreurs variées (réseau, 429, 5xx)
        log.warning("Gemini indisponible : %s", exc)
        raise LearnyIndisponible from exc

    texte = (res.text or "").strip()
    if not texte:
        raise LearnyIndisponible("réponse vide")
    return Reponse(texte=texte, sources=sources)


def titre_depuis(question: str) -> str:
    """Titre court de la discussion, sans appel au modèle (économie de quota)."""
    t = " ".join(question.split())
    return t if len(t) <= 60 else t[:57].rsplit(" ", 1)[0] + "…"


def _demo(matiere: Matiere, question: str) -> str:
    return (
        f"**Mode démonstration.** Learny n'est pas encore relié à Gemini sur ce serveur "
        f"(variable `GEMINI_API_KEY` vide).\n\n"
        f"Avec la clé, je répondrais ici à ta question de {matiere.nom.lower()}, étape par étape, "
        f"en citant la page du cours utilisée."
    )
