from typing import Any, List, Optional
import shutil 
from core.command import Command
from core.shared_state import shared_state
from core.module_manager import ModuleManager 
from core.cont import LEFT_PADDING, COL_SPACING, TAB_SPING, DEFAULT_TERMINAL_WIDTH
from core.option import Option 
from rich import  print
class Show(Command):
    """Bilgilendirmeleredinmeyi sağlayan komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name = "show"
    Description = "Çeşitli verileri (modüller, seçenekler) listeler."
    Category = "core" 
    Aliases = []
    Usage = "show <modules|options|info>"
    Examples = [
        "show modules           # Tüm modülleri listeler",
        "show options           # Seçili modülün seçeneklerini gösterir",
        "show info              # Seçili modül hakkında detaylı bilgi verir"
    ]
    def __init__(self):
        super().__init__()
        self.completer_function = self._show_completer 
    def _show_completer(self, text: str, word_before_cursor: str) -> List[str]:
        """show komutunun otomatik tamamlaması.

        Args:
            text (str): text girdisi.
            word_before_cursor (str): imlecin solundaki text.

        Returns:
            List[str]: otomatik tamamlama listesi.
        """
        parts = text.split()
        if len(parts) == 1 and text.endswith(' '): 
            return sorted(["info", "modules", "options"])
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            return sorted([cmd for cmd in ["info", "modules", "options"] if cmd.startswith(current_arg)])
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalışınca çalışacak fonksiyon.

        Returns:
            bool: başarılı olup olmadığını kontrol çıktısı
        """
        if not args:
            print("Kullanım: show <modules|options|info>")
            return False
        subcommand = args[0].lower()
        module_manager: ModuleManager = shared_state.module_manager 
        if not module_manager:
            print("ModuleManager başlatılmamış.")
            return False
        if subcommand == "modules":
            return self._show_modules(module_manager)
        elif subcommand == "options":
            return self._show_options()
        elif subcommand == "info":
            return self._show_info()
        else:
            print(f"Bilinmeyen 'show' alt komutu: '{subcommand}'. Kullanım: show <modules|options|info>")
            return False
    def _show_modules(self, module_manager: ModuleManager) -> bool:
        """Show modules komutunun çıktısını sağlayan fonksiyon.

        Args:
            module_manager (ModuleManager): Modül yönemeyi sağlayan yapı

        Returns:
            bool: başarılı olup olmadığının kontolü
        """
        categorized_modules = module_manager.get_modules_by_category()
        terminal_width = self._get_terminal_width()
        module_header = "Module"
        desc_header = "Description"
        if not categorized_modules:
            print("Yüklü modül bulunmamaktadır.")
            return True
        for category_display_name in sorted(categorized_modules.keys()):
            modules_in_category = categorized_modules[category_display_name]
            max_module_path_len = max(len(path) for path in modules_in_category.keys()) if modules_in_category else 0
            max_module_path_len = max(max_module_path_len, len(module_header)) 
            fixed_part_width = LEFT_PADDING + max_module_path_len + (2 * TAB_SPING)
            dynamic_max_desc_len = terminal_width - fixed_part_width
            min_desc_len = max(len(desc_header), 10) 
            if dynamic_max_desc_len < min_desc_len:
                dynamic_max_desc_len = min_desc_len
            print(f"\n{category_display_name}")
            print("-" * len(category_display_name))
            print(f"{' ' * LEFT_PADDING}{module_header.ljust(max_module_path_len)}{' ' * (2 * TAB_SPING)}{desc_header}")
            print(f"{' ' * LEFT_PADDING}{'-' * max_module_path_len}{' ' * (2 * TAB_SPING)}{'-' * len(desc_header)}")
            for module_path, module_obj in sorted(modules_in_category.items()):
                description = module_obj.Description
                display_description = self._truncate_description(description, dynamic_max_desc_len)
                print(f"{' ' * LEFT_PADDING}{module_path.ljust(max_module_path_len)}{' ' * (2 * TAB_SPING)}{display_description}")
        return True
    def _show_options(self) -> bool:
        """show options komutunun çıktısını sağlayan komut.

        Returns:
            bool: başarılı olup olmadığının kontrolünü sağlayan çıktı.
        """
        selected_module = shared_state.get_selected_module()
        if not selected_module:
            print("Herhangi bir modül seçili değil. Lütfen önce 'use <modül_yolu>' komutunu kullanın.")
            return False
        options: dict[str, Option] = selected_module.get_options()
        if not options:
            print(f"Seçili modül '{selected_module.Name}' için ayarlanabilir seçenek bulunmamaktadır.")
            return True
        terminal_width = self._get_terminal_width()
        option_header = "Option"
        value_header = "Current Value"
        required_header = "Required"
        description_header = "Description"
        max_option_name_len = max(len(name) for name in options.keys())
        max_value_len = max(len(str(opt.value)) for opt in options.values())
        max_option_name_len = max(max_option_name_len, len(option_header))
        max_value_len = max(max_value_len, len(value_header))
        max_required_len = max(len("Yes"), len("No"), len(required_header)) 
        fixed_part_width = (
            LEFT_PADDING +
            max_option_name_len + COL_SPACING +
            max_value_len + COL_SPACING +
            max_required_len + COL_SPACING
        )
        dynamic_max_desc_len = terminal_width - fixed_part_width
        min_desc_len = max(len(description_header), 10)
        if dynamic_max_desc_len < min_desc_len:
            dynamic_max_desc_len = min_desc_len
        print(f"\n  Seçili Modül: {selected_module.Name}")
        print("-" * (len(selected_module.Name) + 16)) 
        print(f"{' ' * LEFT_PADDING}{option_header.ljust(max_option_name_len)}{' ' * COL_SPACING}"
              f"{value_header.ljust(max_value_len)}{' ' * COL_SPACING}"
              f"{required_header.ljust(max_required_len)}{' ' * COL_SPACING}"
              f"{description_header}")
        print(f"{' ' * LEFT_PADDING}{'-' * max_option_name_len}{' ' * COL_SPACING}"
              f"{'-' * max_value_len}{' ' * COL_SPACING}"
              f"{'-' * max_required_len}{' ' * COL_SPACING}"
              f"{'-' * len(description_header)}")
        for name, opt in options.items():
            req_status = "Yes" if opt.required else "No"
            display_description = self._truncate_description(opt.description, dynamic_max_desc_len)
            print(f"{' ' * LEFT_PADDING}{name.ljust(max_option_name_len)}{' ' * COL_SPACING}"
                  f"{str(opt.value).ljust(max_value_len)}{' ' * COL_SPACING}"
                  f"{req_status.ljust(max_required_len)}{' ' * COL_SPACING}"
                  f"{display_description}")
        return True
    def _get_terminal_width(self) -> int:
        """terminal genişliğini elde etmeyi sağlayan fonksiyon.

        Returns:
            int: terminal genişliğinin değeri.
        """
        try:
            return shutil.get_terminal_size().columns
        except OSError:
            print(f"Terminal genişliği alınamadı, varsayılan {DEFAULT_TERMINAL_WIDTH} kullanılıyor.")
            return DEFAULT_TERMINAL_WIDTH
    def _truncate_description(self, description: str, max_len: int) -> str:
        """Metin veya komut dizesini, belirlenen maksimum karaktere kısaltır ve sonuna '...' ekler.

        Args:
            description (str): Kısaltılacak olan orijinal metin dizesi.
            max_len (int): Metnin alabileceği maksimum toplam karakter uzunluğu (üç nokta dahil).

        Returns:
            str: Kısaltılmış (veya orijinal uzunlukta ise orijinal) metin dizesi.
        """
        if len(description) > max_len and max_len > 3: 
            return description[:max_len - 3] + "..."
        return description
    
    def _show_info(self) -> bool:
        """show info alt komutu - info komutunu çağırır.
        
        Kod tekrarından kaçınmak için Info komutunu import edip çalıştırır.
        
        Returns:
            bool: Başarılı olup olmadığı
        """
        from commands.info import Info
        info_cmd = Info()
        return info_cmd.execute()