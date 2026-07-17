from datetime import datetime, timezone
from confluent_kafka.admin import AdminClient, NewTopic
from dotenv import load_dotenv
from matplotlib.path import Path
from pathlib import Path
from ngRadar_Website.enums import Stations


def latency_calc(event_time):
  #calculates the latency of the message from the time it was sent to the time it was received
  #returns latency in milliseconds

  current_time = datetime.now(timezone.utc)
  latency = current_time - event_time
  latency_ms = latency.total_seconds() * 1000
  return latency_ms


def config_func(sim, bootstrap):
    # Generates config file and Kafka topic info, based on the sim (either 'GBT' or 'DSOC').
    # Designed to be called in conjunction with bootstrap function
    if sim == Stations.GBT:
        
        #bootstrap = os.environ["BOOTSTRAP_SERVER"] 
        admin = AdminClient({"bootstrap.servers": bootstrap})
        topics = [
            NewTopic("user_input", num_partitions=3, replication_factor=1),
            NewTopic("GBT_data", num_partitions=1, replication_factor=1),
        ]
        fs = admin.create_topics(topics, request_timeout=30)

        for topic, f in fs.items():
            # f is a Future; result() will raise if creation failed for reasons other than "already exists"
            f.result()
        
        producer_topic = "GBT_data"  # NOTE The topic to which the messages will be sent, rename accordingly to whatever topic you want to send to
        producer_config = {
            "bootstrap.servers": bootstrap,
            "message.max.bytes": 8388608,# NOTE can make this constant
            "client.id": "GBT-producer"
        }

        consumer_topic = "user_input"
        consumer_config = {
            "bootstrap.servers": bootstrap,
            "fetch.max.bytes": 8388608,
            "session.timeout.ms": 45000, #NOTE this one too
            "client.id": "GBT-consumer",
            "group.id": "GBT-consumer-group",
            "auto.offset.reset": "earliest",
        }
        return producer_topic, producer_config, consumer_topic, consumer_config
    else:
        #DSOC config
        topic = ["GBT_data"]  #consumes from the GBT's topic
        config = {
            "bootstrap.servers": bootstrap,
            "fetch.max.bytes": 8388608,
            "session.timeout.ms": 45000,
            "client.id": "dsoc-consumer",
            "group.id": "consumer-group",
            "auto.offset.reset": "earliest",
        }

    return topic, config


def bootstrap(sim):
    
    load_dotenv()  # Load environment variables from .env file

    p = Path("../../../../out/ngrok_endpoint.env")
    text = p.read_text().strip()

    bootstrap = None
    for line in text.splitlines():
        if line.startswith("BOOTSTRAP_SERVER="):
            bootstrap = line.split("=", 1)[1].strip()
            break

    if not bootstrap:
        raise RuntimeError("BOOTSTRAP_SERVER not found in /out/ngrok_endpoint.env")
    
    if sim == Stations.GBT:
        producer_topic, producer_config, consumer_topic, consumer_config = config_func(sim, bootstrap)
        return producer_topic, producer_config, consumer_topic, consumer_config
    else:
        topic, config = config_func(sim, bootstrap)
        return topic, config