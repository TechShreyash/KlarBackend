# main.py
import asyncio
import logging
from utils import db
from utils.logging_config import setup_logging
from utils.queueHandler import run_service
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List
from utils.schemas import InvoiceResponseModel


setup_logging()
logger = logging.getLogger(__name__)


# --- Lifespan Function ---
# This function manages the application's startup and shutdown events.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Connects to MongoDB on startup and disconnects on shutdown.
    """
    print("Application startup...")
    asyncio.create_task(run_service())

    yield


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Invoice Processing API",
    description="API for processing and retrieving invoices.",
    lifespan=lifespan,
)

# --- CORS (Cross-Origin Resource Sharing) ---
# This allows your frontend (e.g., a React app) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- API Routes ---


@app.get("/")
async def get_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Invoice API is running!"}



@app.get("/getInvoices", response_model=List[InvoiceResponseModel])
async def get_invoices(request: Request):
    """
    Retrieves all invoice documents from the MongoDB collection.
    """
    # Access the database collection from the app state
    invoices = await db.get_all_invoices()
    return invoices


# --- Run the Application ---
if __name__ == "__main__":
    print("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
