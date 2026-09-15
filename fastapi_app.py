from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ngRadar_Website.utils import consume, MAX_BYTES, SESSION_TIMEOUT_MS
import os
import asyncio 
import threading

# create instance 
app = FastAPI()

# module-level variable to store active connections
active_connections: set[WebSocket]= set()
loop = None 

@app.websocket("/ws/status")
async def status_ws(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Process the received data
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.get("/ping")
def ping():
    return {"message": "pong"}


topic = ["obs_status_update"]
config = {
    "bootstrap.servers": os.environ.get("BOOTSTRAP_SERVERS", "kafka-broker:29092"),
    "fetch.max.bytes": MAX_BYTES,
    "session.timeout.ms": SESSION_TIMEOUT_MS,   
    "client.id": "event-consumer",
    "group.id": "event-consumer-group",
    "auto.offset.reset": "earliest",
}


async def broadcast(html):
    # loop thru all active connections and send the html to each one
    for connection in active_connections.copy():
        try:
            await connection.send_text(html)
        except WebSocketDisconnect:
            active_connections.remove(connection)

# pull html text from kafka and send to all active connections
def process_msg(msg, producer_topic, producer_config):
    html = msg.value().decode("utf-8")
    asyncio.run_coroutine_threadsafe(broadcast(html), loop)

@app.on_event("startup")
async def start_consumer_thread():
    global loop
    loop = asyncio.get_running_loop()
    # start the consumer in a separate thread
    threading.Thread(target=consume, args=(topic, config, process_msg), daemon=True).start()
