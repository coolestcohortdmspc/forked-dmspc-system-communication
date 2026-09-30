import json, os
from ngRadar_Website.enums import Message, UIEvent
from ngRadar_Website.models.models import ObservatoryEvent
from ngRadar_Website.utils import (
    MAX_BYTES,
    consume,
    produce,
)
from django.db import transaction
from django.core.management.base import BaseCommand


def process_msg(
    msg,
    producer_topic,
    producer_config,
):
    try:
        incoming_key = msg.key().decode("utf-8")

        # Do not consume our own
        # database acknowledgements when we produce back into dsoc_notif.
        if incoming_key == str(Message.DB_COMMITTED.value):
            return True
        if incoming_key == UIEvent.IMAGE_CHANGED:
            return True
        

        topic = msg.topic()

        payload = json.loads(msg.value().decode("utf-8"))


        with transaction.atomic():
            event, created = record_obs_event(
                payload
            )

           # Capture values needed for the UI event
            event_uuid = str(event.uuid)
            image_key = event.image_key
            rcvr_station = event.rcvr_station

            transaction.on_commit(
                lambda: publish_db_committed(
                    topic=topic,
                    producer_config=producer_config,
                    payload=payload,
                )
            )
            
            # Only publish image_changed SSE event type when
            # this event actually has an image.
            if image_key:
                transaction.on_commit(
                    lambda: publish_ui_event(
                        topic=topic,
                        producer_config=producer_config,
                        event_type=UIEvent.IMAGE_CHANGED,
                        key=event_uuid,
                        data={
                            "event_uuid": event_uuid,
                            "rcvr_station": rcvr_station,
                        },
                    )
                )

        return True


    except json.JSONDecodeError as error:
        print(
            "DB consumer received "
            "invalid JSON: "
            f"{error}"
        )
        return False

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(
            "DB consumer received "
            "invalid payload: "
            f"{error}"
        )
        return False

    except Exception as error:
        print(
            "DB consumer failed to "
            "process message: "
            f"{error}"
        )
        return False


def record_obs_event(payload):
    obs_event, created = (
        ObservatoryEvent.objects.update_or_create(
            uuid=payload["event_uuid"],
            defaults={
                "gbt_uuid": payload.get("gbt_uuid"),
                "transfer_uuid": payload.get("transfer_uuid"),
                "object_id": payload.get("object_id"),
                "target": payload.get("target"),
                "waveform_requester": payload.get("waveform_requester"),
                "tx_waveform": payload.get("tx_waveform"),
                "rec_waveform": payload.get("rec_waveform"),
                "product_type": payload.get("product_type"),
                "product_id": payload.get("product_id"),
                "station": payload.get("station"),
                "event_time": payload["event_time"],
                "xmit_station": payload.get("xmit_station"),
                "rcvr_station": payload.get("rcvr_station"),
                "image_key": payload.get("image_key"),
                "num_bytes": payload.get("num_bytes"),
                "latency_ms": payload.get("latency_ms", 0.0,),
                "status": payload.get("status"),
                "message": payload.get("message","",),
            },
        )
    )

    return obs_event, created


def publish_db_committed(
    *,
    topic,
    producer_config,
    payload,
):
    notification = {
        "event_type": "db_committed",
        "data": payload,
    }

    produce(
        topic,
        producer_config,
        str(
            Message.DB_COMMITTED.value
        ),
        json.dumps(notification),
    )


def publish_ui_event(
    *,
    topic,
    producer_config,
    event_type,
    key,
    data,
):
    notification = {
        "event_type": event_type,
        "key": key,
        "data": data,
    }

    produce(
        topic,
        producer_config,
        event_type,
        json.dumps(notification),
    )






class Command(BaseCommand):
    help = "Consume Kafka domain events and persist them to ObservatoryEvent."

    def handle(self, *args, **options):
        bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"]

        topics = [
            topic.strip()
            for topic in os.getenv(
                "DB_KAFKA_TOPICS",
                (
                    "GBT_notif,"
                    "VLBA_notif,"
                    "DSOC_notif"
                ),
            ).split(",")
            if topic.strip()
        ]

        consumer_config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": os.getenv(
                "DB_KAFKA_GROUP_ID",
                "ngradar-db",
            ),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }

        producer_config = {
            "bootstrap.servers": bootstrap_servers,
            "message.max.bytes": MAX_BYTES,
            "message.timeout.ms": 2000,
            "client.id":
                "db-consumer-producer",
        }

        self.stdout.write(
            self.style.SUCCESS(
                "DB consumer starting\n"
                f"  brokers: {bootstrap_servers}\n"
                f"  topics: {topics}\n"
                "  group: ngradar-db"
            )
        )

        consume(
            topics,
            consumer_config,
            process_msg,
            producer_config=producer_config,
            manual_commit=True,
        )