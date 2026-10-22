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
PHOTO_MAX = 8 * 1024 * 1024  # le téléphone réduit la photo avant l'envoi : ceci ne sert que de garde-fou
ILLISIBLE = "ILLISIBLE"


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


def type_image(debut: bytes):
    """Type MIME d'une photo d'après ses premiers octets, ou None si Gemini ne sait pas la lire."""
    if debut.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if debut.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if debut[:4] == b"RIFF" and debut[8:12] == b"WEBP":
        return "image/webp"
    if debut[4:8] == b"ftyp" and debut[8:12] in {b"heic", b"heix", b"mif1", b"msf1"}:
        return "image/heic"
    return None


def lire_enonce(matiere: Matiere, image: bytes, mime: str) -> str:
    """Recopie l'énoncé d'un exercice photographié. Chaîne vide si la photo est illisible.

    L'élève relit et corrige ce texte avant de l'envoyer : la question enregistrée reste du texte,
    et la photo n'est gardée nulle part.
    """
    c = client()
    if c is None:
        return (
            "Mode démonstration : sans clé Gemini, Learny ne lit pas la photo. "
            "Écris ici l'énoncé de ton exercice, puis envoie-le."
        )

    from google.genai import types

    consigne = (
        f"Voici la photo d'un exercice de {matiere.nom.lower()} de 3e (cahier, livre ou tableau). "
        "Recopie fidèlement l'énoncé, sans le résoudre et sans rien ajouter. Garde la numérotation des questions. "
        "Écris les formules en texte lisible (AB = 6 cm, x² + 3x = 0), sans LaTeX. "
        "S'il y a une figure, décris-la en une phrase entre crochets avec ses valeurs. "
        f"Si tu ne peux pas lire l'énoncé, réponds seulement {ILLISIBLE}."
    )
    try:
        res = c.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=image, mime_type=mime), consigne],
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=2048),
        )
    except Exception as exc:
        log.warning("Gemini indisponible (photo) : %s", exc)
        raise LearnyIndisponible from exc

    texte = (res.text or "").strip()
    if texte.rstrip(" .").upper() == ILLISIBLE:
        return ""
    return texte[:2000]


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
