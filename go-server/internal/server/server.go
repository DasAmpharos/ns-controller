package server

import (
	"context"
	"log/slog"
	"time"

	"google.golang.org/protobuf/types/known/emptypb"

	"ns-controller/go-server/internal/controller"
	"ns-controller/go-server/internal/macro"
	pb "ns-controller/go-server/proto/ns_controller"
)

// NsControllerServer implements the gRPC NsControllerServer interface.
type NsControllerServer struct {
	pb.UnimplementedNsControllerServer
	state      *controller.State
	ctrl       *controller.Controller
}

// New creates a server backed by the given State and Controller.
func New(state *controller.State, ctrl *controller.Controller) *NsControllerServer {
	return &NsControllerServer{state: state, ctrl: ctrl}
}

func (s *NsControllerServer) Click(ctx context.Context, req *pb.ClickRequest) (*pb.ControllerState, error) {
	dur := float32ToMillis(req.Duration)
	return s.state.Click(req.Buttons, dur), nil
}

func (s *NsControllerServer) Press(_ context.Context, req *pb.PressRequest) (*pb.ControllerState, error) {
	return s.state.Press(req.Buttons...), nil
}

func (s *NsControllerServer) Release(_ context.Context, req *pb.ReleaseRequest) (*pb.ControllerState, error) {
	return s.state.Release(req.Buttons...), nil
}

func (s *NsControllerServer) SetStick(_ context.Context, req *pb.StickRequest) (*pb.ControllerState, error) {
	return s.state.SetStick(req.Stick, req.Position), nil
}

func (s *NsControllerServer) SetState(_ context.Context, req *pb.ControllerState) (*pb.ControllerState, error) {
	return s.state.SetState(req), nil
}

func (s *NsControllerServer) GetState(_ context.Context, _ *emptypb.Empty) (*pb.ControllerState, error) {
	return s.state.Get(), nil
}

func (s *NsControllerServer) Clear(_ context.Context, _ *emptypb.Empty) (*pb.ControllerState, error) {
	return s.state.Clear(), nil
}

// RunMacro executes the macro on the server with monotonic timing, streaming
// a MacroEvent per action. Cancelling the RPC context aborts execution.
func (s *NsControllerServer) RunMacro(req *pb.Macro, stream pb.NsController_RunMacroServer) error {
	ctx := stream.Context()
	slog.Info("starting macro", "actions", len(req.Actions))

	exec := macro.New(req, s.state, ctx)
	if err := exec.Execute(); err != nil {
		slog.Error("macro execution error", "err", err)
		return stream.Send(&pb.MacroEvent{
			Error:        true,
			ErrorMessage: err.Error(),
			Completed:    true,
		})
	}

	slog.Info("macro completed")
	return stream.Send(&pb.MacroEvent{Completed: true})
}

// float32ToMillis converts a float32 duration in seconds to a time.Duration.
func float32ToMillis(seconds float32) time.Duration {
	if seconds <= 0 {
		return 100 * time.Millisecond
	}
	return time.Duration(float64(seconds) * float64(time.Second))
}
