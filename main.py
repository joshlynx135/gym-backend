import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class GymHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        response_data = {"message": "Welcome to the Gym API!", "path_requested": self.path}
        json_string = json.dumps(response_data)
        self.wfile.write(json_string.encode('utf-8'))

if __name__ == "__main__":
    port = 8080
    server = ThreadingHTTPServer(('localhost', port), GymHandler)
    print(f"Server is listening on http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer is shutting down.")
        server.server_close()