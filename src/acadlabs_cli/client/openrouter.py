"""OpenRouter API client"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class OpenRouterClient:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.api_key = os.getenv("OPENROUTER_API_KEY")

# Singleton instance
openrouter_client = OpenRouterClient()

def ask_ai(message: str, history: list = None):
    """Kirim pesan ke OpenRouter"""
    if history is None:
        history = []
    
    # Setup system prompt (karakter AI kamu)
    messages = [
        {"role": "system", "content": "Kamu adalah asisten coding pintar dari Acadlabs."},
    ] + history + [{"role": "user", "content": message}]

    try:
        completion = openrouter_client.client.chat.completions.create(
            model="astepfun/step-3.5-flash:free",  # Ganti model sesuka hati
            messages=messages,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error AI: {e}"
