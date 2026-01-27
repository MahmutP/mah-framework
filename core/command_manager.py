# komutları yönetmek ve framework için modöler amaçlı komut yazılmasını destekleyecek kütüphane
from pathlib import Path
import importlib.util
import json # veri tutma, oluşturma ve aliases.json da yazmak için kullanacağım.
from typing import Dict, Optional, List, Tuple, Callable
from core.command import Command # komut sınıfı import edildi
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
        self.commands_dir = Path(commands_dir) # "commands" klasörünün yolu
        self.commands: Dict[str, Command] = {} 
        self.aliases: Dict[str, str] = {} 
        self._ensure_aliases_file() # aliases.json daki alias'lar 
    def _ensure_aliases_file(self): # aliases.json import edilmesi ya da yenisi oluşturulmalı
        """Alias dosyası oluşturucu fonksiyon.
        """
        aliases_path = Path(ALIASES_FILE)
        if not aliases_path.exists():
            aliases_path.parent.mkdir(parents=True, exist_ok=True)
            with open(aliases_path, 'w', encoding='utf-8') as f:
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
        except PermissionError:
            print(f"Aliaslar kaydedilirken izin hatası: {ALIASES_FILE}")
            logger.exception("Alias dosyası yazma izni hatası")
        except IOError as e:
            print(f"Aliaslar kaydedilirken dosya hatası oluştu: {e}")
            logger.exception("Alias dosyası yazma hatası")
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
        if alias_name in self.aliases: # shared_state logic removed
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
        # Önce kullanıcı tanımlı aliasları yükle (böylece overwrite edilmezler)
        self.load_aliases()
        
        for file_path in self.commands_dir.glob('*.py'):
            if file_path.name == '__init__.py':
                continue
            command_name = file_path.stem  # Dosya adını uzantısız alır
            try: # obje olarak modül fonksiyonlarını çekmek için
                spec = importlib.util.spec_from_file_location(command_name, str(file_path))
                if spec is None:
                    print(f"Komut spesifikasyonu alınamadı: {file_path}")
                    continue
                command_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(command_module)
                for name, obj in command_module.__dict__.items():
                    if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command:
                        command_instance = obj()
                        self.commands[command_instance.Name] = command_instance 
                        for alias in command_instance.Aliases:
                            self.add_alias(alias, command_instance.Name) 
                        break 
            except SyntaxError as e:
                print(f"[bold red]Sözdizimi hatası:[/bold red] '{file_path.name}' dosyasında hata var.")
                logger.exception(f"Komut yüklenirken sözdizimi hatası '{file_path}'")
            except ImportError as e:
                print(f"[bold red]İçe aktarma hatası:[/bold red] '{file_path.name}' - {e}")
                logger.exception(f"Komut yüklenirken import hatası '{file_path}'")
            except AttributeError as e:
                print(f"[bold red]Öznitelik hatası:[/bold red] '{file_path.name}' - Komut sınıfı doğru tanımlanmamış.")
                logger.exception(f"Komut yüklenirken öznitelik hatası '{file_path}'")
            except Exception as e:
                print(f"[bold red]Beklenmeyen hata:[/bold red] '{file_path.name}' yüklenirken hata oluştu.")
                logger.exception(f"Komut yüklenirken beklenmeyen hata '{file_path}'")
        logger.info(f"{len(self.commands)} komut yüklendi") 
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
                except TypeError as e:
                    print(f"[bold red]Argüman hatası:[/bold red] '{resolved_command_name}' komutuna yanlış argüman verildi.")
                    logger.exception(f"Komut '{resolved_command_name}' yürütülürken TypeError")
                    return False
                except KeyboardInterrupt:
                    print("\nKomut kullanıcı tarafından kesildi.")
                    logger.info(f"Komut '{resolved_command_name}' kullanıcı tarafından kesildi")
                    return False
                except Exception as e:
                    print(f"[bold red]Kritik hata:[/bold red] '{resolved_command_name}' yürütülürken beklenmeyen hata.")
                    logger.exception(f"Komut '{resolved_command_name}' yürütülürken beklenmeyen hata")
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