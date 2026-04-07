import os
import webbrowser
import http.server
import socketserver
import urllib.parse
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# ... (fungsi login_user email/password tetap ada) ...

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
        print(f"\n🔐 Buka link ini untuk login dengan Google:")
        print(f"[bold blue]{auth_url}[/bold blue]\n")
        
        # 2. Otomatis buka browser
        webbrowser.open(auth_url)
        
        # 3. Mulai server lokal sederhana untuk tangkap callback
        print("⏳ Menunggu autentikasi... (Ctrl+C untuk batal)")
        
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if "/callback" in self.path:
                    # Parse token dari URL
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Cek kalau ada access_token atau error
                    if "error" in params:
                        print(f"\n❌ Error: {params['error'][0]}")
                    elif "access_token" in params or "code" in params:
                        print("\n✅ Login Google berhasil! 🎉")
                        print("🔄 Session sudah disimpan, kamu bisa mulai chat.")
                    
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
        print("\n⚠️ Login dibatalkan.")
        return False
    except Exception as e:
        print(f"\n❌ Error saat login Google: {e}")
        print("\n💡 Alternatif: Login manual via web Acadlabs, lalu copy session token.")
        return False