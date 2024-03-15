import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Bot token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database connection URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./debt_tracker.db")

# Any other configuration variables can be added here
# For example, enabling logging, specifying log file paths, etc.
LOGGING_ENABLED = os.getenv("LOGGING_ENABLED", "true").lower() in ["true", "1", "t"]
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "./logs/bot.log")
