import http.server
import socketserver

# Set the port number for the server
port = 8000

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", port), Handler) as httpd:
    print(f"Serving at http://localhost:{port}")
    httpd.serve_forever()