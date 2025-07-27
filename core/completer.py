# terminal arayüzünde otomatik tamamlama için lokal kütüphane. prompt-toolkit temelli
# birincil hedef komutlar ve onların otomatik tamamlaması.
from prompt_toolkit.completion import Completer, Completion # otomatik tamamlama inşaası için
from prompt_toolkit.document import Document # dökümantasyon için
from typing import List, Iterable, Optional, Tuple
from core.shared_state import shared_state
from core.command import Command # komut temel sınıfı
from core.module import BaseModule # modül temel sınıfı
class CLICompleter(Completer):
    def __init__(self, command_manager, module_manager):
        self.command_manager = command_manager # komut yönetimi için
        self.module_manager = module_manager # m modül yönetimi için
    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]: # otomatik tamamlama çağırıcı fonksiyon
        text_before_cursor = document.text_before_cursor
        words = text_before_cursor.split()
        if not text_before_cursor.strip():
            yield from self._get_command_completions("")
            return
        if text_before_cursor.strip().startswith('#'):
            return
        if len(words) == 1 and not text_before_cursor.endswith(' '):
            current_word = words[0]
            yield from self._get_command_completions(current_word)
        else:
            command_name = words[0].lower()
            resolved_command_name, is_alias = self.command_manager.resolve_command(command_name)
            if resolved_command_name:
                command_obj: Optional[Command] = self.command_manager.get_all_commands().get(resolved_command_name)
                if command_obj:
                    if command_obj.completer_function:
                        completions = command_obj.get_completions(text_before_cursor, document.get_word_before_cursor())
                        for comp in completions:
                            if isinstance(comp, Completion):
                                yield comp
                            else: 
                                word_len = len(document.get_word_before_cursor())
                                yield Completion(comp, start_position=-word_len)
                    else:
                        pass
            else:
                pass
    def _get_command_completions(self, current_word: str) -> Iterable[Completion]: # komutun otomatik tamamlamasını çekecek fonksiyon
        all_names = set(self.command_manager.get_all_commands().keys())
        all_aliases = self.command_manager.get_aliases()
        for alias, target_cmd in all_aliases.items():
            all_names.add(alias)
        for name in sorted(list(all_names)):
            if name.startswith(current_word):
                display_meta = ""
                if name in all_aliases:
                    display_meta = f"(alias for {all_aliases[name]})"
                elif name in self.command_manager.get_all_commands():
                    cmd_obj = self.command_manager.get_all_commands()[name]
                    display_meta = cmd_obj.Description
                yield Completion(name, start_position=-len(current_word), display_meta=display_meta)
    def _get_module_paths_completions(self, current_word: str) -> List[str]: # modül yolu otomatik tamamlaması
        module_paths = list(self.module_manager.get_all_modules().keys())
        return sorted([path for path in module_paths if path.startswith(current_word)])
    def _get_module_options_completions(self, current_word: str) -> List[str]: # set için option otomatik tamamlaması
        selected_module: Optional[BaseModule] = shared_state.get_selected_module()
        if selected_module:
            option_names = list(selected_module.get_options().keys())
            return sorted([name for name in option_names if name.startswith(current_word)])
        return []