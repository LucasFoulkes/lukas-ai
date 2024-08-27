import socketio

# Create a Socket.IO server instance
sio = socketio.Server(async_mode="gevent", cors_allowed_origins="*")
