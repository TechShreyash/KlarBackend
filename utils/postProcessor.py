import logging
from utils import db
from utils.schemas import InvoiceExtractionSchema
from utils.vendors import get_or_create_vendor_id

logger = logging.getLogger(__name__)


async def handle_processed_result(
    task_id: str, status: str, data: InvoiceExtractionSchema | str, auth_email: str
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
        final_vendor_id = data.canonical_vendor_id

        if final_vendor_id is None and data.extracted_vendor_name:
            # The AI couldn't find a match. Let's create one.
            logger.info(
                f"[Task {task_id}] No canonical_vendor_id found. Attempting to get/create ID for '{data.extracted_vendor_name}'"
            )
            final_vendor_id = await get_or_create_vendor_id(data.extracted_vendor_name)
            data.canonical_vendor_id = final_vendor_id

        elif final_vendor_id is None:
            logger.warning(
                f"[Task {task_id}] No vendor ID or extracted name. Cannot canonicalize vendor."
            )
            data.human_verification_required = True
            data.human_verification_reason = "Missing vendor name and ID."

        # save to db
        logger.info(f"[Task {task_id}] Saving processed data to database...")
        await db.update_invoice(task_id, data.model_dump(), auth_email)
        logger.info(f"[Task {task_id}] Data for {data.invoice_id} saved.")

    elif status == "ERROR":
        logger.error(f"[Task {task_id}] Processing FAILED. Error: {data}")

        await db.update_invoice(
            task_id,
            {
                "human_verification_required": True,
                "human_verification_reason": data,
            },
            auth_email,
        )
