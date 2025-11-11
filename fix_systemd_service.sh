#!/bin/bash
set -e

#==============================================================================
# Fix Systemd Service - Add PWD Environment Variable
#==============================================================================
# This script fixes the systemd service by adding the PWD environment variable
# which is required for docker-compose.yml to work correctly.
#
# Usage:
#   sudo ./fix_systemd_service.sh
#==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/local_llm_service"
SERVICE_NAME="local-llm-service"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

print_info "Fixing systemd service configuration..."

# Stop the service
print_info "Stopping service..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

# Update the service file
print_info "Updating service file..."
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
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

print_success "Service file updated"

# Reload systemd
print_info "Reloading systemd..."
systemctl daemon-reload

# Start the service
print_info "Starting service..."
systemctl start "$SERVICE_NAME"

# Check status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "Service is running"
    echo ""
    echo "Check status with: systemctl status $SERVICE_NAME"
    echo "Check logs with: journalctl -u $SERVICE_NAME -f"
else
    print_error "Service failed to start"
    echo ""
    echo "Check logs with: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

print_success "Fix applied successfully!"
