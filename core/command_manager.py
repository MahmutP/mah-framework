# komutları yönetmek ve framework için modöler amaçlı komut yazılmasını destekleyecek kütüphane
import os
import importlib.util
import json # veri tutma, oluşturma ve aliases.json da yazmak için kullanacağım.
from typing import Dict, Optional, List, Tuple, Callable
from core.command import Command # komut sınıfı import edildi
from core.shared_state import shared_state
from core.cont import ALIASES_FILE, COMMAND_CATEGORIES # alias.json ve aliases.json ve komut katagorisi import edildi
from core import logger
from rich import print
class CommandManager:
    """Komut yönetim sınıfı
    """
    def __init__(self, commands_dir="commands"):
        """init fonksiyon.

        Args:
            commands_dir (str, optional): komutların bulunduğu dizin. Defaults to "commands".
        """
        self.commands_dir = commands_dir # "commands" klasörünün yolu
        self.commands: Dict[str, Command] = shared_state.get_commands() # komutları shared_state üzerinden dict olarak tanımlandı. 
        self.aliases: Dict[str, str] = shared_state.get_aliases() # komutların kendi içinde tanımladığı ve aliases.json daki alias'lar
        self._ensure_aliases_file() # aliases.sjon daki alias'lar 
    def _ensure_aliases_file(self): # aliases.json import edilmesi ya da yenisi oluşturulmalı
        """Alias dosyası oluşturucu fonksiyon.
        """
        if not os.path.exists(ALIASES_FILE):
            os.makedirs(os.path.dirname(ALIASES_FILE), exist_ok=True)
            with open(ALIASES_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
            print(f"Varsayılan alias dosyası oluşturuldu: {ALIASES_FILE}")
    def load_aliases(self): # bütün aliasların bir havuza import edilmesi
        """alias'ları yükleyen fonksiyon.
        """
        try:
            with open(ALIASES_FILE, 'r', encoding='utf-8') as f:
                loaded_aliases = json.load(f)
                self.aliases.clear() 
                for alias, target in loaded_aliases.items():
                    self.aliases[alias] = target
                    shared_state.add_alias(alias, target) 
            #print(f"{len(self.aliases)} alias yüklendi.")
        except FileNotFoundError:
            print(f"Alias dosyası bulunamadı: {ALIASES_FILE}. Yeni bir dosya oluşturulacak.")
            self._ensure_aliases_file()
        except json.JSONDecodeError as e:
            print(f"Alias dosyası okunurken hata oluştu '{ALIASES_FILE}': {e}. Dosya bozuk olabilir.")
            self.aliases.clear() 
    def save_aliases(self):# alias kaydedece fonksiyon
        """aliasları kaydeden fonksiyon.
        """
        try:
            with open(ALIASES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.aliases, f, indent=4)
            #print(f"Aliaslar dosyaya kaydedildi: {ALIASES_FILE}")
        except Exception as e:
            print(f"Aliaslar kaydedilirken hata oluştu: {e}")
    def add_alias(self, alias_name: str, target_command: str) -> bool: # framework içi ve alias komutu için alias ekleme fonksiyonum
        """Alias eklemeye yarıyan fonksiyon

        Args:
            alias_name (str): alias komutu.
            target_command (str): hedef komut.

        Returns:
            bool: Başarılı olup olmadığının çıktısı.
        """
        if alias_name in self.commands or alias_name in self.aliases:
            #print(f"'{alias_name}' zaten bir komut veya alias olarak mevcut.")
            return False
        self.aliases[alias_name] = target_command
        shared_state.add_alias(alias_name, target_command)
        self.save_aliases()
        #print(f"Alias '{alias_name}' -> '{target_command}' eklendi.")
        return True
    def remove_alias(self, alias_name: str) -> bool: # alias silecek
        """Alias silici fonksiyon

        Args:
            alias_name (str): alias adı.

        Returns:
            bool: başarılı olup olmadığının kontrolü.
        """
        if shared_state.remove_alias(alias_name):
            if alias_name in self.aliases: 
                del self.aliases[alias_name]
            self.save_aliases()
            #(f"Alias '{alias_name}' kaldırıldı.")
            return True
        #(f"Alias '{alias_name}' bulunamadı.")
        return False
    def get_aliases(self) -> Dict[str, str]: # framework içi alias çekmek için
        """Alias çekmeye yarıyan fonksiyon

        Returns:
            Dict[str, str]: alias'ların olduğu liste çıktısı.
        """
        return self.aliases
    def load_commands(self): # komut yüklemek için
        """Komutları yüklemeye yarıyan ana fonksiyon.
        """
        self.commands.clear() 
        #("Komutlar yükleniyor...")
        for file in os.listdir(self.commands_dir):
            if file.endswith(".py") and file != "__init__.py": # sadece python dilini destekliyor şimdilik
                command_name = file[:-3] # dosya uzantısı
                module_path = os.path.join(self.commands_dir, file) # "modules" klasörünün yoluna girmek için
                try: # obje olarak modül fonksiyonlarını çekmek için
                    spec = importlib.util.spec_from_file_location(command_name, module_path)
                    if spec is None:
                        print(f"Komut spesifikasyonu alınamadı: {module_path}")
                        continue
                    command_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(command_module)
                    for name, obj in command_module.__dict__.items():
                        if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command:
                            command_instance = obj()
                            self.commands[command_instance.Name] = command_instance
                            shared_state.add_command(command_instance.Name, command_instance) 
                            for alias in command_instance.Aliases:
                                self.add_alias(alias, command_instance.Name) 
                            #(f"Komut yüklendi: {command_instance.Name} (Kategori: {command_instance.Category})")
                            break 
                except Exception as e:
                    print(f"Komut yüklenirken hata oluştu '{module_path}': {e}")
                    logger.error(f"Komut yüklenirken hata oluştu '{module_path}': {e}")
        logger.info(f"{len(self.commands)} komut yüklendi")
        self.load_aliases() 
    def resolve_command(self, command_input: str) -> Tuple[Optional[str], bool]: # komut çözücü
        """Komut çözmeye yarıyan fonksiyon.

        Args:
            command_input (str): Komut girdisi.

        Returns:
            Tuple[Optional[str], bool]: değiştilemez çıktı ve başarılı olup olmadığının kontrolü.
        """
        if command_input in self.commands:
            return command_input, False 
        elif command_input in self.aliases:
            return self.aliases[command_input], True 
        return None, False 
    def execute_command(self, command_line: str) -> bool:# komut çalıştırıcı
        """Kullanıcının girdiği tam komut satırını ayrıştırır, aliasları çözer ve hedef komutu yürütür.

        Args:
            command_line (str): Kullanıcı tarafından terminale girilen komut ve argümanları içeren tam dize.

        Returns:
            bool: Komutun başarıyla yürütülüp yürütülmediğini (True) veya bir hata oluştuğunu (False) belirten değer.
        """
        parts = command_line.strip().split(maxsplit=1)
        if not parts:
            return False
        command_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []
        resolved_command_name, is_alias = self.resolve_command(command_name)
        if resolved_command_name:
            if is_alias:# alias mı kontrol edilecek
                full_target_command_line = self.aliases[command_name]
                if len(parts) > 1:
                    full_target_command_line += " " + parts[1]
                target_parts = full_target_command_line.strip().split(maxsplit=1)
                resolved_command_name = target_parts[0].lower()
                args = target_parts[1].split() if len(target_parts) > 1 else []
            command_obj = self.commands.get(resolved_command_name)
            if command_obj:
                try:
                    logger.info(f"Komut çalıştırıldı: {resolved_command_name}")
                    return command_obj.execute(*args)
                except Exception as e:
                    print(f"Komut '{resolved_command_name}' yürütülürken kritik hata oluştu: {e}")
                    logger.error(f"Komut '{resolved_command_name}' yürütülürken hata: {e}")
                    return False
            else:
                print(f"'{resolved_command_name}' komutu bulunamadı.")
                logger.warning(f"Komut bulunamadı: {resolved_command_name}")
                return False
        else:
            print(f"'{command_name}' bilinmeyen bir komut veya alias.")
            logger.warning(f"Bilinmeyen komut: {command_name}")
            return False
    def get_all_commands(self) -> Dict[str, Command]: # bütün komutları çekmek için
        """Bütün komutları çekmeye yarıyan fonksiyon.

        Returns:
            Dict[str, Command]: Bütün komutların listesi.
        """
        return self.commands
    def get_categorized_commands(self) -> Dict[str, Dict[str, Command]]: # karagorizasyon fonksiyonum
        """Kategorize edilimiş komutları çekmeye yarıyan fonksiyon.

        Returns:
            Dict[str, Dict[str, Command]]: katagorize edilmiş komutların çıkışı.
        """
        categorized_commands = {}
        for cmd_name, cmd_obj in self.commands.items():
            category_display_name = cmd_obj.get_category_display_name()
            if category_display_name not in categorized_commands:
                categorized_commands[category_display_name] = {}
            categorized_commands[category_display_name][cmd_name] = cmd_obj
        return categorized_commands
    def get_command_completer_function(self, command_name: str) -> Optional[Callable]: # komut otomatik tamamlama için işleyici
        """Komutların otomatik tamamlamasını çekmeye yarıyan fonksiyon.

        Args:
            command_name (str): komut ismi

        Returns:
            Optional[Callable]: Komutun otomatik tamamlama fonksiyonu.
        """
        command_obj = self.commands.get(command_name)
        if command_obj:
            return command_obj.completer_function
        return None