#!/bin/bash
# Quick fix script for USB gadget configuration issues
# Run with: sudo ./fix-usb-gadget-config.sh

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

echo "=========================================="
echo "Fixing USB Gadget Configuration"
echo "=========================================="
echo ""

# 1. Fix dr_mode=host in boot config
echo "[1/4] Checking boot configuration..."

if grep -q "dtoverlay=dwc2,dr_mode=host" /boot/firmware/config.txt 2>/dev/null; then
    echo "  Fixing /boot/firmware/config.txt..."
    sed -i 's/dtoverlay=dwc2,dr_mode=host/dtoverlay=dwc2/' /boot/firmware/config.txt
    echo "  ✓ Fixed dr_mode=host"
fi

if grep -q "dtoverlay=dwc2,dr_mode=host" /boot/config.txt 2>/dev/null; then
    echo "  Fixing /boot/config.txt..."
    sed -i 's/dtoverlay=dwc2,dr_mode=host/dtoverlay=dwc2/' /boot/config.txt
    echo "  ✓ Fixed dr_mode=host"
fi

echo "  Current boot config:"
grep "dtoverlay=dwc2" /boot/firmware/config.txt /boot/config.txt 2>/dev/null || echo "  Not found"
echo ""

# 2. Clean up duplicate modules in /etc/modules
echo "[2/4] Cleaning up /etc/modules..."

if [ -f /etc/modules ]; then
    # Remove duplicate lines while preserving order
    awk '!seen[$0]++' /etc/modules > /tmp/modules.tmp
    mv /tmp/modules.tmp /etc/modules
    echo "  ✓ Removed duplicate entries from /etc/modules"
fi

# 3. Create modern modules-load.d file
echo "[3/4] Creating /etc/modules-load.d/ns-controller.conf..."

cat > /etc/modules-load.d/ns-controller.conf << 'EOF'
# Kernel modules for Nintendo Switch Controller USB Gadget
dwc2
libcomposite
EOF

echo "  ✓ Created /etc/modules-load.d/ns-controller.conf"
echo ""

# 4. Show current state
echo "[4/4] Current configuration:"
echo ""
echo "Boot config (dwc2):"
grep "dtoverlay=dwc2" /boot/firmware/config.txt /boot/config.txt 2>/dev/null || echo "  Not found"
echo ""
echo "Modules (/etc/modules-load.d/ns-controller.conf):"
cat /etc/modules-load.d/ns-controller.conf
echo ""

echo "=========================================="
echo "Configuration Fixed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Reboot: sudo reboot"
echo "  2. After reboot, check UDC: ls /sys/class/udc/"
echo "  3. Run setup script: sudo ./setup-usb-gadget-manual.sh"
echo ""
echo "Note: A reboot is REQUIRED for the changes to take effect."
echo ""

