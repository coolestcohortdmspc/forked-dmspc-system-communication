from datetime import datetime, timezone
import os, time
from django.core.management.base import BaseCommand
from confluent_kafka import Producer
from confluent_kafka import Consumer
from ngRadar_Website.enums import Stations
from ngRadar_Website.models.models import uiEvent
from ngRadar_Website.models.models import gbtEvent
# from dotenv import find_dotenv
from pathlib import Path
from ngRadar_Website.utils import latency_calc, bootstrap, consume


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
    payload["latency_ms"] = latency_calc(payload["event_time"], event_time)


def latency_calc(gbt_event_time, ui_event_time):
    # calculates the latency of the message from the time it was sent to the time it was received
    # returns latency in milliseconds
    if ui_event_time == -1:
        return 0
    latency = gbt_event_time - ui_event_time
    latency_ms = latency.total_seconds() * 1000 - 5000
    return latency_ms


def generate_payload(ui_event_uuid):
    ui_event = uiEvent.objects.get(uuid=ui_event_uuid)

    set_payload_dict(ui_event.selected_waveform, ui_event.event_time)


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
    time.sleep(5)


def publish_to_db():
    gbt_event = gbtEvent.objects.create(**payload)

    return gbt_event.uuid


def produce(topic, config, key, value):
    # creates a new producer instance
    producer = Producer(config)

    # producing a message to the specified topic 
    producer.produce(topic, key=key, value=value)
    print(f"Produced message to topic {topic} with key {key}.")

    # send any outstanding or buffered messages to the Kafka broker
    producer.flush()


def process_msg(msg, producer_topic, producer_config):
    ui_uuid = msg.key().decode("utf-8")  # this is the uuid of the ui_event
    notif = msg.value().decode("utf-8")

    # turn off the transmitter for 5 seconds
    turn_off_transmitter()

    # fill in the values to be published to the db
    generate_payload(ui_uuid)

    # publish new transmission to the db
    gbt_uuid = publish_to_db()

    key, value = f"{gbt_uuid}", "GBT transmitting"

    # produce this new message, lets DSOC know to produce image(s)
    produce(producer_topic, producer_config, key, value)


class Command(BaseCommand):
    help = "Runs the GBT simulator"

    def handle(self, *args, **options):
        print("Starting GBT simulator")

        producer_topic, producer_config, consumer_topic, consumer_config = bootstrap(Stations.GBT)

        # generate a dummy data payload, publish this data to the db, produce a message with this payload, then start consuming
        set_payload_dict('W48', -1)
        gbt_uuid = publish_to_db()
        key, value = f"{gbt_uuid}", "GBT transmitting"
        produce(producer_topic, producer_config, key, value)
        consume(consumer_topic, consumer_config, process_msg, producer_topic=producer_topic, producer_config=producer_config)