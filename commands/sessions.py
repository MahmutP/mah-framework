import shutil
from core.command import Command
from core.shared_state import shared_state
from core.cont import LEFT_PADDING, COL_SPACING, DEFAULT_TERMINAL_WIDTH
from rich import print

class SessionsCommand(Command):
    Name = "sessions"
    Description = "Aktif oturumları listeler ve yönetir."
    Aliases = []
    Category = "core"
    Usage = "sessions [seçenekler]"
    Examples = [
        "sessions -l              # Aktif oturumları listeler",
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
            self.list_sessions()
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

    def list_sessions(self):
        sessions = shared_state.session_manager.get_all_sessions()
        if not sessions:
            print("Aktif oturum yok.")
            return

        # Prepare rows
        rows = []
        for s_id, data in sessions.items():
            info_str = f"{data['info'].get('host', 'Unknown')}:{data['info'].get('port', 0)}"
            rows.append({
                "id": str(s_id),
                "type": str(data['type']),
                "info": info_str,
                "status": str(data['status'])
            })

        # Define Headers
        headers = ["ID", "Type", "Information", "Status"]

        # Calculate max widths
        id_width = max(len(r["id"]) for r in rows)
        type_width = max(len(r["type"]) for r in rows)
        info_width = max(len(r["info"]) for r in rows)
        status_width = max(len(r["status"]) for r in rows)

        # Ensure headers fit
        id_width = max(id_width, len(headers[0]))
        type_width = max(type_width, len(headers[1]))
        info_width = max(info_width, len(headers[2]))
        status_width = max(status_width, len(headers[3]))

        # Helper method for padding
        def pad(text, width):
            return text.ljust(width)

        print("\nAktif Oturumlar")
        print("=" * len("Aktif Oturumlar"))

        # Print Headers
        header_line = (
            f"{' ' * LEFT_PADDING}"
            f"{pad(headers[0], id_width)}{' ' * COL_SPACING}"
            f"{pad(headers[1], type_width)}{' ' * COL_SPACING}"
            f"{pad(headers[2], info_width)}{' ' * COL_SPACING}"
            f"{pad(headers[3], status_width)}"
        )
        print(header_line)

        # Print Separator
        separator_line = (
            f"{' ' * LEFT_PADDING}"
            f"{'-' * id_width}{' ' * COL_SPACING}"
            f"{'-' * type_width}{' ' * COL_SPACING}"
            f"{'-' * info_width}{' ' * COL_SPACING}"
            f"{'-' * status_width}"
        )
        print(separator_line)

        # Print Rows
        for row in rows:
            line = (
                f"{' ' * LEFT_PADDING}"
                f"{pad(row['id'], id_width)}{' ' * COL_SPACING}"
                f"{pad(row['type'], type_width)}{' ' * COL_SPACING}"
                f"{pad(row['info'], info_width)}{' ' * COL_SPACING}"
                f"{pad(row['status'], status_width)}"
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
