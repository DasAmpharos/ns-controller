.PHONY: proto
proto:
	uv run python -m grpc_tools.protoc -Iprotos --python_out=ns_controller/pb --pyi_out=ns_controller/pb --grpc_python_out=ns_controller/pb protos/ns_controller.proto
	sed -i '' 's/^import ns_controller_pb2/from . import ns_controller_pb2/' ns_controller/pb/ns_controller_pb2_grpc.py

