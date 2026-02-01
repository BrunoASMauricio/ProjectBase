from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading

from data.paths import GetBasePaths

http_servers = {}
http_lock = threading.Lock()
htt_root_path = GetBasePaths()["http"]

def GetHTTPRoot():
    return htt_root_path

class CustomHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=htt_root_path, **kwargs)

def StartHTTPServer(host="0.0.0.0", port=8000):
    global http_servers
    
    with http_lock:
        if host not in http_servers:
            http_servers[host] = {}

        if port not in http_servers[host]:
            http_servers[host][port] = {
                "stopped": None,
                "server":  None,
                "thread":  None,
            }

        http_server = http_servers[host][port]

        # Check if server has stopped
        is_alive =              http_server["stopped"] != None and not http_server["stopped"].is_set()
        is_alive = is_alive and http_server["thread"]  != None and http_server["thread"].is_alive()
        if is_alive:
            return

        http_server["server"] = ThreadingHTTPServer((host, port), CustomHandler)
        http_server["stopped"] = threading.Event()

        def _run():
            try:
                http_server["server"].serve_forever()
            except OSError:
                http_server["server"] = None
                http_server["stopped"] = None
                raise
            finally:
                # signal that server stopped
                http_server["stopped"].set()

        http_server["thread"] = threading.Thread(target=_run, daemon=True)
        http_server["thread"].start()
