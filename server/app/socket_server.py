import socketio
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Socket.IO
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

def create_app(irc_bot):
    app = socketio.ASGIApp(sio)

    @sio.event
    async def connect(sid, environ):
        logger.info(f"Socket.IO client connected: {sid}")
        await sio.emit("response", {"message": "Connected to server"}, room=sid)

    @sio.event
    async def disconnect(sid):
        logger.info(f"Socket.IO client disconnected: {sid}")

    @sio.event
    async def message(sid, data):
        logger.info(f"Message received from Socket.IO client {sid}: {data}")
        if isinstance(data, dict) and 'message' in data:
            message = data['message']
        else:
            message = str(data)
        irc_bot.send_message(irc_bot.channel, message)
        await sio.emit("response", {"message": f"Message sent to IRC: {message}"}, room=sid)

    return app