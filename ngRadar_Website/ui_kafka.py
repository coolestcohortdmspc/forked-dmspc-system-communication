import json
import logging
import os
import threading
from ngRadar_Website.enums import Message
from confluent_kafka import Consumer, KafkaError

from .sse import sse_broker


logger = logging.getLogger(__name__)

_consumer_started = False
_consumer_lock = threading.Lock()


TOPIC_TO_UI_EVENT = {
    "GBT_notif": "gbt_changed",
    "VLBA_notif": "vlba_changed",
    "DSOC_notif": "dsoc_changed",
}


def consume_ui_events():
    topics = os.getenv(
        "UI_KAFKA_TOPICS",
        "GBT_notif,VLBA_notif,DSOC_notif",
    ).split(",")

    topics = [
        topic.strip()
        for topic in topics
        if topic.strip()
    ]

    consumer_config = {
        "bootstrap.servers": os.getenv(
            "BOOTSTRAP_SERVER",
            "kafka-broker:29092",
        ),
        "group.id": os.getenv(
            "UI_KAFKA_GROUP_ID",
            "ngradar-ui-sse",
        ),
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    }

    consumer = Consumer(consumer_config)

    consumer.subscribe(topics)

    logger.info(
        "UI Kafka consumer subscribed to %s",
        topics,
    )

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if (
                    msg.error().code()
                    == KafkaError._PARTITION_EOF
                ):
                    continue

                logger.error(
                    "UI Kafka consumer error: %s",
                    msg.error(),
                )
                continue

            incoming_key = int(
                msg.key().decode("utf-8")
            )

            topic = msg.topic()

            try:
                payload = json.loads(
                    msg.value().decode("utf-8")
                )

            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                logger.exception(
                    "Invalid Kafka message"
                )
                continue


            # =====================================================
            # DATABASE COMMIT NOTIFICATION
            #
            # This event means ObservatoryEvent has already been
            # committed and the Dashboard may safely refresh.
            # =====================================================

            if (
                incoming_key
                == Message.DB_COMMITTED.value
            ):
                committed_payload = payload.get(
                    "data",
                    {},
                )

                logger.info(
                    "Publishing "
                    "observatory_event_created "
                    "for event %s",
                    committed_payload.get(
                        "event_uuid"
                    ),
                )

                sse_broker.publish(
                    {
                        "type": (
                            "observatory_event_created"
                        ),
                        "data": committed_payload,
                    }
                )

                continue


            # =====================================================
            # LIVE DOMAIN EVENT
            #
            # These events update Home immediately without waiting
            # for the database consumer.
            # =====================================================

            event_type = (
                TOPIC_TO_UI_EVENT.get(
                    topic
                )
            )

            if event_type is None:
                logger.warning(
                    "No UI event mapping "
                    "for topic %s",
                    topic,
                )
                continue


            logger.info(
                "Publishing live UI event "
                "%s for event %s",
                event_type,
                payload.get(
                    "event_uuid"
                ),
            )

            sse_broker.publish(
                {
                    "type": event_type,
                    "data": payload,
                }
            )

    finally:
        consumer.close()


def start_ui_kafka_consumer():
    global _consumer_started

    with _consumer_lock:
        if _consumer_started:
            return

        _consumer_started = True

    thread = threading.Thread(
        target=consume_ui_events,
        name="ui-kafka-consumer",
        daemon=True,
    )

    thread.start()

    logger.info(
        "UI Kafka consumer thread started"
    )