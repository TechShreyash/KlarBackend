import motor.motor_asyncio
import config

client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_DB_URL)
db = client.KlerBackend
collection = db.invoices


async def add_invoice(data: dict):
    data["status"] = "pending"
    await collection.update_one(
        {"pdf_path": data["pdf_path"]}, {"$set": data}, upsert=True
    )


async def update_invoice(task_id: str, data: dict):
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
            data["date"] = f"{current_year}-{date_parts[1]}-{date_parts[2]}"

    await collection.update_one({"task_id": task_id}, {"$set": data})


async def check_invoice_exists(pdf_path: str) -> bool:
    document = await collection.find_one({"pdf_path": pdf_path})
    return document is not None


async def get_all_invoices():
    invoices = []
    cursor = collection.find({})
    async for document in cursor:
        document.pop("_id", None)
        invoices.append(document)
    return invoices
