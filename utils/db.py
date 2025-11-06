import motor.motor_asyncio
import config

client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_DB_URL)
db = client.KlerBackend
collection = db.invoices


async def add_invoice(data: dict, auth_email: str):
    data["status"] = "pending"
    data["auth_email"] = auth_email
    await collection.update_one(
        {"pdf_path": data["pdf_path"], "auth_email": auth_email},
        {"$set": data},
        upsert=True,
    )


async def update_invoice(task_id: str, data: dict, auth_email: str):
    data["status"] = (
        "completed"
        if not data["human_verification_required"]
        else "requires_human_verification"
    )

    # update year to current year if date is present
    if "date" in data and data["date"]:
        from datetime import datetime

        current_year = datetime.now().year
        date_parts = data["date"].split("-")
        if len(date_parts) == 3:
            data["date"] = (
                f"{current_year}-{max(int(date_parts[1]), 10)}-{date_parts[2]}"
            )

    await collection.update_one(
        {"task_id": task_id, "auth_email": auth_email}, {"$set": data}
    )


async def check_invoice_exists(pdf_path: str, auth_email: str) -> bool:
    document = await collection.find_one(
        {"pdf_path": pdf_path, "auth_email": auth_email}
    )
    return document is not None

from utils.schemas import InvoiceResponseModel

async def get_all_invoices(auth_email: str) -> list:
    invoices = []
    cursor = collection.find({"auth_email": auth_email})
    async for document in cursor:
        document.pop("_id", None)
        document["file_link"] = (
            f"{config.ROOT_URL}/files/{document['pdf_path'].split('/')[-1]}"
        )
        try:
            InvoiceResponseModel.model_validate(document)
            invoices.append(document)
        except Exception:
            pass
    return invoices
