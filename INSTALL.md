# Installation Guide for Raspberry Pi

This guide will help you install and configure the NS-Controller on your Raspberry Pi to act as a Nintendo Switch Pro Controller.

## Prerequisites

- Raspberry Pi Zero W, Zero 2 W, or Pi 4 (models with USB OTG support)
- Raspberry Pi OS (Bookworm or later recommended)
- MicroSD card with at least 8GB (16GB recommended)
- At least 500MB free disk space for installation
- USB cable to connect Pi to Nintendo Switch

**Note**: If you're running low on disk space, free up space before installation:
```bash
# Remove unused packages
sudo apt autoremove -y

# Clean apt cache
sudo apt clean

# Clean old logs (keep last 7 days)
sudo journalctl --vacuum-time=7d
```

## Quick Installation

1. Clone or copy this repository to your Raspberry Pi:
   ```bash
   git clone <repository-url> ns-controller
   cd ns-controller
   ```

2. Run the installation script with sudo:
   ```bash
   sudo ./install.sh
   ```

3. Reboot the Raspberry Pi:
   ```bash
   sudo reboot
   ```

4. After reboot, connect your Raspberry Pi to the Nintendo Switch via USB cable.

5. Access the Streamlit UI from any device on your network:
   ```
   http://<raspberry-pi-ip>:8501
   ```

## What the Install Script Does

The `install.sh` script performs the following actions:

1. **Checks disk space**: Ensures at least 500MB is available
2. **Installs system dependencies**: Python 3 (full), venv, git, libffi-dev, build-essential
3. **Configures USB gadget mode**: 
   - Adds `dtoverlay=dwc2` to `/boot/config.txt`
   - Adds required modules to `/etc/modules`
4. **Creates USB gadget setup script**: `/usr/local/bin/setup-usb-gadget.sh`
   - Configures the Pi as a Nintendo Switch Pro Controller USB HID device
   - Creates `/dev/hidg0` for controller communication
5. **Creates USB gadget systemd service**: Automatically sets up USB gadget on boot
6. **Installs the application**: Copies files to `/opt/ns-controller`
7. **Installs Python dependencies**: 
   - Creates a virtual environment at `/opt/ns-controller/.venv`
   - Installs packages from requirements.txt using pip (with --no-cache-dir to save space)
8. **Creates ns-controller systemd service**: Runs the server automatically on startup

## Manual Installation

If you prefer to install manually or need to customize the installation:

### 1. Enable USB Gadget Mode

Edit `/boot/config.txt`:
```bash
sudo nano /boot/config.txt
```

Add this line at the end:
```
dtoverlay=dwc2
```

Edit `/etc/modules`:
```bash
sudo nano /etc/modules
```

Add these lines:
```
dwc2
libcomposite
```

### 2. Create USB Gadget Setup Script

Copy the USB gadget setup script from the install script or create your own based on the Nintendo Switch Pro Controller specifications.

### 3. Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install --no-cache-dir -r requirements.txt
```

### 4. Run the Server

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run the server
python -m ns_controller.cli --host 0.0.0.0 --port 9000
```

## Service Management

Once installed, the ns-controller runs as a systemd service:

### Check Status
```bash
sudo systemctl status ns-controller
```

### View Logs
```bash
sudo journalctl -u ns-controller -f
```

### Start/Stop/Restart
```bash
sudo systemctl start ns-controller
sudo systemctl stop ns-controller
sudo systemctl restart ns-controller
```

### Disable Auto-Start
```bash
sudo systemctl disable ns-controller
```

### Enable Auto-Start
```bash
sudo systemctl enable ns-controller
```

## Troubleshooting

### Installation Fails with "No space left on device"

Free up disk space:
```bash
# Remove unused packages
sudo apt autoremove -y

# Clean apt cache
sudo apt clean

# Remove old logs (keep last 7 days)
sudo journalctl --vacuum-time=7d

# Check available space
df -h /
```

After freeing up space, run the install script again.

### Installation Fails with "Package libffi was not found"

This should be fixed by the install script, but if you see this error:
```bash
sudo apt-get update
sudo apt-get install -y libffi-dev build-essential
```

Then run the install script again.

### USB Gadget Not Working

Check if `/dev/hidg0` exists:
```bash
ls -la /dev/hidg0
```

If it doesn't exist, manually run the setup script:
```bash
sudo /usr/local/bin/setup-usb-gadget.sh
```

Check USB gadget service:
```bash
sudo systemctl status usb-gadget
```

### Service Won't Start

Check the logs:
```bash
sudo journalctl -u ns-controller -n 50
```

Verify the HID device exists:
```bash
ls -la /dev/hidg0
```

Try running manually to see errors:
```bash
cd /opt/ns-controller
source .venv/bin/activate
python -m ns_controller.cli
```

### Can't Access Streamlit UI

1. Find your Pi's IP address:
   ```bash
   hostname -I
   ```

2. Make sure port 8501 is accessible:
   ```bash
   sudo netstat -tulpn | grep 8501
   ```

3. Check if Streamlit is running:
   ```bash
   ps aux | grep streamlit
   ```

### Switch Doesn't Recognize Controller

1. Make sure the USB cable supports data transfer (not just charging)
2. Try reconnecting the USB cable
3. Check that the gadget is properly configured:
   ```bash
   lsusb
   ```
   You should see "Nintendo Co., Ltd Pro Controller"

4. Restart the service:
   ```bash
   sudo systemctl restart ns-controller
   ```

## Uninstallation

To remove ns-controller:

```bash
# Stop and disable services
sudo systemctl stop ns-controller
sudo systemctl disable ns-controller
sudo systemctl stop usb-gadget
sudo systemctl disable usb-gadget

# Remove service files
sudo rm /etc/systemd/system/ns-controller.service
sudo rm /etc/systemd/system/usb-gadget.service
sudo rm /usr/local/bin/setup-usb-gadget.sh

# Remove application files
sudo rm -rf /opt/ns-controller

# Reload systemd
sudo systemctl daemon-reload

# Remove USB gadget configuration (optional)
# Edit /boot/config.txt and remove: dtoverlay=dwc2
# Edit /etc/modules and remove: dwc2 and libcomposite
```

## Network Access

The server listens on all network interfaces by default (`0.0.0.0`). This means:
- Access Streamlit UI: `http://<pi-ip>:8501`
- TCP server endpoint: `<pi-ip>:9000`

You can connect from any device on the same network (laptop, phone, tablet).

## Mock Mode

For testing without a physical connection to the Switch:

```bash
sudo systemctl stop ns-controller
cd /opt/ns-controller
source .venv/bin/activate
python -m ns_controller.cli --mock
```

This runs a mock server that simulates the controller without requiring `/dev/hidg0`.

## Performance on Raspberry Pi Zero W

The Raspberry Pi Zero W is resource-constrained:
- Streamlit UI may be slow to load (30-60 seconds)
- Macro execution should be fast and reliable
- Consider disabling the UI in production if not needed

## Support

For issues, questions, or contributions, please open an issue on the project repository.

