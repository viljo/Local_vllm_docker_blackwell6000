# Testing the Installation Script

## Prerequisites

Before testing the installation script, ensure you have:

1. **Sudo Access**: You will need root/sudo privileges
2. **Clean System**: For best results, test on a fresh Debian 13 installation
3. **Backups**: If testing on an existing system, backup important data

## Pre-Installation Verification

### 1. Verify Script Syntax

```bash
# Check installation script
bash -n install_debian.sh
# Should output: (nothing if valid)

# Check uninstall script
bash -n uninstall_debian.sh
# Should output: (nothing if valid)
```

### 2. Check Prerequisites

```bash
# Check if Docker is installed
docker --version

# Check NVIDIA GPU
nvidia-smi

# Check Git
git --version
```

## Installation Test Procedure

### Step 1: Stop Current Services (if running)

```bash
# If you're currently running from the dev directory
cd /home/asvil/git/local_llm_service
docker compose down

# Stop any model containers
docker stop vllm-gpt-oss-120b vllm-gpt-oss-20b vllm-coder vllm-general 2>/dev/null || true
```

### Step 2: Run the Installation Script

```bash
# Run with sudo
sudo ./install_debian.sh
```

**Expected Output:**

```
[INFO] Starting Local vLLM Service installation on Debian 13...
[INFO] Checking system requirements...
[SUCCESS] NVIDIA GPU detected: NVIDIA RTX PRO 6000 ...
[INFO] Installing Docker...
[SUCCESS] Docker is already installed (or newly installed)
[INFO] Installing NVIDIA Container Toolkit...
[SUCCESS] NVIDIA Container Toolkit installed and configured
[INFO] Setting up service in /opt/local_llm_service...
[SUCCESS] Service files copied to /opt/local_llm_service
[INFO] Creating systemd service...
[SUCCESS] Systemd service created
[INFO] Enabling and starting service...
[SUCCESS] Service enabled and started
[INFO] Waiting for services to start...
[SUCCESS] Service is running

========================================================================
✅ Local vLLM Service installed successfully!
========================================================================
```

### Step 3: Verify Installation

Run the automated test script:

```bash
./test_installation.sh
```

**Expected Output:**

```
========================================================================
Installation Test Suite
========================================================================

[TEST] Checking installation directory...
[PASS] Installation directory exists: /opt/local_llm_service
[TEST] Checking docker-compose.yml...
[PASS] docker-compose.yml found
[TEST] Checking systemd service...
[PASS] Systemd service file exists
[TEST] Checking if service is enabled...
[PASS] Service is enabled for autostart
[TEST] Checking if service is running...
[PASS] Service is active
[TEST] Checking Docker containers...
[PASS] Docker containers are running (3 containers)
[TEST] Checking WebUI accessibility...
[PASS] WebUI is accessible at http://localhost:3000
[TEST] Checking API accessibility...
[PASS] API is accessible at http://localhost:8080
[TEST] Checking GPU access in containers...
[PASS] GPU is accessible in containers
[TEST] Checking autostart configuration...
[PASS] Service is configured to start after boot

========================================================================
✅ All tests passed!
Installation is working correctly.
========================================================================
```

### Step 4: Manual Verification

#### Check Service Status

```bash
sudo systemctl status local-llm-service
```

Expected output includes:
- `Active: active (running)`
- `Loaded: loaded (/etc/systemd/system/local-llm-service.service; enabled)`

#### Check Running Containers

```bash
cd /opt/local_llm_service
docker compose ps
```

Should show:
- `vllm-router` - Running (healthy)
- `webui-frontend` - Running
- One or more model containers (e.g., `vllm-gpt-oss-120b`)

#### Check Logs

```bash
# System logs
sudo journalctl -u local-llm-service -n 50

# Container logs
cd /opt/local_llm_service
docker compose logs -f
```

Look for:
- "Auto-starting largest downloaded model"
- "Successfully started gpt-oss-120b" (or similar)
- No error messages

#### Access WebUI

Open browser and navigate to:
- http://localhost:3000

You should see the Local LLM Chat interface.

#### Test API

```bash
# Health check
curl http://localhost:8080/health

# Model status
curl http://localhost:8080/v1/models/status | jq .
```

### Step 5: Test Autostart After Reboot

```bash
# Reboot the system
sudo reboot

# After reboot, check if service started automatically
sudo systemctl status local-llm-service

# Should show "active (running)"
```

## Uninstallation Test

### Test Standard Uninstall

```bash
sudo ./uninstall_debian.sh
```

When prompted, type `yes` and press Enter.

**Verify uninstallation:**

```bash
# Service should not exist
sudo systemctl status local-llm-service
# Should show: "could not be found"

# Directory should be removed
ls /opt/local_llm_service
# Should show: "No such file or directory"

# Containers should be stopped
docker ps --filter "name=vllm-"
# Should show: empty list (just headers)
```

### Test Uninstall with Data Preservation

```bash
# First, install again
sudo ./install_debian.sh

# Wait for models to download (if applicable)
sleep 60

# Uninstall but keep data
sudo ./uninstall_debian.sh --keep-data
```

When prompted, type `yes` and press Enter.

**Verify data preservation:**

```bash
# Check for backup directory
ls -la /opt/ | grep "local_llm_service.backup"
# Should show: backup directory with timestamp

# Check models were preserved
ls /opt/local_llm_service.backup-*/models
# Should show: models directory with data
```

## Troubleshooting Common Issues

### Issue: "Docker is not installed"

**Solution:**
```bash
# The script should install Docker automatically
# If it fails, check logs:
sudo journalctl -xe | grep docker
```

### Issue: "NVIDIA GPU not detected"

**Solution:**
```bash
# Check NVIDIA drivers
nvidia-smi

# If not working, install drivers first:
sudo apt-get update
sudo apt-get install -y nvidia-driver-550
sudo reboot
```

### Issue: "Service fails to start"

**Common Causes**:

#### 1. Read-only filesystem error: `mkdir /root/.docker: read-only file system`

This error occurs when systemd's security settings prevent Docker from creating necessary directories.

**Quick Fix:**
```bash
# Run the fix script
sudo ./fix_systemd_service.sh
```

This will update the service file to remove the conflicting security settings.

#### 2. Missing PWD environment variable

If you see errors related to file paths or template mounting, the service might be missing the `PWD` environment variable.

**Check logs:**
```bash
sudo journalctl -xeu local-llm-service -n 50
```

**Manual Fix:**
```bash
# Edit the service file
sudo nano /etc/systemd/system/local-llm-service.service

# Ensure this line is in the [Service] section:
Environment="PWD=/opt/local_llm_service"

# Remove these lines if present (they conflict with Docker):
# ProtectSystem=strict
# ProtectHome=yes
# ReadWritePaths=/opt/local_llm_service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart local-llm-service
```

**Other Diagnostic Commands:**
```bash
# Check detailed logs
sudo journalctl -u local-llm-service -n 100 --no-pager

# Check Docker status
sudo systemctl status docker

# Verify NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Try running docker compose manually
cd /opt/local_llm_service
sudo docker compose up -d
```

### Issue: "No models visible in Model Manager"

**Symptom**: WebUI loads but Model Manager shows no models, or you see 401 Unauthorized errors in logs

**Root Cause**: Missing `.env` file with API key configuration

**Quick Fix:**
```bash
# Run the fix script
cd /home/asvil/git/local_llm_service
sudo ./fix_env.sh
```

This will create a `.env` file with a randomly generated API key and restart the service.

**Manual Fix:**
```bash
# Copy the template
sudo cp /opt/local_llm_service/.env.example /opt/local_llm_service/.env

# Generate a random API key
RANDOM_KEY="sk-local-$(openssl rand -hex 16)"

# Update the .env file
sudo sed -i "s/sk-local-your-secret-key-here/$RANDOM_KEY/" /opt/local_llm_service/.env

# Restart service
sudo systemctl restart local-llm-service
```

### Issue: "Containers stuck in 'starting' state"

**Solution:**
```bash
# Check container logs
cd /opt/local_llm_service
docker compose logs vllm-router
docker compose logs vllm-gpt-oss-120b

# Common causes:
# - Insufficient GPU memory
# - Model files not downloaded
# - Network issues
```

### Issue: "Port already in use"

**Solution:**
```bash
# Check what's using the ports
sudo lsof -i :3000
sudo lsof -i :8080

# Kill conflicting processes or change ports in docker-compose.yml
```

## Test Results Checklist

After running all tests, verify:

- [ ] Installation script completes without errors
- [ ] Systemd service is created and enabled
- [ ] Containers start successfully
- [ ] WebUI is accessible
- [ ] API endpoints respond
- [ ] GPU is accessible in containers
- [ ] Service survives reboot (autostart works)
- [ ] Uninstallation removes all components
- [ ] `--keep-data` flag preserves model data

## Report Issues

If you encounter issues during testing:

1. **Collect logs:**
   ```bash
   sudo journalctl -u local-llm-service -n 200 > install_test_logs.txt
   docker compose logs >> install_test_logs.txt
   ```

2. **System information:**
   ```bash
   uname -a > system_info.txt
   docker --version >> system_info.txt
   nvidia-smi >> system_info.txt
   ```

3. **Create GitHub issue** with:
   - Description of the problem
   - Installation logs
   - System information
   - Steps to reproduce

## Success Criteria

Installation is considered successful if:

1. ✅ All automated tests pass (`./test_installation.sh`)
2. ✅ WebUI is accessible and functional
3. ✅ Models can be loaded and switched
4. ✅ Service auto-starts after reboot
5. ✅ Uninstallation cleanly removes all components
6. ✅ No errors in logs

---

**Note:** This guide is for testing purposes. For production deployment, review and adjust settings in `/opt/local_llm_service/docker-compose.yml` and `router/app/config.py` as needed.
