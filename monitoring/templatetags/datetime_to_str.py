from django import template
import datetime
register = template.Library()


@register.filter('datetime_to_str')
def convert_datetime_to_string(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")
