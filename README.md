# Acadlabs CLI

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Acadlabs CLI** adalah aplikasi berbasis terminal (Command Line Interface) untuk asisten coding berbasis AI. Dengan Acadlabs CLI, kamu bisa berinteraksi dengan AI langsung dari terminal untuk membantu *coding*, *debugging*, dan tugas pemrograman lainnya.

> **Prefer UI yang lebih enak?** Coba website kami di [acadlabs.fun](https://www.acadlabs.fun) untuk pengalaman dengan tampilan visual yang lebih nyaman.

---

## Fitur Utama

- **Chat dengan AI** - Tanya jawab soal coding langsung dari terminal.
- **Login dengan Email/Password** - Masuk dengan akun yang sudah terdaftar.
- **Login dengan Google** - Masuk lebih cepat dan aman dengan akun Google.
- **Riwayat Chat Tersimpan** - Semua percakapan disimpan dengan aman di *cloud*.

---

## Persyaratan Sistem

Sebelum menginstall, pastikan komputermu sudah terinstall:

- **Python 3.8 atau lebih baru** - [Download Python](https://www.python.org/downloads/)

Cek apakah Python sudah terinstall dengan menjalankan perintah ini di terminal:
```bash
python --version
# atau
python3 --version
```

---

## Cara Instalasi

Pilih cara instalasi yang sesuai dengan sistem operasi kamu:

### Windows

**Cara 1: Menggunakan PowerShell (Rekomendasi)**

1. Buka aplikasi PowerShell.
2. Jalankan perintah one-liner berikut:

```powershell
irm https://acadlabs.fun/install.ps1 | iex
```

**Cara 2: Manual dengan pip**
```cmd
python -m pip install git+https://github.com/Acadgacor/acadlabs-cli.git
```

### macOS / Linux

**Cara 1: Menggunakan Script Otomatis (Rekomendasi)**

Buka terminal dan jalankan perintah berikut:
```bash
curl -fsSL https://acadlabs.fun/install.sh | bash
```

**Cara 2: Manual dengan pip**
```bash
pip install git+https://github.com/Acadgacor/acadlabs-cli.git
```

---

## Cara Menggunakan

### 1. Login Akun

Sebelum mulai chat, kamu harus login ke dalam sistem:

**Login dengan Email:**
```bash
acadlabs login
```
(Kemudian masukkan email dan password akun Acadlabs kamu).

**Login dengan Google:**
```bash
acadlabs login-google
```
(Browser akan terbuka otomatis untuk autentikasi Google. Setelah berhasil, kembali ke terminal).

### 2. Mulai Percakapan

Setelah berhasil login, panggil asisten AI kamu dengan perintah:
```bash
acadlabs chat
```

### 3. Lihat Bantuan

Untuk melihat semua daftar perintah yang tersedia:
```bash
acadlabs --help
```

---

## Struktur Perintah

| Perintah | Deskripsi |
|----------|-----------|
| `acadlabs login` | Login menggunakan kombinasi email dan password |
| `acadlabs login-google` | Login menggunakan akun Google (OAuth) |
| `acadlabs chat` | Memulai sesi obrolan interaktif dengan AI |
| `acadlabs auth --help` | Melihat daftar perintah terkait autentikasi lainnya |
| `acadlabs config --help` | Melihat pengaturan konfigurasi CLI |

---

## Butuh Bantuan?

- **Website UI**: [acadlabs.fun](https://www.acadlabs.fun) - Coba pengalaman visual interaktif kami.
- **Laporkan Bug**: [Issue Tracker GitHub](https://github.com/Acadgacor/acadlabs-cli/issues)

---

## Untuk Developer

Jika kamu ingin berkontribusi atau mengembangkan project ini:

```bash
# Clone repository
git clone https://github.com/Acadgacor/acadlabs-cli.git
cd acadlabs-cli

# Buat virtual environment
python -m venv venv

# Aktifkan venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install dalam mode development
pip install -e .
```

---

## Lisensi

MIT License - Silakan gunakan dan modifikasi sesuai kebutuhan.
