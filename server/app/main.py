from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

connected_clients = []

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],
)

# Logging configuration
logging.basicConfig(level=logging.INFO)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    logging.info(f"Client connected: {websocket.client.host}")

    try:
        # Notify the client that the program has started
        start_message = "Program started"
        logging.info("Sending start message to client")
        await websocket.send_text(start_message)

        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message from client: {data}")
            # Echo the received message back to all connected clients
            for client in connected_clients:
                logging.info(f"Broadcasting message to client: {client.client.host}")
                await client.send_text(data)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logging.info(f"Client disconnected: {websocket.client.host}")
