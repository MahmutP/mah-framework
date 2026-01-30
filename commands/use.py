from typing import Any, List
from core.command import Command
from rich import  print
from core.shared_state import shared_state
from core.module_manager import ModuleManager 
from prompt_toolkit.completion import Completion

class Use(Command):
    """Modül seçmeye yarıyan komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name = "use"
    Description = "Bir modülü adına göre seçer."
    Category = "module"
    Aliases = []
    Usage = "use <kategori/modül_adı>"
    Examples = [
        "use exploit/vsftpd_234_backdoor",
        "use auxiliary/scanner/vsftpd_version",
        "use example/hash_generator",
        "use uncategorized/systeminfo_uncategorized"
    ]
    def __init__(self):
        """init fonksiyonu.
        """
        super().__init__()
        self.completer_function = self._use_completer 
    def _use_completer(self, text: str, word_before_cursor: str) -> List[Any]:
        """use komutu otomatik tamamlaması.

        Args:
            text (str): text girdisi.
            word_before_cursor (str): imlecin solundaki text.

        Returns:
            List[str]: otomatik tamamlama listesi.
        """
        parts = text.split()
        if len(parts) == 1 and text.endswith(' '): 
            module_manager: ModuleManager = shared_state.module_manager
            if module_manager:
                return sorted(list(module_manager.get_all_modules().keys()))
            return []
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            manager: ModuleManager = shared_state.module_manager
            if manager:
                all_module_paths = list(manager.get_all_modules().keys())
                matches = sorted([path for path in all_module_paths if path.startswith(current_arg)])
                # Completion objesi döndürerek start_position'ı manuel ayarlıyoruz.
                # Böylece "payloads/py" yazınca sadece "py" değil "payloads/py" tamamlanıyor.
                return [Completion(path, start_position=-len(current_arg)) for path in matches]
            return []
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalışınca çalışacak komut.

        Returns:
            bool: Başarılı olup olmadığının kontrolünü sağlayan sonuç.
        """
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