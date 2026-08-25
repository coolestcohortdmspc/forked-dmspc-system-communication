from datetime import datetime, timezone
import json
from django.core.management.base import BaseCommand
from ngRadar_Website.enums import Stations, Message
from ngRadar_Website.models.models import uiEvent
from ngRadar_Website.models.models import gbtEvent
from ngRadar_Website.utils import latency_calc, bootstrap, consume, produce


# payload that will be inserted in the gbtEvent db table
payload = {
    "object_id": None, 
    "target": None, 
    "tx_waveform": None, 
    "rec_waveform": None, 
    "event_time": None, 
    "latency_ms": None,
}

def set_payload_dict(waveform, event_time):
    payload["object_id"] = '30104'
    payload["target"] = 'Moretus'
    payload["tx_waveform"] = waveform
    payload["rec_waveform"] = waveform
    payload["event_time"] = datetime.now(timezone.utc)
    payload["latency_ms"] = latency_calc(event_time, Stations.GBT)

    return payload


def generate_payload(ui_event_uuid):
    ui_event = uiEvent.objects.get(uuid=ui_event_uuid)

    payload = set_payload_dict(ui_event.selected_waveform, ui_event.event_time)

    return payload


def turn_off_transmitter():
    gbtEvent.objects.create(
        **
        {
            "object_id": '30104', 
            "target": 'Moretus', 
            "tx_waveform": 'Tx_OFF', 
            "rec_waveform": 'Tx_OFF', 
            "event_time": datetime.now(timezone.utc), 
            "latency_ms": 0,
        }
    )
    # time.sleep(5)


def publish_gbtEvents(payload):
    gbt_event = gbtEvent.objects.create(**payload)

    return gbt_event.uuid


def process_msg(msg, producer_topic, producer_config):
    ui_uuid = msg.value().decode("utf-8")

    turn_off_transmitter()

    payload = generate_payload(ui_uuid)

    # publish new transmission to the db
    gbt_uuid = publish_gbtEvents(payload)

    kafka_payload = {
        "ui_uuid": str(ui_uuid),
        "gbt_uuid": str(gbt_uuid),
    }

    # key = str(Message.GBT_TX)

    produce(
        producer_topic,
        producer_config,
        str(Message.GBT_TX),
        json.dumps(kafka_payload),
    )


class Command(BaseCommand):
    help = "Runs the GBT simulator"

    def handle(self, *args, **options):
        print("Starting GBT simulator")

        producer_topic, producer_config, consumer_topic, consumer_config = bootstrap(
            Stations.GBT
        )

        consume(
            consumer_topic,
            consumer_config,
            process_msg,
            producer_topic=producer_topic,
            producer_config=producer_config,
        )