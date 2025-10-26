#!/bin/bash
# Fix the usb-gadget.service ordering cycle issue

if [ "$EUID" -ne 0 ]; then
    echo "Error: Must run as root (use sudo)"
    exit 1
fi

echo "Fixing usb-gadget.service ordering cycle..."
echo ""

# Stop the service if it's trying to run
systemctl stop usb-gadget.service 2>/dev/null || true

# Create the corrected service file
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

echo "✓ Updated usb-gadget.service"

# Reload systemd
systemctl daemon-reload
echo "✓ Reloaded systemd"

# Re-enable the service
systemctl enable usb-gadget.service
echo "✓ Enabled usb-gadget.service"

# Show status
echo ""
echo "Current status:"
systemctl status usb-gadget.service --no-pager || true

echo ""
echo "=========================================="
echo "Fix Applied!"
echo "=========================================="
echo ""
echo "The ordering cycle has been fixed."
echo ""
echo "Options:"
echo "  1. Reboot to apply changes: sudo reboot"
echo "  2. Or start the service manually now: sudo systemctl start usb-gadget.service"
echo ""
echo "After starting, check /dev/hidg0: ls -la /dev/hidg0"
echo ""

