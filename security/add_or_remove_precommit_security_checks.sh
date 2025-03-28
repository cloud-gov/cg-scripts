#!/bin/bash
# precommit_checks_setup.sh
#
# This script automates the installation and configuration of:
#   - pre-commit: Manages pre-commit hooks.
#   - Semgrep: Static analysis tool for code security.
#   - gitleaks: Scans repositories for secrets.
#   - Caulking: Sets up a global pre-commit hook to integrate gitleaks (from cloud-gov/caulking).
#
# It also sets up a global Git hook in $HOME/.git-hooks,
# updates your shell configuration to include /usr/local/bin in your PATH,
# validates that all installations are successful, and if all components are installed,
# prompts the user to remove them.
#
# Usage:
#   ./precommit_checks_setup.sh [--help|-h]
#
# Options:
#   --help, -h    Display this help message and exit.

#############################
# Color Variables
#############################
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

#############################
# Help Message Handling
#############################
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<EOF
${BLUE}Usage:${NC} ./precommit_checks_setup.sh [--help|-h]

This script automates the installation and configuration of:
  - pre-commit: A framework to manage pre-commit hooks.
  - Semgrep: A static analysis tool for code security.
  - gitleaks: A tool to detect secrets in your codebase.
  - Caulking: A tool from cloud-gov/caulking that sets up a global pre-commit hook for gitleaks.

It performs the following tasks:
  1. Installs pre-commit, Semgrep, gitleaks, and Caulking (cloned into \$HOME/caulking).
  2. Sets up a global Git pre-commit hook in \$HOME/.git-hooks to run Semgrep and gitleaks on staged files.
  3. Updates your shell configuration (e.g., ~/.bashrc or ~/.zshrc) to include /usr/local/bin in your PATH.
  4. Validates that all installations were successful.
  5. If everything is installed, prompts you for removal of all components set up by this script.

After running the script, please restart your terminal or manually source your shell configuration file (e.g., 'source ~/.bashrc' or 'source ~/.zshrc') to apply the changes.
EOF
    exit 0
fi

#############################
# Utility Functions
#############################

# Check if a command exists.
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate that required tools are installed.
validate_installations() {
    echo -e "${BLUE}Validating installations...${NC}"
    if ! command_exists pre-commit; then
        echo -e "${RED}Error: pre-commit not found.${NC}"
        exit 1
    fi
    if ! command_exists semgrep; then
        echo -e "${RED}Error: semgrep not found.${NC}"
        exit 1
    fi
    if ! command_exists gitleaks; then
        echo -e "${RED}Error: gitleaks not found.${NC}"
        exit 1
    fi
    if [ ! -d "$HOME/caulking" ]; then
        echo -e "${YELLOW}Warning: Caulking does not appear to be installed in \$HOME/caulking.${NC}"
    fi
    echo -e "${GREEN}All validations passed.${NC}"
}

#############################
# Installation Functions
#############################

install_pre_commit() {
    if command_exists pre-commit; then
        echo -e "${GREEN}pre-commit is already installed.${NC}"
    else
        echo -e "${BLUE}Installing pre-commit...${NC}"
        if command_exists brew; then
            brew install pre-commit
        elif command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y pre-commit
        elif command_exists pip; then
            pip install pre-commit
        else
            echo -e "${RED}Error: Unable to install pre-commit. Please install it manually.${NC}"
            exit 1
        fi
        echo -e "${GREEN}pre-commit installation complete.${NC}"
    fi
}

install_semgrep() {
    if command_exists semgrep; then
        echo -e "${GREEN}Semgrep is already installed.${NC}"
    else
        echo -e "${BLUE}Installing Semgrep...${NC}"
        if command_exists brew; then
            brew install semgrep
        elif command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y semgrep
        elif command_exists pip; then
            pip install semgrep
        else
            echo -e "${RED}Error: Unable to install Semgrep. Please install it manually.${NC}"
            exit 1
        fi
        echo -e "${GREEN}Semgrep installation complete.${NC}"
    fi
}

install_gitleaks() {
    if command_exists gitleaks; then
        echo -e "${GREEN}gitleaks is already installed.${NC}"
    else
        echo -e "${BLUE}Installing gitleaks...${NC}"
        if command_exists brew; then
            brew install gitleaks
        elif command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y gitleaks
        else
            echo -e "${RED}Error: Unable to install gitleaks. Please install it manually.${NC}"
            exit 1
        fi
        echo -e "${GREEN}gitleaks installation complete.${NC}"
    fi
}

install_caulking() {
    CAULKING_DIR="$HOME/caulking"
    if [ -d "$CAULKING_DIR" ]; then
        echo -e "${GREEN}Caulking is already installed in $CAULKING_DIR.${NC}"
    else
        echo -e "${BLUE}Cloning and installing Caulking from https://github.com/cloud-gov/caulking ...${NC}"
        git clone --recurse-submodules https://github.com/cloud-gov/caulking.git "$CAULKING_DIR"
        ( cd "$CAULKING_DIR" && make install )
        echo -e "${GREEN}Caulking installation complete.${NC}"
        echo -e "${YELLOW}Note: Caulking sets up a global hook in \$HOME/.git-support and installs its configuration there.${NC}"
    fi
}

#############################
# Setup Functions
#############################

setup_global_hooks() {
    echo -e "${BLUE}Setting up global Git hooks...${NC}"
    GLOBAL_HOOKS_DIR="$HOME/.git-hooks"
    mkdir -p "$GLOBAL_HOOKS_DIR"

    # Write the global pre-commit hook script.
    # shellcheck disable=SC2016
    cat <<'EOF' > "$GLOBAL_HOOKS_DIR/pre-commit"
#!/bin/bash
# Global pre-commit hook to run Semgrep and gitleaks on staged files.

LOGFILE="$HOME/.git-hooks/semgrep-gitleaks.log"

if [ "$SKIP_SECURITY" == "1" ]; then
    echo "[SKIP] Security checks bypassed via SKIP_SECURITY flag." | tee -a "$LOGFILE"
    exit 0
fi

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|go|sh|yaml|yml|tf)$' || true)

if [ -z "$STAGED_FILES" ]; then
    echo "No relevant staged files to scan." | tee -a "$LOGFILE"
    exit 0
fi

echo "Running security scans on staged files:" | tee -a "$LOGFILE"
echo "$STAGED_FILES" | tee -a "$LOGFILE"

semgrep --config auto $STAGED_FILES 2>&1 | tee -a "$LOGFILE"
RESULT_SEM=$?

gitleaks detect --source . --redact 2>&1 | tee -a "$LOGFILE"
RESULT_GITLEAKS=$?

if [ $RESULT_SEM -ne 0 ]; then
    echo "Semgrep detected issues. Please resolve them before committing." | tee -a "$LOGFILE"
    exit 1
fi

if [ $RESULT_GITLEAKS -ne 0 ]; then
    echo "gitleaks detected leaks. Please fix them before committing." | tee -a "$LOGFILE"
    exit 1
fi

echo "All security checks passed." | tee -a "$LOGFILE"
exit 0
EOF

    chmod +x "$GLOBAL_HOOKS_DIR/pre-commit"
    git config --global core.hooksPath "$GLOBAL_HOOKS_DIR"
    echo -e "${GREEN}Global Git hooks set up successfully.${NC}"
}

update_shell_config() {
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
            echo -e "${RED}Unsupported shell: $DEFAULT_SHELL. Please update your PATH manually.${NC}"
            return
            ;;
    esac

    if ! grep -q 'export PATH=.*\/usr\/local\/bin' "$SHELL_CONFIG"; then
        echo -e "${BLUE}Updating $SHELL_CONFIG to include /usr/local/bin in PATH...${NC}"
        echo "export PATH=\"/usr/local/bin:\$PATH\"" >> "$SHELL_CONFIG"
        echo -e "${GREEN}Shell configuration updated.${NC}"
    else
        echo -e "${GREEN}$SHELL_CONFIG already includes /usr/local/bin in PATH.${NC}"
    fi
}

#############################
# Removal Functions
#############################

remove_installations() {
    echo -e "${BLUE}Removing global Git hooks...${NC}"
    rm -rf "$HOME/.git-hooks"
    echo -e "${GREEN}Global Git hooks removed.${NC}"

    echo -e "${BLUE}Removing Caulking installation...${NC}"
    rm -rf "$HOME/caulking"
    echo -e "${GREEN}Caulking installation removed.${NC}"

    echo -e "${BLUE}Removing PATH modification from shell configuration...${NC}"
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
            echo -e "${RED}Unsupported shell: $DEFAULT_SHELL. Please remove PATH modifications manually.${NC}"
            return
            ;;
    esac

    if [ -f "$SHELL_CONFIG" ]; then
         sed -i.bak "/export PATH=\"\/usr\/local\/bin:\$PATH\"/d" "$SHELL_CONFIG"
         echo -e "${GREEN}Removed PATH modification from $SHELL_CONFIG. Backup saved as $SHELL_CONFIG.bak.${NC}"
    fi

    echo -e "${GREEN}Removal complete.${NC}"
}

check_for_removal() {
    if command_exists pre-commit && command_exists semgrep && command_exists gitleaks && [ -d "$HOME/caulking" ] && [ -d "$HOME/.git-hooks" ]; then
         echo -e "${YELLOW}All components appear to be installed.${NC}"
         read -r -p "Would you like to remove all installations set up by this script? (y/N): " answer
         if [[ "$answer" =~ ^[Yy]$ ]]; then
              remove_installations
              exit 0
         else
              echo -e "${BLUE}Continuing with installation/validation...${NC}"
         fi
    fi
}

#############################
# Main Execution
#############################

check_for_removal

install_pre_commit
install_semgrep
install_gitleaks
install_caulking
setup_global_hooks
update_shell_config
validate_installations

echo -e "${GREEN}Installation and configuration complete.${NC}"
echo -e "${YELLOW}Please restart your terminal or manually source your shell configuration file (e.g., 'source ~/.bashrc' or 'source ~/.zshrc') to apply the changes.${NC}"
