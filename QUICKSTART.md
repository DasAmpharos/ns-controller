# Quick Start Guide

## Fresh Raspberry Pi Setup

1. **Flash Raspberry Pi OS** to your SD card using Raspberry Pi Imager
   - Choose "Raspberry Pi OS Lite" (64-bit recommended)
   - Configure WiFi and SSH in the imager settings

2. **Boot and connect** to your Pi via SSH:
   ```bash
   ssh pi@raspberrypi.local
   ```

3. **Update the system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Clone this repository**:
   ```bash
   git clone <repository-url> ns-controller
   cd ns-controller
   ```

5. **Run the installation script**:
   ```bash
   chmod +x install.sh
   sudo ./install.sh
   ```

6. **Reboot**:
   ```bash
   sudo reboot
   ```

7. **Connect to Nintendo Switch**:
   - Use a USB cable to connect your Pi to the Switch
   - The Switch should recognize it as a Pro Controller

8. **Access the UI**:
   - From any device on your network, open a browser
   - Navigate to: `http://raspberrypi.local:8501`
   - Or use the Pi's IP address: `http://<pi-ip>:8501`

## Using the Controller

### Via Streamlit UI

The Streamlit UI provides an interactive interface:

1. **Button Controls**: Click buttons to press them on the Switch
2. **Analog Sticks**: Drag the stick indicators or use sliders
3. **Macros**: 
   - Write macros using NXBT syntax
   - Save them with a name
   - Load and run saved macros
   - Control playback (start, stop, pause, resume)

### Via TCP Client

You can also control the Switch programmatically:

```python
from ns_controller.client import Client

client = Client(host="raspberrypi.local", port=9000)

# Press a button
from ns_controller.controller import ControllerState, Buttons
state = ControllerState()
state.press(Buttons.A)
client.send_state(state, down=0.1, up=0.1)

# Run a macro
macro_text = """
A 0.1s
0.5s
B 0.1s
"""
client.start_macro(macro_text)

# Stop macro
client.stop_macro()
```

## Writing Macros

### Basic Button Press
```
A 0.1s
```
Presses A for 0.1 seconds.

### Wait Time
```
A 0.1s
1.0s
```
Press A for 0.1s, then wait 1.0s.

### Multiple Buttons
```
A B 0.2s
```
Press A and B simultaneously for 0.2s.

### Analog Sticks
```
L_STICK@+100+000 0.5s
```
Tilt left stick fully right for 0.5s.

Format: `L_STICK@<X><Y>` where X and Y are signed 3-digit numbers (-100 to +100).

### Loops
```
LOOP 10
    A 0.1s
    0.1s
```
Press A 10 times with 0.1s between presses.

### Complex Example
```
# Spam A button 100 times
LOOP 100
    A 0.05s
    0.05s

# Navigate menu
DPAD_DOWN 0.1s
0.2s
A 0.1s
0.5s

# Move character
L_STICK@+000+100 2.0s
0.1s
L_STICK@+000+000 0.1s
```

## Service Management

### Check if running
```bash
sudo systemctl status ns-controller
```

### View live logs
```bash
sudo journalctl -u ns-controller -f
```

### Restart service
```bash
sudo systemctl restart ns-controller
```

### Stop service
```bash
sudo systemctl stop ns-controller
```

### Start service
```bash
sudo systemctl start ns-controller
```

## Troubleshooting

### Service won't start
```bash
# Check logs for errors
sudo journalctl -u ns-controller -n 50 --no-pager

# Verify USB gadget is working
ls -la /dev/hidg0

# Try running manually
cd /opt/ns-controller
poetry run ns-controller
```

### Can't access UI
```bash
# Find your Pi's IP
hostname -I

# Check if Streamlit is running
ps aux | grep streamlit

# Check if port 8501 is open
sudo netstat -tulpn | grep 8501
```

### Switch doesn't recognize controller
```bash
# Restart USB gadget
sudo systemctl restart usb-gadget
sudo systemctl restart ns-controller

# Check if USB gadget is visible
lsusb | grep Nintendo

# Verify HID device
cat /sys/kernel/config/usb_gadget/procontroller/UDC
```

## Uninstalling

To remove ns-controller:

```bash
cd ns-controller
chmod +x uninstall.sh
sudo ./uninstall.sh
```

## Tips

- **Performance**: The Pi Zero W can be slow. Be patient with Streamlit UI loading.
- **USB Cable**: Make sure you're using a data cable, not a charge-only cable.
- **Port**: Use the USB port labeled "USB" on Pi Zero W (not the "PWR" port).
- **Network**: Both your computer and Pi must be on the same network to access the UI.
- **Mock Mode**: Test without hardware using `--mock` flag.

## Next Steps

- Read [INSTALL.md](INSTALL.md) for detailed documentation
- Check [README.md](README.md) for development information
- Explore the `ns_controller/macros/` directory for macro examples

