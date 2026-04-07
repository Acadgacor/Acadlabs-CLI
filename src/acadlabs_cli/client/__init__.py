"""Client modules"""
from acadlabs_cli.client.openrouter import ask_ai, openrouter_client
from acadlabs_cli.client.supabase import (
    login_user, 
    login_with_google, 
    save_chat_to_db, 
    save_message_to_db, 
    supabase,
    supabase_client
)

__all__ = [
    "ask_ai",
    "openrouter_client",
    "login_user",
    "login_with_google",
    "save_chat_to_db",
    "save_message_to_db",
    "supabase",
    "supabase_client",
]
