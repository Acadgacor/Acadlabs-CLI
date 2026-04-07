"""Supabase client - HTTP-based implementation"""
import os
import json
import webbrowser
import http.server
import socketserver
import urllib.parse
import httpx
from pathlib import Path

# Session file path
SESSION_FILE = Path.home() / ".acadlabs" / "session.json"

def _get_supabase_credentials():
    """Get Supabase URL and key - hardcoded for plug-and-play"""
    # Hardcoded credentials - ganti dengan nilai asli dari project Supabase Anda
    return "https://zmavvvayuyiceccgjaux.supabase.co", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InptYXZ2dmF5dXlpY2VjY2dqYXV4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUwMTUxNzMsImV4cCI6MjA3MDU5MTE3M30.iahcYkRx1x7GdMCKWgNBXMYoSqbleVKmowARxXeechA"

class SupabaseClient:
    def __init__(self):
        self.url, self.key = _get_supabase_credentials()
        self.client = httpx.Client(base_url=self.url, timeout=30.0)
        self.access_token = None
        self.refresh_token = None
        self.user = None
        # Load saved session
        self._load_session()

    def _load_session(self):
        """Load session from file"""
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, "r") as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    self.user = data.get("user")
            except Exception:
                pass

    def _save_session(self):
        """Save session to file"""
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_FILE, "w") as f:
            json.dump({
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "user": self.user
            }, f)

    def _clear_session(self):
        """Clear session file"""
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        self.access_token = None
        self.refresh_token = None
        self.user = None
    
    def _headers(self, with_auth=True):
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json",
        }
        if with_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def sign_in_with_password(self, email: str, password: str):
        """Login dengan email/password"""
        try:
            response = self.client.post(
                "/auth/v1/token?grant_type=password",
                headers=self._headers(with_auth=False),
                json={"email": email, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.user = data.get("user")
                self._save_session()  # Persist to file
                return data
            else:
                print(f"Login error: {response.text}")
                return None
        except Exception as e:
            print(f"Error login: {e}")
            return None
    
    def get_user(self):
        """Get current user info"""
        if not self.access_token:
            return None
        try:
            response = self.client.get(
                "/auth/v1/user",
                headers=self._headers()
            )
            if response.status_code == 200:
                self.user = response.json()
                # Create object with .user.id accessible
                user_data = type('UserData', (), {k: v for k, v in self.user.items() if not k.startswith('_')})()
                return type('User', (), {'user': user_data})()
            return None
        except Exception:
            return None
    
    def sign_in_with_oauth(self, provider: str, options: dict = None):
        """Generate OAuth URL"""
        if options is None:
            options = {}
        redirect_to = options.get("redirect_to", "http://localhost:54321/callback")
        scopes = options.get("scopes", "email profile")
        
        # Build OAuth URL manually
        auth_url = f"{self.url}/auth/v1/authorize?provider={provider}&redirect_to={redirect_to}&scopes={scopes}"
        
        return type('AuthResponse', (), {'url': auth_url})()
    
    def table(self, table_name: str):
        """Create table query builder"""
        return TableQuery(self, table_name)

class TableQuery:
    def __init__(self, client: SupabaseClient, table_name: str):
        self.client = client
        self.table_name = table_name
        self._query = {}
    
    def insert(self, data: dict):
        """Insert data"""
        self._query["data"] = data
        return self
    
    def execute(self):
        """Execute the query"""
        try:
            response = self.client.client.post(
                f"/rest/v1/{self.table_name}",
                headers=self.client._headers(),
                json=self._query.get("data", {})
            )
            if response.status_code in [200, 201]:
                return type('Response', (), {'data': response.json()})()
            else:
                print(f"Error: {response.text}")
                return type('Response', (), {'data': None})()
        except Exception as e:
            print(f"Error: {e}")
            return type('Response', (), {'data': None})()

# Singleton instance
supabase_client = SupabaseClient()

# Create supabase-like interface for compatibility
class SupabaseWrapper:
    def __init__(self, client: SupabaseClient):
        self._client = client
        self.auth = type('Auth', (), {
            'sign_in_with_password': lambda self, **kwargs: client.sign_in_with_password(**kwargs),
            'get_user': lambda self: client.get_user(),
            'sign_in_with_oauth': lambda self, **kwargs: client.sign_in_with_oauth(**kwargs),
        })()
    
    def table(self, table_name: str):
        return self._client.table(table_name)

supabase = SupabaseWrapper(supabase_client)

def login_user(email: str, password: str):
    """Login dengan email/password"""
    try:
        result = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return result
    except Exception as e:
        print(f"Error login: {e}")
        return None

def save_chat_to_db(chat_id: str, user_id: str, title: str, created_at: str, message: str = None) -> bool:
    """Simpan chat session ke database. Returns True jika sukses."""
    try:
        data = {
            "id": chat_id,
            "user_id": user_id,
            "title": title,
            "created_at": created_at,
            "message": message or ""  # Selalu isi, jangan None
        }
        result = supabase.table("chats").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error saving chat: {e}")
        return False

def save_message_to_db(message_id: str, role: str, content: str, chat_id: str, user_id: str, created_at: str) -> bool:
    """Simpan message ke database. Returns True jika sukses."""
    try:
        supabase.table("messages").insert({
            "id": message_id,
            "role": role,
            "content": content,
            "chat_id": chat_id,
            "user_id": user_id,
            "created_at": created_at
        }).execute()
        return True
    except Exception as e:
        print(f"Error saving message: {e}")
        return False

def login_with_google():
    """Login dengan Google OAuth (PKCE Flow)"""
    try:
        # 1. Generate auth URL dengan PKCE
        auth_response = supabase.auth.sign_in_with_oauth(
            provider="google",
            options={
                "scopes": "email profile",
                # Redirect ke localhost untuk tangkap token
                "redirect_to": "http://localhost:54321/callback"
            }
        )
        
        auth_url = auth_response.url
        print(f"\n Buka link ini untuk login dengan Google:")
        print(f"[bold blue]{auth_url}[/bold blue]\n")

        # 2. Otomatis buka browser (coba Chrome dulu)
        try:
            chrome_path = None
            import subprocess
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break

            if chrome_path:
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                webbrowser.get('chrome').open(auth_url)
            else:
                # Fallback ke browser default
                webbrowser.open(auth_url)
        except Exception:
            webbrowser.open(auth_url)
        
        # 3. Mulai server lokal sederhana untuk tangkap callback
        print(" Menunggu autentikasi... (Ctrl+C untuk batal)")
        
        # Variable to store tokens from callback
        callback_tokens = {"data": None}
        
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if "/callback" in self.path:
                    # Parse token dari URL query string
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Cek kalau ada access_token (dari redirect JS)
                    if "access_token" in params:
                        # Simpan token ke client
                        supabase_client.access_token = params["access_token"][0]
                        supabase_client.refresh_token = params.get("refresh_token", [None])[0]
                        supabase_client._save_session()  # Persist to file
                        callback_tokens["data"] = params
                        print("\n Login Google berhasil!")
                        print(" Session sudah disimpan, kamu bisa mulai chat.")
                        
                        # Kirim response ke browser
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"<html><body><h1>Login berhasil! Kembali ke terminal.</h1><script>window.close()</script></body></html>")
                    else:
                        # Token ada di fragment, kirim HTML untuk extract dan redirect
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        html = b"""
                        <html><body>
                        <h1>Processing login...</h1>
                        <script>
                            // Extract fragment and redirect with tokens as query params
                            var hash = window.location.hash.substring(1);
                            if (hash) {
                                window.location.href = '/callback?' + hash;
                            }
                        </script>
                        </body></html>
                        """
                        self.wfile.write(html)
                
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress log
        
        # Jalankan server lokal di port 54321
        with socketserver.TCPServer(("localhost", 54321), CallbackHandler) as httpd:
            # Handle requests sampai token diterima
            while callback_tokens["data"] is None:
                httpd.handle_request()
        
        return True
        
    except KeyboardInterrupt:
        print("\n Login dibatalkan.")
        return False
    except Exception as e:
        print(f"\n Error saat login Google: {e}")
        print("\n Alternatif: Login manual via web Acadlabs, lalu copy session token.")
        return False
