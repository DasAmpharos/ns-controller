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

# Start the service now to test
echo ""
echo "Starting usb-gadget.service..."
systemctl start usb-gadget.service

echo ""
echo "Service status:"
systemctl status usb-gadget.service --no-pager || true

echo ""
echo "Checking for /dev/hidg0..."
if [ -e /dev/hidg0 ]; then
    ls -la /dev/hidg0
    echo ""
    echo "=========================================="
    echo "✓✓✓ SUCCESS! ✓✓✓"
    echo "=========================================="
    echo ""
    echo "/dev/hidg0 has been created!"
    echo "Your Raspberry Pi is now configured as a Nintendo Switch Pro Controller."
    echo ""
    echo "The service will start automatically on boot."
else
    echo "/dev/hidg0 not found"
    echo ""
    echo "Checking logs for errors..."
    journalctl -u usb-gadget.service -n 20 --no-pager
    echo ""
    echo "=========================================="
    echo "Service started but /dev/hidg0 not created"
    echo "=========================================="
    echo ""
    echo "Try running the setup script manually to see errors:"
    echo "  sudo /usr/local/bin/setup-usb-gadget.sh"
fi
echo ""

