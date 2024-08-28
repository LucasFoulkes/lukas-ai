import asyncio
import queue
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import logging
from irc_bot import DCCReceive
import threading

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI and Socket.IO
app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a queue for inter-thread communication
message_queue = queue.Queue()

# Initialize the IRC bot
bot = DCCReceive(message_queue)
bot_thread = threading.Thread(target=bot.run)
bot_thread.start()


# Function to process the message queue
async def process_message_queue():
    while True:
        try:
            message = message_queue.get_nowait()
            await sio.emit("response", {"message": message})
        except queue.Empty:
            await asyncio.sleep(0.1)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_message_queue())


# Define Socket.IO events
@sio.event
async def connect(sid, environ):
    await sio.emit(
        "response",
        {"message": f"SERVER: Connected as {bot.connection.get_nickname()}"},
        room=sid,
    )
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def message(sid, data):
    logger.info(f"Message received from {sid}: {data}")
    if bot.send_message(data["data"]):
        await sio.emit(
            "response", {"message": f"Message sent: {data['data']}"}, room=sid
        )
    else:
        await sio.emit(
            "response",
            {"message": "Failed to send message. Bot not connected."},
            room=sid,
        )


# Define a simple root endpoint
@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Socket.IO server is running"}


# Combine FastAPI and Socket.IO
app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
