from typing import Any, List
from core.command import Command
from core.shared_state import shared_state
from core.module import BaseModule 
from rich import  print
class Set(Command):
    """option'ları değiştirmeye yarıyan komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name = "set"
    Description = "Seçili modülün seçeneklerini ayarlar."
    Category = "module"
    Aliases = []
    def __init__(self):
        """init fonksiyon
        """
        super().__init__()
        self.completer_function = self._set_completer 
    def _set_completer(self, text: str, word_before_cursor: str) -> List[str]:
        """set komutunun otomatik tamamlaması.

        Args:
            text (str): text girdi.
            word_before_cursor (str): imlecin solundaki text.

        Returns:
            List[str]: otomatik tamamlama listesi.
        """
        parts = text.split()
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            return []
        options = selected_module.get_options()
        
        # "set " yazıldığında option isimlerini göster
        if len(parts) == 1 and text.endswith(' '): 
            return sorted(list(options.keys()))
        
        # "set TEX" yazıldığında option isimlerini tamamla
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            return sorted([name for name in options.keys() if name.startswith(current_arg)])
        
        # "set OPTION_NAME " yazıldığında o option'ın choices'larını göster
        elif len(parts) == 2 and text.endswith(' '): 
            option_name = parts[1]
            if option_name in options:
                opt = options[option_name]
                # Eğer choices tanımlanmışsa onları döndür
                if opt.choices:
                    return list(opt.choices)
                # Boolean değer gibi görünüyorsa true/false öner
                current_val = str(opt.value).lower()
                if current_val in ['true', 'false', '0', '1', 'yes', 'no']:
                    return ['true', 'false']
            return []
        
        # "set OPTION_NAME tr" yazıldığında choices'ları filtrele
        elif len(parts) >= 3:
            option_name = parts[1]
            current_value = parts[2] if len(parts) > 2 else ""
            if option_name in options:
                opt = options[option_name]
                choices = []
                if opt.choices:
                    choices = list(opt.choices)
                else:
                    current_val = str(opt.value).lower()
                    if current_val in ['true', 'false', '0', '1', 'yes', 'no']:
                        choices = ['true', 'false']
                return sorted([c for c in choices if c.lower().startswith(current_value.lower())])
            return []
        
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalıştırılacak çalışacak kod.

        Returns:
            bool: Başarılı olup olmadığının sonucu.
        """
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            print("Herhangi bir modül seçili değil. Lütfen önce 'use <modül_yolu>' komutunu kullanın.")
            return False
        if len(args) < 2:
            print("Kullanım: set <seçenek_adı> <değer>")
            return False
        option_name = args[0]
        option_value = " ".join(args[1:]) 
        options = selected_module.get_options()
        if option_name in options:
            if selected_module.set_option_value(option_name, option_value):
                print(f"{option_name} => {option_value}")
                return True
            else:
                print(f"Seçenek '{option_name}' değeri '{option_value}' olarak ayarlanamadı. Regex kontrolü başarısız olabilir.")
                return False
        else:
            print(f"Seçenek '{option_name}' bulunamadı. 'show options' ile mevcut seçenekleri listeleyebilirsiniz.")
            return False