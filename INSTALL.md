# Installation Guide for Raspberry Pi

This guide will help you install and configure the NS-Controller on your Raspberry Pi to act as a Nintendo Switch Pro Controller.

## Prerequisites

- Raspberry Pi Zero W, Zero 2 W, or Pi 4 (models with USB OTG support)
- Raspberry Pi OS (Bookworm or later recommended)
- MicroSD card with at least 8GB
- USB cable to connect Pi to Nintendo Switch

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

1. **Installs system dependencies**: Python 3 (full), venv, git, curl
2. **Configures USB gadget mode**: 
   - Adds `dtoverlay=dwc2` to `/boot/config.txt`
   - Adds required modules to `/etc/modules`
3. **Creates USB gadget setup script**: `/usr/local/bin/setup-usb-gadget.sh`
   - Configures the Pi as a Nintendo Switch Pro Controller USB HID device
   - Creates `/dev/hidg0` for controller communication
4. **Creates USB gadget systemd service**: Automatically sets up USB gadget on boot
5. **Installs the application**: Copies files to `/opt/ns-controller`
6. **Installs Python dependencies**: 
   - Installs Poetry using the official installer (works with externally managed environments)
   - Creates a virtual environment and installs required packages
7. **Creates ns-controller systemd service**: Runs the server automatically on startup

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
# Install Poetry using the official installer
# This works with externally managed Python environments
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH for current session
export PATH="$HOME/.local/bin:$PATH"

# Install project dependencies
cd ns-controller
poetry install
```

**Note**: Raspberry Pi OS uses an externally managed Python environment. The Poetry installer creates an isolated environment that works around this restriction. Do not use `pip install poetry` as it will fail with an externally-managed-environment error.

### 4. Run the Server

```bash
# Make sure Poetry is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Run the server
poetry run ns-controller --host 0.0.0.0 --port 9000
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
export PATH="$HOME/.local/bin:$PATH"
poetry run ns-controller
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
export PATH="$HOME/.local/bin:$PATH"
poetry run ns-controller --mock
```

This runs a mock server that simulates the controller without requiring `/dev/hidg0`.

## Performance on Raspberry Pi Zero W

The Raspberry Pi Zero W is resource-constrained:
- Streamlit UI may be slow to load (30-60 seconds)
- Macro execution should be fast and reliable
- Consider disabling the UI in production if not needed

## Support

For issues, questions, or contributions, please open an issue on the project repository.

