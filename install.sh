#!/bin/bash
set -e

# Colors & Styles
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BOLD='\033[1m'
RESET='\033[0m'

# Header
clear
echo -e "${CYAN}"
echo "  ===================================================="
echo "      ___   _   _         _ _    ___ _      _ _ ___    "
echo "     /   | / \ | |_ ___  | | |  / __| | ___| | __|    "
echo "    / /| |/ _ \| __/ _ \ | | | | |   | |/ _ \ |__ \    "
echo "   / /_| / ___ \||  __/  |_| | | |___| |  __/ |__) |   "
echo "   \____/_/   \_\__\___| (_)_|  \____|_|\___|_____/    "
echo "                                                      "
echo "       Command Line Interface Installer               "
echo "  ====================================================${RESET}"
echo ""

# Step 1: Check Python
echo -e "${BOLD}[1/3] Checking Python...${RESET}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}   ERROR: python3 tidak ditemukan.${RESET}"
    echo -e "   Silakan install Python 3.8+ dari https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo -e "   ${GREEN}Found: Python $PYTHON_VERSION${RESET}"
echo ""

# Step 2: Choose Installation Method
echo -e "${BOLD}[2/3] Installing AcadLabs CLI...${RESET}"
if command -v pipx &> /dev/null; then
    echo -e "   Using ${CYAN}pipx${RESET} (isolated environment)"
    echo ""
    pipx install git+https://github.com/Acadgacor/acadlabs-cli.git --force
else
    echo -e "   Using ${CYAN}pip${RESET} with --break-system-packages"
    echo ""
    python3 -m pip install git+https://github.com/Acadgacor/acadlabs-cli.git --break-system-packages --force-reinstall
fi
echo ""

# Step 3: Verify Installation
echo -e "${BOLD}[3/3] Verifying installation...${RESET}"
if command -v acadlabs &> /dev/null; then
    echo -e "   ${GREEN}Command 'acadlabs' is ready!${RESET}"
else
    echo -e "   ${YELLOW}Note: You may need to add ~/.local/bin to your PATH:${RESET}"
    echo -e "   ${CYAN}export PATH=\"\$PATH:\$HOME/.local/bin\"${RESET}"
    echo -e "   Add to ~/.bashrc for permanent access"
fi
echo ""

# Success Banner
echo -e "${GREEN}"
echo "  =========================================="
echo "        Installation Complete!"
echo "  ==========================================${RESET}"
echo ""
echo -e "  Start with: ${BOLD}${CYAN}acadlabs login${RESET}"
echo -e "  Get help:   ${BOLD}${CYAN}acadlabs --help${RESET}"
echo ""
echo -e "  Web UI: ${CYAN}https://acadlabs.fun${RESET}"
echo ""
