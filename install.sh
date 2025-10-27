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

DEVICE=/dev/hidg0
GADGET_DIR="/sys/kernel/config/usb_gadget/procon"

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
echo 0x00 > bDeviceClass
echo 0x00 > bDeviceSubClass
echo 0x00 > bDeviceProtocol

# Create English strings
mkdir -p strings/0x409
echo "000000000001" > strings/0x409/serialnumber
echo "Nintendo Co., Ltd." > strings/0x409/manufacturer
echo "Pro Controller" > strings/0x409/product

mkdir -p configs/c.1/strings/0x409
echo "Nintendo Switch Pro Controller" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower
echo 0xa0 > configs/c.1/bmAttributes

mkdir -p functions/hid.usb0
echo 0 > functions/hid.usb0/protocol
echo 0 > functions/hid.usb0/subclass
echo 64 > functions/hid.usb0/report_length
echo 050115000904A1018530050105091901290A150025017501950A5500650081020509190B290E150025017501950481027501950281030B01000100A1000B300001000B310001000B320001000B35000100150027FFFF0000751095048102C00B39000100150025073500463B0165147504950181020509190F2912150025017501950481027508953481030600FF852109017508953F8103858109027508953F8103850109037508953F9183851009047508953F9183858009057508953F9183858209067508953F9183C0 | xxd -r -ps > functions/hid.usb0/report_desc

# Link function to configuration
ln -s functions/hid.usb0 configs/c.1/

# Enable gadget
UDC_DEVICE=$(ls /sys/class/udc | head -n 1)
echo "$UDC_DEVICE" > UDC

chmod 666 $DEVICE
ls -l $DEVICE

echo "USB gadget setup complete. HID device should be at $DEVICE"
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
echo "  3. The TCP server will be listening on port 9000"
echo ""
echo "Useful commands:"
echo "  - Check service status: sudo systemctl status ns-controller"
echo "  - View logs: sudo journalctl -u ns-controller -f"
echo "  - Restart service: sudo systemctl restart ns-controller"
echo "  - Stop service: sudo systemctl stop ns-controller"
echo "  - Check USB gadget: ls -la /dev/hidg0"
echo ""
echo "Note: A reboot is required for USB gadget changes to take effect."
