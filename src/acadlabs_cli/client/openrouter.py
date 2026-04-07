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
    system_prompt = """Kamu adalah asisten coding pintar dari Acadlabs.

PENTING - Human-in-the-Loop:
Kamu TIDAK BOLEH mengeksekusi command atau mengubah file secara langsung.
Ketika kamu ingin melakukan aksi yang mengubah sistem, gunakan format ini:

[ACTION]
type: <command|file_write|file_delete|package_install>
target: <file_path atau command>
description: <penjelasan singkat>
[/ACTION]

Contoh:
[ACTION]
type: file_write
target: src/main.py
description: Menambahkan fungsi hello_world
[/ACTION]

Tunggu konfirmasi dari pengguna sebelum aksi benar-benar dieksekusi.
Jika pengguna menolak, tawarkan alternatif yang lebih aman."""

    messages = [
        {"role": "system", "content": system_prompt},
    ] + history + [{"role": "user", "content": message}]

    try:
        completion = openrouter_client.client.chat.completions.create(
            model="astepfun/step-3.5-flash:free",  # Ganti model sesuka hati
            messages=messages,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error AI: {e}"
