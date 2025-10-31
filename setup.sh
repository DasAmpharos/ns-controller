#!/bin/bash

# NS Controller Setup Script
# Based on: https://github.com/omakoto/raspberry-switch-control
# This script sets up a Raspberry Pi Zero W as a Nintendo Switch Pro Controller

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_TXT="/boot/firmware/config.txt"
CMDLINE_TXT="/boot/firmware/cmdline.txt"
MODULES_LOAD_DIR="/etc/modules-load.d"

# Check if running as root
if (( $(id -u) != 0 )); then
    echo "Error: This script must be run as root (use sudo)" 1>&2
    exit 1
fi

echo "=========================================="
echo "NS Controller Setup"
echo "=========================================="
echo ""

# Step 1: Configure boot settings for USB gadget mode
echo "[1/5] Configuring boot settings..."

# Backup config.txt if not already backed up
if [[ ! -f "${CONFIG_TXT}.backup" ]]; then
    echo "  Backing up ${CONFIG_TXT}..."
    cp "${CONFIG_TXT}" "${CONFIG_TXT}.backup"
fi

# Check and add dtoverlay=dwc2
if ! grep -q "^dtoverlay=dwc2" "${CONFIG_TXT}"; then
    echo "  Adding dtoverlay=dwc2,dr_mode=peripheral to ${CONFIG_TXT}..."
    echo "" >> "${CONFIG_TXT}"
    echo "# Enable USB gadget mode for NS Controller" >> "${CONFIG_TXT}"
    echo "dtoverlay=dwc2,dr_mode=peripheral" >> "${CONFIG_TXT}"
else
    echo "  dtoverlay=dwc2 already configured"
fi

# Step 2: Configure modules to load at boot
echo ""
echo "[2/5] Configuring kernel modules..."

mkdir -p "${MODULES_LOAD_DIR}"

# Create dwc2.conf for module loading
echo "  Creating ${MODULES_LOAD_DIR}/dwc2.conf..."
cat > "${MODULES_LOAD_DIR}/dwc2.conf" <<EOF
# USB gadget mode modules for NS Controller
dwc2
libcomposite
EOF

echo "  Modules will be loaded at boot: dwc2, libcomposite"

# Step 3: Create systemd service for USB gadget setup
echo ""
echo "[3/5] Creating systemd service for USB gadget..."

cat > /etc/systemd/system/ns-gadget.service <<EOF
[Unit]
Description=Nintendo Switch Pro Controller USB Gadget
After=systemd-modules-load.service
Before=ns-controller.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=${SCRIPT_DIR}/create-gadget.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "  Created /etc/systemd/system/ns-gadget.service"

# Step 4: Create systemd service for the controller server
echo ""
echo "[4/5] Creating systemd service for NS Controller..."

cat > /etc/systemd/system/ns-controller.service <<EOF
[Unit]
Description=Nintendo Switch Controller HTTP Server
After=network.target ns-gadget.service
Requires=ns-gadget.service

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Give the USB gadget time to be enumerated by the Switch
StartLimitBurst=10
StartLimitIntervalSec=60

[Install]
WantedBy=multi-user.target
EOF

echo "  Created /etc/systemd/system/ns-controller.service"

# Step 5: Enable and start services
echo ""
echo "[5/5] Enabling services..."

systemctl daemon-reload

echo "  Enabling ns-gadget.service..."
systemctl enable ns-gadget.service

echo "  Enabling ns-controller.service..."
systemctl enable ns-controller.service

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Reboot your Raspberry Pi: sudo reboot"
echo "  2. Connect the Pi Zero W to your Nintendo Switch via USB"
echo "  3. The controller should appear as a Pro Controller"
echo "  4. Send commands via HTTP API:"
echo "     curl -X POST http://<pi-ip>:8000/update \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"buttons\": 0, \"hat\": 0, \"lx\": 0, \"ly\": 0, \"rx\": 0, \"ry\": 0}'"
echo ""
echo "Useful commands:"
echo "  - Check gadget status: systemctl status ns-gadget.service"
echo "  - Check controller status: systemctl status ns-controller.service"
echo "  - View controller logs: journalctl -u ns-controller.service -f"
echo "  - Check USB gadget device: ls -l /dev/hidg0"
echo "  - Verify modules loaded: lsmod | grep -E 'dwc2|libcomposite'"
echo ""

