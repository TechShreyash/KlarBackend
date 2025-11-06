# main.py
import asyncio
import logging
import os
import pathlib
import uuid

import aiofiles
from fastapi.responses import FileResponse

from utils import db
from utils.logging_config import setup_logging
from utils.queueHandler import add_task_to_queue, run_service
import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
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
    invoices = await db.get_all_invoices(auth_email=request.headers["auth_email"])
    return invoices


UPLOAD_DIR = pathlib.Path("tests")


@app.post("/processInvoice")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Accepts a file upload (e.g., PDF) and saves it to the 'uploads' directory.
    """
    try:

        file_path = UPLOAD_DIR / (str(uuid.uuid4()) + ".pdf")

        # Save the file asynchronously
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()  # Read file content
            await buffer.write(content)  # Write to disk

        logger.info(f"File saved to '{file_path}'")

        await add_task_to_queue(str(file_path), request.headers["auth_email"])
        return {
            "saved_path": str(file_path),
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Could not upload file: {e}")
    finally:
        await file.close()


# --- NEW: File Serving Route ---
@app.get("/files/{filename}")
async def get_file(filename: str):
    """
    Retrieves a previously uploaded file by its filename from the 'uploads' directory.
    """
    try:
        file_path = UPLOAD_DIR / filename

        # Security check: ensure file is within the UPLOAD_DIR
        if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")

        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logger.warning(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")

        logger.info(f"Serving file: {file_path}")
        return FileResponse(file_path)
    except Exception as e:
        logger.error(f"Error serving file: {e}")
        if isinstance(e, HTTPException):
            raise e  # Re-raise if it's already an HTTPException
        raise HTTPException(status_code=500, detail="Internal server error")


# --- Run the Application ---
if __name__ == "__main__":
    print("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
