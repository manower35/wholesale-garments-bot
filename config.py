import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Token (required)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Google Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Groq API Key (free, fast alternative)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Hugging Face API Key (for free embeddings)
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Database Path
DB_PATH = os.getenv("DB_PATH", "database.db")

# Admin Registration Token (for the owner to claim admin access if they don't hardcode their ID)
# Default is 'admin12345'
ADMIN_SETUP_TOKEN = os.getenv("ADMIN_SETUP_TOKEN", "admin12345")

# Business Card Contact Details
BUSINESS_NAME = "AT SELECTION"
BUSINESS_SUBTITLE = "Wholesale Readymade Garments"
OWNER_NAME = "Syed Ahmer"
OWNER_EMAILS = ["atselection025@gmail.com"]
OWNER_PHONES = ["9701515477", "8019925500", "8019924400"]
BUSINESS_ADDRESS = "1st Floor, Shop No. 7,8,9, City Plaza Complex, Dewan Dewdi, Hyderabad, T.S."
BUSINESS_HOURS = "10:00 AM – 10:00 PM"

# Social/Chat Links
WHATSAPP_LINK = f"https://wa.me/91{OWNER_PHONES[0]}"
INSTAGRAM_LINK = "https://instagram.com/atselection025" # Placeholder or admin-configurable
MAPS_LINK = "https://maps.google.com/?q=City+Plaza+Complex+Dewan+Dewdi+Hyderabad"

# CrewAI Multi-Agent System (set to True to enable CrewAI, False for simple LangChain)
# NOTE: CrewAI uses 2+ LLM calls per message (slow). LangChain uses 1 call (fast).
CREWAI_ENABLED = False

# WhatsApp Gateway & Bridge Settings
WHATSAPP_PORT = int(os.getenv("WHATSAPP_PORT", 5000))
WHATSAPP_BRIDGE_URL = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3001")
