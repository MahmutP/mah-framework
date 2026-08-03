# workspace create|list|use|delete komutu.

from typing import Any

from rich import print

from core.command import Command
from core.shared_state import shared_state


class Workspace(Command):
    Name = "workspace"
    Description = "Workspace / loot alanlarını yönetir (create, list, use, delete)."
    Category = "core"
    Aliases = ["workspaces"]
    Usage = "workspace <create|list|use|delete> [name]"
    Examples = [
        "workspace list",
        "workspace create eng-lab",
        "workspace use eng-lab",
        "workspace delete eng-lab",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.completer_function = self._completer

    def _completer(self, text: str, word_before_cursor: str) -> list[str]:
        parts = text.split()
        subcommands = ["create", "list", "use", "delete"]
        if len(parts) == 1 and text.endswith(" "):
            return sorted(subcommands)
        if len(parts) == 2 and not text.endswith(" "):
            return sorted(s for s in subcommands if s.startswith(parts[1]))
        if len(parts) >= 2 and parts[1].lower() in ("use", "delete"):
            wm = shared_state.workspace_manager
            names = wm.list_workspaces() if wm else []
            if len(parts) == 2 and text.endswith(" "):
                return sorted(names)
            if len(parts) == 3 and not text.endswith(" "):
                return sorted(n for n in names if n.startswith(parts[2]))
        return []

    def execute(self, *args: str, **kwargs: Any) -> bool:
        wm = shared_state.workspace_manager
        if not wm:
            print("[!] Workspace manager başlatılmamış.")
            return False

        if not args:
            self._print_status(wm)
            return True

        sub = args[0].lower()
        if sub == "list":
            names = wm.list_workspaces()
            if not names:
                print("Workspace yok. Oluşturmak için: workspace create <name>")
                return True
            active = wm.active_name
            print("\nWorkspaces")
            print("==========")
            for name in names:
                mark = " *" if name == active else ""
                print(f"  {name}{mark}")
            print()
            return True

        if sub == "create":
            if len(args) < 2:
                print("[!] Kullanım: workspace create <name>")
                return False
            try:
                path = wm.create(args[1])
                print(f"[+] Workspace oluşturuldu: {path}")
                if wm.active_name == args[1]:
                    print(f"[*] Aktif workspace: {args[1]}")
                return True
            except ValueError as e:
                print(f"[!] {e}")
                return False

        if sub == "use":
            if len(args) < 2:
                print("[!] Kullanım: workspace use <name>")
                return False
            try:
                path = wm.use(args[1])
                print(f"[*] Aktif workspace: {args[1]} ({path})")
                return True
            except FileNotFoundError as e:
                print(f"[!] {e}")
                return False

        if sub == "delete":
            if len(args) < 2:
                print("[!] Kullanım: workspace delete <name>")
                return False
            try:
                wm.delete(args[1])
                print(f"[*] Workspace silindi: {args[1]}")
                return True
            except FileNotFoundError as e:
                print(f"[!] {e}")
                return False

        print(f"Kullanım: {self.Usage}")
        return False

    def _print_status(self, wm: Any) -> None:
        active = wm.active_name
        if active:
            print(f"[*] Aktif workspace: {active} ({wm.get_active_path()})")
        else:
            print("[*] Aktif workspace yok. 'workspace create <name>' ile oluşturun.")
        print(f"Kullanım: {self.Usage}")
