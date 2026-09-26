import time
from datetime import timedelta
from typing import Any

from rich import print

from core.command import Command
from core.cont import COL_SPACING, LEFT_PADDING
from core.shared_state import shared_state


class SessionsCommand(Command):
    Name = "sessions"
    Description = "Aktif oturumları listeler ve yönetir."
    Aliases = []
    Category = "core"
    Usage = "sessions [seçenekler]"
    Examples = [
        "sessions -l              # Aktif oturumları listeler",
        "sessions -g              # Oturumları hedefe (IP) göre gruplandırarak listeler",
        "sessions list            # Aktif oturumları listeler",
        "sessions -i <id>         # Belirtilen ID'li oturumla etkileşime geçer",
        "sessions -k <id>         # Belirtilen ID'li oturumu sonlandırır",
        "sessions -u <id>         # Belirtilen ID'li oturumu PTY'ye yükseltir",
        "sessions -p <id>         # PTY modunda etkileşime geçer (raw terminal)",
    ]

    def execute(self, *args: str, **kwargs: Any) -> bool:
        if not shared_state.session_manager:
            print("[!] Session manager başlatılamadı.")
            return False

        if not args:
            self.list_sessions()
            return True

        subcommand = args[0].lower()

        if subcommand == "-l" or subcommand == "list":
            self.list_sessions(group_by_host=False)
        elif subcommand == "-g" or subcommand == "--group":
            self.list_sessions(group_by_host=True)
        elif subcommand == "-i" and len(args) > 1:
            try:
                session_id = int(args[1])
                self.interact_session(session_id)
            except ValueError:
                print("[!] Geçersiz session ID.")
        elif subcommand == "-k" and len(args) > 1:
            try:
                session_id = int(args[1])
                self.kill_session(session_id)
            except ValueError:
                print("[!] Geçersiz session ID.")
        elif subcommand == "-u" and len(args) > 1:
            try:
                session_id = int(args[1])
                method = args[2] if len(args) > 2 else None
                self.upgrade_session(session_id, method=method)
            except ValueError:
                print("[!] Geçersiz session ID.")
        elif subcommand == "-p" and len(args) > 1:
            try:
                session_id = int(args[1])
                self.pty_interact_session(session_id)
            except ValueError:
                print("[!] Geçersiz session ID.")
        else:
            print(f"Kullanım: {self.Usage}")
            print("Detaylı bilgi için 'help sessions' komutunu kullanın.")

        return True

    def list_sessions(self, group_by_host: bool = False) -> None:
        sessions = shared_state.session_manager.get_all_sessions()
        if not sessions:
            print("Aktif oturum yok.")
            return

        current_time = time.time()
        rows = []
        for s_id, data in sessions.items():
            info_str = (
                f"{data['info'].get('host', 'Unknown')}:{data['info'].get('port', 0)}"
            )

            # Uptime hesapla
            connected_at = data.get("connected_at", current_time)
            uptime_seconds = int(current_time - connected_at)
            uptime_str = str(timedelta(seconds=uptime_seconds))

            # PTY upgrade durumu
            pty_upgraded = data.get("info", {}).get("pty_upgraded", False)
            pty_status = "PTY" if pty_upgraded else "Raw"

            rows.append(
                {
                    "id": str(s_id),
                    "type": str(data["type"]),
                    "info": info_str,
                    "host": data["info"].get("host", "Unknown"),
                    "status": str(data["status"]),
                    "shell": pty_status,
                    "uptime": uptime_str,
                }
            )

        if group_by_host:
            # IP adresine göre gruplandır
            groups: dict[str, list] = {}
            for row in rows:
                groups.setdefault(row["host"], []).append(row)

            print("\nAktif Oturumlar (Gruplandırılmış)")
            print("=================================")
            for host, host_rows in groups.items():
                print(f"\n[cyan]Hedef: {host}[/cyan]")
                self._print_table(host_rows)
        else:
            print("\nAktif Oturumlar")
            print("===============")
            self._print_table(rows)

    def _print_table(self, rows: list) -> None:
        if not rows:
            return

        headers = ["ID", "Type", "Information", "Status", "Shell", "Uptime"]

        id_width = max(max(len(r["id"]) for r in rows), len(headers[0]))
        type_width = max(max(len(r["type"]) for r in rows), len(headers[1]))
        info_width = max(max(len(r["info"]) for r in rows), len(headers[2]))
        status_width = max(max(len(r["status"]) for r in rows), len(headers[3]))
        shell_width = max(max(len(r.get("shell", "Raw")) for r in rows), len(headers[4]))
        uptime_width = max(max(len(r["uptime"]) for r in rows), len(headers[5]))

        def pad(text: str, width: int) -> str:
            return text.ljust(width)

        header_line = (
            f"{' ' * LEFT_PADDING}"
            f"{pad(headers[0], id_width)}{' ' * COL_SPACING}"
            f"{pad(headers[1], type_width)}{' ' * COL_SPACING}"
            f"{pad(headers[2], info_width)}{' ' * COL_SPACING}"
            f"{pad(headers[3], status_width)}{' ' * COL_SPACING}"
            f"{pad(headers[4], shell_width)}{' ' * COL_SPACING}"
            f"{pad(headers[5], uptime_width)}"
        )
        print(header_line)

        separator_line = (
            f"{' ' * LEFT_PADDING}"
            f"{'-' * id_width}{' ' * COL_SPACING}"
            f"{'-' * type_width}{' ' * COL_SPACING}"
            f"{'-' * info_width}{' ' * COL_SPACING}"
            f"{'-' * status_width}{' ' * COL_SPACING}"
            f"{'-' * shell_width}{' ' * COL_SPACING}"
            f"{'-' * uptime_width}"
        )
        print(separator_line)

        for row in rows:
            line = (
                f"{' ' * LEFT_PADDING}"
                f"{pad(row['id'], id_width)}{' ' * COL_SPACING}"
                f"{pad(row['type'], type_width)}{' ' * COL_SPACING}"
                f"{pad(row['info'], info_width)}{' ' * COL_SPACING}"
                f"{pad(row['status'], status_width)}{' ' * COL_SPACING}"
                f"{pad(row.get('shell', 'Raw'), shell_width)}{' ' * COL_SPACING}"
                f"{pad(row['uptime'], uptime_width)}"
            )
            print(line)
        print()

    def interact_session(self, session_id: int) -> None:
        session = shared_state.session_manager.get_session(session_id)
        if not session:
            print(f"[!] {session_id} numaralı oturum bulunamadı.")
            return

        print(f"[*] {session_id} numaralı oturumla etkileşime geçiliyor...")
        # Burada handler'ın interact metodunu çağıracağız
        handler = session.get("handler")
        if handler and hasattr(handler, "interact"):
            try:
                handler.interact(session_id)
            except KeyboardInterrupt:
                print("\n[*] Oturum etkileşimi sonlandırıldı.")
        else:
            print("[!] Bu oturum türü interaktif modu desteklemiyor.")

    def upgrade_session(
        self, session_id: int, method: str | None = None
    ) -> None:
        """Oturumu PTY'ye yükseltir."""
        session = shared_state.session_manager.get_session(session_id)
        if not session:
            print(f"[!] {session_id} numaralı oturum bulunamadı.")
            return

        handler = session.get("handler")
        if not handler:
            print(f"[!] Session {session_id}: handler yok.")
            return

        # Handler'ın upgrade_to_pty metodunu kullan
        if hasattr(handler, "upgrade_to_pty"):
            print(f"[*] Session {session_id} PTY'ye yükseltiliyor...")
            success = handler.upgrade_to_pty(
                session_id=session_id, method=method
            )
            if success:
                print(f"[+] Session {session_id} PTY upgrade komutu gönderildi.")
                # Session metadata güncelle
                if "info" in session:
                    session["info"]["pty_upgraded"] = True
                print(
                    f"[*] PTY modunda etkileşim için: sessions -p {session_id}"
                )
            else:
                print(f"[!] Session {session_id} PTY upgrade başarısız.")
        else:
            # Doğrudan pty_handler kullan
            try:
                from core.pty_handler import send_upgrade_payload

                sock = None
                if hasattr(handler, "resolve_client_sock"):
                    sock = handler.resolve_client_sock(session_id)
                if not sock:
                    sock = getattr(handler, "client_sock", None)

                if sock:
                    print(f"[*] Session {session_id} PTY'ye yükseltiliyor...")
                    success = send_upgrade_payload(sock, method=method)
                    if success:
                        print(
                            f"[+] PTY upgrade komutu gönderildi. "
                            f"PTY etkileşim: sessions -p {session_id}"
                        )
                        if "info" in session:
                            session["info"]["pty_upgraded"] = True
                    else:
                        print("[!] PTY upgrade başarısız.")
                else:
                    print(f"[!] Session {session_id}: aktif soket bulunamadı.")
            except ImportError:
                print("[!] core/pty_handler modülü yüklenemedi!")

    def pty_interact_session(self, session_id: int) -> None:
        """Oturumla PTY modunda (raw terminal) etkileşime geçer."""
        session = shared_state.session_manager.get_session(session_id)
        if not session:
            print(f"[!] {session_id} numaralı oturum bulunamadı.")
            return

        handler = session.get("handler")
        if not handler:
            print(f"[!] Session {session_id}: handler yok.")
            return

        # PTY shell loop'u kullan
        if hasattr(handler, "pty_shell_loop"):
            sock = None
            if hasattr(handler, "resolve_client_sock"):
                sock = handler.resolve_client_sock(session_id)
            if not sock:
                sock = getattr(handler, "client_sock", None)

            if sock:
                print(
                    f"[*] Session {session_id} ile PTY modunda etkileşime geçiliyor..."
                )
                try:
                    handler.pty_shell_loop(
                        sock,
                        session_id=session_id,
                        auto_upgrade=False,  # Manuel upgrade zaten yapılmış olmalı
                    )
                except KeyboardInterrupt:
                    print("\n[*] PTY oturumundan çıkıldı.")
            else:
                print(f"[!] Session {session_id}: aktif soket bulunamadı.")
        else:
            # Fallback: pty_handler'ı doğrudan kullan
            try:
                from core.pty_handler import PTYSession

                sock = None
                if hasattr(handler, "resolve_client_sock"):
                    sock = handler.resolve_client_sock(session_id)
                if not sock:
                    sock = getattr(handler, "client_sock", None)

                if sock:
                    pty_session = PTYSession(sock, session_id=session_id)
                    pty_session.start()
                else:
                    print(f"[!] Session {session_id}: aktif soket bulunamadı.")
            except ImportError:
                print("[!] PTY handler modülü yüklenemedi!")
                print("[*] Standart etkileşim kullanılıyor...")
                self.interact_session(session_id)

    def kill_session(self, session_id: int) -> None:
        session = shared_state.session_manager.get_session(session_id)
        if not session:
            print(f"[!] {session_id} numaralı oturum bulunamadı.")
            return

        shared_state.session_manager.remove_session(session_id)
        print(f"[*] {session_id} numaralı oturum sonlandırıldı.")
