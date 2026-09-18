import json
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from confluent_kafka import (
    Consumer,
    KafkaError,
)
from ngRadar_Website.enums import (
    Stations,
    Status,
    Message,
)
from ngRadar_Website.utils import (
    bootstrap,
    consumer_group_has_members,
    produce,
    send_kafka_message,
)


"""
Progress Tracking Worker Simulator

This simulator:

- Consumes VLBA workflow events from Kafka.
- Monitors the incoming e-transfer in the dsoc/incoming volume folder.
- Notifes DSOC when a transfer is complete and ready for processing.

This simulator does NOT write directly to:

- gbtEvent
- dsocEvent
- ETransferEvent
- ObservatoryEvent

The db_consumer is solely responsible for persisting
Kafka events to ObservatoryEvent.
"""


STALL_TIMEOUT_SECONDS = 15

volume_folder = Path("/dsoc/incoming")

# Helper kafka produce function to UI consumer
def publish_progress(
    *,
    producer_config,
    payload,
):
    print(
        "[PROGRESS] Publishing:",
        payload,
    )

    success = produce(
        "progress_tracking",
        producer_config,
        str(Message.PROGRESS_UPDATE.value),
        json.dumps(payload),
    )

    print(
        "[PROGRESS] Kafka publish:",
        success,
    )

    return success

# =============================================================
# process_msg takes message from VLBA indicating a new transfer has started and adds it to the list of active transfers.
# =============================================================

def process_msg(
    msg,
    active_transfers,
    producer_topic,
    producer_config,
):
    incoming_key = int(msg.key().decode("utf-8"))
    payload = json.loads(msg.value().decode("utf-8"))

    if incoming_key != Message.VLBA_TRANSFERRING.value:
        return True
    else:
        payload["last_progress_at"] = time.monotonic()
        payload["last_received_bytes"] = 0
        active_transfers.append(payload)

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

    consumer = Consumer(config)
    consumer.subscribe(topic)
    active_transfers = []

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                # when there are no messages to consume, check the progress of all transfers in the active transfers list

                completed_transfers = []

                for transfer in active_transfers:

                    if get_transfer_progress(transfer, producer_topic, producer_config): # returns True if transfer is complete, then add to completed_transfers list
                        completed_transfers.append(transfer)

                # After loop is done, remove completed transfers from active_transfers list
                for transfer in completed_transfers:
                    active_transfers.remove(transfer)

                continue

            if msg.error():
                error = msg.error()

                if (error.code() == KafkaError._PARTITION_EOF):
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

            if (manual_commit and succeeded):
                consumer.commit(msg)

    finally:
        consumer.close()



# =============================================================
# E-TRANSFER PROGRESS
# =============================================================
# give the function dsoc/incoming path and append the filename from payload

def get_transfer_progress(
    payload,
    producer_topic,
    producer_config,
):
    """
    Check progress of an incoming e-transfer in the DSOC volume.
    """

    filename = payload["filename"]
    transfer_uuid = payload["transfer_uuid"]
    station = payload["station"]
    last_progress_at = payload["last_progress_at"]
    last_received_bytes = payload["last_received_bytes"]
    tracked_file = (volume_folder / filename)
    total_bytes = int(payload["num_bytes"])

    if total_bytes <= 0:
        raise ValueError(
            "Expected transfer size must "
            "be greater than zero."
        )

    # -----------------------------------------------------
    # File has not appeared at DSOC yet.
    # -----------------------------------------------------

    if not tracked_file.exists():
        return False

    current_bytes = (tracked_file.stat().st_size)

    # -----------------------------------------------------
    # New bytes arrived.
    # -----------------------------------------------------

    if current_bytes > last_received_bytes: # update the time if there has been progress since the last check, otherwise don't
        last_progress_at = time.monotonic()

        percent = min(100.0, current_bytes / total_bytes * 100)

        publish_progress(
            producer_config=producer_config,
            payload={
                "gbt_uuid": payload["gbt_uuid"],
                "transfer_uuid": transfer_uuid,
                "station": station,
                "station_name": Stations(station).name,
                "received_bytes": current_bytes,
                "total_bytes": total_bytes,
                "percent": round(percent, 2),
            },
        )

        print(
            f"Transfer {transfer_uuid} "
            f"from VLBA-"
            f"{Stations(station).name}: "
            f"{percent:.2f}% "
            f"({current_bytes}/"
            f"{total_bytes})"
        )

    last_received_bytes = (current_bytes) # always keeping track of what the previous received bytes were

    # -----------------------------------------------------
    # Transfer complete.
    # -----------------------------------------------------

    if current_bytes >= total_bytes:
        print(f"Transfer of <{transfer_uuid}.bin> COMPLETE.")

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
            message=(f"VLBA-{Stations(payload['station']).name} completed sending the data file to DSOC via e-transfer."),

        )

        return True # returns True so any completed transfers can be removed from the active_transfers list in progress_consume()

    # -----------------------------------------------------
    # Transfer has not changed recently.
    # -----------------------------------------------------

    if time.monotonic() - last_progress_at > STALL_TIMEOUT_SECONDS:
        # if the transfer has stalled for more than STALL_TIMEOUT_SECONDS, check if the VLBA station is still alive by checking if there are any members in the consumer group for that station
        vlba_station = Stations(station)

        vlba_consumer_group = (
            f"{vlba_station.name.lower()}"
            "-consumer-group"
        )

        if consumer_group_has_members(vlba_consumer_group):
            # VLBA is still alive.
            # Reset the stall timer and continue monitoring.
            last_progress_at = (time.monotonic())

        else:
            raise RuntimeError(
                f"{vlba_station.label} went offline mid-transfer. Transfer interrupted."
            )

    # -----------------------------------------------------
    # Persist transient tracking state in this
    # active_transfers payload.
    # -----------------------------------------------------

    payload["last_progress_at"] = (last_progress_at)

    payload["last_received_bytes"] = (last_received_bytes)

    return False




class Command(BaseCommand):
    help = "Runs the e-transfer progress tracking simulator"

    def handle(
        self,
        *args,
        **options,
    ):
        print("Starting e-transfer progress tracking simulator")

        (
            producer_topic,
            producer_config,
            consumer_topic,
            consumer_config,
        ) = bootstrap(
            Stations.PTW
        )

        progress_consume(consumer_topic, consumer_config, producer_topic=producer_topic, producer_config=producer_config)