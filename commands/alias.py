# temel komut alias, bunu zsh shellindeki alias komutundan esinlenerek kodladım
import os
import json
import shutil 
from typing import Any, List, Dict, Optional
from core.command import Command
from core.shared_state import shared_state
from core.command_manager import CommandManager 
from core.cont import ALIASES_FILE, LEFT_PADDING, COL_SPACING, DEFAULT_TERMINAL_WIDTH
class Alias(Command):
    Name = "alias"
    Description = "Komutlar için kısayollar oluşturur, listeler ve siler."
    Category = "system"
    Aliases = []
    def __init__(self):
        super().__init__()
        self.completer_function = self._alias_completer 
    def _alias_completer(self, text: str, word_before_cursor: str) -> List[str]:
        parts = text.split()
        if len(parts) == 1 and text.endswith(' '): 
            return sorted(["add", "list", "remove"])
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            return sorted([cmd for cmd in ["add", "list", "remove"] if cmd.startswith(current_arg)])
        elif len(parts) == 3 and parts[1].lower() == "remove" and not text.endswith(' '): 
            current_alias_part = parts[2]
            all_aliases = shared_state.get_aliases().keys()
            return sorted([alias for alias in all_aliases if alias.startswith(current_alias_part)])
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        command_manager: CommandManager = shared_state.command_manager
        if not command_manager:
            print("CommandManager başlatılmamış.")
            return False
        if not args:
            print("Kullanım: alias <add|list|remove> [argümanlar]")
            return False
        subcommand = args[0].lower()
        if subcommand == "add":
            if len(args) < 3:
                print("Kullanım: alias add <yeni_alias_adı> <hedef_komut>")
                return False
            new_alias_name = args[1]
            target_command = " ".join(args[2:])
            return command_manager.add_alias(new_alias_name, target_command)
        elif subcommand == "list":
            return self._list_aliases(command_manager.get_aliases())
        elif subcommand == "remove":
            if len(args) < 2:
                print("Kullanım: alias remove <alias_adı>")
                return False
            alias_to_remove = args[1]
            return command_manager.remove_alias(alias_to_remove)
        else:
            print(f"Bilinmeyen 'alias' alt komutu: '{subcommand}'. Kullanım: alias <add|list|remove>")
            return False
    def _list_aliases(self, aliases: Dict[str, str]) -> bool:
        if not aliases:
            print(f"{' ' * LEFT_PADDING}Tanımlı alias bulunmamaktadır.")
            return True
        terminal_width = self._get_terminal_width()
        alias_header = "Alias"
        target_command_header = "Hedef Komut"
        max_alias_len = max(len(alias_name) for alias_name in aliases.keys()) if aliases else 0
        max_target_len = max(len(target_cmd) for target_cmd in aliases.values()) if aliases else 0
        max_alias_len = max(max_alias_len, len(alias_header))
        max_target_len = max(max_target_len, len(target_command_header))
        fixed_part_width = LEFT_PADDING + max_alias_len + COL_SPACING
        dynamic_max_target_len = terminal_width - fixed_part_width
        min_target_len = max(len(target_command_header), 10)
        if dynamic_max_target_len < min_target_len:
            dynamic_max_target_len = min_target_len
        print(f"\n{' ' * LEFT_PADDING}Kullanıcı Tanımlı Aliaslar")
        print(f"{' ' * LEFT_PADDING}{'=' * len('Kullanıcı Tanımlı Aliaslar')}")
        print(f"{' ' * LEFT_PADDING}{alias_header.ljust(max_alias_len)}{' ' * COL_SPACING}{target_command_header}")
        print(f"{' ' * LEFT_PADDING}{'-' * max_alias_len}{' ' * COL_SPACING}{'-' * len(target_command_header)}")
        for alias_name, target_cmd in sorted(aliases.items()):
            display_target_cmd = self._truncate_description(target_cmd, dynamic_max_target_len)
            print(f"{' ' * LEFT_PADDING}{alias_name.ljust(max_alias_len)}{' ' * COL_SPACING}{display_target_cmd}")
        return True
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