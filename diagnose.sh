#!/bin/bash

echo "=========================================="
echo "NS-Controller Diagnostic Script"
echo "=========================================="
echo ""

echo "=== System Information ==="
echo "Raspberry Pi Model:"
cat /proc/cpuinfo | grep "Model" || echo "Could not detect model"
echo ""

echo "Raspberry Pi OS Version:"
cat /etc/os-release | grep "PRETTY_NAME" || echo "Could not detect OS"
echo ""

echo "Available Disk Space:"
df -h / | tail -1
echo ""

echo "=== USB Gadget Configuration ==="
echo "dwc2 in /boot/config.txt:"
grep "dtoverlay=dwc2" /boot/config.txt 2>/dev/null || grep "dtoverlay=dwc2" /boot/firmware/config.txt 2>/dev/null || echo "NOT FOUND"
echo ""

echo "Modules in /etc/modules:"
grep -E "dwc2|libcomposite" /etc/modules || echo "NOT FOUND"
echo ""

echo "Loaded kernel modules:"
lsmod | grep -E "dwc2|libcomposite" || echo "NOT LOADED"
echo ""

echo "=== ConfigFS ==="
echo "ConfigFS mount:"
mount | grep configfs || echo "NOT MOUNTED"
echo ""

echo "USB Gadget directory exists:"
if [ -d "/sys/kernel/config/usb_gadget/procontroller" ]; then
    echo "YES"
    echo "Contents:"
    ls -la /sys/kernel/config/usb_gadget/procontroller/ 2>/dev/null || echo "Cannot list contents"
else
    echo "NO"
fi
echo ""

echo "=== HID Device ==="
echo "/dev/hidg0 exists:"
if [ -e "/dev/hidg0" ]; then
    ls -la /dev/hidg0
else
    echo "NO - Device does not exist"
fi
echo ""

echo "=== Services Status ==="
echo "usb-gadget.service:"
systemctl status usb-gadget.service --no-pager -l || echo "Service not found"
echo ""

echo "ns-controller.service:"
systemctl status ns-controller.service --no-pager -l || echo "Service not found"
echo ""

echo "=== Service Logs (last 20 lines) ==="
echo "usb-gadget.service logs:"
journalctl -u usb-gadget.service -n 20 --no-pager 2>/dev/null || echo "No logs found"
echo ""

echo "ns-controller.service logs:"
journalctl -u ns-controller.service -n 20 --no-pager 2>/dev/null || echo "No logs found"
echo ""

echo "=== USB Gadget Setup Script ==="
echo "Script exists:"
if [ -f "/usr/local/bin/setup-usb-gadget.sh" ]; then
    echo "YES"
    echo "Attempting to run manually..."
    /usr/local/bin/setup-usb-gadget.sh 2>&1 || echo "Script failed"
    echo ""
    echo "After manual run, /dev/hidg0:"
    ls -la /dev/hidg0 2>/dev/null || echo "Still does not exist"
else
    echo "NO - Script not found"
fi
echo ""

echo "=== Installation Directory ==="
if [ -d "/opt/ns-controller" ]; then
    echo "Directory exists:"
    ls -la /opt/ns-controller/ | head -20
    echo ""
    echo "Virtual environment exists:"
    if [ -d "/opt/ns-controller/.venv" ]; then
        echo "YES"
    else
        echo "NO"
    fi
else
    echo "Installation directory not found"
fi
echo ""

echo "=========================================="
echo "Diagnostic Complete"
echo "=========================================="
echo ""
echo "Please copy the entire output above and share it."

