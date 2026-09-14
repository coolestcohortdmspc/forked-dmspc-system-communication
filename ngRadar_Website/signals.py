from django.db.models.signals import post_save
from django.dispatch import receiver
from ngRadar_Website.enums import Stations
from django.utils import timezone
from django.utils import timezone
from ngRadar_Website.models.models import (
    gbtEvent,
    dsocEvent,
    ETransferEvent,
    ETransferEvent,
    ObservatoryEvent,
)
from django.template.loader import render_to_string
from ngRadar_Website.views.views import get_obs_events 
import os
from ngRadar_Website.utils import produce, MAX_BYTES

@receiver(post_save, sender=gbtEvent)
def create_obsevent_from_gbt(sender, instance, created, **kwargs):
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
        rcvr_station=Stations.HN,
        status=None,
        message=None,
    )


@receiver(post_save, sender=dsocEvent)
def create_obsevent_from_dsoc(sender, instance, created, **kwargs):
    if not created:
        return

    ObservatoryEvent.objects.create(
        object_id=instance.object_id,
        target=instance.target,
        tx_waveform=None,
        rec_waveform=None,
        image_key=instance.image_key,
        num_bytes=instance.num_bytes,
        event_time=instance.event_time,
        latency_ms=instance.latency_ms,
        station=Stations.DSOC,
        xmit_station=instance.xmit_station,
        rcvr_station=instance.rcvr_station,
        transfer_uuid=instance.transfer_uuid,
        status=None,
        message=None,
    )



@receiver(post_save, sender=ETransferEvent)
def create_obsevent_from_etransfer(sender, instance, created, **kwargs):
    if not created:
        return

    ObservatoryEvent.objects.create(
        object_id=instance.object_id,
        target=instance.target,
        tx_waveform=None,
        rec_waveform=None,
        image_key=None,
        num_bytes=instance.num_bytes,
        event_time=instance.event_time,
        latency_ms=instance.latency_ms,
        station=instance.station,
        xmit_station=Stations.GBT,
        rcvr_station=Stations.HN,
        transfer_uuid=instance.transfer_uuid,
        status=instance.status,
        message=instance.message,
    )

@receiver(post_save, sender=ObservatoryEvent)
def notify_obsevent_update(sender, instance, created, **kwargs):
    if not created:
        return

    html = render_to_string("ngRadar_Website/partials/status_partial.html", get_obs_events())

    # init topic and config
    topic = "obs_status_update"
    config = {
        "bootstrap.servers": os.environ.get("BOOTSTRAP_SERVERS", "kafka-broker:29092"),
        "message.max.bytes": MAX_BYTES, 
        "message.timeout.ms": 2000,
        "client.id": "status-notify-producer",
    }

    # use constant key   
    key = "status_update"

    # avoid recursive signal triggering by disconnecting the signal before producing the message
    post_save.disconnect(notify_obsevent_update, sender=ObservatoryEvent)

    try:
        produce(topic, config, key, html)
    finally:
        post_save.connect(notify_obsevent_update, sender=ObservatoryEvent)