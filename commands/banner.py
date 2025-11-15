# temel komut banner, banner ve modül bilgisi basacak.
# modül bilgisini basacak kısım henüz kodlanmadı
from asciistuff import Banner, Lolcat
import random
from typing import Any
from core.command import Command
class BannerCommand(Command):
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
            print(Lolcat(Banner("Hello world!"), spread=random.randint(1,11)))
            #("Banner basıldı.")
            return True
        except ImportError:
            print("asciistuff veya lolcat kütüphaneleri bulunamadı. Lütfen 'pip install asciistuff lolcat' ile yükleyin.")
            return False
        except Exception as e:
            print(f"Banner basılırken hata oluştu: {e}")
            return False