#!/bin/bash
set -e

#==============================================================================
# Local vLLM Service - Debian 13 Installation Script
#==============================================================================
# This script installs the Local vLLM Service on Debian 13 in /opt/local_llm_service
# with systemd autostart after boot.
#
# Usage:
#   sudo ./install_debian.sh
#
# Requirements:
#   - Debian 13 (Trixie)
#   - NVIDIA GPU with drivers installed
#   - Root/sudo privileges
#==============================================================================

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation configuration
INSTALL_DIR="/opt/local_llm_service"
MODELS_DIR="/ssd/LLMs"
SERVICE_NAME="local-llm-service"
REPO_URL="https://github.com/viljo/Local_vllm_docker_blackwell6000.git"
BRANCH="002-gpt-oss-models-dynamic-reload"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to generate secure API key
generate_api_key() {
    if command -v python3 &> /dev/null; then
        # Preferred: Use Python's secrets module (cryptographically secure)
        python3 -c "import secrets; print('sk-local-' + secrets.token_hex(32))"
    elif command -v openssl &> /dev/null; then
        # Fallback: Use openssl with 64 hex chars (256 bits)
        echo "sk-local-$(openssl rand -hex 32)"
    else
        print_error "Cannot generate API key: neither python3 nor openssl found"
        exit 1
    fi
}

# List of known weak/compromised API keys
WEAK_KEYS=(
    "sk-local-dev-key"
    "sk-local-your-secret-key-here"
    "sk-local-CHANGE-THIS-TO-A-SECURE-RANDOM-KEY"
    "sk-local-2ac9387d659f7131f38d83e5f7bee469"  # Compromised key from old code
)

# Check if API key is weak
is_weak_api_key() {
    local key=$1
    for weak_key in "${WEAK_KEYS[@]}"; do
        if [ "$key" = "$weak_key" ]; then
            return 0  # true - it is weak
        fi
    done
    # Also check if key is too short (less than 32 characters after prefix)
    local key_without_prefix=${key#sk-local-}
    if [ ${#key_without_prefix} -lt 32 ]; then
        return 0  # true - it is weak
    fi
    return 1  # false - not weak
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

print_info "Starting Local vLLM Service installation on Debian 13..."

#==============================================================================
# Step 1: Check system requirements
#==============================================================================
print_info "Checking system requirements..."

# Check Debian version
if ! grep -q "trixie\|13" /etc/os-release 2>/dev/null; then
    print_warning "This script is designed for Debian 13 (Trixie). Your system may not be compatible."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    print_warning "nvidia-smi not found. NVIDIA drivers may not be installed."
    print_info "Please install NVIDIA drivers before continuing."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
fi

#==============================================================================
# Step 2: Install Docker
#==============================================================================
print_info "Installing Docker..."

if command -v docker &> /dev/null; then
    print_success "Docker is already installed ($(docker --version))"
else
    print_info "Installing Docker from official repository..."

    # Install prerequisites
    apt-get update
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    print_success "Docker installed successfully"
fi

#==============================================================================
# Step 3: Install NVIDIA Container Toolkit
#==============================================================================
print_info "Installing NVIDIA Container Toolkit..."

if docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null 2>&1; then
    print_success "NVIDIA Container Toolkit is already configured"
else
    print_info "Setting up NVIDIA Container Toolkit..."

    # Add NVIDIA Container Toolkit repository
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    # Install NVIDIA Container Toolkit
    apt-get update
    apt-get install -y nvidia-container-toolkit

    # Configure Docker to use NVIDIA runtime
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker

    print_success "NVIDIA Container Toolkit installed and configured"
fi

#==============================================================================
# Step 4: Install Git (if not present)
#==============================================================================
if ! command -v git &> /dev/null; then
    print_info "Installing Git..."
    apt-get install -y git
    print_success "Git installed"
fi

#==============================================================================
# Step 5: Clone/Copy service to /opt
#==============================================================================
print_info "Setting up service in $INSTALL_DIR..."

# Check if we're running from the git repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/docker-compose.yml" ]] && [[ -d "$SCRIPT_DIR/.git" ]]; then
    print_info "Installing from local repository..."

    # Create install directory if it doesn't exist
    mkdir -p "$INSTALL_DIR"

    # Copy files to /opt (excluding git history, build artifacts, etc.)
    rsync -av --exclude='.git' \
              --exclude='node_modules' \
              --exclude='__pycache__' \
              --exclude='*.pyc' \
              --exclude='.env' \
              --exclude='models/' \
              "$SCRIPT_DIR/" "$INSTALL_DIR/"

    print_success "Service files copied to $INSTALL_DIR"
else
    print_info "Cloning from GitHub repository..."

    # Remove old installation if exists
    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Removing existing installation at $INSTALL_DIR"
        rm -rf "$INSTALL_DIR"
    fi

    # Clone the repository
    git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"

    print_success "Repository cloned to $INSTALL_DIR"
fi

# Create or update .env file
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    print_info "Creating .env file from template..."
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"

    # Generate a secure API key
    print_info "Generating cryptographically secure API key..."
    RANDOM_API_KEY=$(generate_api_key)
    sed -i "s/API_KEY=.*/API_KEY=$RANDOM_API_KEY/" "$INSTALL_DIR/.env"

    print_success ".env file created with generated API key"
    echo ""
    print_success "IMPORTANT: Save this API key for programmatic access:"
    echo -e "  ${GREEN}$RANDOM_API_KEY${NC}"
    echo ""
    print_info "Note: WebUI browser access does not require this key (BFF pattern)"
    print_info "External tools/scripts will need this key for API access"
    echo ""
else
    print_info "Existing .env file found, merging new variables..."

    # Backup existing .env
    cp "$INSTALL_DIR/.env" "$INSTALL_DIR/.env.backup"

    # Preserve existing API key
    EXISTING_API_KEY=$(grep "^API_KEY=" "$INSTALL_DIR/.env" | cut -d'=' -f2-)

    # Copy new template
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env.new"

    # Check if existing API key is weak/compromised
    if [[ -n "$EXISTING_API_KEY" ]] && is_weak_api_key "$EXISTING_API_KEY"; then
        print_warning "Weak or compromised API key detected!"
        echo -e "  Current key: ${YELLOW}$EXISTING_API_KEY${NC}"
        echo ""
        echo "This key is either:"
        echo "  • A default/example key from .env.example"
        echo "  • A previously compromised key"
        echo "  • Too short to be secure"
        echo ""
        echo -n "Generate a new secure API key? [Y/n]: "
        read -r response

        # Default to yes if empty response
        response=${response:-y}

        if [[ "$response" =~ ^[Yy]$ ]] || [ -z "$response" ]; then
            # Generate new secure key
            NEW_API_KEY=$(generate_api_key)
            sed -i "s/API_KEY=.*/API_KEY=$NEW_API_KEY/" "$INSTALL_DIR/.env.new"

            print_success "Generated new secure API key"
            echo -e "  ${GREEN}$NEW_API_KEY${NC}"
            echo ""
            print_info "Note: WebUI browser access does not require this key"
            print_info "External tools/scripts will need this key for API access"
            EXISTING_API_KEY="$NEW_API_KEY"
        else
            print_warning "Keeping existing API key (not recommended)"
            sed -i "s/API_KEY=.*/API_KEY=$EXISTING_API_KEY/" "$INSTALL_DIR/.env.new"
        fi
    elif [[ -n "$EXISTING_API_KEY" ]]; then
        # Key exists and is secure
        print_success "Existing API key is secure, preserving it"
        sed -i "s/API_KEY=.*/API_KEY=$EXISTING_API_KEY/" "$INSTALL_DIR/.env.new"
    else
        # No key exists, generate new one
        print_info "No API key found, generating new secure key..."
        RANDOM_API_KEY=$(generate_api_key)
        sed -i "s/API_KEY=.*/API_KEY=$RANDOM_API_KEY/" "$INSTALL_DIR/.env.new"
        print_success "Generated new API key: $RANDOM_API_KEY"
    fi

    # Copy any custom values from old .env that aren't in the new template
    # (this preserves user customizations)
    while IFS='=' read -r key value; do
        if [[ ! "$key" =~ ^# ]] && [[ -n "$key" ]]; then
            # Check if this key exists in new template
            if ! grep -q "^${key}=" "$INSTALL_DIR/.env.new" 2>/dev/null; then
                echo "${key}=${value}" >> "$INSTALL_DIR/.env.new"
            fi
        fi
    done < "$INSTALL_DIR/.env.backup"

    # Replace old .env with merged version
    mv "$INSTALL_DIR/.env.new" "$INSTALL_DIR/.env"

    print_success ".env file updated with new variables (backup saved as .env.backup)"
fi

# Set ownership to root
chown -R root:root "$INSTALL_DIR"

#==============================================================================
# Step 6: Setup models directory
#==============================================================================
print_info "Setting up models directory at $MODELS_DIR..."

# Create models directory if it doesn't exist
mkdir -p "$MODELS_DIR"

# Set ownership
chown -R root:root "$MODELS_DIR"

print_success "Models directory created at $MODELS_DIR"

#==============================================================================
# Step 7: Copy models from local dev directory if available
#==============================================================================
print_info "Checking for existing models to copy..."

# Check if we're installing from the dev directory and if models exist
if [[ -d "$SCRIPT_DIR/models" ]] && [[ -d "$SCRIPT_DIR/.git" ]]; then
    MODEL_COUNT=$(find "$SCRIPT_DIR/models" -type d -name "models--*" 2>/dev/null | wc -l)

    if [[ $MODEL_COUNT -gt 0 ]]; then
        print_info "Found $MODEL_COUNT model(s) in dev directory, copying to $MODELS_DIR..."
        print_info "This may take several minutes for large models..."

        # Copy models with progress
        rsync -av --info=progress2 "$SCRIPT_DIR/models/" "$MODELS_DIR/"

        print_success "Models copied successfully ($MODEL_COUNT models)"
    else
        print_info "No models found in dev directory, models will be downloaded on first use"
    fi
else
    print_info "No local models directory found, models will be downloaded on first use"
fi

#==============================================================================
# Step 8: Update docker-compose.yml to use /ssd/LLMs
#==============================================================================
print_info "Configuring docker-compose.yml to use $MODELS_DIR..."

# Update docker-compose.yml to mount /ssd/LLMs instead of ./models
sed -i "s|./models:/models|$MODELS_DIR:/models|g" "$INSTALL_DIR/docker-compose.yml"

print_success "docker-compose.yml configured"

#==============================================================================
# Step 9: Create systemd service
#==============================================================================
print_info "Creating systemd service..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Local vLLM Service
Documentation=https://github.com/viljo/Local_vllm_docker_blackwell6000
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
Environment="PWD=$INSTALL_DIR"
ExecStartPre=/usr/bin/docker compose down
ExecStartPre=/usr/bin/docker compose build webui-frontend
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

print_success "Systemd service created at /etc/systemd/system/${SERVICE_NAME}.service"

#==============================================================================
# Step 10: Build containers
#==============================================================================
print_info "Building containers..."

cd "$INSTALL_DIR"

# Build frontend container (BFF pattern - no API key in frontend)
# The router handles authentication, so the frontend doesn't need the API key
docker compose build webui-frontend

print_success "Frontend container built (API key secured via BFF pattern)"

#==============================================================================
# Step 11: Enable and start service
#==============================================================================
print_info "Enabling and starting service..."

# Reload systemd
systemctl daemon-reload

# Enable service for autostart
systemctl enable "$SERVICE_NAME"

# Start service now
systemctl start "$SERVICE_NAME"

print_success "Service enabled and started"

#==============================================================================
# Step 12: Wait for services to be ready
#==============================================================================
print_info "Waiting for services to start..."

sleep 10

# Check service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "Service is running"

    # Show container status
    cd "$INSTALL_DIR"
    docker compose ps
else
    print_error "Service failed to start"
    print_info "Check logs with: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

#==============================================================================
# Installation Complete
#==============================================================================
echo ""
echo "========================================================================"
print_success "Local vLLM Service installed successfully!"
echo "========================================================================"
echo ""
echo "Installation Details:"
echo "  - Install directory: $INSTALL_DIR"
echo "  - Models directory: $MODELS_DIR"
echo "  - Service name: $SERVICE_NAME"
echo "  - Autostart: Enabled"
echo ""
echo "Service Management:"
echo "  - Start:   systemctl start $SERVICE_NAME"
echo "  - Stop:    systemctl stop $SERVICE_NAME"
echo "  - Restart: systemctl restart $SERVICE_NAME"
echo "  - Status:  systemctl status $SERVICE_NAME"
echo "  - Logs:    journalctl -u $SERVICE_NAME -f"
echo ""
echo "Docker Compose Management:"
echo "  - cd $INSTALL_DIR"
echo "  - docker compose ps"
echo "  - docker compose logs -f"
echo "  - docker compose down"
echo "  - docker compose up -d"
echo ""
echo "Access WebUI:"
echo "  - Local:  http://localhost:3000"
echo "  - Remote: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "API Endpoint:"
echo "  - http://localhost:8080/v1"
echo ""
echo "Next Steps:"
echo "  1. Access the WebUI in your browser"
echo "  2. Models will auto-start (largest model first)"
echo "  3. Check logs: journalctl -u $SERVICE_NAME -f"
echo ""
echo "========================================================================"
