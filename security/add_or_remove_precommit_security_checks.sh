#!/bin/bash
# precommit_checks_setup.sh
#
# This script automates the installation and configuration of:
#   - pre-commit: Manages pre-commit hooks.
#   - Semgrep: Static analysis tool for code security.
#   - gitleaks: Scans repositories for secrets.
#   - Caulking: Sets up a global pre-commit hook to integrate gitleaks.

#############################
# Configuration
#############################
GIT_SUPPORT_DIR="$HOME/.git-support"
HOOKS_DIR="$GIT_SUPPORT_DIR/hooks"
GITLEAKS_CONFIG="$GIT_SUPPORT_DIR/gitleaks.toml"
GITLEAKS_VERSION="8.18.1"
LOG_FILE="$GIT_SUPPORT_DIR/install.log"

#############################
# Color Variables
#############################
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

#############################
# Error Handling
#############################
set -e
trap 'echo -e "${RED}Installation failed${NC}"; exit 1' ERR

#############################
# Utility Functions
#############################
log() {
    local level=$1
    shift
    echo -e "${!level}[$(date '+%Y-%m-%d %H:%M:%S')] $*${NC}" | tee -a "$LOG_FILE"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_dependencies() {
    for dep in git curl make; do
        if ! command_exists "$dep"; then
            log "RED" "Error: Required dependency '$dep' is not installed"
            exit 1
        fi
    done
}

check_path() {
    if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
        log "YELLOW" "Warning: /usr/local/bin is not in PATH"
        return 1
    fi
    return 0
}

backup_existing_config() {
    local timestamp
    timestamp="$(date +%Y%m%d_%H%M%S)"
    if [ -d "$GIT_SUPPORT_DIR" ]; then
        cp -r "$GIT_SUPPORT_DIR" "${GIT_SUPPORT_DIR}_backup_${timestamp}"
        log "BLUE" "Backup created: ${GIT_SUPPORT_DIR}_backup_${timestamp}"
    fi
}

#############################
# Installation Functions
#############################
cleanup_existing_hooks() {
    log "BLUE" "Cleaning up existing hook configurations..."
    git config --global --unset core.hooksPath 2>/dev/null || true
    git config --global --unset hooks.gitleaks 2>/dev/null || true
    rm -rf "$GIT_SUPPORT_DIR"
    mkdir -p "$HOOKS_DIR"
    log "GREEN" "Cleanup complete."
}

install_pre_commit() {
    if command_exists pre-commit; then
        log "GREEN" "pre-commit is already installed."
    else
        log "BLUE" "Installing pre-commit..."
        if command_exists brew; then
            brew install pre-commit
        elif command_exists pip; then
            pip install pre-commit
        else
            log "RED" "Error: Unable to install pre-commit. Please install it manually."
            exit 1
        fi
        log "GREEN" "pre-commit installation complete."
    fi
}

install_semgrep() {
    if command_exists semgrep; then
        log "GREEN" "Semgrep is already installed."
    else
        log "BLUE" "Installing Semgrep..."
        if command_exists brew; then
            brew install semgrep
        elif command_exists pip; then
            pip install semgrep
        else
            log "RED" "Error: Unable to install Semgrep. Please install it manually."
            exit 1
        fi
        log "GREEN" "Semgrep installation complete."
    fi
}

install_gitleaks() {
    if command_exists gitleaks; then
        log "GREEN" "gitleaks is already installed."
    else
        log "BLUE" "Installing gitleaks..."
        if command_exists brew; then
            brew install gitleaks
            brew pin gitleaks
        else
            log "RED" "Error: Unable to install gitleaks. Please install it manually or use Homebrew."
            exit 1
        fi
        log "GREEN" "gitleaks installation complete."
    fi
}

install_caulking() {
    CAULKING_DIR="$HOME/caulking"
    if [ -d "$CAULKING_DIR" ]; then
        log "BLUE" "Caulking directory exists, ensuring proper installation..."
        ( cd "$CAULKING_DIR" && make clean ) || true
        ( cd "$CAULKING_DIR" && make install )
    else
        log "BLUE" "Cloning and installing Caulking..."
        git clone --recurse-submodules https://github.com/cloud-gov/caulking.git "$CAULKING_DIR"
        ( cd "$CAULKING_DIR" && make install )
    fi

    if [ ! -f "$GITLEAKS_CONFIG" ]; then
        log "YELLOW" "Creating gitleaks configuration..."
        mkdir -p "$GIT_SUPPORT_DIR"
        if [ -f "$CAULKING_DIR/local.toml" ]; then
            cp "$CAULKING_DIR/local.toml" "$GITLEAKS_CONFIG"
            log "GREEN" "Copied gitleaks configuration from caulking."
        else
            log "RED" "Error: Could not find gitleaks configuration."
            exit 1
        fi
    fi
}

setup_global_hooks() {
    log "BLUE" "Setting up global Git hooks..."
    mkdir -p "$HOOKS_DIR"
    
    # Create pre-commit hook script
    cat <<'EOF' > "$HOOKS_DIR/pre-commit"
#!/bin/bash
LOGFILE="$HOME/.git-support/semgrep-gitleaks.log"
CONFIG="$HOME/.git-support/gitleaks.toml"

if [ "$SKIP_SECURITY" == "1" ]; then
    echo "[SKIP] Security checks bypassed via SKIP_SECURITY flag." | tee -a "$LOGFILE"
    exit 0
fi

STAGED_FILES=$(git diff --cached --name-only)
if [ -z "$STAGED_FILES" ]; then
    echo "no leaks found" | tee -a "$LOGFILE"
    exit 0
fi

# Run gitleaks check
if ! gitleaks protect --staged --config="$CONFIG" --verbose; then
    exit 1
fi

echo "no leaks found" | tee -a "$LOGFILE"
exit 0
EOF

    chmod +x "$HOOKS_DIR/pre-commit"
    git config --global core.hooksPath "$HOOKS_DIR"
    git config --global hooks.gitleaks true
    log "GREEN" "Global Git hooks set up successfully."
}

update_shell_config() {
    log "BLUE" "Updating shell configuration..."
    if command_exists getent; then
        DEFAULT_SHELL=$(getent passwd "$USER" | awk -F: '{print $7}')
    else
        DEFAULT_SHELL="$SHELL"
    fi
    
    SHELL_CONFIG=""
    case "$DEFAULT_SHELL" in
        */bash)
            SHELL_CONFIG="$HOME/.bashrc"
            ;;
        */zsh)
            SHELL_CONFIG="$HOME/.zshrc"
            ;;
        *)
            log "YELLOW" "Unsupported shell: $DEFAULT_SHELL"
            return
            ;;
    esac
    
    if [ -f "$SHELL_CONFIG" ]; then
        if ! grep -q "export PATH=\"/usr/local/bin:\$PATH\"" "$SHELL_CONFIG"; then
            echo "export PATH=\"/usr/local/bin:\$PATH\"" >> "$SHELL_CONFIG"
            log "GREEN" "Updated PATH in $SHELL_CONFIG"
        fi
    fi
}

validate_installations() {
    log "BLUE" "Validating installations..."
    local failed=0
    
    for cmd in pre-commit semgrep gitleaks; do
        if ! command_exists "$cmd"; then
            log "RED" "Error: $cmd not found."
            failed=1
        fi
    done

    if [ ! -d "$GIT_SUPPORT_DIR" ] || [ ! -f "$GITLEAKS_CONFIG" ]; then
        log "RED" "Error: Git support directory or configuration missing."
        failed=1
    fi

    if [ $failed -eq 1 ]; then
        exit 1
    fi
    
    log "GREEN" "All validations passed."
}

#############################
# Main Execution
#############################
# Help message handling
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
Usage: ./precommit_checks_setup.sh [--help|-h]
Installs and configures pre-commit, Semgrep, gitleaks, and Caulking for repository security checks.
EOF
    exit 0
fi

# Main installation process
mkdir -p "$GIT_SUPPORT_DIR"
check_dependencies
backup_existing_config
cleanup_existing_hooks
# ... rest of the script
install_pre_commit
install_semgrep
install_gitleaks
install_caulking
setup_global_hooks
update_shell_config
validate_installations

log "GREEN" "Installation and configuration complete."
log "YELLOW" "Please restart your terminal or source your shell configuration file."