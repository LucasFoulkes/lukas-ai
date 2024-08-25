from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from dcc_receive import start_dcc_receive_client

app = FastAPI()

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
    logging.info(f"Client connected: {websocket.client.host}")
    try:
        data = await websocket.receive_text()
        logging.info(f"Received message from client: {data}")
        if data == "/start":
            await start_dcc_receive_client(websocket)
        else:
            await websocket.send_text("Use /start to begin the DCC client.")
    except WebSocketDisconnect:
        logging.info(f"Client disconnected: {websocket.client.host}")
    except Exception as e:
        logging.error(f"Error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
