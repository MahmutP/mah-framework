from typing import Any
from core.command import Command
from core.shared_state import shared_state
from core.module import BaseModule 
from rich import  print
class Run(Command):
    """Modülleri çalıştırmaya yarıyan bir komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name = "run"
    Description = "Seçili modülü çalıştırır."
    Category = "module"
    Aliases = ["exploit", "execute"]
    Usage = "run"
    Examples = [
        "run                    # Seçili modülü çalıştırır",
        "exploit                # 'run' için alias",
        "execute                # 'run' için alias"
    ]
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalışınca çalışacak komut.

        Returns:
            bool: Komutun başarılı olup olmadığının sonucu.
        """
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            print("Çalıştırılacak bir modül seçili değil. Lütfen önce 'use <modül_yolu>' komutunu kullanın.")
            return False
        if not selected_module.check_required_options():
            print(f"[{selected_module.Name}] Modül çalıştırılamaz: Zorunlu seçenekler ayarlanmamış.") 
            return False
        print(f"[{selected_module.Name}] Modül çalıştırılıyor...")
        try:
            current_options = {name: opt.value for name, opt in selected_module.get_options().items()}
            result = selected_module.run(current_options)
            
            # [Fix/Explanation] Modüllerden dönen çıktıların ekrana basılması sağlandı.
            # Önceden return edilen değerler (örneğin IP bilgisi) ekrana yazdırılmıyordu.
            if result:
                print(result)
                
            print(f"[{selected_module.Name}] Modül başarıyla çalıştırıldı.") 
            return True
        except Exception as e:
            print(f"[{selected_module.Name}] Modül çalıştırılırken beklenmedik bir hata oluştu: {e}")
            print(f"Hata detayı: {e}") 
            print(f"[{selected_module.Name}] Modül çalışması başarısız oldu.") 
            return False