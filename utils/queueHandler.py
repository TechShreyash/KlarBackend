import asyncio
import logging
import pathlib
from typing import List, Tuple
import uuid

import config
from utils import db
from utils.extractor import InvoiceExtractor
from utils.postProcessor import handle_processed_result
from utils.schemas import InvoiceExtractionSchema
from utils.vendors import get_current_vendors

logger = logging.getLogger(__name__)

# --- Task/Result Queue Definitions ---
# A task is now just an ID and a file path
ProcessTask = Tuple[str, pathlib.Path]
# A result includes its ID, status, and the data (or error message)
ProcessResult = Tuple[str, str, InvoiceExtractionSchema | str]

# --- Global Queues ---
task_queue = asyncio.Queue[ProcessTask]()
result_queue = asyncio.Queue[ProcessResult]()


# --- Public-Facing Functions ---


async def add_task_to_queue(pdf_path_str: str) -> str:
    """
    Public function to add a new PDF processing task to the queue.

    Args:
        pdf_path_str: The string path to the PDF file.

    Returns:
        The unique task_id for this job.
    """
    task_id = str(uuid.uuid4())
    pdf_path = pathlib.Path(pdf_path_str)

    if not pdf_path.exists():
        logger.error(
            f"[Task {task_id}] File not found: {pdf_path_str}. Task not added."
        )
        raise FileNotFoundError(f"File not found: {pdf_path_str}")

    # The task is now much lighter, as requested.
    task = (task_id, pdf_path)

    await task_queue.put(task)
    await db.add_invoice({"task_id": task_id, "pdf_path": pdf_path_str})
    logger.info(f"[Task {task_id}] Added to queue: {pdf_path.name}")
    return task_id


async def worker(name: str, extractor: InvoiceExtractor):
    """
    A single worker coroutine.
    Pulls tasks from task_queue, processes them, and puts results in result_queue.
    """
    logger.info(f"[{name}] Worker starting...")
    while True:
        task_id = None
        try:
            # 1. Get the light task (ID and path)
            task_id, pdf_path = await task_queue.get()

            logger.info(f"[{name}] [Task {task_id}] Processing {pdf_path.name}...")

            # 2. Fetch the LATEST vendor list just-in-time
            logger.info(f"[{name}] [Task {task_id}] Fetching latest vendor list...")
            current_vendors_snapshot = await get_current_vendors()

            # 3. Run extraction
            extracted_data = await extractor.extract_from_pdf_async(
                pdf_path, current_vendors_snapshot
            )

            # 4. Put the full result on the result queue
            await result_queue.put((task_id, "SUCCESS", extracted_data))
            logger.info(f"[{name}] [Task {task_id}] Finished {pdf_path.name}.")

        except Exception as e:
            if task_id is not None:
                logger.error(
                    f"[{name}] [Task {task_id}] Unhandled error in worker: {e}",
                    exc_info=True,
                )
                await result_queue.put((task_id, "ERROR", str(e)))
            else:
                logger.error(
                    f"[{name}] Worker failed before acquiring task: {e}", exc_info=True
                )
        finally:
            # Ensure task_done is called even if errors occur
            if task_id is not None:
                task_queue.task_done()


async def result_processor():
    """
    A single result processor coroutine.
    Pulls results from result_queue and calls the handler function.
    """
    logger.info("[ResultProcessor] Starting...")
    while True:
        task_id = None
        try:
            task_id, status, data = await result_queue.get()
            await handle_processed_result(task_id, status, data)
        except Exception as e:
            if task_id:
                logger.error(
                    f"[ResultProcessor] [Task {task_id}] Critical error in handle_processed_result: {e}",
                    exc_info=True,
                )
            else:
                logger.error(
                    f"[ResultProcessor] Critical error before processing task: {e}",
                    exc_info=True,
                )
        finally:
            result_queue.task_done()


async def run_service():
    """
    Main asynchronous function to start all workers and the result processor.
    """
    if not config.GOOGLE_API_KEYS or len(config.GOOGLE_API_KEYS) == 0:
        logger.critical("No GOOGLE_API_KEYS found in config.py. Exiting.")
        return

    num_workers = len(config.GOOGLE_API_KEYS)
    logger.info(f"Starting service with {num_workers} workers.")

    # Start workers
    worker_tasks = []
    for i, api_key in enumerate(config.GOOGLE_API_KEYS):
        worker_name = f"Worker-{i+1}"
        extractor = InvoiceExtractor(api_key=api_key)
        task = asyncio.create_task(worker(worker_name, extractor), name=worker_name)
        worker_tasks.append(task)

    # Start the single result processor
    result_task = asyncio.create_task(result_processor(), name="ResultProcessor")

    # --- Demo: Add initial tasks ---
    logger.info("Adding demo tasks...")
    pdf_dir = pathlib.Path("tests")
    if pdf_dir.exists():
        demo_tasks = []
        for pdf_path in pdf_dir.glob("*.pdf"):
            if not (await db.check_invoice_exists(str(pdf_path))):
                demo_tasks.append(add_task_to_queue(str(pdf_path)))

        if demo_tasks:
            await asyncio.gather(*demo_tasks)
            logger.info(f"Added {len(demo_tasks)} demo tasks.")
        else:
            logger.warning(f"No demo PDFs found in 'tests/' directory.")
    else:
        logger.warning("'tests/' directory not found. No demo tasks added.")

    # Keep the service alive
    logger.info("Service is running. Workers are watching for new tasks.")
    await asyncio.gather(*worker_tasks, result_task)
