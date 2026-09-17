from datetime import datetime

import io
import json
import os
import time
import uuid

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from django.core.management.base import BaseCommand

from confluent_kafka import (
    Consumer,
    KafkaError,
    Producer,
)

from ngRadar_Website.enums import (
    Stations,
    Status,
    Message,
)

from ngRadar_Website.utils import (
    bootstrap,
    consumer_group_has_members,
    send_kafka_message,
    write_transfer_progress,
)


"""
Progress Tracking Worker Simulator

This simulator:

- Consumes VLBA workflow events from Kafka.
- Checks DSOC storage availability.
- Monitors the incoming e-transfer.
- Verifies the completed transfer.
- Generates the simulated DDM product.
- Stores the DDM image in SeaweedFS.
- Sends DSOC state/workflow events to Kafka.

This simulator does NOT write directly to:

- gbtEvent
- dsocEvent
- ETransferEvent
- ObservatoryEvent

The db_consumer is solely responsible for persisting
Kafka events to ObservatoryEvent.
"""


STALL_TIMEOUT_SECONDS = 15

MAX_STORAGE_RETRIES = 15

volume_folder = Path("/dsoc/incoming")

# =============================================================
# process_msg takes message from VLBA indicating a new transfer has started and adds it to the list of active transfers.
# =============================================================

def process_msg(
    msg,
    active_transfers,
    producer_topic,
    producer_config,
):
    incoming_key = int(
        msg.key().decode("utf-8")
    )

    payload = json.loads(
        msg.value().decode("utf-8")
    )

    if incoming_key == Message.VLBA_TRANSFERRING.value:
        # Add the transfer to the list of active transfers
        # add two fields in the payload for last_progress_at and received bytes to track when the last progress was made for this transfer
        payload["last_progress_at"] = time.monotonic()
        payload["last_received_bytes"] = 0
        active_transfers.append(payload)

    else:
        print(
            "Invalid Kafka Message Key!"
        )

    return True



# =============================================================
# NEW CONSUME FUNCTION
# =============================================================

def progress_consume(
    topic,
    config,
    producer_topic=None,
    producer_config=None,
    manual_commit=False,
):
    """
    Consume Kafka messages and pass them to process_msg().

    If manual_commit=True, a message is committed only when
    process_msg() returns True.
    """

    if manual_commit:
        config = {
            **config,
            "enable.auto.commit": False,
        }

    consumer = Consumer(
        config
    )

    consumer.subscribe(
        topic
    )

    active_transfers = []

    try:
        while True:
            msg = consumer.poll(
                1.0
            )

            if msg is None:

                # check progress for current list of active transfers
                # for transfer in active_transfers:
                completed_transfers = []

                for transfer in active_transfers:

                    if get_transfer_progress(transfer, producer_topic, producer_config): # if transfer is complete, add to completed_transfers list
                        completed_transfers.append(transfer)

                # remove completed transfers from active_transfers list
                for transfer in completed_transfers:
                    active_transfers.remove(transfer)


                #     check_transfer_progress(transfer)



                    # if transfer is complete, remove from active transfer list and send kafka message to DSOC that transfer### data is ready for processing

                # continue after checking instantaneous progress for all active transfers



                continue

            if msg.error():
                error = msg.error()

                if (
                    error.code()
                    == KafkaError._PARTITION_EOF
                ):
                    print(
                        "Consumer reached "
                        "partition EOF."
                    )
                    continue

                print(
                    "Consumer error:",
                    error,
                )

                break

            succeeded = process_msg(
                msg,
                active_transfers,
                producer_topic,
                producer_config,
            )

            if (
                manual_commit
                and succeeded
            ):
                consumer.commit(
                    msg
                )

    finally:
        consumer.close()



# =============================================================
# E-TRANSFER PROGRESS
# =============================================================

# give the function dsoc/incoming path and append the filename from payload

def get_transfer_progress(payload, producer_topic, producer_config):
    """
    Track bytes arriving from VLBA.

    This no longer checks ETransferEvent to decide whether the
    transfer should continue. Kafka/workflow state and the actual
    incoming file are now the source of truth.
    """

    filename = payload["filename"]
    transfer_uuid = payload["transfer_uuid"]
    station = payload["station"]
    last_progress_at = payload["last_progress_at"]
    last_received_bytes = payload["last_received_bytes"]
    tracked_file = volume_folder / filename

    total_bytes = int(payload["num_bytes"])

    if total_bytes <= 0:
        raise ValueError(
            "Expected transfer size must "
            "be greater than zero."
        )

    if tracked_file.exists():
        current_bytes = (tracked_file.stat().st_size)

        if current_bytes > last_received_bytes:
            last_progress_at = time.monotonic()

        last_received_bytes = current_bytes

        percent = (last_received_bytes / total_bytes  * 100)
        print(f"Transfer of <{transfer_uuid}.bin> is {percent:.2f}% complete. ({last_received_bytes}/{total_bytes} bytes)")

        if last_received_bytes >= total_bytes:
            print(
                "Transfer of "
                f"<{transfer_uuid}.bin> "
                "COMPLETE."
            )

            del payload["last_progress_at"]
            del payload["last_received_bytes"]

            send_kafka_message(
                producer_topic=producer_topic,
                producer_config=producer_config,
                message_type=Message.PROGRESS_COMPLETE,
                transfer_uuid=transfer_uuid,
                gbt_uuid=payload["gbt_uuid"],
                gbt_event_time=payload["gbt_event_time"],
                station=Stations(payload["station"]),
                status=Status.TRANSFERRED,
                object_id=payload["object_id"],
                target=payload["target"],
                tx_waveform=payload["tx_waveform"],
                rec_waveform=payload["rec_waveform"],
                num_bytes=payload["num_bytes"],
                filename=payload["filename"],
                xmit_station=payload["xmit_station"],
                rcvr_station=Stations.DSOC,
                message=(
                    f"VLBA-{Stations(payload['station']).name} completed "
                    "sending the data file to DSOC "
                    "via e-transfer."
                ),

            )

            # VLBA already sends a kafka message to the UI when etc_send is complete. We need to notify DSOC that the transfer is complete and ready for processing but don't want it to look like duplicates on the UI.

            return True


        if time.monotonic() - last_progress_at > STALL_TIMEOUT_SECONDS:
            vlba_consumer_group = (
                f"{vlba_station.name.lower()}"
                "-consumer-group"
            )

            if consumer_group_has_members(vlba_consumer_group):
                # VLBA is alive. The transfer may
                # simply be slow.
                last_progress_at = time.monotonic()

            else:
                vlba_station = Stations(station)
                raise RuntimeError(
                    f"{vlba_station.label} "
                    "went offline "
                    "mid-transfer. "
                    "Transfer interrupted."
                )
        payload["last_progress_at"] = last_progress_at
        payload["last_received_bytes"] = last_received_bytes

    else:
        print(
            f"Transfer file <{filename}> "
            "not found in DSOC incoming folder."
        )

    return False





class Command(BaseCommand):
    help = "Runs the e-transfer progress tracking simulator"

    def handle(
        self,
        *args,
        **options,
    ):
        print(
            "Starting e-transfer progress tracking simulator"
        )

        (
            producer_topic,
            producer_config,
            consumer_topic,
            consumer_config,
        ) = bootstrap(
            Stations.PTW
        )

        progress_consume(consumer_topic, consumer_config, producer_topic=producer_topic, producer_config=producer_config)