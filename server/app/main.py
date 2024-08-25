from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from dcc_receive import start_dcc_receive_client

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
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message from client: {data}")

            if data == "start":
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, start_dcc_receive_client, websocket)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logging.info(f"Client disconnected: {websocket.client.host}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
