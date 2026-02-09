from core.command import Command
from core.shared_state import shared_state
from rich.table import Table
from rich import print

class SessionsCommand(Command):
    Name = "sessions"
    Description = "Aktif oturumları listeler ve yönetir."
    Aliases = []
    Category = "core"

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
            print(self.help())
            
        return True

    def list_sessions(self):
        sessions = shared_state.session_manager.get_all_sessions()
        if not sessions:
            print("Aktif oturum yok.")
            return

        table = Table(title="Aktif Oturumlar")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Information", style="green")
        table.add_column("Status", style="yellow")

        for s_id, data in sessions.items():
            info_str = f"{data['info'].get('host', 'Unknown')}:{data['info'].get('port', 0)}"
            table.add_row(str(s_id), data['type'], info_str, data['status'])

        print(table)

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

    def help(self):
        return """
        Kullanım: sessions [seçenekler]
        
        Seçenekler:
            -l, list       : Aktif oturumları listeler.
            -i <id>        : Belirtilen ID'li oturumla etkileşime geçer.
            -k <id>        : Belirtilen ID'li oturumu sonlandırır.
        """
