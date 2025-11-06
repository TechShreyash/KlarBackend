# extractor.py
from google import genai
from google.genai import types
from google.genai.types import GenerationConfig
import pathlib
import json
from pydantic import ValidationError

# Local imports
from utils.schemas import InvoiceExtractionSchema
from utils.prompts import INVOICE_EXTRACTION_PROMPT_TEMPLATE
import config


class InvoiceExtractor:
    """
    Manages the connection to the Gemini API and handles invoice extraction.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model_name
        self.json_schema = InvoiceExtractionSchema.model_json_schema()

    def _build_prompt(self, vendor_list: list[tuple[str, str]]) -> str:
        """
        Formats the vendor list and injects it into the prompt template.
        """
        # Convert list of tuples to a string representation for the prompt
        vendor_list_str = str(vendor_list)
        return INVOICE_EXTRACTION_PROMPT_TEMPLATE.format(
            vendor_list_str=vendor_list_str
        )

    def extract_from_pdf(
        self, pdf_path: pathlib.Path, vendor_list: list[tuple[str, str]]
    ) -> InvoiceExtractionSchema:
        """
        Extracts, canonicalizes, and validates invoice data from a PDF.

        Args:
            pdf_path: Path to the invoice PDF file.
            vendor_list: The current list of known vendors.

        Returns:
            A validated InvoiceExtractionSchema object.

        Raises:
            FileNotFoundError: If the PDF path does not exist.
            ValidationError: If the AI output does not match the Pydantic schema.
            Exception: For other API or parsing errors.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"File not found: {pdf_path}")

        print(f"Processing {pdf_path.name}...")

        # 1. Build the dynamic prompt
        prompt = self._build_prompt(vendor_list)

        # 2. Prepare API request
        pdf_bytes = pdf_path.read_bytes()
        invoice_file = types.Part.from_bytes(
            data=pdf_bytes, mime_type="application/pdf"
        )

        response = None

        # 3. Call the API
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[invoice_file, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": self.json_schema,
                },
            )

            # 4. Validate the response with Pydantic
            # This ensures the AI output matches your schema exactly
            if not response or not response.text:
                raise Exception("No response text received from the API.")

            validated_data = InvoiceExtractionSchema.model_validate_json(response.text)
            print(f"Successfully extracted data from {pdf_path.name}.")
            return validated_data

        except ValidationError as e:
            print(f"Error: AI output failed validation for {pdf_path.name}:\n{e}")
            if response:
                if response.text:
                    print(f"Raw AI Output:\n{response.text}")
            raise
        except Exception as e:
            print(f"An error occurred during API call for {pdf_path.name}: {e}")
            raise
