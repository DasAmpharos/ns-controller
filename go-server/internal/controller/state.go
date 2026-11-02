package controller

import (
	"sync"
	"time"

	pb "ns-controller/go-server/proto/ns_controller"
)

// State is a thread-safe wrapper around a ControllerState protobuf, mirroring
// Python's EnhancedControllerState. A notify callback is fired on every
// mutation so the HID input-report goroutine can send immediately.
type State struct {
	mu      sync.Mutex
	proto   *pb.ControllerState
	notify  func()
}

func NewState() *State {
	return &State{
		proto: &pb.ControllerState{
			Ls: &pb.Position{},
			Rs: &pb.Position{},
		},
	}
}

// SetNotify registers a callback invoked on every state mutation.
func (s *State) SetNotify(fn func()) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.notify = fn
}

func (s *State) changed() {
	if s.notify != nil {
		s.notify()
	}
}

// Get returns a shallow copy of the current proto state (safe to read without lock).
func (s *State) Get() *pb.ControllerState {
	s.mu.Lock()
	defer s.mu.Unlock()
	// Return a copy so callers don't need to hold the lock while encoding.
	cp := *s.proto
	return &cp
}

func (s *State) Press(buttons ...pb.Button) *pb.ControllerState {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, b := range buttons {
		s.proto.Buttons |= 1 << uint(b)
	}
	s.changed()
	return s.proto
}

func (s *State) Release(buttons ...pb.Button) *pb.ControllerState {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, b := range buttons {
		s.proto.Buttons &^= 1 << uint(b)
	}
	s.changed()
	return s.proto
}

func (s *State) Click(buttons []pb.Button, duration time.Duration) *pb.ControllerState {
	s.Press(buttons...)
	time.Sleep(duration)
	return s.Release(buttons...)
}

func (s *State) SetStick(stick pb.Stick, pos *pb.Position) *pb.ControllerState {
	s.mu.Lock()
	defer s.mu.Unlock()
	switch stick {
	case pb.Stick_LS:
		s.proto.Ls = &pb.Position{X: pos.X, Y: pos.Y}
	case pb.Stick_RS:
		s.proto.Rs = &pb.Position{X: pos.X, Y: pos.Y}
	}
	s.changed()
	return s.proto
}

func (s *State) SetState(state *pb.ControllerState) *pb.ControllerState {
	s.mu.Lock()
	defer s.mu.Unlock()
	ls := &pb.Position{}
	rs := &pb.Position{}
	if state.Ls != nil {
		ls = &pb.Position{X: state.Ls.X, Y: state.Ls.Y}
	}
	if state.Rs != nil {
		rs = &pb.Position{X: state.Rs.X, Y: state.Rs.Y}
	}
	s.proto = &pb.ControllerState{Buttons: state.Buttons, Ls: ls, Rs: rs}
	s.changed()
	return s.proto
}

func (s *State) Clear() *pb.ControllerState {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.proto = &pb.ControllerState{Ls: &pb.Position{}, Rs: &pb.Position{}}
	s.changed()
	return s.proto
}
