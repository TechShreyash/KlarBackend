# main.py
import pathlib
from utils.extractor import InvoiceExtractor
import config

CURRENT_VENDORS = [
    ("SuperStore Inc", "VEND_0001"),
    ("EZStore", "VEND_0002"),
]


def process_new_invoice(pdf_file_path: str):
    """
    Main function to process a single invoice.
    """
    extractor = InvoiceExtractor(config.GOOGLE_API_KEY)
    filepath = pathlib.Path(pdf_file_path)

    try:
        extracted_data = extractor.extract_from_pdf(filepath, CURRENT_VENDORS)

        # --- Human-in-the-Loop Logic ---

        # 1. Check for general low confidence
        if extracted_data.human_verification_required:
            print(
                f"FLAG: Invoice {extracted_data.invoice_id} requires human verification."
            )

        # 2. Check for new vendors (the critical canonicalization loop)
        known_vendor_ids = [vendor[1] for vendor in CURRENT_VENDORS]

        if extracted_data.canonical_vendor_id not in known_vendor_ids:
            print(
                f"NEW VENDOR DETECTED: AI created new ID '{extracted_data.canonical_vendor_id}' "
                f"for extracted name '{extracted_data.extracted_vendor_name}'."
            )

            # A human would confirm:
            #   a) Is 'SuperStore' truly a new vendor?
            #   b) Or should it be mapped to 'SuperStore Inc' (VEND_0001)?

        print("\n--- Extracted Data ---")
        print(extracted_data.model_dump_json(indent=2))

    except FileNotFoundError:
        print(f"Error: The file {pdf_file_path} was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    process_new_invoice("tests/invoice1-updated.pdf")
