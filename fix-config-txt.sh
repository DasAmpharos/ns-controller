#!/bin/bash
# Fix the config.txt for Raspberry Pi Zero W USB gadget mode

BOOT_CONFIG="/boot/firmware/config.txt"

if [ "$EUID" -ne 0 ]; then
    echo "Error: Must run as root"
    exit 1
fi

echo "Fixing $BOOT_CONFIG for USB gadget mode..."
echo ""

# Backup original
cp "$BOOT_CONFIG" "$BOOT_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backed up original config"

# Check which section we need to add [pi0] or [pi02] for Pi Zero
# For now, the [all] section should work, but let's make it explicit

# Remove dtoverlay=dwc2 from [all] section if it exists
sed -i '/^\[all\]/,/^\[/{/^dtoverlay=dwc2$/d;}' "$BOOT_CONFIG"

# Add a Pi Zero specific section before [all]
if ! grep -q "^\[pi0\]" "$BOOT_CONFIG"; then
    # Find the [all] section and insert [pi0] before it
    sed -i '/^\[all\]/i\[pi0\]\n# USB Gadget mode for Pi Zero\ndtoverlay=dwc2\n' "$BOOT_CONFIG"
    echo "✓ Added [pi0] section with dtoverlay=dwc2"
else
    echo "✓ [pi0] section already exists"
fi

echo ""
echo "Updated configuration:"
echo "---"
grep -A2 "^\[pi0\]" "$BOOT_CONFIG" || echo "[pi0] section not found"
grep -A2 "^\[all\]" "$BOOT_CONFIG" || echo "[all] section not found"
echo "---"
echo ""
echo "Reboot required for changes to take effect."

