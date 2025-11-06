# utils/extractor.py

import asyncio
import aiofiles
import logging
from google import genai
from google.genai import types
from google.genai.types import GenerationConfig
import pathlib
from pydantic import ValidationError

# Local imports
from utils.schemas import InvoiceExtractionSchema
from utils.prompts import INVOICE_EXTRACTION_PROMPT_TEMPLATE

# Get a logger for this module
logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """
    Manages the connection to the Gemini API and handles invoice extraction.
    Each instance is tied to a specific API key.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        # This synchronously sets up the client configuration
        self.client = genai.Client(api_key=api_key).aio
        self.model = model_name
        self.json_schema = InvoiceExtractionSchema.model_json_schema()

    def _build_prompt(self, vendor_list: list[tuple[str, str]]) -> str:
        """
        Formats the vendor list and injects it into the prompt template.
        """
        vendor_list_str = str(vendor_list)
        return INVOICE_EXTRACTION_PROMPT_TEMPLATE.format(
            vendor_list_str=vendor_list_str
        )

    async def extract_from_pdf_async(
        self, pdf_path: pathlib.Path, vendor_list: list[tuple[str, str]]
    ) -> InvoiceExtractionSchema:
        """
        Extracts, canonicalizes, and validates invoice data from a PDF asynchronously.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"File not found: {pdf_path}")

        prompt = self._build_prompt(vendor_list)

        try:
            # Use aiofiles for true async file I/O
            async with aiofiles.open(pdf_path, "rb") as f:
                pdf_bytes = await f.read()
            invoice_file = types.Part.from_bytes(
                data=pdf_bytes, mime_type="application/pdf"
            )
        except Exception as e:
            logger.error(f"Error reading file {pdf_path.name}: {e}")
            raise

        response_text = None

        try:
            response = await self.client.models.generate_content(
                model=self.model,
                contents=[invoice_file, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": self.json_schema,
                },
            )

            if not response or not response.text:
                raise Exception("No response text received from the API.")

            response_text = response.text

            # Validate the response
            validated_data = InvoiceExtractionSchema.model_validate_json(response_text)
            return validated_data

        except ValidationError as e:
            logger.error(f"AI output failed validation for {pdf_path.name}:\n{e}")
            if response_text:
                logger.error(f"Raw AI Output:\n{response_text}")
            raise
        except Exception as e:
            logger.error(f"API call failed for {pdf_path.name}: {e}")
            raise
