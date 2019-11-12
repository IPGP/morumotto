from django import template

register = template.Library()

# add a custom filter to django templates which replaces dots with underscore

@register.filter
def pt2underscore(value):
    return value.replace(".","_")
