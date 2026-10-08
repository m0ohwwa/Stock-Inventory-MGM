from django import template

from inventory.currency import format_currency


register = template.Library()


@register.simple_tag(takes_context=True)
def currency(context, amount):
    return format_currency(
        amount,
        context.get('currency_code', 'USD'),
        context.get('usd_to_khr_rate', 4000),
    )
