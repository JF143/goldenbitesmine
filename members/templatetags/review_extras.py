from django import template

register = template.Library()

@register.filter
def get_review(review_lookup, key):
    return review_lookup.get(key) 