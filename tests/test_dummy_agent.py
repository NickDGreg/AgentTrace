import contextlib
import http.server
import socketserver
import threading

from tools.dummy_agent import generate_agent_output


@contextlib.contextmanager
def serve_content(body: str):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, *_args, **_kwargs):
            return

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}"
        finally:
            httpd.shutdown()
            thread.join()


def test_dummy_agent_extracts_btc_address():
    html = "<html><body>Address: bc1qagenttrace0static0stage000000000000000000</body></html>"
    with serve_content(html) as url:
        output = generate_agent_output(url)
    assert output["artifacts"]["BTC"] == "bc1qagenttrace0static0stage000000000000000000"


def test_dummy_agent_reports_error():
    html = "<html><body>No address here</body></html>"
    with serve_content(html) as url:
        output = generate_agent_output(url)
    assert "error" in output
