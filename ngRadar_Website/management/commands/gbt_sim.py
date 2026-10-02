import json
import time
import uuid
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.db.backends.utils import logger

from ngRadar_Website.enums import (
    Stations,
    Status,
    Message,
)
from ngRadar_Website.utils import (
    bootstrap,
    consume,
    latency_calc,
    send_kafka_message,
)
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

resource = Resource.create(
    {
        "service.name": "gbt",
    }
)

metric_exporter = OTLPMetricExporter(
    endpoint="http://otel-collector:4317",
    insecure=True,
)

metric_reader = PeriodicExportingMetricReader(
    metric_exporter,
    export_interval_millis=5000,
)

provider = MeterProvider(
    resource=resource,
    metric_readers=[metric_reader],
)

metrics.set_meter_provider(provider)

meter = metrics.get_meter("gbt")

messages_processed = meter.create_counter(
    "gbt_messages_processed_total",
    description="Number of messages processed by the GBT simulator",
)

def process_msg(
    msg,
    producer_topic,
    producer_config,
):
    incoming_key = msg.key().decode("utf-8")

    # GBT only reacts to waveform requests
    # submitted by the UI.
    if (incoming_key!= str(Message.UI_EVENT.value)):
        return True

    messages_processed.add(1)

    payload = json.loads(msg.value().decode("utf-8"))

    waveform = payload["tx_waveform"]
    waveform_requester = payload["waveform_requester"]

    ui_event_time = (
        datetime.fromisoformat(
            payload["event_time"]
        )
    )

    print(
        "GBT received waveform request: "
        f"{waveform}"
    )

    # One ID correlates both the OFF and ON
    # events with the same observation.
    gbt_uuid = uuid.uuid4()

    # -------------------------------------------------
    # 1. Turn transmitter OFF
    # -------------------------------------------------
    print(
        "GBT transmitter OFF"
    )

    send_kafka_message(
        message_type=(Message.STATUS_UPDATE),
        producer_topic=producer_topic,
        producer_config=producer_config,
        waveform_requester=waveform_requester,
        station=Stations.GBT,
        gbt_uuid=gbt_uuid,
        object_id="30104",
        target="Moretus",
        tx_waveform="TX_OFF",
        rec_waveform="TX_OFF",
        status=None,
        xmit_station=Stations.GBT,
        rcvr_station=None,
        latency_ms=latency_calc(
            ui_event_time,
            Stations.GBT,
        ),
        message=(
            "GBT transmitter turned OFF "
            "for waveform change."
        ),
    )

    # -------------------------------------------------
    # 2. Remain OFF for five seconds
    # -------------------------------------------------

    #time.sleep(5)

    # -------------------------------------------------
    # 3. Turn transmitter ON with new waveform
    # -------------------------------------------------
    gbt_event_time = datetime.now(timezone.utc)

    print(
        "GBT transmitter ON with "
        f"waveform {waveform}"
    )

    event_uuid = send_kafka_message(
        message_type=(Message.GBT_TX),
        producer_topic=producer_topic,
        producer_config=producer_config,
        waveform_requester=waveform_requester,
        station=Stations.GBT,
        gbt_uuid=gbt_uuid,
        gbt_event_time=(gbt_event_time.isoformat()),
        object_id="30104",
        target="Moretus",
        tx_waveform=waveform,
        rec_waveform=waveform,
        status=None,
        xmit_station=Stations.GBT,
        rcvr_station=None,
        latency_ms=latency_calc(
            ui_event_time,
            Stations.GBT,
        ),
        message=(
            "GBT transmitting waveform "
            f"{waveform}."
        ),
    )

    print(
        "GBT published TX event "
        f"{event_uuid}"
    )

    return True


class Command(BaseCommand):
    help = "Runs the GBT simulator"

    def handle(
        self,
        *args,
        **options,
    ):
        print("Starting GBT simulator")

        (
            producer_topic,
            producer_config,
            consumer_topic,
            consumer_config,
        ) = bootstrap(Stations.GBT)

        consume(
            consumer_topic,
            consumer_config,
            process_msg,
            producer_topic=producer_topic,
            producer_config=producer_config,
            manual_commit=True,
        )