import os
import re
import shutil 
from typing import Any, List, Dict, Optional
from core.command import Command
from core.shared_state import shared_state
from core.module_manager import ModuleManager 
from core.module import BaseModule 
from core.cont import LEFT_PADDING, COL_SPACING, DEFAULT_TERMINAL_WIDTH
class ModuleSearcher:
    def __init__(self, module_manager: ModuleManager):
        self.module_manager = module_manager
    def search(self, term: str) -> List[Dict[str, Any]]:
        matching_modules = []
        term_lower = term.lower()
        all_modules: Dict[str, BaseModule] = self.module_manager.get_all_modules()
        for module_path, module_obj in all_modules.items():
            search_fields = {
                "name": module_obj.Name,
                "description": module_obj.Description,
                "author": module_obj.Author,
                "category": module_obj.Category,
                "path": module_path 
            }
            found_in_fields = {}
            for field_name, field_value in search_fields.items():
                if term_lower in str(field_value).lower():
                    found_in_fields[field_name] = field_value
            if found_in_fields:
                matching_modules.append({
                    "path": module_path,
                    "name": module_obj.Name,
                    "description": module_obj.Description,
                    "author": module_obj.Author,
                    "category": module_obj.Category,
                    "matches": found_in_fields 
                })
        return matching_modules
class Search(Command):
    Name = "search"
    Description = "Modülleri arar."
    Category = "core"
    Aliases = []
    def __init__(self):
        super().__init__()
        self.completer_function = self._search_completer 
    def _search_completer(self, text: str, word_before_cursor: str) -> List[str]:
        parts = text.split()
        if len(parts) == 1 and text.endswith(' '): 
            return []
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        if not args:
            print("Kullanım: search <arama_terimi>")
            return False
        search_term = " ".join(args)
        module_manager: ModuleManager = shared_state.module_manager
        if not module_manager:
            print("ModuleManager başlatılmamış.")
            return False
        searcher = ModuleSearcher(module_manager)
        results = searcher.search(search_term)
        if not results:
            print("Eşleşen modül bulunamadı.")
            return True
        self._display_search_results(results, search_term)
        return True
    def _display_search_results(self, results: List[Dict[str, Any]], search_term: str):
        terminal_width = self._get_terminal_width()
        path_header = "Path"
        name_header = "Name"
        description_header = "Description"
        author_header = "Author"
        category_header = "Category"
        max_path_len = max(len(r["path"]) for r in results)
        max_name_len = max(len(r["name"]) for r in results)
        max_author_len = max(len(r["author"]) for r in results)
        max_category_len = max(len(r["category"]) for r in results)
        max_path_len = max(max_path_len, len(path_header))
        max_name_len = max(max_name_len, len(name_header))
        max_author_len = max(max_author_len, len(author_header))
        max_category_len = max(max_category_len, len(category_header))
        fixed_part_width = (
            LEFT_PADDING +
            max_path_len + COL_SPACING +
            max_name_len + COL_SPACING +
            max_author_len + COL_SPACING +
            max_category_len + COL_SPACING
        )
        dynamic_max_desc_len = terminal_width - fixed_part_width
        min_desc_len = max(len(description_header), 10)
        if dynamic_max_desc_len < min_desc_len:
            dynamic_max_desc_len = min_desc_len
        print("\nEşleşen Modüller:")
        print(f"{' ' * LEFT_PADDING}{path_header.ljust(max_path_len)}{' ' * COL_SPACING}"
              f"{name_header.ljust(max_name_len)}{' ' * COL_SPACING}"
              f"{description_header.ljust(dynamic_max_desc_len)}{' ' * COL_SPACING}" 
              f"{author_header.ljust(max_author_len)}{' ' * COL_SPACING}"
              f"{category_header.ljust(max_category_len)}")
        print(f"{' ' * LEFT_PADDING}{'-' * max_path_len}{' ' * COL_SPACING}"
              f"{'-' * max_name_len}{' ' * COL_SPACING}"
              f"{'-' * dynamic_max_desc_len}{' ' * COL_SPACING}"
              f"{'-' * max_author_len}{' ' * COL_SPACING}"
              f"{'-' * max_category_len}")
        for result in results:
            path = result["path"]
            name = result["name"]
            description = result["description"]
            author = result["author"]
            category = result["category"]
            display_description = self._truncate_and_highlight(description, search_term, dynamic_max_desc_len)
            display_path = self._highlight_text(path, search_term)
            display_name = self._highlight_text(name, search_term)
            display_author = self._highlight_text(author, search_term)
            display_category = self._highlight_text(category, search_term)
            print(f"{' ' * LEFT_PADDING}{display_path.ljust(max_path_len + self._get_ansi_len_diff(display_path))}{' ' * COL_SPACING}"
                  f"{display_name.ljust(max_name_len + self._get_ansi_len_diff(display_name))}{' ' * COL_SPACING}"
                  f"{display_description.ljust(dynamic_max_desc_len + self._get_ansi_len_diff(display_description))}{' ' * COL_SPACING}"
                  f"{display_author.ljust(max_author_len + self._get_ansi_len_diff(display_author))}{' ' * COL_SPACING}"
                  f"{display_category.ljust(max_category_len + self._get_ansi_len_diff(display_category))}")
    def _get_terminal_width(self) -> int:
        try:
            return shutil.get_terminal_size().columns
        except OSError:
            print(f"Terminal genişliği alınamadı, varsayılan {DEFAULT_TERMINAL_WIDTH} kullanılıyor.")
            return DEFAULT_TERMINAL_WIDTH
    def _truncate_and_highlight(self, text: str, term: str, max_len: int) -> str:
        highlighted_text = self._highlight_text(text, term)
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', highlighted_text)
        if len(clean_text) > max_len and max_len > 3:
            truncated_clean_text = clean_text[:max_len - 3] + "..."
            return self._highlight_text(truncated_clean_text, term)
        return highlighted_text
    def _highlight_text(self, text: str, term: str) -> str:
        term_pattern = re.compile(re.escape(term), re.IGNORECASE)
        return term_pattern.sub(lambda match: f"\033[91m{match.group(0)}\033[0m", text)
    def _get_ansi_len_diff(self, text: str) -> int:
        return len(text) - len(re.sub(r'\x1b\[[0-9;]*m', '', text))