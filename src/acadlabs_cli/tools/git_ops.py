"""Git Operations - Tools for git status, diff, and log"""
import os
import subprocess


def git_status() -> str:
    """
    Menjalankan git status untuk melihat file yang dimodifikasi.
    
    Returns:
        Output dari git status
    """
    try:
        # Cek apakah ini git repository
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            return "Info: Ini bukan git repository. Git commands tidak tersedia."
        
        result = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        if not result.stdout.strip():
            return "Git status: Working tree clean (tidak ada perubahan)"
        
        # Parse dan format output
        lines = result.stdout.strip().split('\n')
        output = ["Git Status - File yang berubah:", "-" * 40]
        
        for line in lines:
            status = line[:2].strip()
            filepath = line[3:]
            
            # Status codes
            status_map = {
                'M': 'Modified',
                'A': 'Added',
                'D': 'Deleted',
                'R': 'Renamed',
                'C': 'Copied',
                '??': 'Untracked',
                '!!': 'Ignored'
            }
            
            status_text = status_map.get(status, status)
            output.append(f"  [{status}] {status_text}: {filepath}")
        
        
        return '\n'.join(output)
    
    except subprocess.TimeoutExpired:
        return "Error: git status timeout"
    except FileNotFoundError:
        return "Error: git tidak ditemukan. Install git terlebih dahulu."
    except Exception as e:
        return f"Error: {e}"


def git_diff(target: str = "", staged: bool = False) -> str:
    """
    Menjalankan git diff untuk melihat perubahan detail.
    
    Args:
        target: File atau commit spesifik (optional)
        staged: Jika True, tampilkan staged changes
    
    Returns:
        Output dari git diff
    """
    try:
        # Cek apakah ini git repository
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            return "Info: Ini bukan git repository. Git commands tidak tersedia."
        
        
        # Build command
        cmd = ['git', 'diff']
        if staged:
            cmd.append('--staged')
        if target:
            cmd.append(target)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        if not result.stdout.strip():
            return "Git diff: Tidak ada perubahan untuk ditampilkan"
        
        # Truncate jika terlalu panjang
        diff_output = result.stdout
        if len(diff_output) > 3000:
            diff_output = diff_output[:3000] + "\n... (truncated, diff terlalu panjang)"
        
        
        return f"Git Diff:\n{diff_output}"
    
    except subprocess.TimeoutExpired:
        return "Error: git diff timeout"
    except FileNotFoundError:
        return "Error: git tidak ditemukan. Install git terlebih dahulu."
    except Exception as e:
        return f"Error: {e}"


def git_log(limit: int = 10) -> str:
    """
    Menjalankan git log untuk melihat commit history.
    
    Args:
        limit: Jumlah maksimal commit yang ditampilkan
    
    Returns:
        Output dari git log (oneline format)
    """
    try:
        # Cek apakah ini git repository
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            return "Info: Ini bukan git repository. Git commands tidak tersedia."
        
        
        result = subprocess.run(
            ['git', 'log', '--oneline', f'-{limit}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        if not result.stdout.strip():
            return "Git log: Belum ada commit"
        
        lines = result.stdout.strip().split('\n')
        output = [f"Git Log (last {limit} commits):", "-" * 40]
        output.extend(lines)
        
        return '\n'.join(output)
    
    except subprocess.TimeoutExpired:
        return "Error: git log timeout"
    except FileNotFoundError:
        return "Error: git tidak ditemukan. Install git terlebih dahulu."
    except Exception as e:
        return f"Error: {e}"
