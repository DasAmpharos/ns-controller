#!/bin/bash
# Diagnose USB gadget setup issues

echo "========================================"
echo "USB Gadget Diagnostic Script"
echo "========================================"
echo ""

echo "=== Kernel Modules ==="
echo "dwc2:"
lsmod | grep dwc2 || echo "NOT LOADED"
echo ""
echo "libcomposite:"
lsmod | grep libcomposite || echo "NOT LOADED"
echo ""

echo "=== UDC Devices ==="
echo "Available UDC devices:"
ls -la /sys/class/udc/ 2>/dev/null || echo "Directory not found"
echo ""

echo "=== USB Gadget Configuration ==="
GADGET_DIR="/sys/kernel/config/usb_gadget/procon"
if [ -d "$GADGET_DIR" ]; then
    echo "Gadget directory exists: $GADGET_DIR"
    echo ""
    echo "UDC binding:"
    cat "$GADGET_DIR/UDC" 2>/dev/null || echo "Not bound"
    echo ""
    echo "Gadget structure:"
    ls -la "$GADGET_DIR" 2>/dev/null
    echo ""
    echo "Functions:"
    ls -la "$GADGET_DIR/functions/" 2>/dev/null || echo "No functions"
    echo ""
    echo "Configs:"
    ls -la "$GADGET_DIR/configs/c.1/" 2>/dev/null || echo "No configs"
else
    echo "Gadget directory does NOT exist: $GADGET_DIR"
fi
echo ""

echo "=== HID Devices ==="
echo "/dev/hidg* devices:"
ls -la /dev/hidg* 2>/dev/null || echo "No hidg devices found"
echo ""

echo "=== Boot Configuration ==="
echo "dtoverlay=dwc2 in boot config:"
grep "dtoverlay=dwc2" /boot/firmware/config.txt /boot/config.txt 2>/dev/null || echo "NOT FOUND"
echo ""

echo "=== Loaded Modules Config ==="
echo "/etc/modules-load.d/ns-controller.conf:"
cat /etc/modules-load.d/ns-controller.conf 2>/dev/null || echo "File not found"
echo ""

echo "=== Service Status ==="
systemctl status usb-gadget.service --no-pager -l 2>/dev/null || echo "Service not found"
echo ""

echo "=== Recent Service Logs ==="
journalctl -u usb-gadget.service -n 20 --no-pager 2>/dev/null || echo "No logs found"
echo ""

echo "========================================"
echo "Diagnostic Complete"
echo "========================================"

