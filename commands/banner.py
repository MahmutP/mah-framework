# temel komut banner, banner ve modül bilgisi basacak.
# modül bilgisini basacak kısım henüz kodlanmadı
from typing import Any
from core.command import Command
from core.banner import print_banner

class BannerCommand(Command):
    """Banner basmaya yarıyan komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name = "banner"
    Description = "Rastgele bir banner basar."
    Category = "system" 
    Aliases = [] 
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalıştırılınca çalışacak kod

        Returns:
            bool: Başarılı olup olmadığının sonucu
        """
        try:
            print_banner()
            return True
        except Exception as e:
            print(f"Banner basılırken hata oluştu: {e}")
            return False