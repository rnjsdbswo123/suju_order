# users/templatetags/auth_tags.py
from django import template
from users.permissions import is_in_role as is_in_role_func

register = template.Library()

@register.simple_tag
def is_in_role(user, role_name):
    return is_in_role_func(user, role_name)
