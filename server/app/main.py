import socketio
import uvicorn
from queue import Queue
from threading import Thread
from runner import run_irc_bot
from irc_bot import logger

# Initialize Socket.IO
sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
app = socketio.ASGIApp(sio)

# Message queue
message_queue = Queue()

# Start the IRC bot in a separate thread
bot_thread = Thread(
    target=run_irc_bot,
    args=("#ebooks", "lukyfox", "irc.irchighway.net", 6667, sio, message_queue),
)
bot_thread.daemon = True
bot_thread.start()


@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    await sio.emit("response", {"message": "Connected"}, room=sid)


@sio.event
def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def message(sid, data):
    logger.info(f"Message received from {sid}: {data}")
    message = data.get("data")
    message_queue.put(message)


if __name__ == "__main__":
    logger.info("Starting server")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        ssl_keyfile="privkey.pem",
        ssl_certfile="fullchain.pem",
        ssl_keyfile_password=None,
        log_level="info",
    )
