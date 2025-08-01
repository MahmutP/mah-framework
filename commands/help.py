from typing import Any, List, Optional
import shutil 
from core.command import Command # temel komut yapısı/sınıfı
from core.shared_state import shared_state
from core.command_manager import CommandManager 
from core.cont import LEFT_PADDING, COL_SPACING, DEFAULT_TERMINAL_WIDTH # dökümantasyon çıktılarının daha güzel olması için
from rich import print
class Help(Command):
    Name = "help"
    Description = "Yardım menüsünü gösterir veya belirli bir komut hakkında bilgi verir."
    Category = "core"
    Aliases = ["?"]
    def __init__(self):
        super().__init__()
        self.completer_function = self._help_completer 
    def _help_completer(self, text: str, word_before_cursor: str) -> List[str]:
        parts = text.split()
        if len(parts) == 1 and text.endswith(' '): 
            all_commands = list(self.shared_state.get_commands().keys())
            return sorted(all_commands)
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            all_commands = list(self.shared_state.get_commands().keys())
            return sorted([cmd for cmd in all_commands if cmd.startswith(current_arg)])
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        command_manager: CommandManager = self.shared_state.command_manager 
        if not command_manager:
            print("CommandManager başlatılmamış.")
            return False
        if args:
            command_name = args[0].lower()
            resolved_command_name, is_alias = command_manager.resolve_command(command_name)
            if not resolved_command_name:
                print(f"'{command_name}' adında bir komut veya alias bulunamadı.")
                return False
            cmd_obj: Optional[Command] = command_manager.get_all_commands().get(resolved_command_name)
            if cmd_obj:
                print(f"\n  Komut: {cmd_obj.Name}")
                print(f"  Açıklama: {cmd_obj.Description}") 
                print(f"  Kategori: {cmd_obj.get_category_display_name()}")
                if cmd_obj.Aliases:
                    print(f"  Aliaslar: {', '.join(cmd_obj.Aliases)}")
                print("\n  Kullanım: (Henüz örnek kullanım bilgisi mevcut değil.)") 
            else:
                print(f"'{resolved_command_name}' komut objesi bulunamadı.")
            return True
        else:
            self._display_general_help(command_manager)
            return True
    def _display_general_help(self, command_manager: CommandManager):
        categorized_commands = command_manager.get_categorized_commands()
        terminal_width = self._get_terminal_width()
        cmd_header = "Komut"
        desc_header = "Açıklama"
        for category_display_name in sorted(categorized_commands.keys()):
            commands_in_category = categorized_commands[category_display_name]
            max_cmd_len = max(len(cmd_name) for cmd_name in commands_in_category.keys()) if commands_in_category else 0
            max_cmd_len = max(max_cmd_len, len(cmd_header)) 
            fixed_part_width = LEFT_PADDING + max_cmd_len + COL_SPACING
            dynamic_max_desc_len = terminal_width - fixed_part_width
            min_desc_len = max(len(desc_header), 10) 
            if dynamic_max_desc_len < min_desc_len:
                dynamic_max_desc_len = min_desc_len
            print(f"\n{category_display_name}")
            print("-" * len(category_display_name))
            print(f"{' ' * LEFT_PADDING}{cmd_header.ljust(max_cmd_len)}{' ' * COL_SPACING}{desc_header}")
            print(f"{' ' * LEFT_PADDING}{'-' * max_cmd_len}{' ' * COL_SPACING}{'-' * len(desc_header)}")
            for cmd_name, cmd_obj in sorted(commands_in_category.items()):
                description = cmd_obj.Description
                display_description = self._truncate_description(description, dynamic_max_desc_len)
                print(f"{' ' * LEFT_PADDING}{cmd_name.ljust(max_cmd_len)}{' ' * COL_SPACING}{display_description}")
        print("\nBir komut hakkında detaylı bilgi edinmek için `help <komut>` ifadesini kullanın.")
    def _get_terminal_width(self) -> int:
        try:
            return shutil.get_terminal_size().columns
        except OSError:
            print(f"Terminal genişliği alınamadı, varsayılan {DEFAULT_TERMINAL_WIDTH} kullanılıyor.")
            return DEFAULT_TERMINAL_WIDTH
    def _truncate_description(self, description: str, max_len: int) -> str:
        if len(description) > max_len and max_len > 3: 
            return description[:max_len - 3] + "..."
        return description
