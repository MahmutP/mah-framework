import contextlib
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from rich import print

from core.handler import BaseHandler


class Handler(BaseHandler):
    """
    Mahpreter Reverse HTTP Handler.

    Agent GET /connect/{id} ile komut alır, POST /output/{id} ile çıktı gönderir.
    Etkileşim: MultiHandler ön plan veya `sessions -i <id>`.
    """

    def __init__(self, options: dict[str, Any]) -> None:
        super().__init__(options)
        self.cmd_queue: dict[str, str] = {}
        self.output_events: dict[str, threading.Event] = {}
        self.output_data: dict[str, str] = {}
        self.client_sessions: dict[str, int] = {}  # agent_id -> session_id
        self.session_agents: dict[int, str] = {}  # session_id -> agent_id
        self.httpd: HTTPServer | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        handler_ref = self

        class HTTPRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:
                if not self.path.startswith("/connect/"):
                    self.send_response(404)
                    self.end_headers()
                    return

                client_id = self.path.rstrip("/").split("/")[-1]
                if not client_id:
                    self.send_response(400)
                    self.end_headers()
                    return

                handler_ref._ensure_session(client_id, self.client_address)

                with handler_ref._lock:
                    cmd = handler_ref.cmd_queue.get(client_id, "")
                    if cmd:
                        handler_ref.cmd_queue[client_id] = ""

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(cmd.encode("utf-8"))

            def do_POST(self) -> None:
                if not self.path.startswith("/output/"):
                    self.send_response(404)
                    self.end_headers()
                    return

                client_id = self.path.rstrip("/").split("/")[-1]
                if not client_id:
                    self.send_response(400)
                    self.end_headers()
                    return

                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length > 0 else b""
                output = raw.decode("utf-8", errors="replace")

                handler_ref._ensure_session(client_id, self.client_address)
                handler_ref._deliver_output(client_id, output)

                self.send_response(200)
                self.end_headers()

        try:
            self.httpd = HTTPServer((self.lhost, self.lport), HTTPRequestHandler)
            self.sock = self.httpd.socket
            self.running = True
            print(f"[*] HTTP Dinleyici başlatıldı: {self.lhost}:{self.lport}")
            print("[*] Agent GET /connect/<id> ve POST /output/<id> bekleniyor...")
            print("[*] Durdurmak: jobs -k   |  oturum: sessions -i <id>")

            self.httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] HTTP dinleyici durduruluyor...")
        except OSError as e:
            print(f"[!] HTTP dinleyici bağlanamadı ({self.lhost}:{self.lport}): {e}")
        except Exception as e:
            print(f"[!] Hata: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        self.running = False
        if self.httpd is not None:
            with contextlib.suppress(BaseException):
                self.httpd.shutdown()
            with contextlib.suppress(BaseException):
                self.httpd.server_close()
            self.httpd = None
        self.sock = None
        with self.clients_lock:
            self.clients.clear()
        self.client_sock = None
        self.client_addr = None

    def handle_connection(
        self, client_sock: Any, session_id: int | None = None
    ) -> None:
        """HTTP polling kullanır; kalıcı TCP oturumu yok."""
        return

    def interact(self, session_id: int) -> None:
        client_id = self.session_agents.get(session_id)
        if not client_id:
            print(f"[!] Session {session_id}: aktif HTTP agent yok.")
            return

        print("-" * 50)
        print("[*] HTTP komut satırı aktif. Çıkmak için 'exit', 'background' veya CTRL+C.")
        print("-" * 50)

        while True:
            try:
                cmd = input("mahpreter-http > ")
                if not cmd.strip():
                    continue

                if cmd in ("exit", "quit", "terminate"):
                    print("[*] Oturum kapatılıyor...")
                    with self._lock:
                        self.cmd_queue[client_id] = "terminate"
                    if cmd == "terminate":
                        self._drop_session(session_id, client_id)
                    break

                if cmd in ("background", "bg"):
                    print("[*] Oturum arka plana atıldı.")
                    break

                event = threading.Event()
                with self._lock:
                    self.output_data[client_id] = ""
                    self.output_events[client_id] = event
                    self.cmd_queue[client_id] = cmd

                if event.wait(timeout=60):
                    response = self.output_data.get(client_id, "")
                    if response:
                        print(response)
                    else:
                        print("[*] (boş çıktı)")
                else:
                    print("[!] Zaman aşımı — agent yanıt vermedi (poll bekleniyor olabilir).")
            except KeyboardInterrupt:
                print("\n[*] Oturum arka plana alındı (CTRL+C).")
                break
            except EOFError:
                print("\n[*] Oturum arka plana alındı.")
                break
            except Exception as e:
                print(f"[!] Hata: {e}")
                break
            finally:
                with self._lock:
                    self.output_events.pop(client_id, None)

    def _ensure_session(self, client_id: str, client_addr: tuple) -> int | None:
        with self._lock:
            if client_id in self.client_sessions:
                return self.client_sessions[client_id]

        from core.shared_state import shared_state

        session_id = None
        if shared_state.session_manager:
            connection_info = {
                "host": client_addr[0],
                "port": client_addr[1],
                "type": "HTTP",
                "client_id": client_id,
            }
            session_id = shared_state.session_manager.add_session(self, connection_info)
            print(
                f"[+] HTTP agent bağlandı: id={client_id} "
                f"({client_addr[0]}:{client_addr[1]}) -> Session {session_id}"
            )
            print(f"[*] Etkileşim için: sessions -i {session_id}")

        with self._lock:
            if session_id is not None:
                self.client_sessions[client_id] = session_id
                self.session_agents[session_id] = client_id

        # MultiHandler ön plan / clients sözlüğü (sock yerine agent id)
        self.client_sock = client_id
        self.client_addr = client_addr
        if session_id is not None:
            with self.clients_lock:
                self.clients[session_id] = {
                    "sock": client_id,
                    "addr": client_addr,
                    "thread": None,
                    "client_id": client_id,
                }

        return session_id

    def _deliver_output(self, client_id: str, output: str) -> None:
        with self._lock:
            event = self.output_events.get(client_id)
            if event is not None:
                self.output_data[client_id] = output
                event.set()
                return

        print(f"\n[{client_id}] Output:\n{output}")

    def _drop_session(self, session_id: int, client_id: str) -> None:
        with self._lock:
            self.client_sessions.pop(client_id, None)
            self.session_agents.pop(session_id, None)
            self.cmd_queue.pop(client_id, None)
            self.output_events.pop(client_id, None)
            self.output_data.pop(client_id, None)

        with self.clients_lock:
            self.clients.pop(session_id, None)

        if self.client_sock == client_id:
            self.client_sock = None
            self.client_addr = None

        from core.shared_state import shared_state

        if shared_state.session_manager:
            with contextlib.suppress(BaseException):
                shared_state.session_manager.remove_session(session_id)
