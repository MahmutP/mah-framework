# temel komut clear, terminali temizlemeyecek.
import os
from core.command import Command
from typing import Any
from rich import  print
class Clear(Command):
    Name = "clear"
    Description = "Ekranı temizler."
    Category = "system"
    Aliases = [] 
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalıştırılınca çalışacak kod

        Returns:
            bool: başarılı olup olmadığının kontrol edicek.
        """
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            #("Ekran temizlendi.")
            return True
        except Exception as e:
            print(f"Ekran temizlenirken hata oluştu: {e}")
            return False