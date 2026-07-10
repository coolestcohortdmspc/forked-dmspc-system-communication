from django.db.models.signals import post_save
from django.dispatch import receiver
from ngRadar_Website.enums import Stations

from ngRadar_Website.models.models import (
    gbtEvent,
    dsocEvent,
    ObservatoryEvent,
)

@receiver(post_save, sender=gbtEvent)
def create_observatory_from_gbt(sender, instance, created, **kwargs):
    if not created:
        return

    ObservatoryEvent.objects.create(
        object_id=instance.object_id,
        target=instance.target,
        tx_waveform=instance.tx_waveform,   # Included for GBT
        rec_waveform=instance.rec_waveform, # Included for GBT
        image_key=None,                     # GBT records do not have images
        num_bytes=None,                     # GBT records do not have images
        event_time=instance.event_time,
        latency_ms=instance.latency_ms,
        station=Stations.GBT,      
        xmit_station=Stations.GBT, 
        rcvr_station=Stations.GBT,
    )


@receiver(post_save, sender=dsocEvent)
def create_observatory_from_dsoc(sender, instance, created, **kwargs):
    if not created:
        return

    ObservatoryEvent.objects.create(
        object_id=instance.object_id,
        target=instance.target,
        tx_waveform=None,                   # DSOC records do not have waveforms
        rec_waveform=None,                  # DSOC records do not have waveforms
        image_key=instance.image_key,       # Included for DSOC
        num_bytes=instance.num_bytes,       # Included for DSOC
        event_time=instance.event_time,
        latency_ms=instance.latency_ms,
        station=Stations.DSOC,      
        xmit_station=Stations.DSOC, 
        rcvr_station=Stations.DSOC,
    )
