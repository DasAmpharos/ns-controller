import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from ns_controller import NsController

target = "/dev/hidg0"
controller = NsController()
controller.connect(target)


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.startswith('/update'):
            try:
                # Parse query parameters for down and up times
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                down = float(params.get('down', ['0.1'])[0])
                up = float(params.get('up', ['0.1'])[0])

                # Read and parse JSON body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                inputs_dict = json.loads(body)

                # Convert dict to InputStruct
                inputs = NsController.InputStruct(**inputs_dict)

                # Update controller
                temp = controller.inputs
                controller.inputs = inputs
                time.sleep(down)
                controller.inputs = temp
                time.sleep(up)

                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({"status": "success"})
                self.wfile.write(response.encode())

            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({"status": "error", "message": str(e)})
                self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Override to customize logging or suppress it
        print(f"{self.address_string()} - {format % args}")


def run_server(host='0.0.0.0', port=8000):
    server = HTTPServer((host, port), RequestHandler)
    print(f"Server running on http://{host}:{port}")
    server.serve_forever()


if __name__ == '__main__':
    run_server()
