"""Frontend configuration."""

import os

# Backend API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# App branding
APP_TITLE = "Research Paper Analyzer"
APP_ICON = "🔬"
APP_TAGLINE = "AI-powered Q&A for academic research papers"

# UI settings
PAGE_SIZE = 10
MAX_QUESTION_LENGTH = 2000
DEFAULT_TOP_K = 5
DEFAULT_TEMPERATURE = 0.1

# Supported file types
ALLOWED_FILE_TYPES = ["pdf", "txt"]
MAX_FILE_SIZE_MB = 50

# Colour palette (used in markdown / HTML snippets)
PRIMARY_COLOR = "#4F8BF9"
SECONDARY_COLOR = "#0e1117"
SUCCESS_COLOR = "#00C851"
WARNING_COLOR = "#FF8800"
ERROR_COLOR = "#FF4444"
