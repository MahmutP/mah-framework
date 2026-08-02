# Bu modül, framework içindeki komutların yüklenmesi, yönetilmesi ve çalıştırılmasından sorumludur.
# Komutların dinamik olarak yüklenmesi, alias (takma ad) yönetimi ve komut yürütme akışı burada kontrol edilir.

from __future__ import annotations

import ast
import importlib.util
import json  # Alias'ları JSON formatında okumak ve yazmak için kullanılır.
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich import print

from core import logger
from core.command import Command  # Temel Komut sınıfı

# Sabitler: Alias dosya yolu ve komut kategorileri
from core.cont import ALIASES_FILE
from core.hooks import HookType
from core.plugin_manager import PluginManager as PluginManagerType
from core.shared_state import shared_state


@dataclass
class CommandMeta:
    name: str
    description: str
    category: str
    aliases: list[str] = field(default_factory=list)
    usage: str = ""
    examples: list[str] = field(default_factory=list)
    file_path: str = ""
    class_name: str = ""


def _ast_const(node: ast.AST | None) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _ast_str_list(node: ast.AST | None) -> list[str]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return []
    out: list[str] = []
    for elt in node.elts:
        val = _ast_const(elt)
        if isinstance(val, str):
            out.append(val)
    return out


def extract_command_meta(source: str, file_path: Path) -> CommandMeta | None:
    """Command alt sınıfı metadata'sını AST ile çıkarır (exec yok)."""
    if "Command" not in source:
        return None
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return None

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.append(base.attr)
        if "Command" not in base_names:
            continue

        fields: dict[str, Any] = {
            "Name": file_path.stem,
            "Description": "",
            "Category": "core",
            "Aliases": [],
            "Usage": "",
            "Examples": [],
        }
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in fields:
                        if target.id in ("Aliases", "Examples"):
                            fields[target.id] = _ast_str_list(item.value)
                        else:
                            val = _ast_const(item.value)
                            if isinstance(val, str):
                                fields[target.id] = val
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.target.id in fields and item.value is not None:
                    if item.target.id in ("Aliases", "Examples"):
                        fields[item.target.id] = _ast_str_list(item.value)
                    else:
                        val = _ast_const(item.value)
                        if isinstance(val, str):
                            fields[item.target.id] = val

        return CommandMeta(
            name=fields["Name"],
            description=fields["Description"],
            category=fields["Category"],
            aliases=list(fields["Aliases"]),
            usage=fields["Usage"],
            examples=list(fields["Examples"]),
            file_path=str(file_path),
            class_name=node.name,
        )
    return None


class CommandStub(Command):
    """help/completer için hafif stub; execute anında gerçek komut yüklenir."""

    def __init__(self, meta: CommandMeta, manager: CommandManager) -> None:
        self.Name = meta.name
        self.Description = meta.description
        self.Category = meta.category
        self.Aliases = list(meta.aliases)
        self.Usage = meta.usage
        self.Examples = list(meta.examples)
        self._meta = meta
        self._manager = manager
        self._is_stub = True
        self.shared_state = shared_state
        self.completer_function = None

    def execute(self, *args: str, **kwargs: Any) -> bool:
        real = self._manager.ensure_loaded(self.Name)
        if real is None:
            print(f"[bold red]Komut yüklenemedi:[/bold red] {self.Name}")
            return False
        return bool(real.execute(*args, **kwargs))

    def get_completions(self, text: str, word_before_cursor: str) -> list[str]:
        real = self._manager.ensure_loaded(self.Name)
        if real is None:
            return []
        return real.get_completions(text, word_before_cursor)


class CommandManager:
    """
    Komut Yönetim Sınıfı (CommandManager).

    Bu sınıfın temel görevleri:
    1. Belirtilen dizindeki (varsayılan: 'commands') komut dosyalarını tarayıp yüklemek.
    2. Komutlara ait alias'ları (kısa yolları) yönetmek (ekleme, silme, kaydetme).
    3. Kullanıcıdan gelen metin girdisini ayrıştırıp ilgili komutu çalıştırmak.
    """

    def __init__(
        self,
        commands_dir: str = "commands",
        plugin_manager: PluginManagerType | None = None,
        context: Any = None,
    ) -> None:
        """
        CommandManager başlatıcı metod.

        Args:
            commands_dir (str, optional): Komut dosyalarının bulunduğu dizin yolu. Varsayılan: "commands".
            plugin_manager (PluginManager | None, optional): DI ile enjekte edilen plugin yöneticisi.
            context (Any, optional): AppContext örneği (DI için).
        """
        self.commands_dir = Path(commands_dir)  # Komutların aranacağı dizin
        self.commands: dict[
            str, Command
        ] = {}  # Yüklenen komut nesnelerini tutan sözlük (İsim -> Obje)
        self.aliases: dict[
            str, str
        ] = {}  # Yüklenen alias'ları tutan sözlük (Alias -> Hedef Komut)
        self._plugin_manager = plugin_manager
        self._context = context
        self._completion_names_cache: list[str] | None = None
        # Alias dosyasının varlığından emin ol, yoksa oluştur.
        self._ensure_aliases_file()

    @property
    def plugin_manager(self) -> Any:
        if self._plugin_manager:
            return self._plugin_manager
        if self._context and hasattr(self._context, "plugin_manager") and self._context.plugin_manager:
            return self._context.plugin_manager
        return shared_state.plugin_manager

    def _invalidate_completion_cache(self) -> None:
        self._completion_names_cache = None

    def get_completion_names(self) -> list[str]:
        """Komut + alias isimlerinin sıralı anlık görüntüsü."""
        if self._completion_names_cache is None:
            names = set(self.commands.keys())
            names.update(self.aliases.keys())
            self._completion_names_cache = sorted(names)
        return self._completion_names_cache

    def _ensure_aliases_file(self) -> None:
        """
        Alias dosyasının (genellikle aliases.json) diskte var olup olmadığını kontrol eder.
        Eğer dosya yoksa, boş bir JSON dosyası oluşturur.
        Bu, uygulamanın ilk çalıştırılmasında dosya bulunamadı hatalarını önler.
        """
        aliases_path = Path(ALIASES_FILE)
        if not aliases_path.exists():
            # Dosyanın ebeveyn klasörlerini de gerekirse oluştur.
            aliases_path.parent.mkdir(parents=True, exist_ok=True)
            with open(aliases_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)  # Boş bir JSON objesi yaz.
            print(f"Varsayılan alias dosyası oluşturuldu: {ALIASES_FILE}")

    def load_aliases(self) -> None:
        """
        Alias dosyasını okur ve belleğe yükler.
        Bu metod, uygulamanın başlangıcında veya alias'lar diskten tekrar okunmak istendiğinde çağrılır.
        """
        try:
            with open(ALIASES_FILE, encoding="utf-8") as f:
                loaded_aliases = json.load(f)
                self.aliases.clear()  # Mevcut hafızadaki aliasları temizle
                for alias, target in loaded_aliases.items():
                    self.aliases[alias] = target
            # Başarılı yükleme sonrası loglanabilir veya sessiz geçilebilir.
            # print(f"{len(self.aliases)} alias yüklendi.")
        except FileNotFoundError:
            # Dosya bir şekilde silindiyse tekrar oluşturmayı dener.
            print(
                f"Alias dosyası bulunamadı: {ALIASES_FILE}. Yeni bir dosya oluşturulacak."
            )
            self._ensure_aliases_file()
        except json.JSONDecodeError as e:
            # json dosyası bozuk formatta ise hata verir ve alias listesini temizler.
            print(
                f"Alias dosyası okunurken hata oluştu '{ALIASES_FILE}': {e}. Dosya bozuk olabilir."
            )
            self.aliases.clear()

    def save_aliases(self) -> None:
        """
        Mevcut alias listesini JSON dosyasına kaydeder.
        Alias eklendiğinde veya silindiğinde bu metod çağrılmalıdır.
        """
        try:
            with open(ALIASES_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    self.aliases, f, indent=4
                )  # Okunabilir (indent=4) formatta kaydet.
            # print(f"Aliaslar dosyaya kaydedildi: {ALIASES_FILE}")
        except PermissionError:
            print(f"Aliaslar kaydedilirken izin hatası: {ALIASES_FILE}")
            logger.exception("Alias dosyası yazma izni hatası")
        except OSError as e:
            print(f"Aliaslar kaydedilirken dosya hatası oluştu: {e}")
            logger.exception("Alias dosyası yazma hatası")

    def add_alias(
        self, alias_name: str, target_command: str, *, persist: bool = True
    ) -> bool:
        """
        Yeni bir alias ekler.

        Args:
            alias_name: Kullanıcının kullanacağı kısa ad (örn: 'ls').
            target_command: Alias'ın çalıştıracağı asıl komut.
            persist: True ise disk dosyasına yazar (kullanıcı alias'ları).
                     False ise yalnızca belleğe ekler (built-in alias yükleme).
        """
        if alias_name in self.commands or alias_name in self.aliases:
            return False

        self.aliases[alias_name] = target_command
        self._invalidate_completion_cache()
        if persist:
            self.save_aliases()
        return True

    def remove_alias(self, alias_name: str) -> bool:
        """Mevcut bir alias'ı siler ve dosyayı günceller."""
        if alias_name in self.aliases:
            del self.aliases[alias_name]
            self._invalidate_completion_cache()
            self.save_aliases()
            return True
        return False

    def get_aliases(self) -> dict[str, str]:
        """
        Tüm aktif alias'ların listesini döndürür.

        Returns:
            Dict[str, str]: Alias -> Hedef Komut eşleşmeleri.
        """
        return self.aliases

    def load_commands(self) -> None:
        """
        Commands dizinindeki komutları AST ile indeksler (lazy load).
        Gerçek import yalnızca execute / completer sırasında yapılır.
        """
        self.commands.clear()
        self.load_aliases()

        for file_path in self.commands_dir.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
            try:
                source = file_path.read_text(encoding="utf-8")
                meta = extract_command_meta(source, file_path)
                if meta is None:
                    continue
                key = meta.name.lower()
                self.commands[key] = CommandStub(meta, self)
                for alias in meta.aliases:
                    self.add_alias(alias.lower(), meta.name, persist=False)
            except SyntaxError:
                print(
                    f"[bold red]Sözdizimi hatası:[/bold red] '{file_path.name}' dosyasında hata var."
                )
                logger.exception(f"Komut taranırken sözdizimi hatası '{file_path}'")
            except Exception:
                print(
                    f"[bold red]Beklenmeyen hata:[/bold red] '{file_path.name}' taranırken hata oluştu."
                )
                logger.exception(f"Komut taranırken beklenmeyen hata '{file_path}'")

        self._invalidate_completion_cache()
        logger.info(f"{len(self.commands)} komut indekslendi")

    def ensure_loaded(self, name: str) -> Command | None:
        """İsim verilen komutu gerçek sınıf olarak yükler (stub ise)."""
        key = name.lower()
        cmd = self.commands.get(key)
        if cmd is None:
            return None
        if not getattr(cmd, "_is_stub", False):
            return cmd

        meta: CommandMeta = cmd._meta  # type: ignore[attr-defined]
        file_path = Path(meta.file_path)
        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, str(file_path))
            if spec is None or spec.loader is None:
                print(f"Komut spesifikasyonu alınamadı: {file_path}")
                return None

            command_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(command_module)

            command_instance: Command | None = None
            for _name, obj in command_module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, Command)
                    and obj is not Command
                    and obj is not CommandStub
                ):
                    command_instance = obj()
                    break

            if command_instance is None:
                print(f"[bold red]Komut sınıfı bulunamadı:[/bold red] {meta.name}")
                return None

            self.commands[key] = command_instance
            for alias in getattr(command_instance, "Aliases", []) or []:
                self.add_alias(alias.lower(), command_instance.Name, persist=False)
            self._invalidate_completion_cache()
            logger.debug(f"Komut yüklendi: {key}")
            return command_instance
        except Exception as e:
            print(
                f"[bold red]Hata:[/bold red] Komut '{meta.name}' yüklenirken sorun oluştu: {e}"
            )
            logger.exception(f"Komut yükleme hatası ({meta.name}): {e}")
            return None

    def resolve_command(self, command_input: str) -> tuple[str | None, bool]:
        """
        Verilen komut girdisinin (string) gerçek bir komut mu yoksa bir alias mı olduğunu çözer.

        Args:
            command_input (str): Kullanıcının girdiği ilk kelime (komut adı).

        Returns:
            Tuple[Optional[str], bool]:
                - str: Çözümlenen komutun veya alias'ın hedef değeri. Bulunamazsa None.
                - bool: True ise bir alias bulundu, False ise doğrudan komut bulundu.
        """
        key = command_input.lower()
        if key in self.commands:
            return key, False
        elif key in self.aliases:
            return self.aliases[key], True

        return None, False

    def execute_command(self, command_line: str) -> bool:
        """
        Kullanıcıdan alınan komut satırını işler ve ilgili komutu çalıştırır.

        Süreç:
        1. PRE_COMMAND hook tetiklenir (eklenti sistemi için).
        2. Komut satırı parçalanır (komut adı ve argümanlar).
        3. Alias çözümlemesi yapılır. Eğer alias ise argümanlar yeniden düzenlenir.
        4. Komut nesnesi bulunur ve execute metodu çağrılır.
        5. POST_COMMAND hook tetiklenir (sonuç başarılı veya başarısız).

        Args:
            command_line (str): Kullanıcının girdiği tam satır.

        Returns:
            bool: Komut başarıyla çalıştıysa True, aksi halde False.
        """
        # Kullanıcı boşluklar girmişse temizle
        parts = command_line.strip().split(maxsplit=1)
        if not parts:
            return False

        # İlk parça komut adıdır (veya alias)
        command_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        # Komutu çöz (Alias mı, gerçek komut mu?)
        resolved_command_name, is_alias = self.resolve_command(command_name)

        # PRE_COMMAND hook'unu tetikle (Komut çalışmadan hemen önce)
        # Bu, eklentilerin komutları izlemesine veya engellemesine olanak tanır.
        if self.plugin_manager:
            self.plugin_manager.trigger_hook(
                HookType.PRE_COMMAND, command_line=command_line
            )

        if resolved_command_name:
            # Makro kaydı (record komutu hariç)
            if (
                shared_state.is_recording
                and not resolved_command_name.strip().lower().startswith("record")
            ):
                shared_state.recorded_commands.append(command_line)

            # Eğer bir alias kullanıldıysa karmaşık bir işleme gerekebilir.
            # Çünkü alias birden fazla kelimeden oluşabilir (örn: 'pull' -> 'git pull')
            if is_alias:
                full_target_command_line = self.aliases[command_name]

                # Kullanıcının girdiği ek argümanları alias'ın sonuna ekle
                if len(parts) > 1:
                    full_target_command_line += " " + parts[1]

                # Yeni komut satırını tekrar parçala
                target_parts = full_target_command_line.strip().split(maxsplit=1)
                resolved_command_name = target_parts[
                    0
                ].lower()  # Artık asıl komut adı (örn: git)
                args = (
                    target_parts[1].split() if len(target_parts) > 1 else []
                )  # Argümanlar güncellendi

            # Çözümlenen isme karşılık gelen komut nesnesini al
            command_obj = self.commands.get(resolved_command_name)

            if command_obj:
                result = False
                try:
                    logger.info(f"Komut çalıştırıldı: {resolved_command_name}")
                    exec_result = command_obj.execute(*args)
                    result = bool(exec_result)
                    return result
                except TypeError:
                    print(
                        f"[bold red]Argüman hatası:[/bold red] '{resolved_command_name}' komutuna yanlış argüman verildi."
                    )
                    logger.exception(
                        f"Komut '{resolved_command_name}' yürütülürken TypeError"
                    )
                    return False
                except KeyboardInterrupt:
                    print("\nKomut kullanıcı tarafından kesildi.")
                    logger.info(
                        f"Komut '{resolved_command_name}' kullanıcı tarafından kesildi"
                    )
                    return False
                except Exception:
                    print(
                        f"[bold red]Kritik hata:[/bold red] '{resolved_command_name}' yürütülürken beklenmeyen hata."
                    )
                    logger.exception(
                        f"Komut '{resolved_command_name}' yürütülürken beklenmeyen hata"
                    )
                    return False
                finally:
                    if self.plugin_manager:
                        self.plugin_manager.trigger_hook(
                            HookType.POST_COMMAND,
                            command_line=command_line,
                            success=result,
                        )
            else:
                print(f"'{resolved_command_name}' komutu bulunamadı.")
                logger.warning(f"Komut bulunamadı: {resolved_command_name}")
                return False
        else:
            print(f"'{command_name}' bilinmeyen bir komut veya alias.")
            logger.warning(f"Bilinmeyen komut: {command_name}")
            return False

    def get_all_commands(self) -> dict[str, Command]:
        """
        Yüklü tüm komut nesnelerini döndürür.

        Returns:
            Dict[str, Command]: Komut Adı -> Komut Nesnesi
        """
        return self.commands

    def get_categorized_commands(self) -> dict[str, dict[str, Command]]:
        """
        Komutları kategorilerine göre gruplayarak döndürür.
        Bu genellikle 'help' komutunda çıktıyı düzenlemek için kullanılır.

        Returns:
            Dict[str, Dict[str, Command]]: Kategori Adı -> (Komut Adı -> Komut Nesnesi)
        """
        categorized_commands: dict[str, dict[str, Command]] = {}
        for cmd_name, cmd_obj in self.commands.items():
            category_display_name = cmd_obj.get_category_display_name()

            if category_display_name not in categorized_commands:
                categorized_commands[category_display_name] = {}

            categorized_commands[category_display_name][cmd_name] = cmd_obj

        return categorized_commands

    def get_command_completer_function(self, command_name: str) -> Callable | None:
        """
        Belirli bir komut için tanımlanmış otomatik tamamlama fonksiyonunu döndürür.

        Args:
            command_name (str): Komutun adı.

        Returns:
            Optional[Callable]: Varsa tamamlama fonksiyonu, yoksa None.
        """
        command_obj = self.commands.get(command_name)
        if command_obj:
            return command_obj.completer_function
        return None
