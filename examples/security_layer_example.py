"""
Contoh penggunaan 5 Layer Security System

LAYER 5: Containerization (Eksekusi Terisolasi)
- Kode AI dijalankan di Docker container ephemeral
- Tidak ada akses ke filesystem host
- Container dihancurkan setelah eksekusi

LAYER 4: Path Locking (Pembatasan Scope Direktori)
- AI hanya bisa mengakses file di dalam project directory
- Path traversal (../), home directory (~), dan sistem path diblokir

LAYER 3: Anti-Injection (Isolasi Parameter)
- Parse command dengan shlex (aman)
- Deteksi karakter injeksi: &&, ||, |, ;, $(), dll
- Eksekusi dengan shell=False (OS tidak interpret karakter spesial)

LAYER 2: Whitelist Validation
- Hanya perintah dalam COMMAND_WHITELIST yang diizinkan
- Command di luar whitelist DITOLAK OTOMATIS

LAYER 1: Human-in-the-Loop
- Setiap operasi yang lolos layer lain wajib melewati konfirmasi y/n
- User memiliki kendali penuh untuk menolak

Flow: LAYER 5 -> LAYER 4 -> LAYER 3 -> LAYER 2 -> LAYER 1 -> Eksekusi
"""

from acadlabs_cli.utils import (
    # Layer 5: Containerization
    DockerExecutor,
    ContainerizationError,
    docker_executor,
    
    # Layer 4: Path Locking
    PathLocker,
    PathLockError,
    path_locker,
    FORBIDDEN_PATHS,
    
    # Layer 3: Anti-Injection
    CommandParser,
    CommandInjectionError,
    command_parser,
    
    # Layer 2: Whitelist
    CommandWhitelist,
    CommandWhitelistError,
    COMMAND_WHITELIST,
    
    # Layer 1: Secure Executor
    run_command,
    write_file,
    delete_file,
    SecurityViolationError,
    
    # Decorator
    require_confirmation,
)


def example_layer5_containerization():
    """
    Layer 5: Eksekusi kode di Docker container terisolasi.
    """
    print("\n" + "=" * 60)
    print("LAYER 5: Containerization (Eksekusi Terisolasi)")
    print("=" * 60)
    
    docker = DockerExecutor()
    
    # Check Docker availability
    if not docker.is_docker_available():
        print("\n[INFO] Docker tidak tersedia di sistem ini")
        print("       Install Docker untuk mengaktifkan Layer 5")
        return
    
    print("\n[DOKER AVAILABLE] Container siap digunakan")
    print("\n[KEUNGGULAN LAYER 5]:")
    print("  - Kode dijalankan di container ephemeral")
    print("  - Tidak ada akses ke filesystem host")
    print("  - Memory limit: 256MB")
    print("  - CPU limit: 50%")
    print("  - Network: disabled (no internet)")
    print("  - Timeout: 30 detik")
    print("  - Container dihancurkan setelah eksekusi")


def example_layer4_path_locking():
    """
    Layer 4: AI tidak bisa mengakses path di luar project.
    """
    print("\n" + "=" * 60)
    print("LAYER 4: Path Locking (Pembatasan Scope)")
    print("=" * 60)
    
    locker = PathLocker()
    
    print(f"\n[PROJECT ROOT]: {locker.project_root}")
    print(f"\n[FORBIDDEN PATHS]: {list(FORBIDDEN_PATHS)[:5]}...")
    
    # Path yang ditolak
    forbidden_attempts = [
        "../../../etc/passwd",       # Path traversal
        "~/../secret.txt",          # Home directory
        "/etc/shadow",              # System file
        "C:\\Windows\\System32",    # Windows system
        "../.env",                  # Parent directory
    ]
    
    print("\n[PATH YANG DITOLAK]:")
    for path in forbidden_attempts:
        try:
            locker.validate(path)
            print(f"  [OK] {path}")
        except PathLockError as e:
            print(f"  [DITOLAK] {path}")
            print(f"     -> {e}")
    
    # Path yang diizinkan
    print("\n[PATH YANG DIIZINKAN] (dalam project):")
    safe_paths = [
        "src/main.py",
        "config.json",
        "data/output.txt",
    ]
    
    for path in safe_paths:
        try:
            safe = locker.validate(path)
            print(f"  [OK] {path} -> {safe}")
        except PathLockError as e:
            print(f"  [DITOLAK] {path}: {e}")


def example_layer3_anti_injection():
    """
    Layer 3: Mencegah command injection.
    """
    print("\n" + "=" * 60)
    print("LAYER 3: Anti-Injection Protection")
    print("=" * 60)
    
    parser = CommandParser()
    
    injection_attempts = [
        "npm install && rm -rf /",
        "echo hello | cat /etc/passwd",
        "git status; curl malicious.com",
        "echo $(whoami)",
    ]
    
    print("\n[KARAKTER BERBAHAYA]: &&, ||, |, ;, $(), ${}, >, <")
    
    for cmd in injection_attempts:
        has_injection, detected = parser.detect_injection(cmd)
        status = "DITOLAK" if has_injection else "OK"
        print(f"\n[{status}] {cmd}")
        if has_injection:
            print(f"   -> Injection: {detected}")


def example_layer2_whitelist():
    """
    Layer 2: Command di luar whitelist ditolak.
    """
    print("\n" + "=" * 60)
    print("LAYER 2: Whitelist Validation")
    print("=" * 60)
    
    print(f"\n[WHITELIST]: {sorted(COMMAND_WHITELIST)[:8]}...")
    
    try:
        print("\n[MENCoba] run_command('format C:')")
        run_command("format C:")
    except (CommandWhitelistError, CommandInjectionError, PathLockError) as e:
        print(f"[DITOLAK] {e}")


def example_full_flow():
    """
    Demonstrasi flow lengkap semua 5 layer.
    """
    print("\n" + "=" * 60)
    print("FLOW LENGKAP: 5 Layer Security")
    print("=" * 60)
    
    parser = CommandParser()
    whitelist = CommandWhitelist()
    locker = PathLocker()
    
    test_cases = [
        ("npm install react", "OK", "Lolos semua layer"),
        ("npm install && rm -rf /", "Layer 3", "Injection detected"),
        ("format C:", "Layer 2", "Not in whitelist"),
        ("write_file('../../../etc/passwd', 'hacked')", "Layer 4", "Path traversal"),
        ("git status", "OK", "Lolos, perlu konfirmasi y/n"),
    ]
    
    for cmd, rejected_at, reason in test_cases:
        print(f"\n[TEST] {cmd}")
        print(f"   Expected: {rejected_at} - {reason}")


def example_architecture():
    """
    Arsitektur 5 Layer Security.
    """
    print("\n" + "=" * 60)
    print("ARSITEKTUR 5 LAYER SECURITY")
    print("=" * 60)
    
    print("""
                    Command/Aksi dari AI
                           |
                           v
    +-------------------------------------------+
    | LAYER 5: Containerization (Opsional)      |
    | - Eksekusi kode di Docker container       |
    | - Ephemeral, isolated, no network         |
    +-------------------------------------------+
                           |
                           v
    +-------------------------------------------+
    | LAYER 4: Path Locking                     |
    | - Validasi path dalam project directory   |
    | - Blokir ../, ~/, /etc/, C:\\Windows      |
    +-------------------------------------------+
                           |
                           v
    +-------------------------------------------+
    | LAYER 3: Anti-Injection                   |
    | - Deteksi: &&, ||, |, ;, $()              |
    | - Parse dengan shlex, shell=False         |
    +-------------------------------------------+
                           |
                           v
    +-------------------------------------------+
    | LAYER 2: Whitelist Validation             |
    | - Hanya command di whitelist diizinkan    |
    | - npm, git, python, node, dll            |
    +-------------------------------------------+
                           |
                           v
    +-------------------------------------------+
    | LAYER 1: Human-in-the-Loop                |
    | - Konfirmasi y/n dari user                |
    | - User memiliki veto power                |
    +-------------------------------------------+
                           |
                           v
                    [EKSEKUSI AMAN]
    """)


@require_confirmation("mengubah konfigurasi sistem")
def update_config(key: str, value: str):
    """Fungsi ini akan meminta konfirmasi sebelum dijalankan"""
    print(f"Config updated: {key} = {value}")


if __name__ == "__main__":
    print("=" * 60)
    print("ACADLABS CLI - 5 LAYER SECURITY SYSTEM")
    print("=" * 60)
    
    # Demo semua layer (tidak memerlukan interaksi)
    example_layer5_containerization()
    example_layer4_path_locking()
    example_layer3_anti_injection()
    example_layer2_whitelist()
    example_full_flow()
    example_architecture()
    
    # Layer 1 demo (memerlukan interaksi y/n)
    print("\n" + "-" * 60)
    print("Untuk test Layer 1 (konfirmasi y/n), uncomment:")
    print("  from acadlabs_cli.utils import secure_executor")
    print("  secure_executor.run_command('echo Hello')")
    print("  secure_executor.write_file('test.txt', 'content')")
    print("  secure_executor.execute_in_container('print(1+1)')")
    print("-" * 60)
