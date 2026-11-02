# ns-controller Go Server

The Go module that handles USB HID device communication and the gRPC control server. The Python scripting client connects to this over gRPC.

## Build

```bash
go build -o ns-controller-server .
```

Or cross-compile for Raspberry Pi (ARM64):

```bash
GOOS=linux GOARCH=arm64 go build -o ns-controller-server .
```

## Run

```
Usage:
  ns-controller-server [flags]

Flags:
  --hid-path    Path to USB HID gadget device  (default: /dev/hidg0)
  --host        Host to listen on              (default: all interfaces)
  --port        gRPC port                      (default: 50051)
  --mock        Open /dev/null instead of HID  (for local testing)
  --log-level   debug | info | warn | error    (default: info)
```

## Regenerating protobuf stubs

From the repository root:

```bash
protoc \
  --go_out=go-server/proto \
  --go_opt=paths=source_relative \
  --go_opt=Mns_controller.proto=ns-controller/go-server/proto/ns_controller \
  --go-grpc_out=go-server/proto \
  --go-grpc_opt=paths=source_relative \
  --go-grpc_opt=Mns_controller.proto=ns-controller/go-server/proto/ns_controller \
  --proto_path=protos \
  --proto_path=/path/to/protoc/include \
  ns_controller.proto

mv go-server/proto/ns_controller*.pb.go go-server/proto/ns_controller/
```

## Architecture

```
main.go                     CLI entry point (cobra)
internal/
  controller/
    state.go                Thread-safe ControllerState with notify callback
    controller.go           HID /dev/hidg0: counter + comm + input-report goroutines
  macro/
    executor.go             Server-side macro runner with sub-ms hybrid timing
  server/
    server.go               gRPC servicer wiring state + macro executor
  spidata/
    spidata.go              Embeds SPI ROM .bin blobs for Switch handshake
    data/0x60.bin, 0x80.bin
proto/ns_controller/        Generated gRPC/protobuf Go stubs
```
