from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import logging

logger = logging.getLogger(__name__)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        # Suppress standard HTTP logs to keep console clean
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), SimpleHandler)
        logger.info(f"🌐 Keep-alive server running on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Keep-alive server failed: {e}")

def keep_alive():
    """Starts a dummy web server in a background thread to satisfy host health checks."""
    t = Thread(target=run_server)
    t.daemon = True
    t.start()
