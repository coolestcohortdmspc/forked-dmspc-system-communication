from datetime import datetime, timezone
from confluent_kafka.admin import AdminClient, NewTopic
from dotenv import load_dotenv
from matplotlib.path import Path
from pathlib import Path
from ngRadar_Website.enums import Stations
from confluent_kafka import Consumer


def latency_calc(event_time):
    """
    Description: Calculates the latency of the message from the time it was sent to the time it was received
    Inputs: event_time = Time in the past. This is the time when the 'stopwatch' starts on our latency calculation
    Returns: latency_ms = Latency in milliseconds
    """
    current_time = datetime.now(timezone.utc)
    latency = current_time - event_time
    latency_ms = latency.total_seconds() * 1000
    return latency_ms


def config_func(sim, bootstrap):
    """
    Description: Generates config file and Kafka topic info, based on the sim.
                Designed to be called in conjunction with bootstrap function.
    Inputs: sim = the sim file in use (GBT or DSOC)
            bootstrap = bootstrap info derived from .env
    Returns: topic(s) and config(s) variables
    """
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

        consumer_topic = ["user_input"]
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
    """
    Description: Extracts bootstrap info from .env and ngrok, then uses config_func to generate outputs
    Inputs: sim = the sim file in use (GBT or DSOC)
    Returns: topic(s) and config(s) variables
    """
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
    

def consume(topic, config, process_msg, producer_topic=None, producer_config=None):
    """
    Description: Creates a new consumer instance; subscribes to a Kafka topic and receives messages.
    Inputs: topic = The Kafka topic to receieve messages from.
            config = Server configuration defining the bootstrap, byte and timeout limits, and IDs.
            process_msg = A function which accepts the Kafka message as an input.
    Returns: N/A
    """
    consumer = Consumer(config)

    #subscribes to the specified topic
    consumer.subscribe(topic)
    
    try:
        while True:
            #consumer polls the topic and prints any incoming messages
            msg = consumer.poll(1.0) #polls for messages for 1 second
            
            if msg is None:
                continue
            if msg.error() is not None:
                print("Consumer error:", msg.error())
                continue

            #if msg is not None and msg.error() is None:
            process_msg(msg, producer_topic, producer_config)
    except Exception as e:
        import traceback
        print("An unhandled exception occurred in the consumer loop:")
        traceback.print_exc()
        raise