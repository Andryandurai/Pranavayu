from django import template
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

register = template.Library()


@register.filter
def evidence_markdown(value):
    # Escape source/client HTML. MarkdownIt's URL validator rejects javascript,
    # vbscript, file and data URLs; no raw HTML, linkify or custom unsafe plugins.
    renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
    return mark_safe(renderer.render(str(value)))
