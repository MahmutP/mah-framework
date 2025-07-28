from typing import Any, List
from core.command import Command
from rich import  print
from core.shared_state import shared_state
from core.module_manager import ModuleManager 
class Use(Command):
    Name = "use"
    Description = "Bir modülü adına göre seçer."
    Category = "module"
    Aliases = []
    def __init__(self):
        super().__init__()
        self.completer_function = self._use_completer 
    def _use_completer(self, text: str, word_before_cursor: str) -> List[str]:
        parts = text.split()
        if len(parts) == 1 and text.endswith(' '): 
            module_manager: ModuleManager = shared_state.module_manager
            if module_manager:
                return sorted(list(module_manager.get_all_modules().keys()))
            return []
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            module_manager: ModuleManager = shared_state.module_manager
            if module_manager:
                all_module_paths = list(module_manager.get_all_modules().keys())
                return sorted([path for path in all_module_paths if path.startswith(current_arg)])
            return []
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        if not args:
            print("Kullanım: use <modül_yolu>")
            return False
        module_path = args[0]
        module_manager: ModuleManager = shared_state.module_manager
        if not module_manager:
            print("ModuleManager başlatılmamış.")
            return False
        module_obj = module_manager.get_module(module_path)
        if module_obj:
            shared_state.set_selected_module(module_obj)
            print(f"Modül '{module_obj.Category}/{module_obj.Name}' seçildi.")
            return True
        else:
            print(f"Modül bulunamadı: '{module_path}'. 'show modules' ile mevcut modülleri listeleyebilirsiniz.")
            return False