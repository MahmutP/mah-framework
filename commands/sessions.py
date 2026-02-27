import shutil
from core.command import Command
from core.shared_state import shared_state
from core.cont import LEFT_PADDING, COL_SPACING, DEFAULT_TERMINAL_WIDTH
from rich import print

import time
from datetime import timedelta

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
        "sessions -k <id>         # Belirtilen ID'li oturumu sonlandırır"
    ]

    def execute(self, *args) -> bool:
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
        else:
            print(f"Kullanım: {self.Usage}")
            print("Detaylı bilgi için 'help sessions' komutunu kullanın.")
            
        return True

    def list_sessions(self, group_by_host: bool = False):
        sessions = shared_state.session_manager.get_all_sessions()
        if not sessions:
            print("Aktif oturum yok.")
            return

        current_time = time.time()
        rows = []
        for s_id, data in sessions.items():
            info_str = f"{data['info'].get('host', 'Unknown')}:{data['info'].get('port', 0)}"
            
            # Uptime hesapla
            connected_at = data.get("connected_at", current_time)
            uptime_seconds = int(current_time - connected_at)
            uptime_str = str(timedelta(seconds=uptime_seconds))
            
            rows.append({
                "id": str(s_id),
                "type": str(data['type']),
                "info": info_str,
                "host": data['info'].get('host', 'Unknown'),
                "status": str(data['status']),
                "uptime": uptime_str
            })

        if group_by_host:
            # IP adresine göre gruplandır
            groups = {}
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

    def _print_table(self, rows: list):
        if not rows:
            return
            
        headers = ["ID", "Type", "Information", "Status", "Uptime"]

        id_width = max(max(len(r["id"]) for r in rows), len(headers[0]))
        type_width = max(max(len(r["type"]) for r in rows), len(headers[1]))
        info_width = max(max(len(r["info"]) for r in rows), len(headers[2]))
        status_width = max(max(len(r["status"]) for r in rows), len(headers[3]))
        uptime_width = max(max(len(r["uptime"]) for r in rows), len(headers[4]))

        def pad(text, width):
            return text.ljust(width)

        header_line = (
            f"{' ' * LEFT_PADDING}"
            f"{pad(headers[0], id_width)}{' ' * COL_SPACING}"
            f"{pad(headers[1], type_width)}{' ' * COL_SPACING}"
            f"{pad(headers[2], info_width)}{' ' * COL_SPACING}"
            f"{pad(headers[3], status_width)}{' ' * COL_SPACING}"
            f"{pad(headers[4], uptime_width)}"
        )
        print(header_line)

        separator_line = (
            f"{' ' * LEFT_PADDING}"
            f"{'-' * id_width}{' ' * COL_SPACING}"
            f"{'-' * type_width}{' ' * COL_SPACING}"
            f"{'-' * info_width}{' ' * COL_SPACING}"
            f"{'-' * status_width}{' ' * COL_SPACING}"
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
                f"{pad(row['uptime'], uptime_width)}"
            )
            print(line)
        print() 

    def interact_session(self, session_id):
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

    def kill_session(self, session_id):
        session = shared_state.session_manager.get_session(session_id)
        if not session:
             print(f"[!] {session_id} numaralı oturum bulunamadı.")
             return
        
        shared_state.session_manager.remove_session(session_id)
        print(f"[*] {session_id} numaralı oturum sonlandırıldı.")
