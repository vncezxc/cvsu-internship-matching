from django import template
register = template.Library()

@register.filter
def file_ext(value, ext):
    """Return True if value (filename) ends with ext (case-insensitive). Usage: {{ file|file_ext:'.pdf' }}"""
    if not value:
        return False
    return str(value).lower().endswith(ext.lower())
