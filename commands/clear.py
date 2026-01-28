# temel komut clear, terminali temizlemeyecek.
import os
from core.command import Command
from typing import Any
from rich import  print
class Clear(Command):
    """Terminali temizlemeye yarıyan komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name = "clear"
    Description = "Ekranı temizler."
    Category = "system"
    Aliases = ["cls"]
    Usage = "clear"
    Examples = [
        "clear                    # Terminal ekranını temizler",
        "cls                      # 'clear' için alias (Windows stili)"
    ] 
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