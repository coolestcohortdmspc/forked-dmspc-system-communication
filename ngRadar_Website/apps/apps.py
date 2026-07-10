from django.apps import AppConfig
from django.db.models.signals import post_save

class NgradarWebAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'ngRadar_Website'

    def ready(self):
        from ngRadar_Website.models.models import dsocEvent, gbtEvent
        from ngRadar_Website.signals import create_observatory_from_dsoc, create_observatory_from_gbt
        
        post_save.connect(create_observatory_from_gbt, sender=gbtEvent, weak=False)
        post_save.connect(create_observatory_from_dsoc, sender=dsocEvent, weak=False)
