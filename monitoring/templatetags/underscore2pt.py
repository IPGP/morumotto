from django import template

register = template.Library()

# add a custom filter to django templates which replaces dots with underscore

@register.filter
def underscore2pt(value):
    return value.replace("_",".")
