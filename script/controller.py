from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button


def main():
    client = NsControllerClient('10.117.1.143', 50051)
    # client.click([Button.HOME])
    client.click([Button.DPAD_DOWN], post_delay=0.1)
    for _ in range(6):
        client.click([Button.DPAD_RIGHT], post_delay=0.1)
    client.click([Button.A], post_delay=1)
    client.click([Button.A])

if __name__ == '__main__':
    main()
