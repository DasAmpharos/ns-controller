package main

import (
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"syscall"

	"github.com/spf13/cobra"
	"google.golang.org/grpc"

	"ns-controller/go-server/internal/controller"
	"ns-controller/go-server/internal/server"
	pb "ns-controller/go-server/proto/ns_controller"
)

const (
	defaultHidPath  = "/dev/hidg0"
	defaultHost     = ""
	defaultPort     = 50051
)

func main() {
	var (
		hidPath  string
		host     string
		port     int
		mock     bool
		logLevel string
	)

	cmd := &cobra.Command{
		Use:   "ns-controller-server",
		Short: "Nintendo Switch Pro Controller emulator — gRPC server",
		RunE: func(cmd *cobra.Command, args []string) error {
			return run(hidPath, host, port, mock, logLevel)
		},
	}

	cmd.Flags().StringVar(&hidPath, "hid-path", defaultHidPath, "Path to USB HID gadget device")
	cmd.Flags().StringVar(&host, "host", defaultHost, "Host to listen on (empty = all interfaces)")
	cmd.Flags().IntVar(&port, "port", defaultPort, "gRPC port to listen on")
	cmd.Flags().BoolVar(&mock, "mock", false, "Mock mode: open /dev/null instead of the HID device")
	cmd.Flags().StringVar(&logLevel, "log-level", "info", "Log level: debug, info, warn, error")

	if err := cmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(hidPath, host string, port int, mock bool, logLevel string) error {
	setupLogger(logLevel)

	state := controller.NewState()
	ctrl := controller.New(state)

	connectPath := hidPath
	if mock {
		connectPath = "/dev/null"
	}

	slog.Info("connecting to HID device", "path", connectPath)
	if err := ctrl.Connect(connectPath); err != nil {
		return fmt.Errorf("failed to connect to HID device: %w", err)
	}
	defer ctrl.Close()

	addr := fmt.Sprintf("%s:%d", host, port)
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", addr, err)
	}

	grpcServer := grpc.NewServer()
	pb.RegisterNsControllerServer(grpcServer, server.New(state, ctrl))

	slog.Info("gRPC server listening", "addr", addr)

	// Graceful shutdown on SIGINT/SIGTERM.
	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
		<-sig
		slog.Info("shutting down")
		grpcServer.GracefulStop()
	}()

	return grpcServer.Serve(lis)
}

func setupLogger(level string) {
	var l slog.Level
	switch level {
	case "debug":
		l = slog.LevelDebug
	case "warn", "warning":
		l = slog.LevelWarn
	case "error":
		l = slog.LevelError
	default:
		l = slog.LevelInfo
	}
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: l})))
}
