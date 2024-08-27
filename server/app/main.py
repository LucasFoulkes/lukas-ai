from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from flask import Flask
import threading
import logging
from shared_sio import sio  # Import the shared sio instance
from irc_bot import Bot  # Import the Bot class
import socketio

# Create a Flask app
app = Flask(__name__)

# Attach Socket.IO server to the Flask app
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# Dictionary to hold the IRC bot instances keyed by sid
bots = {}


# Define a connect handler
@sio.event
def connect(sid, environ):
    nickname = f"bot_{sid[:8]}"  # Create a unique nickname using the sid
    bot = Bot(
        channel="#ebooks",
        nickname=nickname,
        server="irc.irchighway.net",
        port=6667,
        sio=sio,
        sid=sid,
    )
    bots[sid] = bot
    threading.Thread(target=bot.start).start()  # Start the bot in a separate thread
    print(f"Client connected: {sid} with IRC bot nickname: {nickname}")


@sio.event
def message(sid, data):
    if sid in bots:
        bot = bots[sid]
        # Extract the message text from the data dictionary or convert to string if needed
        if isinstance(data, dict) and "data" in data:
            message_text = data["data"]
        else:
            message_text = str(data)

        bot.connection.privmsg(
            bot.channel, message_text
        )  # Send message to the IRC channel


# Define a disconnect handler
@sio.event
def disconnect(sid):
    if sid in bots:
        bot = bots[sid]
        bot.die("WebSocket client disconnected.")
        del bots[sid]
    print(f"Client disconnected: {sid}")


if __name__ == "__main__":
    server = pywsgi.WSGIServer(("0.0.0.0", 8080), app, handler_class=WebSocketHandler)
    server.serve_forever()
