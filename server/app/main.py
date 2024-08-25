from fastapi import FastAPI, HTTPException
import logging
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Example list of books as a list of formatted strings
books = [
    "To Kill a Mockingbird by Harper Lee (1960)",
    "1984 by George Orwell (1949)",
    "The Great Gatsby by F. Scott Fitzgerald (1925)",
    "The Catcher in the Rye by J.D. Salinger (1951)",
    "The Hobbit by J.R.R. Tolkien (1937)",
    "Fahrenheit 451 by Ray Bradbury (1953)",
    "Pride and Prejudice by Jane Austen (1813)",
    "The Lord of the Rings by J.R.R. Tolkien (1954)",
    "Animal Farm by George Orwell (1945)",
    "Moby-Dick by Herman Melville (1851)",
    "War and Peace by Leo Tolstoy (1869)",
    "The Odyssey by Homer (-800)",
    "Crime and Punishment by Fyodor Dostoevsky (1866)",
    "Brave New World by Aldous Huxley (1932)",
    "Jane Eyre by Charlotte Brontë (1847)",
    "Wuthering Heights by Emily Brontë (1847)",
    "The Divine Comedy by Dante Alighieri (1320)",
    "The Brothers Karamazov by Fyodor Dostoevsky (1880)",
    "Les Misérables by Victor Hugo (1862)",
    "The Iliad by Homer (-750)",
]


@app.get("/book/init")
async def start_program():
    """
    Handle GET requests to /book/init.
    Returns a JSON response indicating the program has started.
    """
    await asyncio.sleep(2)
    logging.info("Received request to /book/init endpoint")
    return {"message": "Program started"}


@app.get("/book/{command}")
async def handle_command(command: str):
    """
    Handle GET requests to /book/{command}.
    Returns a JSON response based on the command.
    """
    logging.info(f"Received command: {command}")

    # Add a delay of 2 seconds
    await asyncio.sleep(2)

    if command == "list":
        return {"message": "List of books", "data": books}

    if command == "test":
        return {"message": "This is a test response"}

    return {"message": f"Received command: {command}"}
