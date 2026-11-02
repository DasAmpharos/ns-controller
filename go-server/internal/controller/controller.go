package controller

import (
	"fmt"
	"log/slog"
	"math"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"ns-controller/go-server/internal/spidata"
	pb "ns-controller/go-server/proto/ns_controller"
)

// reportKeepalive matches the real Pro Controller USB input report interval.
const reportKeepalive = 8 * time.Millisecond

// Controller manages the USB HID gadget device and three background goroutines:
//   - counter:     increments a packet counter every 5ms
//   - comm:        reads Switch requests and responds (handshake, SPI, UART)
//   - inputReport: sends controller state at ≤8ms keepalive or on trigger
type Controller struct {
	state *State
	fp    *os.File
	count atomic.Uint32

	// reportTrigger is signalled by TriggerReport to wake the input-report
	// goroutine immediately on state changes (buffered 1 so non-blocking).
	reportTrigger chan struct{}

	// inputMu protects stopInput; replaced each time input reporting restarts.
	inputMu   sync.Mutex
	stopInput chan struct{}

	stopComm    chan struct{}
	stopCounter chan struct{}
	writeMu     sync.Mutex
}

// New creates a Controller backed by the given State. The State's notify
// callback is set to TriggerReport so HID reports fire on every state change.
func New(state *State) *Controller {
	c := &Controller{
		state:         state,
		reportTrigger: make(chan struct{}, 1),
		stopInput:     make(chan struct{}),
		stopComm:      make(chan struct{}),
		stopCounter:   make(chan struct{}),
	}
	state.SetNotify(c.TriggerReport)
	return c
}

// Connect opens the HID gadget device and starts all background goroutines.
func (c *Controller) Connect(path string) error {
	fp, err := os.OpenFile(path, os.O_RDWR, 0)
	if err != nil {
		return fmt.Errorf("controller: open %s: %w", path, err)
	}
	c.fp = fp

	c.startCounter()

	// Reset magic — mirrors the Python initialisation sequence.
	c.write(0x81, 0x03, nil)
	c.write(0x81, 0x01, []byte{0x00, 0x03})

	go c.runComm()
	return nil
}

// TriggerReport wakes the input-report goroutine immediately.
// Safe to call before Connect; no-op if not yet running.
func (c *Controller) TriggerReport() {
	select {
	case c.reportTrigger <- struct{}{}:
	default:
	}
}

// Close shuts down all goroutines and closes the device file.
func (c *Controller) Close() {
	close(c.stopComm)
	close(c.stopCounter)

	c.inputMu.Lock()
	select {
	case <-c.stopInput:
	default:
		close(c.stopInput)
	}
	c.inputMu.Unlock()

	if c.fp != nil {
		c.fp.Close()
		c.fp = nil
	}
}

// write sends a 64-byte packet to the HID device.
func (c *Controller) write(ack, cmd byte, payload []byte) {
	data := make([]byte, 64)
	data[0] = ack
	data[1] = cmd
	copy(data[2:], payload)

	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	if _, err := c.fp.Write(data); err != nil {
		slog.Error("hid write failed", "err", err)
	}
}

func (c *Controller) startCounter() {
	go func() {
		t := time.NewTicker(5 * time.Millisecond)
		defer t.Stop()
		for {
			select {
			case <-t.C:
				c.count.Add(1)
			case <-c.stopCounter:
				return
			}
		}
	}()
}

func (c *Controller) startInputReport() {
	c.inputMu.Lock()
	stopInput := make(chan struct{})
	c.stopInput = stopInput
	c.inputMu.Unlock()

	go func() {
		for {
			select {
			case <-stopInput:
				return
			case <-c.reportTrigger:
				c.write(0x30, byte(c.count.Load()), c.getInputBuffer())
			case <-time.After(reportKeepalive):
				c.write(0x30, byte(c.count.Load()), c.getInputBuffer())
			}
		}
	}()
}

func (c *Controller) stopInputReport() {
	c.inputMu.Lock()
	defer c.inputMu.Unlock()
	select {
	case <-c.stopInput:
		// already closed
	default:
		close(c.stopInput)
	}
}

func (c *Controller) uart(ack bool, subCmd byte, data []byte) {
	ackByte := byte(0x00)
	if ack {
		ackByte = 0x80
		if len(data) > 0 {
			ackByte |= subCmd
		}
	}
	inputBuf := c.getInputBuffer()
	combined := make([]byte, len(inputBuf)+2+len(data))
	copy(combined, inputBuf)
	combined[len(inputBuf)] = ackByte
	combined[len(inputBuf)+1] = subCmd
	copy(combined[len(inputBuf)+2:], data)
	c.write(0x21, byte(c.count.Load()), combined)
}

func (c *Controller) runComm() {
	buf := make([]byte, 128)
	for {
		select {
		case <-c.stopComm:
			return
		default:
		}

		n, err := c.fp.Read(buf)
		if err != nil {
			slog.Error("hid read failed", "err", err)
			continue
		}
		slog.Debug("hid read", "data", fmt.Sprintf("%x", buf[:n]))

		if n < 2 {
			continue
		}

		switch buf[0] {
		case 0x80:
			switch buf[1] {
			case 0x01:
				c.write(0x81, buf[1], []byte{0x00, 0x03, 0x00, 0x00, 0x5e, 0x00, 0x53, 0x5e})
			case 0x02, 0x03:
				c.write(0x81, buf[1], nil)
			case 0x04:
				c.startInputReport()
			case 0x05:
				c.stopInputReport()
			}
		case 0x01:
			if n < 11 {
				continue
			}
			switch buf[10] {
			case 0x01:
				c.uart(true, buf[10], []byte{0x03, 0x01})
			case 0x02:
				c.uart(true, buf[10], []byte{
					0x03, 0x48, 0x03, 0x02, 0x5e, 0x53, 0x00, 0x5e, 0x00, 0x00, 0x03, 0x01,
				})
			case 0x03, 0x08, 0x30, 0x38, 0x40, 0x41, 0x48:
				c.uart(true, buf[10], nil)
			case 0x04:
				c.uart(true, buf[10], nil)
			case 0x10:
				if n < 16 {
					continue
				}
				data := spidata.Get(buf[12])
				if data != nil {
					offset := int(buf[11])
					length := int(buf[15])
					end := offset + length
					if end > len(data) {
						end = len(data)
					}
					// Response: 5-byte address header + data slice
					resp := make([]byte, 5+length)
					copy(resp[:5], buf[11:16])
					copy(resp[5:], data[offset:end])
					c.uart(true, buf[10], resp)
					slog.Debug("SPI read", "page", fmt.Sprintf("0x%02x", buf[12]),
						"offset", fmt.Sprintf("0x%02x", buf[11]), "len", length)
				} else {
					c.uart(false, buf[10], nil)
					slog.Debug("SPI unknown page", "page", fmt.Sprintf("0x%02x", buf[12]))
				}
			case 0x21:
				c.uart(true, buf[10], []byte{0x01, 0x00, 0xff, 0x00, 0x03, 0x00, 0x05, 0x01})
			default:
				slog.Debug("UART unknown subcommand", "cmd", fmt.Sprintf("0x%02x", buf[10]))
			}
		case 0x00, 0x10:
			// normal input / ignored
		default:
			slog.Debug("unknown HID request", "byte0", fmt.Sprintf("0x%02x", buf[0]))
		}
	}
}

// getInputBuffer encodes the current controller state into the 11-byte
// Nintendo Switch Pro Controller USB input report format.
func (c *Controller) getInputBuffer() []byte {
	s := c.state.Get()

	bit := func(pos int, cond bool) byte {
		if cond {
			return 1 << uint(pos)
		}
		return 0
	}

	// Pack two 12-bit values into 3 bytes (Nintendo's little-endian 12-bit format).
	packShorts := func(x, y int) (byte, byte, byte) {
		return byte(x & 0xFF),
			byte(((y << 4) & 0xF0) | ((x >> 8) & 0x0F)),
			byte((y >> 4) & 0xFF)
	}

	btns := s.Buttons

	// "left" byte (right-side face buttons + shoulder)
	left := bit(0, btns>>uint(pb.Button_Y)&1 == 1) |
		bit(1, btns>>uint(pb.Button_X)&1 == 1) |
		bit(2, btns>>uint(pb.Button_B)&1 == 1) |
		bit(3, btns>>uint(pb.Button_A)&1 == 1) |
		bit(6, btns>>uint(pb.Button_R)&1 == 1) |
		bit(7, btns>>uint(pb.Button_ZR)&1 == 1)

	// "center" byte (system buttons + stick clicks)
	center := bit(0, btns>>uint(pb.Button_MINUS)&1 == 1) |
		bit(1, btns>>uint(pb.Button_PLUS)&1 == 1) |
		bit(2, btns>>uint(pb.Button_R_STICK)&1 == 1) |
		bit(3, btns>>uint(pb.Button_L_STICK)&1 == 1) |
		bit(4, btns>>uint(pb.Button_HOME)&1 == 1) |
		bit(5, btns>>uint(pb.Button_CAPTURE)&1 == 1)

	// "right" byte (d-pad + left shoulder)
	right := bit(0, btns>>uint(pb.Button_DPAD_DOWN)&1 == 1) |
		bit(1, btns>>uint(pb.Button_DPAD_UP)&1 == 1) |
		bit(2, btns>>uint(pb.Button_DPAD_RIGHT)&1 == 1) |
		bit(3, btns>>uint(pb.Button_DPAD_LEFT)&1 == 1) |
		bit(6, btns>>uint(pb.Button_L)&1 == 1) |
		bit(7, btns>>uint(pb.Button_ZL)&1 == 1)

	toAxis := func(v float32) int {
		return int(math.Round(float64(1+v) * 2047.5))
	}

	var lx, ly, rx, ry int
	if s.Ls != nil {
		lx = toAxis(s.Ls.X)
		ly = toAxis(s.Ls.Y)
	} else {
		lx, ly = 2048, 2048
	}
	if s.Rs != nil {
		rx = toAxis(s.Rs.X)
		ry = toAxis(s.Rs.Y)
	} else {
		rx, ry = 2048, 2048
	}

	ls0, ls1, ls2 := packShorts(lx, ly)
	rs0, rs1, rs2 := packShorts(rx, ry)

	return []byte{0x81, left, center, right, ls0, ls1, ls2, rs0, rs1, rs2, 0x00}
}
