"""File Operations - Tools for reading, writing, and listing files"""
import os


def read_file(path: str, offset: int = 0, limit: int = 100) -> str:
    """
    Membaca isi file dari path yang diberikan.
    
    Args:
        path: Path absolut atau relatif ke file
        offset: Line number mulai (0-indexed)
        limit: Jumlah maksimal baris yang dibaca
    
    Returns:
        Isi file sebagai string
    """
    try:
        # Security: Cegah path traversal
        if ".." in path or path.startswith("/etc") or path.startswith("~"):
            return f"Error: Access denied to path '{path}'"
        
        if not os.path.exists(path):
            return f"Error: File not found: '{path}'"
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        # Apply offset and limit
        start = offset
        end = offset + limit if limit > 0 else len(lines)
        selected_lines = lines[start:end]
        
        # Format dengan line numbers
        result = []
        for i, line in enumerate(selected_lines, start=offset + 1):
            result.append(f"{i:4d} | {line.rstrip()}")
        
        return "\n".join(result) if result else "(empty file)"
    
    except Exception as e:
        return f"Error reading file: {e}"


def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """
    Melihat isi direktori.
    
    Args:
        path: Path ke direktori (default: current directory)
        show_hidden: Tampilkan hidden files
    
    Returns:
        Daftar file dan folder
    """
    try:
        # Security check
        if ".." in path:
            return "Error: Path traversal not allowed"
        
        if not os.path.exists(path):
            return f"Error: Directory not found: '{path}'"
        
        if not os.path.isdir(path):
            return f"Error: '{path}' is not a directory"
        
        items = os.listdir(path)
        
        if not show_hidden:
            items = [i for i in items if not i.startswith('.')]
        
        # Sort: folders first, then files
        folders = []
        files = []
        
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                folders.append(f"DIR   {item}/")
            else:
                size = os.path.getsize(full_path)
                files.append(f"FILE  {item} ({size} bytes)")
        
        result = [f"Contents of '{path}':", "-" * 40]
        result.extend(sorted(folders))
        result.extend(sorted(files))
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error listing directory: {e}"


def write_file(path: str, content: str, mode: str = "write") -> str:
    """
    Menulis ke file (DANGEROUS - perlu konfirmasi user).
    
    Args:
        path: Path ke file
        content: Konten yang akan ditulis
        mode: "write" (overwrite) atau "append"
    
    Returns:
        Status operasi
    """
    # WARNING: Fungsi ini harus di-handle dengan konfirmasi user
    
    try:
        # Security: Cek ekstensi berbahaya
        dangerous_exts = ['.exe', '.bat', '.cmd', '.sh', '.ps1']
        if any(path.lower().endswith(ext) for ext in dangerous_exts):
            return f"Error: Writing to '{path}' is blocked for safety"
        
        write_mode = 'w' if mode == "write" else 'a'
        
        # Buat direktori jika belum ada
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(path, write_mode, encoding='utf-8') as f:
            f.write(content)
        
        action = "written to" if mode == "write" else "appended to"
        return f"Success: Content {action} '{path}'"
    
    except Exception as e:
        return f"Error writing file: {e}"


def replace_code_block(path: str, old_code: str, new_code: str, replace_all: bool = False) -> str:
    """
    Mengganti blok kode lama dengan blok kode baru (DANGEROUS - perlu konfirmasi user).
    
    Jauh lebih efisien daripada rewrite seluruh file. AI hanya perlu mengirim
    blok kode yang lama dan yang baru, fungsi ini akan mencari dan menggantinya.
    
    Args:
        path: Path ke file yang akan diedit
        old_code: Blok kode yang akan dicari dan diganti (harus exact match)
        new_code: Blok kode baru untuk menggantikan old_code
        replace_all: Jika True, ganti semua kemunculan old_code (default: False)
    
    Returns:
        Status operasi dengan detail perubahan
    """
    # WARNING: Fungsi ini harus di-handle dengan konfirmasi user
    
    try:
        # Security: Cek ekstensi berbahaya
        dangerous_exts = ['.exe', '.bat', '.cmd', '.sh', '.ps1']
        if any(path.lower().endswith(ext) for ext in dangerous_exts):
            return f"Error: Editing '{path}' is blocked for safety"
        
        # Security: Cegah path traversal
        if ".." in path or path.startswith("/etc") or path.startswith("~"):
            return f"Error: Access denied to path '{path}'"
        
        if not os.path.exists(path):
            return f"Error: File not found: '{path}'"
        
        # Baca file
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cari old_code
        if old_code not in content:
            # Berikan hint tentang kemungkinan masalah
            hints = []
            
            # Cek apakah ada whitespace mismatch
            old_lines = old_code.strip().split('\n')
            content_lines = content.strip().split('\n')
            
            # Cari baris pertama yang cocok
            first_line = old_lines[0].strip() if old_lines else ""
            for i, line in enumerate(content_lines):
                if first_line and first_line in line:
                    hints.append(f"Hint: Baris pertama old_code ditemukan di sekitar line {i+1}, mungkin ada whitespace/indentation mismatch")
                    break
            
            # Cek ukuran
            if len(old_code) < 10:
                hints.append("Hint: old_code terlalu pendek, gunakan blok kode yang lebih besar untuk keunikan")
            
            hint_msg = "\n".join(hints) if hints else "Pastikan old_code exactly match dengan isi file (termasuk whitespace/indentation)"
            
            return f"Error: old_code tidak ditemukan di file.\n{hint_msg}"
        
        
        # Hitung jumlah kemunculan
        occurrences = content.count(old_code)
        
        if occurrences > 1 and not replace_all:
            return (
                f"Error: old_code ditemukan {occurrences} kali di file. "
                f"Gunakan replace_all=True untuk mengganti semua kemunculan, "
                f"atau perbesar blok kode untuk membuatnya unik."
            )
        
        
        # Lakukan replacement
        if replace_all:
            new_content = content.replace(old_code, new_code)
            count = occurrences
        else:
            new_content = content.replace(old_code, new_code, 1)
            count = 1
        
        # Tulis kembali file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Hitung statistik perubahan
        old_lines = old_code.count('\n') + 1
        new_lines = new_code.count('\n') + 1
        
        return (
            f"Success: Replaced {count} occurrence(s) in '{path}'\n"
            f"  - Old: {old_lines} lines\n"
            f"  - New: {new_lines} lines\n"
            f"  - File size: {len(content)} -> {len(new_content)} bytes"
        )
    
    except Exception as e:
        return f"Error editing file: {e}"
