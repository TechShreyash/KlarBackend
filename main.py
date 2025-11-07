# main.py
import asyncio
import io
import logging
import os
import pathlib
import uuid
from contextlib import asynccontextmanager
from typing import List

import aiofiles
from fastapi.responses import FileResponse
import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from utils import db
from utils.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from utils.logging_config import setup_logging
from utils.queueHandler import add_task_to_queue, run_service
from utils.schemas import InvoiceResponseModel
import config

setup_logging()
logger = logging.getLogger(__name__)


# Auth schemas
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)  # allow long passphrase


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    await db.ensure_user_indexes()
    asyncio.create_task(run_service())
    yield
    logger.info("Application shutdown...")


app = FastAPI(
    title="Invoice Processing API",
    description="API for processing and retrieving invoices.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth routes
@app.post("/auth/signup", response_model=TokenResponse, tags=["auth"])
async def signup(payload: SignupRequest):
    existing = await db.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = hash_password(payload.password)
    await db.create_user(payload.email, hashed)
    token = create_access_token(subject=payload.email.lower())
    return TokenResponse(access_token=token)


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(payload: LoginRequest):
    user = await db.get_user_by_email(payload.email)
    if (not user) or (
        not verify_password(payload.password, user.get("password_hash", ""))
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=user["email"])
    return TokenResponse(access_token=token)


# Root
@app.get("/")
async def get_root():
    return {"message": "Invoice API is running!"}


# Invoice routes (protected)
@app.get("/getInvoices", response_model=List[InvoiceResponseModel], tags=["invoices"])
async def get_invoices(current_email: str = Depends(get_current_user)):
    invoices = await db.get_all_invoices(auth_email=current_email)
    return invoices


@app.get(
    "/invoice_details/{task_id}", response_model=InvoiceResponseModel, tags=["invoices"]
)
async def get_invoice_details(
    task_id: str, current_email: str = Depends(get_current_user)
):
    invoice = await db.get_invoice_by_task_id(task_id, auth_email=current_email)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


UPLOAD_DIR = pathlib.Path("tests")

from PIL import Image


# --- [NEW] Image Conversion Helper Function ---
def convert_image_to_pdf(image_bytes: bytes) -> bytes:
    """
    Converts image bytes (JPG, PNG, etc.) into PDF bytes.
    This is a blocking (CPU/memory-bound) function.
    """
    try:
        # Open image from in-memory bytes
        image = Image.open(io.BytesIO(image_bytes))

        # Handle images with transparency (e.g., PNGs)
        if image.mode == "RGBA":
            # Create a white background
            bg = Image.new("RGB", image.size, (255, 255, 255))
            # Paste the image onto the background, using alpha channel as mask
            bg.paste(image, (0, 0), image)
            image = bg
        elif image.mode != "RGB":
            # Convert other modes (like P, L) to RGB
            image = image.convert("RGB")

        # Save to an in-memory PDF
        pdf_bytes_io = io.BytesIO()
        image.save(pdf_bytes_io, format="PDF", resolution=100.0)
        return pdf_bytes_io.getvalue()
    except Exception as e:
        logger.error(f"Error converting image to PDF: {e}")
        # Re-raise to be caught by the route's exception handler
        raise


@app.post("/processInvoice", tags=["invoices"])
async def upload_file(
    file: UploadFile = File(...), current_email: str = Depends(get_current_user)
):
    """
    Accepts a PDF or Image (JPG, PNG) upload.
    If it's an image, it converts it to PDF before saving and queuing.
    """
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # We always save as .pdf
        file_path = UPLOAD_DIR / (f"{uuid.uuid4()}.pdf")

        # Read the entire file into memory
        content = await file.read()
        pdf_bytes_to_save = None

        # Check the MIME type
        if file.content_type == "application/pdf":
            logger.info("PDF file detected. Saving directly.")
            pdf_bytes_to_save = content

        elif file.content_type in [
            "image/jpeg",
            "image/png",
            "image/bmp",
            "image/gif",
            "image/webp",
        ]:
            logger.info(
                f"Image file detected ({file.content_type}). Converting to PDF..."
            )
            # Run the blocking conversion in a separate thread
            pdf_bytes_to_save = await asyncio.to_thread(convert_image_to_pdf, content)
            logger.info("Image successfully converted to PDF.")

        else:
            logger.warning(f"Unsupported file type: {file.content_type}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Please upload a PDF, JPG, or PNG.",
            )

        # Asynchronously write the final PDF bytes to disk
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(pdf_bytes_to_save)

        logger.info("File saved to '%s'", file_path)
        await add_task_to_queue(str(file_path), current_email)

        return {"saved_path": str(file_path)}

    except Exception as e:
        # Use logger.exception to automatically include stack trace
        logger.exception("Error uploading file")
        # Don't leak internal error details to the client
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Could not process uploaded file.")
    finally:
        await file.close()


# human in loop
@app.post("/updateInvoice", tags=["invoices"])
async def update_invoice(data: dict, current_email: str = Depends(get_current_user)):
    data = data["data"]
    data["status"] = "completed"
    data["human_verification_required"] = False
    data["human_verification_reason"] = None
    data.pop("file_link", None)
    await db.update_invoice(data["task_id"], data, auth_email=current_email)
    return {"message": "Invoice updated successfully"}


@app.get("/files/{filename}", tags=["files"])
async def get_file(filename: str):
    try:
        file_path = UPLOAD_DIR / filename
        if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
        if not file_path.exists() or not file_path.is_file():
            logger.warning("File not found: %s", file_path)
            raise HTTPException(status_code=404, detail="File not found")
        logger.info("Serving file: %s", file_path)
        return FileResponse(file_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error serving file")
        raise HTTPException(status_code=500, detail="Internal server error") from e


if __name__ == "__main__":
    logger.info("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
