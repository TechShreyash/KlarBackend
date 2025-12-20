# sample_config.py
# ------------------------------------------------------------------------------
# Configuration Template
# ------------------------------------------------------------------------------
# INSTRUCTIONS:
# 1. Copy this file and rename it to 'config.py'.
# 2. 'config.py' is gitignored, so your secrets will not be committed.
# 3. Fill in the values below with your actual configuration.
# ------------------------------------------------------------------------------

# --- AI Configuration ---
# List of Google Gemini API keys.
# Providing multiple keys allows the system to spawn multiple concurrent workers
# (one per key) to increase processing throughput.
GOOGLE_API_KEYS: list[str] = [
    "YOUR_GEMINI_API_KEY_1",
    "YOUR_GEMINI_API_KEY_2",
]

# --- Database Configuration ---
# Connection string for your MongoDB instance.
# Example: "mongodb://localhost:27017" or your MongoDB Atlas connection string.
MONGO_DB_URL: str = "mongodb://localhost:27017"

# --- Server Configuration ---
# The root URL where your backend API is hosted.
# This is used for generating file links (e.g., for uploaded PDFs).
# Local development default: "http://localhost:8000"
ROOT_URL: str = "http://localhost:8000"

# --- Security Configuration ---
# Secret key used for signing JWT tokens.
# Change this to a strong, random string for production security.
JWT_SECRET: str = "your_super_secret_jwt_key_here"

# Token expiration time in minutes.
JWT_EXPIRES_MINUTES: int = 120

# Algorithm used for JWT encoding/decoding.
# Default is "HS256".
JWT_ALGORITHM: str = "HS256"
