# =============================================================================
# Post-Exploitation: SOCKS5 Proxy Server
# =============================================================================
# Hedef üzerinde basit bir SOCKS5 proxy sunucusu başlatan modül.
# RFC 1928 uyumlu, opsiyonel kimlik doğrulama ve threading desteği.
#
# KULLANIM:
#   1. use post/pivot/socks_proxy
#   2. set BIND_HOST 0.0.0.0
#   3. set BIND_PORT 1080
#   4. set AUTH false
#   5. run                        # proxy'yi başlatır
#   6. (Ctrl+C veya stop ile durdurulur)
# =============================================================================

import contextlib
import select
import socket
import struct
import threading
from typing import Any

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option


class socks_proxy(BaseModule):
    """SOCKS5 Proxy Sunucusu (Post-Exploitation / Pivoting)

    Hedef üzerinde bir SOCKS5 proxy çalıştırarak ağ pivotlama imkânı sağlar.
    Saldırganın trafiğini hedef ağ üzerinden yönlendirmesine olanak tanır.

    Özellikler:
        - SOCKS5 protokolü (RFC 1928 — CONNECT komutu)
        - İsteğe bağlı kullanıcı adı / parola doğrulama (RFC 1929)
        - Threading ile eşzamanlı çoklu istemci desteği
        - Bağlantı istatistikleri takibi
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "SOCKS5 Proxy"
    Description = "Hedef üzerinden SOCKS5 proxy oluşturarak ağ pivotlama sağlar"
    Author = "Mahmut P."
    Category = "post/pivot"
    Version = "1.0"

    Requirements: dict[str, list[str]] = {}

    def __init__(self):
        super().__init__()
        self.Options = {
            "BIND_HOST": Option(
                name="BIND_HOST",
                value="0.0.0.0",
                required=True,
                description="Proxy'nin dinleyeceği adres",
            ),
            "BIND_PORT": Option(
                name="BIND_PORT",
                value=1080,
                required=True,
                description="Proxy'nin dinleyeceği port",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "AUTH": Option(
                name="AUTH",
                value="false",
                required=False,
                description="Kullanıcı/parola doğrulaması aktif mi? (true/false)",
                choices=["true", "false"],
            ),
            "USERNAME": Option(
                name="USERNAME",
                value="mah",
                required=False,
                description="AUTH=true ise kullanıcı adı",
            ),
            "PASSWORD": Option(
                name="PASSWORD",
                value="mah123",
                required=False,
                description="AUTH=true ise parola",
            ),
            "TIMEOUT": Option(
                name="TIMEOUT",
                value=30,
                required=False,
                description="Bağlantı zaman aşımı (saniye)",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "MAX_CLIENTS": Option(
                name="MAX_CLIENTS",
                value=50,
                required=False,
                description="Eşzamanlı maksimum istemci sayısı",
                regex_check=True,
                regex=r"^\d+$",
            ),
        }
        for opt_name, opt_obj in self.Options.items():
            setattr(self, opt_name, opt_obj.value)

        self.console = Console()

        # Çalışma durumu
        self._server_socket: socket.socket | None = None
        self._running = False
        self._threads: list[threading.Thread] = []
        self._stats = {"connections": 0, "active": 0, "bytes_sent": 0, "bytes_recv": 0}
        self._stats_lock = threading.Lock()

    # ── SOCKS5 PROTOKOLü ────────────────────────────────────────────────────

    def _handle_client(
        self,
        client: socket.socket,
        addr: tuple[str, int],
        auth_required: bool,
        username: str,
        password: str,
        timeout: int,
    ) -> None:
        """Tek bir SOCKS5 istemci bağlantısını yönetir."""
        remote: socket.socket | None = None
        try:
            client.settimeout(timeout)
            with self._stats_lock:
                self._stats["connections"] += 1
                self._stats["active"] += 1

            # ── Greeting ──────────────────────────────────────────────────
            header = client.recv(2)
            if len(header) < 2:
                return
            ver, nmethods = struct.unpack("!BB", header)
            if ver != 0x05:
                return
            client.recv(nmethods)

            if auth_required:
                # 0x02 = Username / Password
                client.sendall(struct.pack("!BB", 0x05, 0x02))
                # RFC 1929 kimlik doğrulama
                auth_ver = client.recv(1)
                if not auth_ver or auth_ver[0] != 0x01:
                    return
                ulen = client.recv(1)[0]
                uname = client.recv(ulen).decode("utf-8", errors="replace")
                plen = client.recv(1)[0]
                passwd = client.recv(plen).decode("utf-8", errors="replace")
                if uname != username or passwd != password:
                    client.sendall(struct.pack("!BB", 0x01, 0x01))  # Fail
                    logger.warning(f"SOCKS5 auth başarısız: {addr[0]}:{addr[1]}")
                    return
                client.sendall(struct.pack("!BB", 0x01, 0x00))  # Success
            else:
                # 0x00 = No auth
                client.sendall(struct.pack("!BB", 0x05, 0x00))

            # ── Request ───────────────────────────────────────────────────
            req = client.recv(4)
            if len(req) < 4:
                return
            ver, cmd, _rsv, atype = struct.unpack("!BBBB", req)
            if cmd != 0x01:  # Sadece CONNECT destekleniyor
                reply = struct.pack("!BBBBIH", 0x05, 0x07, 0x00, 0x01, 0, 0)
                client.sendall(reply)
                return

            # Hedef adresini oku
            if atype == 0x01:  # IPv4
                raw_addr = client.recv(4)
                dst_addr = socket.inet_ntoa(raw_addr)
            elif atype == 0x03:  # Domain
                dlen = client.recv(1)[0]
                dst_addr = client.recv(dlen).decode("utf-8", errors="replace")
            elif atype == 0x04:  # IPv6
                raw_addr = client.recv(16)
                dst_addr = socket.inet_ntop(socket.AF_INET6, raw_addr)
            else:
                reply = struct.pack("!BBBBIH", 0x05, 0x08, 0x00, 0x01, 0, 0)
                client.sendall(reply)
                return

            dst_port = struct.unpack("!H", client.recv(2))[0]

            # ── Connect ──────────────────────────────────────────────────
            try:
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.settimeout(timeout)
                remote.connect((dst_addr, dst_port))
            except Exception:
                reply = struct.pack("!BBBBIH", 0x05, 0x05, 0x00, 0x01, 0, 0)
                client.sendall(reply)
                return

            # Başarılı yanıt
            bind_addr = remote.getsockname()
            reply = (
                struct.pack("!BBBB", 0x05, 0x00, 0x00, 0x01)
                + socket.inet_aton(bind_addr[0])
                + struct.pack("!H", bind_addr[1])
            )
            client.sendall(reply)

            # ── Relay ────────────────────────────────────────────────────
            self._relay(client, remote)

        except Exception as exc:
            logger.debug(f"SOCKS5 istemci hatası ({addr}): {exc}")
        finally:
            with self._stats_lock:
                self._stats["active"] -= 1
            if remote:
                with contextlib.suppress(Exception):
                    remote.close()
            with contextlib.suppress(Exception):
                client.close()

    def _relay(self, client: socket.socket, remote: socket.socket) -> None:
        """İstemci ↔ hedef arasında çift yönlü veri aktarımı."""
        sockets = [client, remote]
        while self._running:
            try:
                readable, _, _ = select.select(sockets, [], [], 1.0)
            except Exception:
                break
            for sock in readable:
                try:
                    data = sock.recv(8192)
                except Exception:
                    data = b""
                if not data:
                    return
                target = remote if sock is client else client
                try:
                    target.sendall(data)
                    with self._stats_lock:
                        if sock is client:
                            self._stats["bytes_sent"] += len(data)
                        else:
                            self._stats["bytes_recv"] += len(data)
                except Exception:
                    return

    # ── SUNUCU YAŞAM DÖNGÜSÜ ────────────────────────────────────────────────

    def _start_server(
        self,
        bind_host: str,
        bind_port: int,
        auth: bool,
        username: str,
        password: str,
        timeout: int,
        max_clients: int,
    ) -> None:
        """Proxy sunucusunu başlatır ve gelen bağlantıları kabul eder."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)

        try:
            self._server_socket.bind((bind_host, bind_port))
            self._server_socket.listen(max_clients)
        except OSError as e:
            print(
                f"[bold red][-] Bind hatası ({bind_host}:{bind_port}): {e}[/bold red]"
            )
            self._running = False
            return

        self._running = True

        auth_label = (
            f"[yellow]AUTH ({username})[/yellow]" if auth else "[green]Yok[/green]"
        )
        self.console.print(
            Panel.fit(
                f"[bold green]✔ SOCKS5 Proxy Aktif[/bold green]\n"
                f"  Adres     : [cyan]{bind_host}:{bind_port}[/cyan]\n"
                f"  Doğrulama : {auth_label}\n"
                f"  Timeout   : {timeout}s\n\n"
                f"  [dim]Durdurmak için Ctrl+C kullanın.[/dim]",
                border_style="green",
            )
        )

        while self._running:
            try:
                client_sock, client_addr = self._server_socket.accept()
                logger.info(f"SOCKS5 yeni istemci: {client_addr[0]}:{client_addr[1]}")
                t = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, client_addr, auth, username, password, timeout),
                    daemon=True,
                )
                t.start()
                self._threads.append(t)
            except TimeoutError:
                continue
            except OSError:
                break

    def _stop_server(self) -> None:
        """Proxy sunucusunu durdurur."""
        self._running = False
        if self._server_socket:
            with contextlib.suppress(Exception):
                self._server_socket.close()
            self._server_socket = None

        # Canlı thread'leri bekle (kısa süre)
        for t in self._threads:
            t.join(timeout=1)
        self._threads.clear()

    def _print_stats(self) -> None:
        """Bağlantı istatistiklerini gösterir."""
        with self._stats_lock:
            s = self._stats.copy()
        tbl = Table(
            title="📊 Proxy İstatistikleri", show_header=False, border_style="cyan"
        )
        tbl.add_column("Metrik", style="cyan")
        tbl.add_column("Değer", style="white")
        tbl.add_row("Toplam Bağlantı", str(s["connections"]))
        tbl.add_row("Aktif Bağlantı", str(s["active"]))
        tbl.add_row("Gönderilen", f"{s['bytes_sent']:,} B")
        tbl.add_row("Alınan", f"{s['bytes_recv']:,} B")
        self.console.print(tbl)

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        bind_host = str(options.get("BIND_HOST", "0.0.0.0"))
        bind_port = int(options.get("BIND_PORT", 1080))
        auth = str(options.get("AUTH", "false")).lower() == "true"
        username = str(options.get("USERNAME", "mah"))
        password = str(options.get("PASSWORD", "mah123"))
        timeout = int(options.get("TIMEOUT", 30))
        max_clients = int(options.get("MAX_CLIENTS", 50))

        logger.info(f"SOCKS5 proxy başlatılıyor: {bind_host}:{bind_port}")

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]🌐 SOCKS5 PROXY — Pivoting Modülü[/bold cyan]",
                border_style="cyan",
            )
        )

        try:
            self._start_server(
                bind_host, bind_port, auth, username, password, timeout, max_clients
            )
        except KeyboardInterrupt:
            pass
        finally:
            self._stop_server()
            self.console.print(
                "\n[bold yellow][*] SOCKS5 Proxy durduruldu.[/bold yellow]"
            )
            self._print_stats()

        return True
