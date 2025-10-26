#!/bin/bash
# Standalone USB Gadget Setup Script for Nintendo Switch Pro Controller
# Run this with: sudo ./setup-usb-gadget-manual.sh

set -e

echo "Setting up Nintendo Switch Pro Controller USB Gadget..."

GADGET_DIR="/sys/kernel/config/usb_gadget/procontroller"

# Check if we're root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if dwc2 modules are loaded
if ! lsmod | grep -q dwc2; then
    echo "Loading dwc2 module..."
    modprobe dwc2
fi

if ! lsmod | grep -q libcomposite; then
    echo "Loading libcomposite module..."
    modprobe libcomposite
fi

# Check if configfs is mounted
if ! mount | grep -q configfs; then
    echo "Mounting configfs..."
    mount -t configfs none /sys/kernel/config
fi

# Remove existing gadget if it exists
if [ -d "$GADGET_DIR" ]; then
    echo "Removing existing USB gadget..."

    # Unbind from UDC
    if [ -e "$GADGET_DIR/UDC" ]; then
        echo "" > "$GADGET_DIR/UDC" 2>/dev/null || true
    fi

    # Remove symlinks
    find "$GADGET_DIR/configs/c.1" -maxdepth 1 -type l -exec rm {} \; 2>/dev/null || true

    # Remove directories in reverse order
    rmdir "$GADGET_DIR/configs/c.1/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR/configs/c.1" 2>/dev/null || true
    rmdir "$GADGET_DIR/functions/hid.usb0" 2>/dev/null || true
    rmdir "$GADGET_DIR/strings/0x409" 2>/dev/null || true
    rmdir "$GADGET_DIR" 2>/dev/null || true

    echo "Existing gadget removed."
fi

# Create gadget directory
echo "Creating USB gadget directory..."
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

# Configure USB device descriptor
echo "Configuring device descriptor..."
echo 0x057e > idVendor   # Nintendo
echo 0x2009 > idProduct  # Pro Controller
echo 0x0200 > bcdUSB     # USB 2.0
echo 0x0100 > bcdDevice  # Device version 1.0

# Create English strings
mkdir -p strings/0x409
echo "000000000001" > strings/0x409/serialnumber
echo "Nintendo Co., Ltd." > strings/0x409/manufacturer
echo "Pro Controller" > strings/0x409/product

echo "Device strings configured."

# Create HID function
echo "Configuring HID function..."
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol
echo 1 > functions/hid.usb0/subclass
echo 64 > functions/hid.usb0/report_length

# Pro Controller HID Report Descriptor
echo "Writing HID report descriptor..."
echo -ne '\x05\x01\x09\x05\xa1\x01\x15\x00\x25\x01\x35\x00\x45\x01\x75\x01\x95\x0e\x05\x09\x19\x01\x29\x0e\x81\x02\x95\x02\x81\x03\x05\x01\x25\x07\x46\x3b\x01\x75\x04\x95\x01\x65\x14\x09\x39\x81\x42\x65\x00\x95\x01\x81\x03\x26\xff\x00\x46\xff\x00\x09\x30\x09\x31\x09\x32\x09\x35\x75\x08\x95\x04\x81\x02\x06\x00\xff\x09\x20\x95\x01\x81\x02\x0a\x21\x26\x95\x08\x81\x02\x0a\x21\x26\x95\x1d\x81\x02\x85\x30\x0a\x21\x26\x95\x30\x91\x02\x85\x21\x0a\x21\x26\x95\x30\x91\x02\x85\x80\x0a\x21\x26\x95\x30\x91\x02\x85\x81\x0a\x21\x26\x95\x30\x91\x02\x85\x82\x0a\x21\x26\x95\x30\x91\x02\xc0' > functions/hid.usb0/report_desc

echo "HID function configured."

# Create configuration
echo "Creating configuration..."
mkdir -p configs/c.1
mkdir -p configs/c.1/strings/0x409
echo "Config 1" > configs/c.1/strings/0x409/configuration
echo 500 > configs/c.1/MaxPower

# Link function to configuration
echo "Linking HID function to configuration..."
ln -s functions/hid.usb0 configs/c.1/

# Find and enable UDC
echo "Finding UDC device..."
UDC_DEVICE=$(ls /sys/class/udc | head -n 1)

if [ -z "$UDC_DEVICE" ]; then
    echo "Error: No UDC device found!"
    echo "This might mean:"
    echo "  1. dwc2 module is not loaded properly"
    echo "  2. Your Raspberry Pi model doesn't support USB gadget mode"
    echo "  3. You need to reboot after enabling dtoverlay=dwc2"
    exit 1
fi

echo "Found UDC device: $UDC_DEVICE"
echo "Enabling USB gadget..."
echo "$UDC_DEVICE" > UDC

echo ""
echo "=========================================="
echo "USB Gadget Setup Complete!"
echo "=========================================="
echo ""
echo "Checking /dev/hidg0..."
sleep 1

if [ -e /dev/hidg0 ]; then
    ls -la /dev/hidg0
    echo ""
    echo "✓ Success! /dev/hidg0 has been created."
    echo ""
    echo "Your Raspberry Pi is now configured as a Nintendo Switch Pro Controller."
    echo "Connect it to your Nintendo Switch via USB to test."
else
    echo "✗ Warning: /dev/hidg0 was not created."
    echo "This might take a few seconds. Try checking again:"
    echo "  ls -la /dev/hidg0"
fi

