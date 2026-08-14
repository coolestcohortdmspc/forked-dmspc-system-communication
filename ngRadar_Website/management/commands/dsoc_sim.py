from datetime import datetime, timezone
import uuid
from django.core.management.base import BaseCommand
from confluent_kafka import Producer
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import io
from ngRadar_Website.models.models import gbtEvent, dsocEvent, ETransferEvent
from ngRadar_Website.enums import Stations, Status, Message
from ngRadar_Website.utils import latency_calc, bootstrap, consume, create_s3_client, upload_seaweedfs, produce, send_kafka_message
from pathlib import Path
import json
import uuid
import time
from itertools import groupby
import os
import subprocess


"""
This code will:
- consume a message from the VLBA that data is being e-transferred
- pull the record from the GBT table using uuid sent in Kafka message from VLBA
- generate an image file using random data (not e-transferred data yet)
- save image file to seaweedfs object store
- load the image key + the uuid into the DB
"""


def DB_import(uuid):
    
  gbt_data = gbtEvent.objects.filter(uuid=uuid).values_list('object_id', 'target', 'tx_waveform', 'event_time').first()

  return gbt_data


def DB_columns(gbt_data):
    data = {
        "event_time": datetime.now(timezone.utc),
        "object_id": gbt_data[0], # object_id
        "target": gbt_data[1],    # target
    }

    return data



def publish_DB(
    *,
    image_key,
    num_bytes,
    data,
    xmit_station,
    rcvr_station,
    transfer_uuid,
):
    payload_data = data.copy()


    payload_data.update({
        "image_key": image_key,
        "num_bytes": num_bytes,
        "xmit_station": xmit_station,
        "rcvr_station": rcvr_station,
        "transfer_uuid": transfer_uuid,
        "status": Status.COMPLETED,
    })
    try:
          # Create and capture the instantiated record model
          record = dsocEvent.objects.create(**payload_data)
          print("Payload saved to database successfully.")
          return record  # <-- Return the actual object record
  
    except Exception as e:
          print(f"Database error: {e}")
          return None  # <-- Return None if something broke


def create_img(tx_waveform):
    #generate a random image payload to simulate the DSOC's DDM product: 
    matplotlib.use('Agg')  # Use a non-interactive backend for matplotlib
        
    #generating random data and formatting the graph:
    x_data = np.random.uniform(-30, 30, 40)
    y_data = np.random.uniform(-300, 300, 40)

    plt.scatter(x_data, y_data, color='red')
    plt.axhline(0, color='black', linewidth=0.5)
    plt.axvline(0, color='black', linewidth=0.5)
    plt.title(f"DDM for {tx_waveform}", size=20)
    plt.xlabel("Doppler Freq (Hz)")
    plt.ylabel("Range (km)")
    plt.grid(True)

    #saving the bytes to a buffer instead of a file
    byte_buffer = io.BytesIO()
    plt.savefig(byte_buffer, format='png')
    byte_buffer.seek(0)

    image_file = byte_buffer.getvalue()

    plt.close()  # Close the plot to free memory
        
    num_bytes = len(image_file)

    return image_file, num_bytes

def save_image_to_seaweedfs(target, image_file, dsoc_uuid):
    # Saves the image to SeaweedFS using S3 API

    image_key = f"ddm/{target}/{dsoc_uuid}.png"

    s3 = create_s3_client()
    
    file_data = image_file

    image_key = upload_seaweedfs(s3, image_key, file_data)

    print(f"Success: Image saved to SeaweedFS at {image_key}")

    return image_key




# Verifies that the incoming file exists and has the expected number of bytes that VLBA sent in the kafka message.
def verify_incoming_transfer(
    *,
    incoming_file,
    expected_num_bytes,
    attempts=10,
    delay_seconds=0.5,
    ):
        for _ in range(attempts):
            if incoming_file.is_file():
                actual_num_bytes = incoming_file.stat().st_size

                if actual_num_bytes == expected_num_bytes:
                    return actual_num_bytes

            time.sleep(delay_seconds)

        raise RuntimeError(
            f"Transfer verification failed for {incoming_file}. "
            f"Expected {expected_num_bytes} bytes."
        )


# Helper function to record the status of the e-transfer in the ETransferEvent table
def record_transfer_event(
    *,
    transfer_uuid,
    gbt_uuid,
    station,
    status,
    num_bytes=0,
    latency_ms=0.0,
    message="",
):
    gbt_event = gbtEvent.objects.get(uuid=gbt_uuid)

    return ETransferEvent.objects.create(
        transfer_uuid=transfer_uuid,
        gbt_uuid=gbt_uuid,
        object_id=gbt_event.object_id,
        target=gbt_event.target,
        station=station,
        event_time=datetime.now(timezone.utc),
        latency_ms=latency_ms,
        num_bytes=num_bytes,
        status=status,
        message=message,
    )

def get_storage_used(folder_path):
    storage_used = 0

    for file in folder_path.rglob("*"):
        if file.is_file():
            storage_used += file.stat().st_size
            print(f"Size of folder: {storage_used} bytes")
    return storage_used


def process_msg(msg, producer_topic, producer_config):
    incoming_key = int(msg.key().decode("utf-8"))
    payload = json.loads(msg.value().decode("utf-8"))
    
    if incoming_key == Message.VLBA_REQUEST_STORAGE.value:
        # storage check logic
        transfer_uuid = uuid.UUID(payload["transfer_uuid"])
        gbt_uuid = uuid.UUID(payload["gbt_uuid"])
        status = Status(payload["status"])
        filename = payload["filename"]
        expected_num_bytes = int(payload["num_bytes"])

        key = f"{Message.DSOC_RESPOND_STORAGE}" #produced message will have this key no matter what the result of the below logic is
        
        if payload["status"] == Status.FAILED: #NOTE is this correct syntax?
            #TODO: Handle FAILED status Kafka message just in case.
            pass

        volume_path = Path("/dsoc/incoming") / filename

        storage_limit = int(os.environ["DSOC_VOLUME_SIZE"]) * 1000000000
        print(f"DSOC has {storage_limit} bytes of storage total.")
        storage_used = int(get_storage_used(volume_path))
        print(f"DSOC has {storage_used}/{storage_limit} bytes of storage capacity.")
        if storage_used+expected_num_bytes >= storage_limit-1:
            # if the current storage plus the incoming file gets within 1GB of our imposed limit, we decline the e-transfer
            send_kafka_message(
                key = key, 
                producer_topic=producer_topic,
                producer_config=producer_config, 
                transfer_uuid=transfer_uuid,
                gbt_uuid=gbt_uuid,
                status=payload["status"],
                num_bytes=expected_num_bytes,
                filename=filename,
                message="No",
            )

        else:
            send_kafka_message(
                key = key, 
                producer_topic=producer_topic,
                producer_config=producer_config, 
                transfer_uuid=transfer_uuid,
                gbt_uuid=gbt_uuid,
                status=payload["status"],
                num_bytes=expected_num_bytes,
                filename=filename,
                message="Yes",
            )


    elif incoming_key == Message.VLBA_TRANSFERRING.value:
        payload = json.loads(msg.value().decode("utf-8")) 
        key = f"{Message.VLBA_DELETE}"
        if payload["status"] == Status.FAILED:
            #TODO Handle receiving a FAILED transfer later.
            pass
        else:
            filename = payload["filename"]
            transfer_uuid = uuid.UUID(payload["transfer_uuid"])
            gbt_uuid = uuid.UUID(payload["gbt_uuid"])
            incoming_file = Path("/dsoc/incoming") / filename
            while True:
                #TODO write to progress.json logic. Can get rid of etr_progress_writer worker later. For now, just check every 0.5 seconds if it's complete.
                #TODO To avoid getting stuck in inifinite loop when we interrupt transfers, poll DB for most recent status under the transfer_uuid and break if status is FAILED.
                
                with open("/service/mock_assets/progress.json", "r", encoding="utf-8") as f:
                    progress_payload = json.load(f)
                    print(f"Progress Payload %: {progress_payload['percent']}")
                    if progress_payload["percent"] == "100.0":
                        break
                    else:
                        time.sleep(0.5)


            record_transfer_event(
                transfer_uuid=payload["transfer_uuid"],
                gbt_uuid=payload["gbt_uuid"],
                station=Stations.HN,
                status=Status.TRANSFERRED,
                num_bytes=payload["num_bytes"],
                message="Hancock VLBA e-transfer in progress",
            )

            record_transfer_event(
                transfer_uuid=payload["transfer_uuid"],
                gbt_uuid=payload["gbt_uuid"],
                station=Stations.DSOC,
                status=Status.VERIFYING,
                num_bytes=payload["num_bytes"],
                message=f"Verifying {payload['filename']}",
            )

            try:
                actual_num_bytes = verify_incoming_transfer( 
                    incoming_file=incoming_file,
                    expected_num_bytes=payload["num_bytes"],
                )
            except Exception as exc:
                record_transfer_event(
                    transfer_uuid=payload["transfer_uuid"],
                    gbt_uuid=payload["gbt_uuid"],
                    station=Stations.DSOC,
                    status=Status.FAILED,
                    num_bytes=0,
                    message=str(exc),
                )
                return

            try:
                gbt_data = DB_import(payload["gbt_uuid"])
                dsoc_latency = latency_calc(gbt_data[3])

                data = DB_columns(gbt_data)
                data["latency_ms"] = dsoc_latency

                object_id, target, tx_waveform, event_time = gbt_data
                image_file, image_num_bytes = create_img(tx_waveform)
                dsoc_uuid = str(uuid.uuid4())

                image_key = save_image_to_seaweedfs(
                    target,
                    image_file,
                    dsoc_uuid,
                )

                data["uuid"] = dsoc_uuid

                publish_DB(
                    image_key=image_key,
                    num_bytes=image_num_bytes,
                    data=data,
                    xmit_station=Stations.GBT,
                    rcvr_station=Stations.HN,
                    transfer_uuid=payload["transfer_uuid"],
                )

            except Exception as exc:
                record_transfer_event(
                    transfer_uuid=payload["transfer_uuid"],
                    gbt_uuid=payload["gbt_uuid"],
                    station=Stations.DSOC,
                    status=Status.FAILED,
                    num_bytes=payload["num_bytes"],
                    message=f"DSOC image processing failed: {exc}",
                )
                return

            record_transfer_event(
                transfer_uuid=payload["transfer_uuid"],
                gbt_uuid=payload["gbt_uuid"],
                station=Stations.DSOC,
                status=Status.COMPLETED,
                num_bytes=actual_num_bytes,
                latency_ms=dsoc_latency,
                message="DSOC has verified etransfer, image generated, and image stored.",
            )

            send_kafka_message(
                key = key, 
                producer_topic=producer_topic,
                producer_config=producer_config, 
                transfer_uuid=payload["transfer_uuid"],
                gbt_uuid=payload["gbt_uuid"],
                status=payload["status"],
                num_bytes=payload["num_bytes"],
                filename=payload["filename"],
                message="Processing complete. Delete your raw data.",
            )
        
    else:
        print("Invalid Kafka Message Key!")
    # payload = json.loads(msg.value().decode("utf-8"))

    # transfer_uuid = uuid.UUID(payload["transfer_uuid"])
    # gbt_uuid = uuid.UUID(payload["gbt_uuid"])
    # status = Status(payload["status"])
    # filename = payload.get("filename")
    # expected_num_bytes = payload.get("num_bytes", 0)
    # message = payload.get("message", "")
    # incoming_file = Path("/dsoc/incoming") / filename

    # record_transfer_event(
    #     transfer_uuid=transfer_uuid,
    #     gbt_uuid=gbt_uuid,
    #     station=Stations.HN,
    #     status=status,
    #     num_bytes=expected_num_bytes,
    #     message=message,
    # )

# NOTE Figure out where to put the safegaurds below
    # if status == Status.FAILED:
    #     return

    # if status != Status.TRANSFERRED:
    #     return

    # already_completed = ETransferEvent.objects.filter(
    #     transfer_uuid=transfer_uuid,
    #     station=Stations.DSOC,
    #     status=Status.COMPLETED,
    # ).exists()

    # if already_completed:
    #     print(f"This transfer {transfer_uuid} has already been processed. Skipping.")
    #     return

    # already_processing = ETransferEvent.objects.filter(
    #     transfer_uuid=transfer_uuid,
    #     station=Stations.DSOC,
    #     status__in=[Status.VERIFYING],
    #     ).exists()

    # if already_processing:
    #     print(f"Transfer {transfer_uuid} is already being processed currently.")
    #     return

    # if not filename:
    #     record_transfer_event(
    #         transfer_uuid=transfer_uuid,
    #         station=Stations.DSOC,
    #         status=Status.FAILED,
    #         num_bytes=expected_num_bytes,
    #         message="Kafka transfer message did not contain a filename",
    #     )
    #     return




class Command(BaseCommand):
    help = "Runs the DSOC simulator"

    def handle(self, *args, **options):
        print("Starting DSOC simulator")

        producer_topic, producer_config, consumer_topic, consumer_config = bootstrap(Stations.DSOC)

        consume(consumer_topic, consumer_config, process_msg, producer_topic=producer_topic, producer_config=producer_config)