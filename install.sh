#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                                                                           ║
# ║   🎓 AcadLabs CLI Installer v1.0.1                                        ║
# ║   Command Line Interface untuk Platform AcadLabs                          ║
# ║                                                                           ║
# ║   GitHub: https://github.com/Acadgacor/acadlabs-cli                       ║
# ║   Docs:   https://acadlabs.fun/docs                                       ║
# ║                                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

set -e

# ═══════════════════════════════════════════════════════════════════════════
# 🎨 COLORS & STYLES
# ═══════════════════════════════════════════════════════════════════════════
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly GRAY='\033[0;90m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m'

# ═══════════════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
readonly REPO_URL="https://github.com/Acadgacor/acadlabs-cli.git"
readonly DOCS_URL="https://acadlabs.fun/docs"
readonly WEB_UI="https://acadlabs.fun"
readonly INSTALLER_VERSION="1.0.1"

# Default values
INSTALL_METHOD="auto"
NO_PROMPT=false
VERBOSE=false
DRY_RUN=false

# ═══════════════════════════════════════════════════════════════════════════
# 🔧 UTILITY FUNCTIONS (LOGGING KE STDERR)
# ═══════════════════════════════════════════════════════════════════════════

# ✅ SEMUA LOG FUNCTION MENGGUNAKAN >&2 AGAR TIDAK MENGGANGGU STDOUT CAPTURE
log_info()    { echo -e "${GREEN}[INFO]${NC}  $1" >&2; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1" >&2; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_step()    { echo -e "${BLUE}[STEP]${NC}  ${BOLD}$1${NC}" >&2; }
log_success() { echo -e "${GREEN}[✓]${NC}    $1" >&2; }

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "  ╔════════════════════════════════════════════════════════════╗"
    echo "  ║                                                            ║"
    echo "  ║   ${BOLD}╔═╗╔═╗╦  ╔═╗╔═╗╔╦╗╔═╗╦═╗${NC}  ${BOLD}╦ ╦╔═╗╔╗╔╔╦╗╔═╗╦═╗╔╦╗${NC}  ${BOLD}╔═╗╦╔╗╔╔╦╗╦ ╦╔═╗╦  ╔═╗${NC}  ║"
    echo "  ║   ${BOLD}╠╣ ║ ║║  ║╣ ╚═╗ ║ ║ ║╠╦╝${NC}  ${BOLD}╠═╣║ ║║║║ ║║║╣ ╠╦╝ ║║${NC}  ${BOLD}╠═╣║║║║ ║ ║ ║╠═╝║  ╠╣ ${NC}  ║"
    echo "  ║   ${BOLD}╚  ╚═╝╩═╝╚═╝╚═╝ ╩ ╚═╝╩╚═${NC}  ${BOLD}╩ ╩╚═╝╝╚╝═╩╝╚═╝╩╚══╩╝${NC}  ${BOLD}╩ ╩╩╝╚╝ ╩ ╚═╝╩  ╩  ╚═╝${NC}  ║"
    echo "  ║                                                            ║"
    echo "  ║         ${WHITE}${BOLD}🎓 AcadLabs CLI Installer v${INSTALLER_VERSION}${NC}${CYAN}              ║"
    echo "  ║         ${DIM}Command Line Interface untuk Platform AcadLabs${NC}${CYAN}      ║"
    echo "  ║                                                            ║"
    echo "  ╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    local title="$1"
    echo "" >&2
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    echo -e "${WHITE}${BOLD}  $title${NC}" >&2
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    echo "" >&2
}

check_command() {
    command -v "$1" &>/dev/null
}

confirm() {
    local message="$1"
    local default="${2:-y}"
    
    if $NO_PROMPT; then
        [[ "$default" == "y" ]]
        return $?
    fi
    
    local prompt="[Y/n]"
    [[ "$default" != "y" ]] && prompt="[y/N]"
    
    echo -en "${YELLOW}  $message $prompt: ${NC}"
    read -r response
    response=${response:-$default}
    
    [[ "$response" =~ ^[yY](es)?$ ]]
}

# ═══════════════════════════════════════════════════════════════════════════
# 📋 ARGUMENT PARSING
# ═══════════════════════════════════════════════════════════════════════════

print_usage() {
    cat << EOF
${CYAN}${BOLD}Usage:${NC}
  $0 [OPTIONS]

${CYAN}${BOLD}Options:${NC}
  --method <auto|pipx|pip>   Installation method (default: auto)
  --no-prompt                Skip interactive prompts, use defaults
  --verbose                  Enable verbose output
  --dry-run                  Show what would be done, don't execute
  -h, --help                 Show this help message

${CYAN}${BOLD}Environment Variables:${NC}
  ACADLABS_INSTALL_METHOD    Set installation method
  ACADLABS_NO_PROMPT         Disable prompts (1/0)
  ACADLABS_VERBOSE           Enable verbose mode (1/0)

${CYAN}${BOLD}Examples:${NC}
  $0                                    # Interactive install
  $0 --method pipx --no-prompt          # Silent pipx install
  $0 --dry-run                          # Preview installation steps
  ACADLABS_INSTALL_METHOD=pip $0        # Force pip installation

${CYAN}Documentation: ${WHITE}${DOCS_URL}${NC}
${CYAN}Web UI:       ${WHITE}${WEB_UI}${NC}
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --method)
                INSTALL_METHOD="$2"
                shift 2
                ;;
            --no-prompt)
                NO_PROMPT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_warn "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

# ═══════════════════════════════════════════════════════════════════════════
# 🔍 SYSTEM CHECKS
# ═══════════════════════════════════════════════════════════════════════════

check_python() {
    print_section "🐍 Checking Python Environment"
    
    if ! check_command python3; then
        log_error "python3 not found!"
        echo "" >&2
        echo -e "  ${WHITE}Please install Python 3.8+ from:${NC}" >&2
        echo -e "  ${CYAN}  https://www.python.org/downloads/${NC}" >&2
        echo "" >&2
        return 1
    fi
    
    local version
    version=$(python3 --version 2>&1 | cut -d' ' -f2)
    local major minor
    IFS='.' read -r major minor _ <<< "$version"
    
    if [[ $major -lt 3 ]] || [[ $major -eq 3 && $minor -lt 8 ]]; then
        log_error "Python $version detected, but 3.8+ is required"
        return 1
    fi
    
    log_success "Python $version detected ✓"
    
    if ! python3 -m pip --version &>/dev/null; then
        log_warn "pip not found, attempting to bootstrap..."
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - || {
            log_error "Failed to install pip"
            return 1
        }
        log_success "pip installed ✓"
    else
        log_success "pip is available ✓"
    fi
    echo "" >&2
    return 0
}

# ✅ FIXED: Hanya method name yang ke stdout, log ke stderr
detect_install_method() {
    local method="$INSTALL_METHOD"
    
    if [[ "$method" == "auto" ]]; then
        if check_command pipx; then
            log_info "pipx detected - using isolated environment (recommended)"
            method="pipx"
        else
            log_info "pipx not found - falling back to pip"
            method="pip"
        fi
    fi
    
    # ✅ Hanya return method name ke stdout (untuk variable capture)
    echo "$method"
}

# ═══════════════════════════════════════════════════════════════════════════
# 📦 INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════

install_with_pipx() {
    print_section "📦 Installing via pipx"
    
    log_step "Installing AcadLabs CLI with pipx..."
    
    if $DRY_RUN; then
        echo "  [DRY RUN] pipx install git+${REPO_URL} --force" >&2
        return 0
    fi
    
    local cmd=(pipx install "git+${REPO_URL}" --force)
    $VERBOSE && cmd+=(--verbose)
    
    "${cmd[@]}" || {
        log_error "pipx installation failed"
        return 1
    }
    
    log_success "Installed via pipx ✓"
    return 0
}

install_with_pip() {
    print_section "📦 Installing via pip"
    
    log_step "Installing AcadLabs CLI with pip..."
    log_warn "Using --break-system-packages (system Python)"
    
    if $DRY_RUN; then
        echo "  [DRY RUN] python3 -m pip install git+${REPO_URL} --break-system-packages --force-reinstall" >&2
        return 0
    fi
    
    local cmd=(python3 -m pip install "git+${REPO_URL}" --break-system-packages --force-reinstall)
    $VERBOSE && cmd+=(--verbose)
    
    "${cmd[@]}" || {
        log_error "pip installation failed"
        return 1
    }
    
    log_success "Installed via pip ✓"
    return 0
}

# ═══════════════════════════════════════════════════════════════════════════
# ✅ VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

verify_installation() {
    print_section "✅ Verifying Installation"
    
    hash -r 2>/dev/null || true
    
    if check_command acadlabs; then
        local version
        version=$(acadlabs --version 2>/dev/null || echo "unknown")
        log_success "Command 'acadlabs' is ready! (v${version})"
        echo "" >&2
        return 0
    fi
    
    log_warn "'acadlabs' command not found in PATH"
    echo "" >&2
    
    local locations=("$HOME/.local/bin" "/usr/local/bin" "$HOME/.local/pipx/bin")
    for loc in "${locations[@]}"; do
        if [[ -x "$loc/acadlabs" ]]; then
            log_info "Found acadlabs at: $loc/acadlabs"
            echo "" >&2
            echo -e "  ${YELLOW}Add to your PATH:${NC}" >&2
            echo -e "  ${CYAN}  export PATH=\"\$PATH:$loc\"${NC}" >&2
            echo -e "  ${DIM}  Add to ~/.bashrc or ~/.zshrc for permanent access${NC}" >&2
            echo "" >&2
            return 0
        fi
    done
    
    log_error "Installation may have failed. Please check the output above."
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════
# 🎉 SUCCESS BANNER
# ═══════════════════════════════════════════════════════════════════════════

print_success() {
    echo ""
    echo -e "${GREEN}"
    echo "  ╔════════════════════════════════════════════════════════════╗"
    echo "  ║                                                            ║"
    echo "  ║   ${BOLD}🎉 Installation Complete! 🎉${NC}${GREEN}        ║"
    echo "  ║                                                            ║"
    echo "  ╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "  ${WHITE}${BOLD}Get Started:${NC}"
    echo -e "    ${CYAN}acadlabs login${NC}              # Authenticate your account"
    echo -e "    ${CYAN}acadlabs login-google${NC}       # Authenticate with Google"
    echo -e "    ${CYAN}acadlabs --help${NC}             # View all available commands"
    echo -e "    ${CYAN}acadlabs labs list${NC}          # List available labs"
    echo ""
    echo -e "  ${WHITE}${BOLD}Resources:${NC}"
    echo -e "    ${CYAN}${WEB_UI}${NC}                  # Web Dashboard"
    echo -e "    ${CYAN}${DOCS_URL}${NC}                # Documentation"
    echo -e "    ${CYAN}https://github.com/Acadgacor/acadlabs-cli${NC}  # Source Code"
    echo ""
    echo -e "  ${DIM}Need help? Run: acadlabs support${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
# 🚀 MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

main() {
    parse_args "$@"
    
    print_banner
    
    if $DRY_RUN; then
        echo -e "${YELLOW}[DRY RUN MODE]${NC} - No changes will be made" >&2
        echo "" >&2
    fi
    
    if ! check_python; then
        exit 1
    fi
    
    # ✅ FIXED: Capture hanya method name, log tampil terpisah di stderr
    local method
    method=$(detect_install_method)
    
    echo -e "${BLUE}[METHOD]${NC}  Using: ${BOLD}${method}${NC}" >&2
    echo "" >&2
    
    if ! $NO_PROMPT; then
        if ! confirm "Proceed with installation?"; then
            echo -e "\n${YELLOW}Installation cancelled.${NC}" >&2
            exit 0
        fi
        echo "" >&2
    fi
    
    case "$method" in
        pipx)  install_with_pipx || exit 1 ;;
        pip)   install_with_pip  || exit 1 ;;
        *)     log_error "Unknown method: $method"; exit 1 ;;
    esac
    
    verify_installation
    print_success
}

# ═══════════════════════════════════════════════════════════════════════════
# 🏁 ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

trap 'echo -e "\n${RED}Installation interrupted.${NC}\n" >&2; exit 130' INT TERM

main "$@"