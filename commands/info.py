# temel komut info, modül hakkında dökümantasyonu ekrana basacak
from typing import Any
from core.command import Command
from core.shared_state import shared_state
from core.option import Option 
from rich import  print
class Info(Command):
    Name = "info"
    Description = "Seçili modül bilgilerini gösterir."
    Category = "module"
    Aliases = [] 
    def execute(self, *args: str, **kwargs: Any) -> bool:
        selected_module = shared_state.get_selected_module()
        if not selected_module:
            print("Herhangi bir modül seçili değil. Lütfen önce 'use <modül_yolu>' komutunu kullanın.")
            return False
        print(f"Modül Bilgileri: {selected_module.Name}")
        print("-" * (len(selected_module.Name) + 16)) 
        print(f"  Ad:          {selected_module.Name}")
        print(f"  Açıklama:    {selected_module.Description}")
        print(f"  Yazar:       {selected_module.Author}")
        print(f"  Kategori:    {selected_module.Category}")
        print("\n  Seçenekler:")
        options: dict[str, Option] = selected_module.get_options()
        if options:
            max_option_name_len = max(len(name) for name in options.keys()) if options else 0
            max_value_len = max(len(str(opt.value)) for opt in options.values()) if options else 0
            option_header = "Seçenek"
            current_value_header = "Mevcut Değer"
            required_header = "Zorunlu"
            description_header = "Açıklama"
            min_option_name_width = max(len(option_header), max_option_name_len)
            min_value_width = max(len(current_value_header), max_value_len)
            min_required_width = max(len(required_header), len("Evet"), len("Hayır"))
            terminal_width = shared_state.console_instance.get_terminal_width() if hasattr(shared_state, 'console_instance') else 120
            fixed_width_part = (
                4 + 
                min_option_name_width + 4 + 
                min_value_width + 4 + 
                min_required_width + 4 
            )
            print(f"    {option_header.ljust(min_option_name_width)}{' ' * 4}"
                  f"{current_value_header.ljust(min_value_width)}{' ' * 4}"
                  f"{required_header.ljust(min_required_width)}{' ' * 4}"
                  f"{description_header}")
            print(f"    {'-' * min_option_name_width}{' ' * 4}"
                  f"{'-' * min_value_width}{' ' * 4}"
                  f"{'-' * min_required_width}{' ' * 4}"
                  f"{'-' * len(description_header)}") 
            for name, opt in options.items():
                req_status = "Evet" if opt.required else "Hayır"
                print(f"    {name.ljust(min_option_name_width)}{' ' * 4}"
                      f"{str(opt.value).ljust(min_value_width)}{' ' * 4}"
                      f"{req_status.ljust(min_required_width)}{' ' * 4}"
                      f"{opt.description}")
        else:
            print("    Bu modülün ayarlanabilir seçeneği bulunmamaktadır.")
        return True