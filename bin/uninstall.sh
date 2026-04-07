#!/bin/bash
set -e

echo "==================================="
echo "NS-Controller Uninstall Script"
echo "==================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

echo "This will remove ns-controller from your system."
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

INSTALL_DIR="/opt/ns-controller"

# 1. Stop and disable services
echo "[1/5] Stopping and disabling services..."
systemctl stop ns-controller 2>/dev/null || true
systemctl disable ns-controller 2>/dev/null || true
systemctl stop usb-gadget 2>/dev/null || true
systemctl disable usb-gadget 2>/dev/null || true
echo "  Services stopped and disabled"

# 2. Remove service files
echo "[2/5] Removing service files..."
rm -f /etc/systemd/system/ns-controller.service
rm -f /etc/systemd/system/usb-gadget.service
rm -f /usr/local/bin/setup-usb-gadget.sh
echo "  Service files removed"

# 3. Reload systemd
echo "[3/5] Reloading systemd..."
systemctl daemon-reload
systemctl reset-failed
echo "  Systemd reloaded"

# 4. Remove application files
echo "[4/5] Removing application files..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo "  Removed $INSTALL_DIR"
else
    echo "  $INSTALL_DIR not found (already removed?)"
fi

# 5. Clean up USB gadget
echo "[5/5] Cleaning up USB gadget..."
GADGET_DIR="/sys/kernel/config/usb_gadget/procontroller"
if [ -d "$GADGET_DIR" ]; then
    if [ -e "$GADGET_DIR/UDC" ]; then
        echo "" > "$GADGET_DIR/UDC" 2>/dev/null || true
    fi
    find "$GADGET_DIR/configs/c.1" -maxdepth 1 -type l -exec rm {} \; 2>/dev/null || true
    rmdir "$GADGET_DIR/configs/c.1/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR/configs/c.1" 2>/dev/null || true
    rmdir "$GADGET_DIR/functions/hid.usb0" 2>/dev/null || true
    rmdir "$GADGET_DIR/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR" 2>/dev/null || true
    echo "  USB gadget cleaned up"
else
    echo "  USB gadget not found (already removed?)"
fi

echo ""
echo "==================================="
echo "Uninstall Complete!"
echo "==================================="
echo ""
echo "NS-Controller has been removed from your system."
echo ""
echo "Note: USB gadget configuration in /boot/config.txt and /etc/modules"
echo "      has NOT been removed. If you want to completely remove USB gadget"
echo "      support, manually edit these files:"
echo ""
echo "  1. sudo nano /boot/config.txt"
echo "     Remove line: dtoverlay=dwc2"
echo ""
echo "  2. sudo nano /etc/modules"
echo "     Remove lines: dwc2 and libcomposite"
echo ""
echo "  3. sudo reboot"
echo ""

