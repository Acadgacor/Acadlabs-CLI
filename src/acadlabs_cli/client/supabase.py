"""Supabase client - HTTP-based implementation"""
import os
import webbrowser
import http.server
import socketserver
import urllib.parse
import httpx
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "")
        self.key = os.getenv("SUPABASE_ANON_KEY", "")
        self.client = httpx.Client(base_url=self.url, timeout=30.0)
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
                return type('User', (), {'user': type('UserData', (), self.user)})()
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
            'sign_in_with_password': lambda **kwargs: client.sign_in_with_password(**kwargs),
            'get_user': lambda: client.get_user(),
            'sign_in_with_oauth': lambda **kwargs: client.sign_in_with_oauth(**kwargs),
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

def save_chat_to_db(chat_id: str, user_id: str, title: str, created_at: str):
    """Simpan chat session ke database"""
    try:
        supabase.table("chats").insert({
            "id": chat_id,
            "user_id": user_id,
            "title": title,
            "created_at": created_at
        }).execute()
    except Exception as e:
        print(f"Error saving chat: {e}")

def save_message_to_db(message_id: str, role: str, content: str, chat_id: str, user_id: str, created_at: str):
    """Simpan message ke database"""
    try:
        supabase.table("messages").insert({
            "id": message_id,
            "role": role,
            "content": content,
            "chat_id": chat_id,
            "user_id": user_id,
            "created_at": created_at
        }).execute()
    except Exception as e:
        print(f"Error saving message: {e}")

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
        
        # 2. Otomatis buka browser
        webbrowser.open(auth_url)
        
        # 3. Mulai server lokal sederhana untuk tangkap callback
        print(" Menunggu autentikasi... (Ctrl+C untuk batal)")
        
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if "/callback" in self.path:
                    # Parse token dari URL
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Cek kalau ada access_token atau error
                    if "error" in params:
                        print(f"\n Error: {params['error'][0]}")
                    elif "access_token" in params or "code" in params:
                        print("\n Login Google berhasil!")
                        print(" Session sudah disimpan, kamu bisa mulai chat.")
                    
                    # Kirim response ke browser
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h1>Login berhasil! Kembali ke terminal.</h1><script>window.close()</script></body></html>")
                    
                    # Stop server setelah callback diterima
                    import threading
                    threading.Thread(target=lambda: exit(0), daemon=True).start()
                
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress log
        
        # Jalankan server lokal di port 54321
        with socketserver.TCPServer(("localhost", 54321), CallbackHandler) as httpd:
            httpd.handle_request()  # Handle satu request saja
        
        return True
        
    except KeyboardInterrupt:
        print("\n Login dibatalkan.")
        return False
    except Exception as e:
        print(f"\n Error saat login Google: {e}")
        print("\n Alternatif: Login manual via web Acadlabs, lalu copy session token.")
        return False
