
# Klar - AI-Powered Invoice Automation SaaS Platform

![Klar Banner](https://img.shields.io/badge/Klar-AI%20Invoice%20Automation-blue?style=for-the-badge&logo=google-gemini)

**Winner of Problem Statement 3 at CodeUtsava 9.0**

Klar is an intelligent, multi-tenant SaaS platform designed to streamline accounts payable by automating the extraction and processing of invoices. Leveraging the power of **Google Gemini**, Klar achieves high accuracy in data extracting, normalization, and vendor identification, capable of handling high-volume document processing with ease.

## 🚀 Key Features

- **🤖 AI-Powered Data Extraction**: Uses Google Gemini to extract key fields from invoices with >95% accuracy.
- **⚡ High-Performance Async Workers**: Built with Python `asyncio` to handle 500+ documents/day efficiently using a dedicated worker queue system.
- **🔄 Intelligent Normalization**: 
  - Automatic currency conversion.
  - Fuzzy matching for accurate vendor identification.
- **✅ Human-in-the-Loop (HITL)**: A dedicated workflow for manually verifying low-confidence AI predictions, ensuring execution data integrity.
- **📁 Multi-Format Support**: Seamlessly processes PDFs and image-based invoices (JPG, PNG) by auto-converting them.
- **🔐 Secure & Scalable**: JWT-based authentication and MongoDB for robust data storage.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI
- **Database**: MongoDB (Async Motor driver)
- **AI/ML**: Google Gemini API
- **Frontend**: React.js ([Separate repository](https://github.com/priyanshu-matrix/KlarFrontend))
- **Package Manager**: uv / pip

## 🔗 Resources

- **Frontend Repository**: [github.com/priyanshu-matrix/KlarFrontend](https://github.com/priyanshu-matrix/KlarFrontend)
- **Project Presentation**: [View Slide Deck](https://docs.google.com/presentation/d/1kz1XuOULI-U7puXUmMgN95WGXE1NeuNXrApUDuvDeyA/edit?usp=sharing)

## 📂 Project Structure

```bash
KlarBackend/
├── main.py              # Application entry point & API routes
├── config.py            # Configuration & Env variables (Gitignored)
├── utils/
│   ├── db.py            # MongoDB connection & CRUD operations
│   ├── queueHandler.py  # Async task queue & worker management
│   ├── extractor.py     # Gemini AI extraction logic
│   ├── auth.py          # JWT Authentication
│   └── ...
├── tests/               # Directory for storing uploaded/demo files
└── pyproject.toml       # Dependencies
```

## 🏁 Getting Started

### Prerequisites

- Python 3.12+
- MongoDB instance (Local or Atlas)
- Google Gemini API Key(s)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/TechShreyash/KlarBackend.git
   cd KlarBackend
   ```

2. **Install Dependencies**
   It is recommended to use `uv` for fast dependency management, but `pip` works too.
   ```bash
   # Using pip
   pip install .
   
   # OR using uv
   uv sync
   ```

3. **Configuration**
   Copy the sample configuration file to create your local config:
   ```bash
   cp sample_config.py config.py
   ```
   Open `config.py` and fill in your actual values (MongoDB URL, Gemini API Keys, etc.). This file is gitignored for security.
   > **Note**: You can provide multiple API keys in `GOOGLE_API_KEYS`. The system will spawn one worker per key to maximize throughput.

4. **Run the Application**
   ```bash
   python main.py
   ```
   The API will start at `http://0.0.0.0:8000`.

## 📖 API Documentation

Once the server is running, you can access the interactive API docs (Swagger UI) at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Core Endpoints

- **Auth**: `/auth/signup`, `/auth/login`
- **Invoices**: 
  - `POST /processInvoice`: Upload PDF/Image for processing.
  - `GET /getInvoices`: List all user invoices.
  - `GET /invoice_details/{task_id}`: Get specific invoice data.
  - `POST /updateInvoice`: Submit manual verification corrections.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">
  Created with ❤️ by the Klar Team
</p>
