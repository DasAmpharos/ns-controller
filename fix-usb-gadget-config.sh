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

# 1. Fix dr_mode=host in boot config and remove duplicates
echo "[1/4] Checking boot configuration..."

BOOT_CONFIG="/boot/firmware/config.txt"

if [ ! -f "$BOOT_CONFIG" ]; then
    echo "  Error: $BOOT_CONFIG not found!"
    exit 1
fi

echo "  Working with: $BOOT_CONFIG"

# Fix dr_mode=host if present
if grep -q "dtoverlay=dwc2,dr_mode=host" "$BOOT_CONFIG"; then
    echo "  Fixing dr_mode=host..."
    sed -i 's/dtoverlay=dwc2,dr_mode=host/dtoverlay=dwc2/' "$BOOT_CONFIG"
    echo "  ✓ Fixed dr_mode=host"
fi

# Remove duplicate dtoverlay=dwc2 lines
echo "  Checking for duplicates..."
DWCCOUNT=$(grep -c "^dtoverlay=dwc2$" "$BOOT_CONFIG" 2>/dev/null || echo "0")

if [ "$DWCCOUNT" -gt 1 ]; then
    echo "  Found $DWCCOUNT duplicate dtoverlay=dwc2 entries, cleaning up..."
    # Remove all dtoverlay=dwc2 lines, then add it back once
    sed -i '/^dtoverlay=dwc2$/d' "$BOOT_CONFIG"
    echo "dtoverlay=dwc2" >> "$BOOT_CONFIG"
    echo "  ✓ Removed duplicates, kept one entry"
elif [ "$DWCCOUNT" -eq 0 ]; then
    echo "  dtoverlay=dwc2 not found, adding it..."
    echo "dtoverlay=dwc2" >> "$BOOT_CONFIG"
    echo "  ✓ Added dtoverlay=dwc2"
else
    echo "  ✓ dtoverlay=dwc2 configured correctly (1 entry)"
fi

echo ""
echo "  Current boot config:"
grep "dtoverlay=dwc2" "$BOOT_CONFIG" || echo "  Not found"
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
echo "Boot config (/boot/firmware/config.txt):"
grep "dtoverlay=dwc2" /boot/firmware/config.txt || echo "  Not found"
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

