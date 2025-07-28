# çıkış için temel komut
import sys
from typing import Any
from core.command import Command
from core.shared_state import shared_state 
from rich import  print
class Exit(Command):
    Name = "exit"
    Description = "Uygulamadan çıkar."
    Category = "core"
    Aliases = ["quit"]
    def execute(self, *args: str, **kwargs: Any) -> bool:
        print("Uygulamadan çıkış yapılıyor...")
        if hasattr(shared_state, 'console_instance') and shared_state.console_instance:
            shared_state.console_instance.shutdown()
        else:
            print("Console instance bulunamadı, doğrudan çıkılıyor.")
            sys.exit(0) 
        return True 