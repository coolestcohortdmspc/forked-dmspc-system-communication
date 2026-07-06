import hashlib
import json
import os
import csv
import time
from datetime import datetime
from PIL import Image
from confluent_kafka import Consumer
import psycopg
from dotenv import load_dotenv
import ast

load_dotenv()  # loads .env from current working dir

database = os.environ["POSTGRES_DB"]
user = os.environ["POSTGRES_USER"]
password = os.environ["POSTGRES_PASSWORD"]
host = os.environ["POSTGRES_HOST"]
port = os.environ["POSTGRES_PORT"]

config = {
    "bootstrap.servers": os.environ["BOOTSTRAP_SERVER"],
    "fetch.max.bytes": 8388608,
    "session.timeout.ms": 45000,
    "client.id": "universal-consumer",
    "group.id": "consumer-group",
    "auto.offset.reset": "earliest",
  }


#Connecting to the team's render database (fill in password):
conn = psycopg.connect(dbname=database, user=user, password=password, host=host, port=port)
cursor = conn.cursor()

topic = ["GBT_data", "DSOC_data"]  #NOTE The topic which the messages will be received from, rename accordingly to whatever topic you are using


def latency_calc(event_time):
  #calculates the latency of the message from the time it was sent to the time it was received
  #returns latency in milliseconds

  event_time = datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S.%f")
  current_time = datetime.now()
  latency = current_time - event_time
  latency_ms = latency.total_seconds() * 1000
  return latency_ms

def DB_columns(value):
  #dissects the payload to get individual values, and publishes to the correct column in the database
  #some values only exist for messages with images - these have if statements

  object_id = value['Object_ID']#done
  target = value['Object']#done

  if value['Source'] == "GBT":
    xmit_station = value['Source']
    #latency_ms = 
    tx_waveform = value['Tx_WF']
    rec_waveform = value['Rec_WF']
    event_time = value['Timestamp']
    latency_ms = latency_calc(event_time)
    return object_id, target, event_time, xmit_station, latency_ms, rec_waveform, tx_waveform
  else:
    xmit_station = "GBT"
    rcvr_station = value['Source']
    product_type = value['Type']
    product_id = value['Image_ID']
    event_time = value['Timestamp']
    created_at = datetime.now()
    image_file = ast.literal_eval(value['Image'])
    num_bytes = value['Bytes']
    latency_ms = latency_calc(event_time)
    return object_id, target, product_type, product_id, event_time, created_at, xmit_station, rcvr_station, image_file, num_bytes, latency_ms

  #return object_id, target, product_type, product_id, station, event_time, created_at, xmit_station, rcvr_station, image_file, num_bytes, rec_waveform, tx_waveform

def publish_DB(object_id, target, product_type, product_id, station, event_time, created_at, xmit_station, rcvr_station, image_file, num_bytes, latency_ms, rec_waveform, tx_waveform):
  #saves the DDM payload to the database, commits it, and closes the DB connection. 
  #using placeholder values for the required column fields - will update with data from the actual message metadata
  cursor.execute("""
                 INSERT INTO \"ngRadar_Website_observatoryevent\" (
                 object_id, 
                 target, 
                 product_type, 
                 product_id, 
                 station, 
                 event_time, 
                 created_at, 
                 xmit_station, 
                 rcvr_station, 
                 image_file, 
                 num_bytes, 
                 latency_ms,
                 rec_waveform, 
                 tx_waveform)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                 """, (
                   object_id, 
                   target, 
                   product_type, 
                   product_id, 
                   station, 
                   event_time, 
                   created_at, 
                   xmit_station, 
                   rcvr_station, 
                   image_file, 
                   num_bytes, 
                   latency_ms,
                   rec_waveform, 
                   tx_waveform))
  conn.commit()
  #conn.close()

  return print("DDM payload saved to database successfully.")


def consume(topic, config):
  #creates a new consumer instance
  consumer = Consumer(config)

  #subscribes to the specified topic
  consumer.subscribe(topic)

  try:
    while True:
      #consumer polls the topic and prints any incoming messages
        msg = consumer.poll(1.0) #polls for messages for 1 second
      #if msg is not None and msg.error() is None:
        if msg is None:
            continue
        if msg.error() is not None:
            print("Consumer error:", msg.error())
            continue

        key = msg.key().decode("utf-8")
        value = json.loads(msg.value().decode("utf-8"))
        #DB_columns(value)

        if value['Source'] == "GBT":
          object_id, target, event_time, xmit_station, latency_ms, rec_waveform, tx_waveform = DB_columns(value)
          publish_DB(object_id, target, product_type=None, product_id=None, station=None, event_time=event_time, created_at=None, xmit_station=xmit_station, rcvr_station=None, image_file=None, num_bytes=None, latency_ms=latency_ms, rec_waveform=rec_waveform, tx_waveform=tx_waveform)
        else:
          object_id, target, product_type, product_id, event_time, created_at, xmit_station, rcvr_station, image_file, num_bytes, latency_ms = DB_columns(value)
          publish_DB(object_id, target, product_type, product_id, station=None, event_time=event_time, created_at=created_at, xmit_station=xmit_station, rcvr_station=rcvr_station, image_file=image_file, num_bytes=num_bytes, latency_ms=latency_ms, rec_waveform=None, tx_waveform=None)

        if value['Source'] == "GBT":
          print(f"Received message from {value['Source']} for object {value['Object']} (Object ID: {value['Object_ID']}).")
          if value['Tx_WF'] != "Tx_OFF":
             print(f"Observing with waveform {value['Tx_WF']}.")
          else:
             print(f"Transmitter is currently OFF.")

        else:
          print(f"Received message from DSOC {(value['Source'])} for object {value['Object']} (Object ID: {value['Object_ID']}). Checking if quick-look product is ready...")
          if value['Type'] == "Spec":
            print(f"CW Spectrum plot is ready (Image ID: {value['Image_ID']}). Produced by {value['Source']}") # add more robust rcvr identification using enums later
            unique = hashlib.sha256(str(value['Image']).encode('utf-8')).hexdigest()
            filename = f"{value['Type']}-{value['Image_ID']}-{value['Timestamp']}-{unique:.15}.png"
            print(f"Image saved as {filename}")
          elif value['Type'] == "DDM":
            print(f"DDM is ready (Image ID: {value['Image_ID']}). Produced by {value['Source']}") # add more robust rcvr identification using enums later
            unique = hashlib.sha256(str(value['Image']).encode('utf-8')).hexdigest()
            filename = f"{value['Type']}-{value['Image_ID']}-{value['Timestamp']}-{unique:.15}.png"
            print(f"Image saved as {filename}")
                #save image first
                #img = Image.open(filename)
                #img.show()
          else:
            print("Image is of an unknown type. Expecting 'Spec' or 'DDM'.")

      #NOTE: NOT ACTUALLY SAVING IMAGES YET
      #NOTE: ADD LATENCY CALCS

  except KeyboardInterrupt: 
    pass
  finally:
    #closes the consumer connection
    consumer.close()


def main():
  consume(topic, config)


main()

