#!/bin/bash
# Quick fix script to update the USB gadget setup script on the Pi
# Run with: sudo bash fix-usb-gadget-now.sh

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Error: Must run as root (use sudo)"
    exit 1
fi

echo "=========================================="
echo "Updating USB Gadget Setup Script"
echo "=========================================="
echo ""

# Create the updated setup script
cat > /usr/local/bin/setup-usb-gadget.sh << 'EOFSCRIPT'
#!/bin/bash
set -e

echo "Setting up USB gadget..."

DEVICE=/dev/hidg0
GADGET_DIR="/sys/kernel/config/usb_gadget/procon"

# Check if configfs is mounted
if ! mount | grep -q configfs; then
    echo "Error: configfs is not mounted"
    exit 1
fi

# Load modules
modprobe libcomposite 2>/dev/null || true

# Remove existing gadget if it exists
if [ -d "$GADGET_DIR" ]; then
    echo "Removing existing USB gadget..."
    if [ -f "$GADGET_DIR/UDC" ] && [ -s "$GADGET_DIR/UDC" ]; then
        echo "" > "$GADGET_DIR/UDC" 2>/dev/null || true
    fi
    sleep 0.5
    find "$GADGET_DIR/configs/c.1" -maxdepth 1 -type l -exec rm {} \; 2>/dev/null || true
    rmdir "$GADGET_DIR/configs/c.1/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR/configs/c.1" 2>/dev/null || true
    rmdir "$GADGET_DIR/functions/hid.usb0" 2>/dev/null || true
    rmdir "$GADGET_DIR/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR" 2>/dev/null || true
fi

# Check if UDC exists
if [ ! -d /sys/class/udc ] || [ -z "$(ls -A /sys/class/udc 2>/dev/null)" ]; then
    echo "Error: No UDC device found"
    echo "Make sure dtoverlay=dwc2 is in /boot/firmware/config.txt under [all] section"
    echo "Then reboot"
    exit 1
fi

# Create gadget
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

# Device descriptor
echo 0x057e > idVendor
echo 0x2009 > idProduct
echo 0x0200 > bcdUSB
echo 0x0100 > bcdDevice
echo 0x00 > bDeviceClass
echo 0x00 > bDeviceSubClass
echo 0x00 > bDeviceProtocol

# Strings
mkdir -p strings/0x409
echo "000000000001" > strings/0x409/serialnumber
echo "Nintendo Co., Ltd." > strings/0x409/manufacturer
echo "Pro Controller" > strings/0x409/product

# Config
mkdir -p configs/c.1/strings/0x409
echo "Nintendo Switch Pro Controller" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower
echo 0xa0 > configs/c.1/bmAttributes

# HID function
mkdir -p functions/hid.usb0
echo 0 > functions/hid.usb0/protocol
echo 0 > functions/hid.usb0/subclass
echo 64 > functions/hid.usb0/report_length

# Write report descriptor using hex directly (no xxd needed)
printf '\x05\x01\x15\x00\x09\x04\xa1\x01\x85\x30\x05\x01\x09\x30\x09\x31\x09\x32\x09\x35\x15\x00\x27\xff\xff\x00\x00\x75\x10\x95\x04\x81\x02\x06\x00\xff\x09\x20\x95\x01\x81\x02\x0a\x21\x26\x95\x08\x81\x02\x0a\x21\x26\x95\x1d\x81\x02\x85\x21\x0a\x21\x26\x95\x30\x91\x02\x85\x81\x0a\x21\x26\x95\x30\x91\x02\x85\x01\x0a\x21\x26\x95\x30\x91\x02\x85\x10\x0a\x21\x26\x95\x30\x91\x02\x85\x80\x0a\x21\x26\x95\x30\x91\x02\x85\x82\x0a\x21\x26\x95\x30\x91\x02\xc0' > functions/hid.usb0/report_desc

if [ ! -s functions/hid.usb0/report_desc ]; then
    echo "Error: Failed to write HID report descriptor"
    exit 1
fi

# Link function to config
if [ ! -e configs/c.1/hid.usb0 ]; then
    ln -s functions/hid.usb0 configs/c.1/
fi

# Get UDC and enable
UDC_DEVICE=$(ls /sys/class/udc | head -n 1)
if [ -z "$UDC_DEVICE" ]; then
    echo "Error: No UDC device found"
    exit 1
fi

echo "Enabling gadget with UDC: $UDC_DEVICE"
if ! echo "$UDC_DEVICE" > UDC; then
    echo "Error: Failed to enable USB gadget"
    cat UDC 2>/dev/null || echo "UDC file empty"
    exit 1
fi

# Wait for device
for i in {1..10}; do
    if [ -e "$DEVICE" ]; then
        chmod 666 "$DEVICE"
        echo "Success! $DEVICE created"
        ls -la "$DEVICE"
        exit 0
    fi
    sleep 0.5
done

echo "Error: $DEVICE was not created"
exit 1
EOFSCRIPT

chmod +x /usr/local/bin/setup-usb-gadget.sh

echo "✓ Updated /usr/local/bin/setup-usb-gadget.sh"
echo ""

# Check if dtoverlay=dwc2 is in [all] section
echo "Checking boot configuration..."
if grep -A 5 "^\[all\]" /boot/firmware/config.txt | grep -q "^dtoverlay=dwc2"; then
    echo "✓ dtoverlay=dwc2 is in [all] section"
else
    echo "✗ dtoverlay=dwc2 NOT in [all] section!"
    echo ""
    echo "Adding it now..."
    if grep -q "^\[all\]" /boot/firmware/config.txt; then
        sed -i '/^\[all\]/a dtoverlay=dwc2' /boot/firmware/config.txt
        echo "✓ Added dtoverlay=dwc2 to [all] section"
    else
        echo "" >> /boot/firmware/config.txt
        echo "[all]" >> /boot/firmware/config.txt
        echo "dtoverlay=dwc2" >> /boot/firmware/config.txt
        echo "✓ Created [all] section with dtoverlay=dwc2"
    fi
    echo ""
    echo "⚠ REBOOT REQUIRED for boot config changes to take effect"
    echo "Run: sudo reboot"
    exit 0
fi

# Restart the service
echo ""
echo "Restarting usb-gadget service..."
systemctl daemon-reload
systemctl restart usb-gadget.service

sleep 2

echo ""
echo "=========================================="
echo "Service Status:"
echo "=========================================="
systemctl status usb-gadget.service --no-pager -l || true

echo ""
echo "=========================================="
echo "Checking /dev/hidg0:"
echo "=========================================="
if [ -e /dev/hidg0 ]; then
    ls -la /dev/hidg0
    echo ""
    echo "✓✓✓ SUCCESS! ✓✓✓"
    echo "/dev/hidg0 has been created!"
else
    echo "✗ /dev/hidg0 still not created"
    echo ""
    echo "Debug info:"
    echo "UDC devices:"
    ls -la /sys/class/udc/ 2>/dev/null || echo "Not found"
    echo ""
    echo "Gadget directory:"
    ls -la /sys/kernel/config/usb_gadget/procon/ 2>/dev/null || echo "Not found"
    echo ""
    echo "Recent logs:"
    journalctl -u usb-gadget.service -n 10 --no-pager
fi

