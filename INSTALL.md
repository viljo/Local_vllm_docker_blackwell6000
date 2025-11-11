# Installation Guide - Local vLLM Service

This guide covers the installation of the Local vLLM Service on Debian 13 (Trixie) with automatic startup after boot.

## Prerequisites

### System Requirements
- **OS**: Debian 13 (Trixie) or compatible
- **GPU**: NVIDIA GPU with CUDA support
- **RAM**: 16GB+ recommended
- **Disk**: 500GB+ recommended (for model storage)
- **Network**: Internet connection for initial setup

### Required Software
- NVIDIA GPU Drivers (version 525+)
- Root/sudo privileges

## Quick Install

### One-Command Installation

```bash
sudo ./install_debian.sh
```

This automated script will:
1. ✅ Check system requirements
2. ✅ Install Docker and Docker Compose
3. ✅ Install NVIDIA Container Toolkit
4. ✅ Clone/copy service to `/opt/local_llm_service`
5. ✅ Create `.env` file with generated API key
6. ✅ Setup models directory at `/ssd/LLMs`
7. ✅ Copy existing models from dev directory (if installing from git repo)
8. ✅ Configure docker-compose.yml to use `/ssd/LLMs`
9. ✅ Create systemd service for autostart
10. ✅ Start the service

### Installation Process

The script will show progress like this:

```
[INFO] Starting Local vLLM Service installation on Debian 13...
[INFO] Checking system requirements...
[SUCCESS] NVIDIA GPU detected: NVIDIA RTX 6000 Ada, Driver Version: 550.120, 48685 MiB
[INFO] Installing Docker...
[SUCCESS] Docker installed successfully
[INFO] Installing NVIDIA Container Toolkit...
[SUCCESS] NVIDIA Container Toolkit installed and configured
[INFO] Setting up service in /opt/local_llm_service...
[SUCCESS] Service files copied to /opt/local_llm_service
[INFO] Creating systemd service...
[SUCCESS] Systemd service created
[INFO] Enabling and starting service...
[SUCCESS] Service enabled and started
[SUCCESS] Local vLLM Service installed successfully!
```

## Manual Installation

If you prefer manual installation:

### 1. Install Docker

```bash
# Add Docker repository
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
```

### 2. Install NVIDIA Container Toolkit

```bash
# Add NVIDIA repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 3. Clone Repository

```bash
# Clone to /opt
sudo git clone -b 002-gpt-oss-models-dynamic-reload \
    https://github.com/viljo/Local_vllm_docker_blackwell6000.git \
    /opt/local_llm_service

cd /opt/local_llm_service
```

### 4. Create Systemd Service

```bash
sudo tee /etc/systemd/system/local-llm-service.service > /dev/null <<'EOF'
[Unit]
Description=Local vLLM Service
Documentation=https://github.com/viljo/Local_vllm_docker_blackwell6000
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/local_llm_service
Environment="PWD=/opt/local_llm_service"
ExecStartPre=/usr/bin/docker compose down
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
```

### 5. Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable local-llm-service
sudo systemctl start local-llm-service
```

## Post-Installation

### Verify Installation

```bash
# Check service status
sudo systemctl status local-llm-service

# Check running containers
cd /opt/local_llm_service
docker compose ps

# View logs
docker compose logs -f
```

### Access the Service

- **WebUI**: http://localhost:3000 (or http://YOUR_IP:3000)
- **API**: http://localhost:8080/v1

### First Run

On first run, the service will:
1. Auto-start the largest downloaded model (if any models were copied during installation)
2. Download models on-demand when you start them in the WebUI
3. Initialize GPU memory allocation

**Note:**
- Models are stored in `/ssd/LLMs` for fast access and large storage capacity
- If you run the installer from the dev directory (`/home/asvil/git/local_llm_service`), any existing models will be automatically copied to `/ssd/LLMs` to save download time

Wait 1-2 minutes for models to fully load after starting them.

## Service Management

### Start/Stop/Restart

```bash
# Start service
sudo systemctl start local-llm-service

# Stop service
sudo systemctl stop local-llm-service

# Restart service
sudo systemctl restart local-llm-service

# Check status
sudo systemctl status local-llm-service
```

### View Logs

```bash
# System logs
sudo journalctl -u local-llm-service -f

# Container logs
cd /opt/local_llm_service
docker compose logs -f

# Specific container
docker compose logs -f vllm-router
docker compose logs -f vllm-gpt-oss-120b
```

### Disable Autostart

```bash
sudo systemctl disable local-llm-service
```

### Re-enable Autostart

```bash
sudo systemctl enable local-llm-service
```

## Uninstallation

### Quick Uninstall

```bash
sudo ./uninstall_debian.sh
```

### Keep Model Data

```bash
sudo ./uninstall_debian.sh --keep-data
```

This will:
- Stop and remove the service
- Remove installation files
- Preserve model data in backup directory

### Manual Uninstall

```bash
# Stop and disable service
sudo systemctl stop local-llm-service
sudo systemctl disable local-llm-service

# Stop containers
cd /opt/local_llm_service
docker compose down -v

# Remove service file
sudo rm /etc/systemd/system/local-llm-service.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/local_llm_service
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u local-llm-service -n 100

# Check Docker status
sudo systemctl status docker

# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### NVIDIA GPU Not Detected

```bash
# Check drivers
nvidia-smi

# Reinstall NVIDIA Container Toolkit
sudo apt-get install --reinstall nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Insufficient GPU Memory

The service will auto-unload models to free memory. Check logs:

```bash
docker compose logs vllm-router | grep -i "memory\|unload"
```

### WebUI Shows 401 Authentication Errors

If the WebUI shows "Error: HTTP error! status: 401" when sending messages:

**Cause**: API key mismatch between frontend and backend. The frontend has the API key baked in at build time.

**Solution**: Rebuild the frontend container:

```bash
cd /opt/local_llm_service
sudo docker compose build webui-frontend
sudo docker compose up -d webui-frontend
```

**Prevention**: The installer scripts now automatically rebuild the frontend. If you manually change the API key in `.env`, always rebuild:

```bash
# After changing API_KEY in .env
sudo docker compose build webui-frontend
sudo docker compose up -d webui-frontend
```

### Port Already in Use

If ports 3000 or 8080 are in use, edit `/opt/local_llm_service/docker-compose.yml`:

```yaml
services:
  vllm-router:
    ports:
      - "8081:8080"  # Change 8080 to 8081

  webui-frontend:
    ports:
      - "3001:3000"  # Change 3000 to 3001
```

Then restart:

```bash
sudo systemctl restart local-llm-service
```

## Updating

### Update to Latest Version

```bash
cd /opt/local_llm_service
sudo git pull
sudo systemctl restart local-llm-service
```

### Update Docker Images

```bash
cd /opt/local_llm_service
docker compose pull
sudo systemctl restart local-llm-service
```

## Advanced Configuration

### Models Storage Location

By default, models are stored in `/ssd/LLMs`. This is configured during installation.

To change the models directory:

1. Stop the service:
   ```bash
   sudo systemctl stop local-llm-service
   ```

2. Edit `/opt/local_llm_service/docker-compose.yml`:
   ```bash
   sudo nano /opt/local_llm_service/docker-compose.yml
   ```

3. Find all lines with `/ssd/LLMs:/models` and change to your desired path:
   ```yaml
   volumes:
     - /your/new/path:/models  # Change this
   ```

4. Move existing models (optional):
   ```bash
   sudo mv /ssd/LLMs/* /your/new/path/
   ```

5. Restart the service:
   ```bash
   sudo systemctl restart local-llm-service
   ```

### Configure GPU Memory Limit

Edit model settings in `docker-compose.yml`:

```yaml
environment:
  - GPU_MEMORY_UTILIZATION=0.85  # Default is 0.85 (85%)
```

### Add More Models

Edit `router/app/config.py` and rebuild:

```bash
cd /opt/local_llm_service
docker compose build router
sudo systemctl restart local-llm-service
```

## Support

- **Issues**: https://github.com/viljo/Local_vllm_docker_blackwell6000/issues
- **Documentation**: See project README.md
- **Logs**: Always check logs first with `journalctl -u local-llm-service -f`

## License

See project LICENSE file.
