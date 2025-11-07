# utils/db.py
import motor.motor_asyncio
import config

client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_DB_URL)
db = client.KlerBackend

# collections
users_collection = db.users
invoices_collection = db.invoices


# --- Users ---
async def ensure_user_indexes():
    # unique index on email
    try:
        await users_collection.create_index("email", unique=True)
    except Exception:
        pass


async def get_user_by_email(email: str) -> dict | None:
    if not email:
        return None
    return await users_collection.find_one({"email": email.lower()})


async def create_user(email: str, password_hash: str) -> dict:
    doc = {"email": email.lower(), "password_hash": password_hash}
    await users_collection.insert_one(doc)
    return {"email": doc["email"]}


# --- Invoices ---
from utils.schemas import InvoiceResponseModel


async def add_invoice(data: dict, auth_email: str):
    data["status"] = "pending"
    data["auth_email"] = auth_email
    await invoices_collection.update_one(
        {"pdf_path": data["pdf_path"], "auth_email": auth_email},
        {"$set": data},
        upsert=True,
    )


async def update_invoice(task_id: str, data: dict, auth_email: str):
    data["status"] = (
        "completed"
        if not data.get("human_verification_required")
        else "requires_human_verification"
    )
    # if "date" in data and data["date"]:
    #     from datetime import datetime

    #     current_year = datetime.now().year
    #     date_parts = data["date"].split("-")
    #     if len(date_parts) == 3:
    #         data["date"] = (
    #             f"{current_year}-{max(int(date_parts[1]),10)}-{date_parts[2]}"
    #         )
    await invoices_collection.update_one(
        {"task_id": task_id, "auth_email": auth_email}, {"$set": data}
    )


async def check_invoice_exists(pdf_path: str, auth_email: str) -> bool:
    document = await invoices_collection.find_one(
        {"pdf_path": pdf_path, "auth_email": auth_email}
    )
    return document is not None


async def get_all_invoices(auth_email: str) -> list:
    invoices = []
    cursor = invoices_collection.find({"auth_email": auth_email})
    async for document in cursor:
        document.pop("_id", None)
        document["file_link"] = (
            f"{config.ROOT_URL}/files/{document['pdf_path'].split('/')[-1]}"
        )
        try:
            InvoiceResponseModel.model_validate(document)
            invoices.append(document)
        except Exception:
            print("Invalid invoice data:", document["task_id"])
            pass
    return invoices


async def get_invoice_by_task_id(task_id: str, auth_email: str) -> dict | None:
    document = await invoices_collection.find_one(
        {"task_id": task_id, "auth_email": auth_email}
    )
    if document:
        document.pop("_id", None)
        document["file_link"] = (
            f"{config.ROOT_URL}/files/{document['pdf_path'].split('/')[-1]}"
        )
        try:
            InvoiceResponseModel.model_validate(document)
            return document
        except Exception:
            return None
    return None
