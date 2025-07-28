from typing import Any, List
from core.command import Command
from core.shared_state import shared_state
from core.module import BaseModule 
from rich import  print
class Set(Command):
    Name = "set"
    Description = "Seçili modülün seçeneklerini ayarlar."
    Category = "module"
    Aliases = []
    def __init__(self):
        super().__init__()
        self.completer_function = self._set_completer 
    def _set_completer(self, text: str, word_before_cursor: str) -> List[str]:
        parts = text.split()
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            return []
        options = selected_module.get_options()
        if len(parts) == 1 and text.endswith(' '): 
            return sorted(list(options.keys()))
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            return sorted([name for name in options.keys() if name.startswith(current_arg)])
        elif len(parts) >= 2 and text.endswith(' '): 
            return []
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
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