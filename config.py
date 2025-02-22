import os
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not Config.OPENAI_API_KEY:
    raise ValueError("ERROR: API Key de OpenAI no encontrada. Verifica tu archivo .env.")

if not Config.GEMINI_API_KEY:
    print("Advertencia: No se encontró una API Key de Google Gemini.")
