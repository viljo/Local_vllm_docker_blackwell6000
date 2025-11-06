#!/bin/bash
# NVIDIA Container Toolkit Installation Script for Debian 13
# Run this script with: sudo bash scripts/setup-nvidia-toolkit.sh

set -e

echo "=========================================="
echo "NVIDIA Container Toolkit Installation"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Check NVIDIA driver
echo "1. Checking NVIDIA driver..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: NVIDIA driver not found. Install NVIDIA drivers first."
    exit 1
fi
echo "✓ NVIDIA driver found:"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
echo ""

# Add NVIDIA Container Toolkit repository
echo "2. Adding NVIDIA Container Toolkit repository..."

# Add GPG key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# Add repository (Debian 13 uses bookworm repository)
echo "deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/deb/\$(ARCH) /" | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

echo "✓ Repository added"
echo ""

# Update package list
echo "3. Updating package list..."
apt-get update
echo "✓ Package list updated"
echo ""

# Install NVIDIA Container Toolkit
echo "4. Installing NVIDIA Container Toolkit..."
apt-get install -y nvidia-container-toolkit
echo "✓ NVIDIA Container Toolkit installed"
echo ""

# Configure Docker
echo "5. Configuring Docker to use NVIDIA runtime..."
nvidia-ctk runtime configure --runtime=docker
echo "✓ Docker configured"
echo ""

# Restart Docker
echo "6. Restarting Docker..."
systemctl restart docker
echo "✓ Docker restarted"
echo ""

# Verify installation
echo "7. Verifying installation..."
if docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi; then
    echo ""
    echo "=========================================="
    echo "✓ SUCCESS! NVIDIA Container Toolkit is installed and working"
    echo "=========================================="
    echo ""
    echo "You can now start your LLM service:"
    echo "  cd /home/asvil/git/local_llm_service"
    echo "  ./run.sh start"
else
    echo ""
    echo "=========================================="
    echo "✗ ERROR: Verification failed"
    echo "=========================================="
    echo ""
    echo "Please check Docker logs and NVIDIA driver installation"
    exit 1
fi
