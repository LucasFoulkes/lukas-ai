import uvicorn
import ssl
import logging
from app import app  # Import the FastAPI app from app.py

# Set up logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Configure SSL (only for development, don't use CERT_NONE in production)
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('fullchain.pem', 'privkey.pem')
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE  # Only for development!

    logger.info("Starting server")
    uvicorn.run(
        "app:app",  # Reference the app in app.py
        host="0.0.0.0",
        port=8000,
        reload=True,
        ssl_keyfile="privkey.pem",
        ssl_certfile="fullchain.pem",
        ssl_keyfile_password=None,  # Add this if your key is password-protected
        log_level="info"
    )
