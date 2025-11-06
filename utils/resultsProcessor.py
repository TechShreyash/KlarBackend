import logging
from utils.schemas import InvoiceExtractionSchema
from utils.vendors import get_or_create_vendor_id

logger = logging.getLogger(__name__)


async def handle_processed_result(
    task_id: str, status: str, data: InvoiceExtractionSchema | str
):
    """
    This is your callback function for every finished task.
    This is where you will add your database saving logic.
    """
    if status == "SUCCESS" and isinstance(data, InvoiceExtractionSchema):
        logger.info(
            f"[Task {task_id}] Processing SUCCESS for Invoice: {data.invoice_id}"
        )

        # --- New Vendor Canonicalization Step ---
        # This is the robust way to handle new vendors.
        final_vendor_id = data.canonical_vendor_id

        if final_vendor_id is None and data.extracted_vendor_name:
            # The AI couldn't find a match. Let's create one.
            logger.info(
                f"[Task {task_id}] No canonical_vendor_id found. Attempting to get/create ID for '{data.extracted_vendor_name}'"
            )
            try:
                final_vendor_id = await get_or_create_vendor_id(
                    data.extracted_vendor_name
                )
                # Update the object before saving
                data.canonical_vendor_id = final_vendor_id
            except Exception as e:
                logger.error(
                    f"[Task {task_id}] Error during vendor creation for '{data.extracted_vendor_name}': {e}"
                )
                # Flag for review
                data.human_verification_required = True
                data.human_verification_reason = f"Failed to create new vendor: {e}"

        elif final_vendor_id is None:
            logger.warning(
                f"[Task {task_id}] No vendor ID or extracted name. Cannot canonicalize vendor."
            )
            data.human_verification_required = True
            data.human_verification_reason = "Missing vendor name and ID."

        # --- Your Database & HIL Logic ---

        # 1. Save the final, updated data to your database
        # E.g.: await db.save_invoice_data(task_id, data.model_dump())
        logger.info(f"[Task {task_id}] Saving processed data to database...")
        # (Your DB save logic here)
        logger.info(f"[Task {task_id}] Data for {data.invoice_id} saved.")

        # 2. Check for human verification
        if data.human_verification_required:
            logger.warning(
                f"[Task {task_id}] FLAG: Invoice {data.invoice_id} requires human review. "
                f"Reason: {data.human_verification_reason}"
            )
            # E.g.: await db.flag_for_review(task_id, data.human_verification_reason)

    elif status == "ERROR":
        logger.error(f"[Task {task_id}] Processing FAILED. Error: {data}")
        # E.g.: await db.log_error(task_id, str(data))
