from .models import GlobalSettings


def currency_settings(request):
    settings = GlobalSettings.get_solo()
    return {
        'global_settings': settings,
        'currency_code': settings.currency_code,
        'usd_to_khr_rate': settings.usd_to_khr_rate,
    }
