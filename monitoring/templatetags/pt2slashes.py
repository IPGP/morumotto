from django import template

register = template.Library()

# add a custom filter to django templates which replaces dots with slashes
@register.filter
def pt2slashes(value):
    return value.replace(".","/")
