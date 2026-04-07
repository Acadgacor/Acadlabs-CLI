#!/bin/bash
set -e # Berhenti kalau ada error

echo -e "\033[1;36m\U0001F680 Installing AcadLabs CLI...\033[0m"

# 1. Cek Python
if ! command -v python3 &> /dev/null; then
    echo -e "\033[1;31m\U0000274C Error: python3 tidak ditemukan.\033[0m"
    exit 1
fi

# 2. Cek Pip (Ini yang tadi lu kurang)
if ! python3 -m pip --version &> /dev/null; then
    echo -e "\033[1;33m\U0001F4E6 Pip tidak ditemukan. Mencoba install pip...\033[0m"
    sudo apt update && sudo apt install python3-pip -y || { echo -e "\033[1;31m\U0000274C Gagal install pip. Silakan install manual: sudo apt install python3-pip\033[0m"; exit 1; }
fi

# 3. Proses Install
echo "\U0001F4E6 Downloading and installing from GitHub..."
# Pakai --user agar tidak butuh sudo dan masuk ke PATH user
python3 -m pip install git+https://github.com/Acadgacor/acadlabs-cli.git --force-reinstall

# 4. Cek PATH (Penting buat Linux/WSL)
if ! command -v acadlabs &> /dev/null; then
    echo -e "\033[1;33m\U000026A0  Peringatan: Perintah 'acadlabs' mungkin belum masuk ke PATH.\033[0m"
    echo "Silakan jalankan: echo 'export PATH=\$PATH:\$HOME/.local/bin' >> ~/.bashrc && source ~/.bashrc"
fi

echo -e "\033[1;32m\U00002705 Installation complete!\033[0m"
echo -e "Coba jalankan: \033[1macadlabs login\033[0m"
