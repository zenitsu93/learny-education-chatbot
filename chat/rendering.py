"""Markdown des réponses → HTML sûr.

Le texte vient d'un modèle : il est converti côté serveur puis nettoyé par nh3,
qui ne garde qu'une liste fermée de balises. Aucun script ni attribut d'événement ne passe.
"""
import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable("table")

BALISES = {
    "p", "br", "strong", "em", "b", "i", "code", "pre", "blockquote",
    "ul", "ol", "li", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td", "hr", "a", "sup", "sub",
}
ATTRIBUTS = {"a": {"href", "title"}, "th": {"scope"}, "ol": {"start"}}


def markdown_sur(texte: str) -> str:
    html = _md.render(texte or "")
    # Les titres de niveau 1 et 2 écraseraient la hiérarchie de la page.
    for n in ("1", "2"):
        html = html.replace(f"<h{n}>", "<h3>").replace(f"</h{n}>", "</h3>")
    return nh3.clean(
        html,
        tags=BALISES,
        attributes=ATTRIBUTS,
        url_schemes={"https", "http"},
        link_rel="noopener noreferrer nofollow",
    )
