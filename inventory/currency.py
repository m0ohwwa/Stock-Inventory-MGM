from decimal import Decimal, ROUND_HALF_UP


USD_QUANTUM = Decimal('0.01')
KHR_QUANTUM = Decimal('1')


def to_decimal(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def from_usd(amount, currency_code, usd_to_khr_rate):
    amount = to_decimal(amount)
    if currency_code == 'KHR':
        amount *= to_decimal(usd_to_khr_rate)
        return amount.quantize(KHR_QUANTUM, rounding=ROUND_HALF_UP)
    return amount.quantize(USD_QUANTUM, rounding=ROUND_HALF_UP)


def to_usd(amount, currency_code, usd_to_khr_rate):
    amount = to_decimal(amount)
    if currency_code == 'KHR':
        amount /= to_decimal(usd_to_khr_rate)
    return amount.quantize(USD_QUANTUM, rounding=ROUND_HALF_UP)


def format_currency(amount, currency_code, usd_to_khr_rate):
    converted = from_usd(amount, currency_code, usd_to_khr_rate)
    if currency_code == 'KHR':
        return f"៛{converted:,.0f}"
    return f"${converted:,.2f}"
