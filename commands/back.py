# temel komut back, modül seçilmesi halinde geri root prompta dönmek için
from typing import Any
from core.command import Command
from core.shared_state import shared_state
from rich import  print
class Back(Command):
    Name = "back"
    Description = "Mevcut modülden çıkarak ana kabuğa döner."
    Category = "module"
    Aliases = []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalıştığında çalışacak komut

        Returns:
            bool: başarılı olup olmadığının sonucu
        """
        selected_module = shared_state.get_selected_module()
        if selected_module:
            shared_state.set_selected_module(None)
            #(f"Modül '{selected_module.Name}' seçiminden çıkıldı. Ana kabuğa dönüldü.")
            return True
        else:
            print("Zaten bir modül seçili değil. Ana kabuktasınız.")
            return False