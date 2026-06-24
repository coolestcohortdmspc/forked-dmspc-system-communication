# mock_producer.py
import json
import time
import os
from datetime import datetime
from kafka import KafkaProducer

""" 
    This producer simulates the sending of DDM payloads programmatically to a Kafka topic
    This has not been tested at all. Just some ideas for it. 
    Will still need to account for a user inputted payload to send
    to kafka, but the user inputted payload should probably be handled in the views, not here.
    But idk, would have to research how best to handle the user input.
 """

# Target configuration details matching your docker network parameters
BOOTSTRAP_SERVERS = ['localhost:9092']
TOPIC_NAME = 'DDM_Payload'

def get_binary_image_data(filename):
    """Safely extracts local asset payloads from the workstation root."""
    asset_path = os.path.join(os.path.dirname(__file__), 'mock_assets', filename)
    if not os.path.exists(asset_path):
        print(f"Warning: Mock asset source '{asset_path}' not found! Creating dummy bytes.")
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    with open(asset_path, 'rb') as f:
        return f.read()

def run_mock_producer():
    print(f"Initializing Mock Producer targeting {BOOTSTRAP_SERVERS}...")
    try:
        # Note: We do NOT use a value_serializer because value is raw binary image data
        producer = KafkaProducer(bootstrap_servers=BOOTSTRAP_SERVERS)
    except Exception as e:
        print(f"Connection failed: {e}. Is your Docker Kafka service currently running?")
        return

    # Payload Variant A: Your exact Moon payload
    dsoc_metadata = {
        "obs_ID": "obs_001",
        "target": "Moon", #idk??
        "xmit_station": "Green Bank (100-m, GBT)",
        "rcvr_station": "North Liberty (25-m, VLBA)",
        "productType": "DDM",
        "productID": "ddm_002",
        "productSource": "DSOC",
        "creationTime": "2026-06-04 15:05:20.103",
        "eventTime": "2026-06-04 14:59:05.096"
    }

    # Payload Variant B: Brand new Mars observation payload
    dsoc_metadata_2 = {
        "obs_ID": "obs_002",
        "target": "Mars", #idk??
        "xmit_station": "Los Alamos (25-m, VLBA)",
        "rcvr_station": "Hancock (25-m, VLBA)",
        "productType": "DDM",
        "productID": "ddm_009",
        "productSource": "DSOC",
        "creationTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "eventTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    }

    # Payload Variant C: Some GBT data
    gbt_metadata = {
        "obs_ID": "obs_003",
        "target": "Jupiter", #idk??
        "xmit_station": "Green Bank (100-m, GBT)",
        "rcvr_station": "North Liberty (25-m, VLBA)",
        "productType": "DDM",
        "productID": "ddm_015",
        "productSource": "GBT",
        "creationTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "eventTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    }

    # Payload Variant D: Some more GBT data
    gbt_metadata_2 = {
        "obs_ID": "obs_004",
        "target": "Saturn", #idk??
        "xmit_station": "Green Bank (100-m, GBT)",
        "rcvr_station": "North Liberty (25-m, VLBA)",
        "productType": "DDM",
        "productID": "ddm_020",
        "productSource": "GBT",
        "creationTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "eventTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    }

    scenarios = [
        {"meta": dsoc_metadata, "image_file": "molniya.png"},
        {"meta": dsoc_metadata_2, "image_file": "mtex-ngVLA.png"},
        {"meta": gbt_metadata, "image_file": "jupiter.png"},
        {"meta": gbt_metadata_2, "image_file": "saturn.png"}
    ]

    for index, run in enumerate(scenarios):
        meta = run["meta"]
        img_bytes = get_binary_image_data(run["image_file"])

        # Format metadata to look like header bytes matching your consumer specifications
        kafka_headers = [
            ("DDM metadata", json.dumps(meta).encode('utf-8'))
        ]

        print(f"\n[Sending Payload #{index+1}] Target: {meta['target']}...")
        
        # Fire raw bytes payload down Kafka channel
        producer.send(
            topic=TOPIC_NAME,
            value=img_bytes,
            headers=kafka_headers
        )
        producer.flush()
        print(f"Successfully broadcasted {meta['obs_ID']} data packet to cluster.")
        time.sleep(2) # Simulate delay, is this the frequency we want to send these payloads?

    producer.close()
    print("\nTransmission simulation complete.")

if __name__ == '__main__':
    run_mock_producer()



#=============================================
# Nicole's DSOC producer logic here for
# safe-keeping until we figure out producer
# logic:
#=============================================

# import json
# import time
# import csv
# from confluent_kafka import Producer


# topic = "DSOC_data"  # NOTE The topic to which the messages will be sent, rename accordingly to whatever topic you want to send the DDM payloads to.

# run = False # set to True when you're ready to produce to kafka.

# def read_config():
#   # reads the client (producer) configuration from producer.properties
#   # and returns it as a key-value map
#   config = {}
#   with open("producer.properties") as fh:
#     for line in fh:
#       line = line.strip()
#       if len(line) != 0 and line[0] != "#":
#         parameter, value = line.strip().split('=', 1)
#         config[parameter] = value.strip()
#   return config


# def produce(topic, config, key, value):
#   # creates a new producer instance
#   producer = Producer(config)

#   # producing a message to the specified topic 
#   producer.produce(topic, key=key, value=value) 
#   print(f"Produced message to topic {topic} with key {key}.")

#   # send any outstanding or buffered messages to the Kafka broker
#   producer.flush()




# with open("DSOC-data.csv", newline="") as f:
#     reader = csv.DictReader(f, delimiter=" ")  # uses header row as keys
#     for row in reader:
#         if row["Image"]:
#             with open(row["Image"], 'rb') as file :
#                 image = file.read()
#         else: None
        
#         # build JSON payload from the row
#         payload = {
#             "Object": row["Object"],
#             "Object_ID": row["Object_ID"],
#             "Source": row["Source"],
#             "Receiver": row["Receiver"],
#             "Timestamp": f"{time.time()}",
#             "Type": row["Type"],
#             "Bytes": f"{len(image)}" if row["Image"] else None,
#             "Image": f"{image}" if row["Image"] else None
#         }
#         #print(payload) # sanity check

#         key = str(payload["Object_ID"]) if payload.get("Object_ID") else None
#         value = json.dumps(payload).encode("utf-8")

#         if run:
#             config = read_config()
#             produce(topic, config, key, value)

#             time.sleep(10)



#==============================================
# Nicole's GBT producer logic here for
# safe-keeping until we figure out producer
# logic:
#==============================================
# import json
# import time
# import csv
# from confluent_kafka import Producer


# topic = "GBT_data"  # NOTE The topic to which the messages will be sent, rename accordingly to whatever topic you want to send the DDM payloads to.

# run = False # set to true when ready to produce to kafka

# def read_config():
#   # reads the client (producer) configuration from producer.properties
#   # and returns it as a key-value map
#   config = {}
#   with open("producer.properties") as fh:
#     for line in fh:
#       line = line.strip()
#       if len(line) != 0 and line[0] != "#":
#         parameter, value = line.strip().split('=', 1)
#         config[parameter] = value.strip()
#   return config


# def produce(topic, config, key, value):
#   # creates a new producer instance
#   producer = Producer(config)

#   # producing a message to the specified topic 
#   producer.produce(topic, key=key, value=value) 
#   print(f"Produced message to topic {topic} with key {key}.")

#   # send any outstanding or buffered messages to the Kafka broker
#   producer.flush()


# with open("GBT-data.csv", newline="") as f:
#     reader = csv.DictReader(f, delimiter=" ")  # uses header row as keys
#     for row in reader:
#         # build JSON payload from the row
#         payload = {
#             "Object": row["Object"],
#             "Object_ID": row["Object_ID"],
#             "Source": row["Source"],
#             "Tx_Status": row["Tx_Status"],
#             "Transmitted_WF": row["Transmitted_WF"],
#             "Recorded_WF": row["Recorded_WF"],
#             "Timestamp": f"{time.time()}"
#         }
#         print(payload) # sanity check

#         key = str(payload["Object_ID"]) if payload.get("Object_ID") else None
#         value = json.dumps(payload).encode("utf-8")

#         if run:
#             config = read_config()
#             produce(topic, config, key, value)
#             time.sleep(10)

