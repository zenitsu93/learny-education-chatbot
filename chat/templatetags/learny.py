from django import template
from django.utils.safestring import mark_safe

from chat.rendering import markdown_sur

register = template.Library()


@register.filter
def markdown(texte):
    """Markdown d'une réponse → HTML nettoyé (voir chat.rendering)."""
    return mark_safe(markdown_sur(texte))
