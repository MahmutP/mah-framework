from typing import Any, List
from core.command import Command
from core.shared_state import shared_state
from core.module import BaseModule 
from rich import  print
class Unset(Command):
    Name = "unset"
    Description = "Ayarlanmış option'u sıfırlamak (default hali) için kullanılan bir komuttur."
    Category = "module"
    Aliases = []
    def __init__(self):
        super().__init__()
        self.completer_function = self._unset_completer 
    def _unset_completer(self, text: str, word_before_cursor: str) -> List[str]:
        parts = text.split()
        if len(parts) == 1 and text.endswith(' '): 
            selected_module: BaseModule = shared_state.get_selected_module()
            if selected_module:
                return sorted(list(selected_module.get_options().keys()))
            return []
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            selected_module: BaseModule = shared_state.get_selected_module()
            if selected_module:
                all_option_names = list(selected_module.get_options().keys())
                return sorted([name for name in all_option_names if name.startswith(current_arg)])
            return []
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            print("Herhangi bir modül seçili değil. Lütfen önce 'use <modül_yolu>' komutunu kullanın.")
            return False
        if not args:
            print("Kullanım: unset <seçenek_adı>")
            return False
        option_name = args[0]
        options = selected_module.get_options()
        if option_name in options:
            option_obj = options[option_name]
            selected_module.set_option_value(option_name, None)
            print(f"Seçenek '{option_name}' sıfırlandı.")
            return True
        else:
            print(f"Seçenek '{option_name}' bulunamadı.")
            return False