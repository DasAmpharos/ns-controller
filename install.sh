#!/bin/bash
set -e

echo "==================================="
echo "NS-Controller Installation Script"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

INSTALL_DIR="/opt/ns-controller"
SERVICE_USER="${SUDO_USER:-$USER}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing to: $INSTALL_DIR"
echo "Running as user: $SERVICE_USER"
echo ""

# Check available disk space (require at least 500MB free)
echo "Checking disk space..."
AVAILABLE_SPACE=$(df / | tail -1 | awk '{print $4}')
REQUIRED_SPACE=512000  # 500MB in KB

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo "Error: Not enough disk space available"
    echo "Available: $(($AVAILABLE_SPACE / 1024))MB"
    echo "Required: $(($REQUIRED_SPACE / 1024))MB"
    echo ""
    echo "Free up space by:"
    echo "  - Removing unused packages: sudo apt autoremove"
    echo "  - Cleaning apt cache: sudo apt clean"
    echo "  - Removing old logs: sudo journalctl --vacuum-time=7d"
    exit 1
fi
echo "Available disk space: $(($AVAILABLE_SPACE / 1024))MB"
echo ""

# 1. Install system dependencies
echo "[1/7] Installing system dependencies..."
apt-get update
apt-get install -y python3-full python3-venv
# Clean up to save space
apt-get clean
echo "  Cleaned apt cache to free up space"

# 2. Enable dwc2 overlay for USB gadget mode
echo "[2/7] Configuring USB gadget mode..."

# Detect which config file to use
if [ -f /boot/firmware/config.txt ]; then
    BOOT_CONFIG="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    BOOT_CONFIG="/boot/config.txt"
else
    echo "Error: Could not find boot config file"
    exit 1
fi

echo "  Using boot config: $BOOT_CONFIG"

# Check for and fix dr_mode=host if present
if grep -q "dtoverlay=dwc2,dr_mode=host" "$BOOT_CONFIG"; then
    echo "  Fixing dr_mode=host in $BOOT_CONFIG..."
    sed -i 's/dtoverlay=dwc2,dr_mode=host/dtoverlay=dwc2/' "$BOOT_CONFIG"
    echo "  Fixed: Changed dr_mode=host to gadget mode"
fi

# Add dwc2 overlay if not already present
if ! grep -q "^dtoverlay=dwc2" "$BOOT_CONFIG"; then
    echo "dtoverlay=dwc2" >> "$BOOT_CONFIG"
    echo "  Added dtoverlay=dwc2 to $BOOT_CONFIG"
else
    echo "  dtoverlay=dwc2 already configured in $BOOT_CONFIG"
fi

# Use modern /etc/modules-load.d/ instead of obsolete /etc/modules
MODULES_FILE="/etc/modules-load.d/ns-controller.conf"
echo "  Configuring kernel modules in $MODULES_FILE"

cat > "$MODULES_FILE" << 'EOF'
# Kernel modules for Nintendo Switch Controller USB Gadget
dwc2
libcomposite
EOF

echo "  Created $MODULES_FILE"

# 3. Create USB gadget setup script
echo "[3/7] Creating USB gadget setup script..."
cat > /usr/local/bin/setup-usb-gadget.sh << 'EOF'
#!/bin/bash
# Setup Nintendo Switch Pro Controller USB Gadget

GADGET_DIR="/sys/kernel/config/usb_gadget/procontroller"

# Remove existing gadget if it exists
if [ -d "$GADGET_DIR" ]; then
    echo "Removing existing USB gadget..."
    if [ -e "$GADGET_DIR/UDC" ]; then
        echo "" > "$GADGET_DIR/UDC"
    fi
    find "$GADGET_DIR/configs/c.1" -maxdepth 1 -type l -exec rm {} \; 2>/dev/null || true
    rmdir "$GADGET_DIR/configs/c.1/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR/configs/c.1" 2>/dev/null || true
    rmdir "$GADGET_DIR/functions/hid.usb0" 2>/dev/null || true
    rmdir "$GADGET_DIR/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR" 2>/dev/null || true
fi

# Load modules
modprobe libcomposite

# Create gadget directory
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

# Configure USB device descriptor
echo 0x057e > idVendor   # Nintendo
echo 0x2009 > idProduct  # Pro Controller
echo 0x0200 > bcdUSB     # USB 2.0
echo 0x0100 > bcdDevice  # Device version 1.0

# Create English strings
mkdir -p strings/0x409
echo "000000000001" > strings/0x409/serialnumber
echo "Nintendo Co., Ltd." > strings/0x409/manufacturer
echo "Pro Controller" > strings/0x409/product

# Create HID function
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol
echo 1 > functions/hid.usb0/subclass
echo 64 > functions/hid.usb0/report_length

# Pro Controller HID Report Descriptor
echo -ne '\x05\x01\x09\x05\xa1\x01\x15\x00\x25\x01\x35\x00\x45\x01\x75\x01\x95\x0e\x05\x09\x19\x01\x29\x0e\x81\x02\x95\x02\x81\x03\x05\x01\x25\x07\x46\x3b\x01\x75\x04\x95\x01\x65\x14\x09\x39\x81\x42\x65\x00\x95\x01\x81\x03\x26\xff\x00\x46\xff\x00\x09\x30\x09\x31\x09\x32\x09\x35\x75\x08\x95\x04\x81\x02\x06\x00\xff\x09\x20\x95\x01\x81\x02\x0a\x21\x26\x95\x08\x81\x02\x0a\x21\x26\x95\x1d\x81\x02\x85\x30\x0a\x21\x26\x95\x30\x91\x02\x85\x21\x0a\x21\x26\x95\x30\x91\x02\x85\x80\x0a\x21\x26\x95\x30\x91\x02\x85\x81\x0a\x21\x26\x95\x30\x91\x02\x85\x82\x0a\x21\x26\x95\x30\x91\x02\xc0' > functions/hid.usb0/report_desc

# Create configuration
mkdir -p configs/c.1
mkdir -p configs/c.1/strings/0x409
echo "Config 1" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower

# Link function to configuration
ln -s functions/hid.usb0 configs/c.1/

# Enable gadget
UDC_DEVICE=$(ls /sys/class/udc | head -n 1)
echo "$UDC_DEVICE" > UDC

echo "USB gadget setup complete. HID device should be at /dev/hidg0"
EOF

chmod +x /usr/local/bin/setup-usb-gadget.sh
echo "  Created /usr/local/bin/setup-usb-gadget.sh"

# 4. Create systemd service for USB gadget setup
echo "[4/7] Creating USB gadget systemd service..."
cat > /etc/systemd/system/usb-gadget.service << 'EOF'
[Unit]
Description=Setup Nintendo Switch Pro Controller USB Gadget
DefaultDependencies=no
After=sys-kernel-config.mount
Before=basic.target
ConditionPathExists=/sys/kernel/config

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-usb-gadget.sh
RemainAfterExit=yes

[Install]
WantedBy=basic.target
EOF

systemctl daemon-reload
systemctl enable usb-gadget.service
echo "  Created and enabled usb-gadget.service"

# Start the service immediately to create /dev/hidg0
echo "  Starting usb-gadget service..."
systemctl start usb-gadget.service

# Verify /dev/hidg0 was created
sleep 1
if [ -e /dev/hidg0 ]; then
    echo "  ✓ /dev/hidg0 created successfully"
else
    echo "  ⚠ Warning: /dev/hidg0 not created. Check 'systemctl status usb-gadget.service' after installation."
fi

# 5. Copy project files
echo "[5/7] Installing ns-controller application..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# 6. Install Python dependencies
echo "[6/7] Installing Python dependencies..."
cd "$INSTALL_DIR"

# Create virtual environment
VENV_PATH="$INSTALL_DIR/.venv"
echo "  Creating virtual environment..."
sudo -u "$SERVICE_USER" python3 -m venv "$VENV_PATH"

# Install dependencies with pip (no cache to save space)
echo "  Installing packages (this may take a few minutes)..."
sudo -u "$SERVICE_USER" bash << EOF
source "$VENV_PATH/bin/activate"
pip install --no-cache-dir -r "$INSTALL_DIR/requirements.txt"
deactivate
EOF

PYTHON_PATH="$VENV_PATH/bin/python"

echo "  Virtual environment: $VENV_PATH"
echo "  Python path: $PYTHON_PATH"

# 7. Create systemd service for ns-controller
echo "[7/7] Creating ns-controller systemd service..."

cat > /etc/systemd/system/ns-controller.service << EOF
[Unit]
Description=Nintendo Switch Controller Server
After=network.target usb-gadget.service
Requires=usb-gadget.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$PYTHON_PATH -m ns_controller.cli --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/dev/hidg0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ns-controller.service
echo "  Created and enabled ns-controller.service"

echo ""
echo "==================================="
echo "Installation Complete!"
echo "==================================="
echo ""
echo "The USB gadget and ns-controller service have been installed."
echo ""
echo "Next steps:"
echo "  1. Reboot the Raspberry Pi: sudo reboot"
echo "  2. After reboot, connect the Pi to your Nintendo Switch via USB"
echo "  3. Access the Streamlit UI at: http://$(hostname -I | awk '{print $1}'):8501"
echo "  4. The TCP server will be listening on port 9000"
echo ""
echo "Useful commands:"
echo "  - Check service status: sudo systemctl status ns-controller"
echo "  - View logs: sudo journalctl -u ns-controller -f"
echo "  - Restart service: sudo systemctl restart ns-controller"
echo "  - Stop service: sudo systemctl stop ns-controller"
echo "  - Check USB gadget: ls -la /dev/hidg0"
echo ""
echo "Note: A reboot is required for USB gadget changes to take effect."

