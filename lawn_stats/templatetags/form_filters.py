# templatetags/form_filters.py

from django import template

register = template.Library()


@register.filter
def get_field(form, field_name):
    return form[field_name]


@register.filter
def get_ignore_field(form, field_name):
    return form[f"ignore_{field_name}"]


@register.filter
def get_field_id(field):
    return field.id_for_label
