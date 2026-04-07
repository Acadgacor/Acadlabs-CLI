"""OpenRouter API client with Function Calling support"""
import json
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

class OpenRouterClient:
    def __init__(self):
        self.default_model = "nvidia/nemotron-3-super-120b-a12b:free"  # Model default

    @property
    def client(self):
        # Import supabase client di dalam sini untuk menghindari circular import
        from acadlabs_cli.client.supabase import supabase_client
        
        # Ambil Karcis Masuk (JWT Token) dari user yang udah login di CLI
        token = supabase_client.access_token
        
        if not token:
            token = "belum-login" # Biar gak error kalau ngetest, tapi nanti akan ditolak server
            
        # Bikin client OpenAI tapi diarahkan ke Supabase Edge Function
        return OpenAI(
            base_url="https://zmavvvayuyiceccgjaux.supabase.co/functions/v1/hyper-responder", 
            api_key=token, # Kita masukin JWT Token kesini, BUKAN masukin API Key OpenRouter!
        )

# Singleton instance
openrouter_client = OpenRouterClient()


def get_system_prompt() -> str:
    """System prompt untuk AI dengan tool calling"""
    return """Kamu adalah asisten coding pintar dari Acadlabs CLI.

Kamu memiliki akses ke TOOLS untuk membantu user:
- read_file: Membaca isi file
- list_directory: Melihat struktur folder
- search_code: Mencari kode di project
- run_terminal_command: Menjalankan command (PERLU KONFIRMASI)
- write_file: Menulis ke file (PERLU KONFIRMASI)
- get_current_directory: Melihat current directory

ALUR KERJA:
1. Jika user minta analisis kode -> gunakan read_file, search_code, list_directory
2. Jika perlu mengubah file -> gunakan write_file (akan minta konfirmasi)
3. Jika perlu menjalankan command -> gunakan run_terminal_command (akan minta konfirmasi)

PENTING:
- Selalu eksplorasi dulu dengan read_file/list_directory sebelum mengusulkan perubahan
- Jelaskan apa yang akan kamu lakukan sebelum memanggil tool berbahaya
- Jika tool error, analisis dan coba cara lain"""


def ask_ai(message: str, history: list = None) -> str:
    """Kirim pesan ke OpenRouter (tanpa tools - backward compatible)"""
    if history is None:
        history = []
    
    messages = [
        {"role": "system", "content": get_system_prompt()},
    ] + history + [{"role": "user", "content": message}]

    try:
        completion = openrouter_client.client.chat.completions.create(
            model=openrouter_client.default_model,
            messages=messages,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error AI: {e}"


def ask_ai_with_tools(
    message: str,
    history: list = None,
    tools_schema: List[Dict] = None
) -> Tuple[Optional[str], Optional[List[Dict]]]:
    """
    Kirim pesan ke OpenRouter dengan function calling support.
    
    Args:
        message: Pesan dari user
        history: Chat history
        tools_schema: Schema tools dari get_tools_schema()
    
    Returns:
        (text_response, tool_calls) - salah satu bisa None
        - text_response: Teks balasan AI
        - tool_calls: List of tool calls [{"name": "...", "arguments": {...}}]
    """
    if history is None:
        history = []
    
    if tools_schema is None:
        # Jika tidak ada tools, gunakan fungsi biasa
        return ask_ai(message, history), None
    
    messages = [
        {"role": "system", "content": get_system_prompt()},
    ] + history + [{"role": "user", "content": message}]

    try:
        completion = openrouter_client.client.chat.completions.create(
            model=openrouter_client.default_model,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",  # AI memilih kapan menggunakan tools
        )
        
        message_obj = completion.choices[0].message
        
        # Cek apakah ada tool calls
        if message_obj.tool_calls:
            tool_calls = []
            for tc in message_obj.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })
            return message_obj.content, tool_calls
        
        # Jika tidak ada tool calls, return text saja
        return message_obj.content, None
        
    except Exception as e:
        return f"Error AI: {e}", None


def send_tool_results(
    history: list,
    tool_calls: List[Dict],
    tool_results: List[str]
) -> Tuple[Optional[str], Optional[List[Dict]]]:
    """
    Mengirim hasil eksekusi tools kembali ke AI untuk analisis.
    
    Args:
        history: Chat history sebelumnya
        tool_calls: Tool calls yang dieksekusi
        tool_results: Hasil dari setiap tool call
    
    Returns:
        (text_response, tool_calls) - response berikutnya dari AI
    """
    # Build messages dengan tool results
    messages = [
        {"role": "system", "content": get_system_prompt()},
    ] + history
    
    # Tambahkan assistant message dengan tool calls
    assistant_message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"])
                }
            }
            for tc in tool_calls
        ]
    }
    messages.append(assistant_message)
    
    # Tambahkan tool results
    for tc, result in zip(tool_calls, tool_results):
        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "name": tc["name"],
            "content": result
        })
    
    # Import tools schema
    from acadlabs_cli.tools import get_tools_schema
    tools_schema = get_tools_schema()
    
    try:
        completion = openrouter_client.client.chat.completions.create(
            model=openrouter_client.default_model,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
        )
        
        message_obj = completion.choices[0].message
        
        if message_obj.tool_calls:
            tool_calls = []
            for tc in message_obj.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })
            return message_obj.content, tool_calls
        
        return message_obj.content, None
        
    except Exception as e:
        return f"Error AI: {e}", None
