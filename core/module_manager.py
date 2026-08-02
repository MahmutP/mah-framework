# Framework'ün en kritik parçalarından biri olan Modül Yöneticisi (ModuleManager).
# Bu modül, sistemdeki tüm modüllerin (exploit, scanner vb.) bulunmasını, yüklenmesini,
# yönetilmesini ve çalıştırılmasını sağlar. Ayrıca eklenti (plugin) sistemiyle entegre çalışır.

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rich import print

from core import logger
from core.code_scanner import print_scan_report, scan_source
from core.hooks import HookType
from core.module import BaseModule
from core.plugin_manager import PluginManager as PluginManagerType
from core.shared_state import shared_state
from core.validation_pipeline import ValidationPipeline, print_validation_report

MANIFEST_VERSION = 1
DEFAULT_MANIFEST_PATH = Path("config/module_manifest.json")

# Seçilebilir framework modülü olmayan destek dosya adları (yine de BaseModule varsa yüklenir).
_SUPPORT_FILENAMES = frozenset(
    {"agent.py", "__init__.py", "conftest.py"}
)


@dataclass
class ModuleMeta:
    """Disk keşfinden gelen hafif modül meta verisi (exec olmadan)."""

    path: str
    file_path: str
    name: str
    description: str
    author: str
    category: str
    mtime_ns: int
    size: int
    content_hash: str
    class_name: str
    scan_ok: bool = True


class ModuleStub(BaseModule):
    """show/search için hafif stub; gerçek kod get_module ile yüklenir."""

    def __init__(self, meta: ModuleMeta) -> None:
        self.Name = meta.name
        self.Description = meta.description
        self.Author = meta.author
        self.Category = meta.category or "uncategorized"
        self.Path = meta.path
        self.Options = {}
        self._meta = meta
        self._is_stub = True
        super().__init__()

    def run(self, options: dict[str, Any]) -> bool:
        raise RuntimeError(f"Modül henüz yüklenmedi: {self.Path}")


def _ast_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _base_names(bases: list[ast.expr]) -> list[str]:
    names: list[str] = []
    for base in bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def extract_module_meta_from_source(
    source: str, module_path: str, file_path: Path, mtime_ns: int, size: int
) -> ModuleMeta | None:
    """Kaynak koddan BaseModule alt sınıfı ve metadata çıkarır (exec yok)."""
    if "BaseModule" not in source:
        return None

    # Saf template dosyaları (generator değilse) atla
    if "{{" in source and "}}" in source and "class " not in source:
        return None

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return None

    content_hash = hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest()

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if "BaseModule" not in _base_names(node.bases):
            continue

        fields = {
            "Name": None,
            "Description": None,
            "Author": "Unknown",
            "Category": "uncategorized",
        }

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in fields:
                        value = _ast_str(item.value)
                        if value is not None:
                            fields[target.id] = value
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.target.id in fields and item.value is not None:
                    value = _ast_str(item.value)
                    if value is not None:
                        fields[item.target.id] = value
            elif isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if not isinstance(stmt, ast.Assign):
                        continue
                    for target in stmt.targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                            and target.attr in fields
                        ):
                            value = _ast_str(stmt.value)
                            if value is not None:
                                fields[target.attr] = value

        name = fields["Name"] or Path(module_path).name
        description = fields["Description"] or ""
        author = fields["Author"] or "Unknown"
        category = fields["Category"] or "uncategorized"

        return ModuleMeta(
            path=module_path,
            file_path=str(file_path),
            name=name,
            description=description,
            author=author,
            category=category,
            mtime_ns=mtime_ns,
            size=size,
            content_hash=content_hash,
            class_name=node.name,
            scan_ok=True,
        )

    return None


class ModuleManager:
    """
    Modül Yönetim Sınıfı.

    Açılışta dosyaları AST ile indeksler (lazy catalog); gerçek import
    yalnızca use/run/info sırasında yapılır.
    """

    def __init__(
        self,
        modules_dir: str = "modules",
        plugin_manager: PluginManagerType | None = None,
        context: Any = None,
        use_validation_pipeline: bool = False,
        restricted_exec: bool = False,
        manifest_path: str | Path | None = None,
    ) -> None:
        self.modules_dir = Path(modules_dir)
        self.modules: dict[str, BaseModule] = {}
        self._catalog: dict[str, ModuleMeta] = {}
        self._plugin_manager = plugin_manager
        self._context = context
        self.use_validation_pipeline = use_validation_pipeline
        self.restricted_exec = restricted_exec
        self._validation_pipeline: ValidationPipeline | None = (
            ValidationPipeline() if use_validation_pipeline else None
        )
        self.manifest_path = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST_PATH
        self._module_paths_cache: list[str] | None = None

    @property
    def plugin_manager(self) -> Any:
        if self._plugin_manager:
            return self._plugin_manager
        if self._context and self._context.plugin_manager:
            return self._context.plugin_manager
        return shared_state.plugin_manager

    @plugin_manager.setter
    def plugin_manager(self, value: Any) -> None:
        self._plugin_manager = value

    def _invalidate_path_cache(self) -> None:
        self._module_paths_cache = None

    def get_module_paths(self) -> list[str]:
        """Sıralı modül yolu listesi (completer cache)."""
        if self._module_paths_cache is None:
            self._module_paths_cache = sorted(self.modules.keys())
        return self._module_paths_cache

    def _load_manifest(self) -> dict[str, ModuleMeta]:
        if not self.manifest_path.exists():
            return {}
        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != MANIFEST_VERSION:
                return {}
            entries: dict[str, ModuleMeta] = {}
            for path, raw in data.get("entries", {}).items():
                entries[path] = ModuleMeta(**raw)
            return entries
        except Exception:
            logger.debug("Modül manifest okunamadı; yeniden oluşturulacak")
            return {}

    def _save_manifest(self) -> None:
        try:
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": MANIFEST_VERSION,
                "entries": {path: asdict(meta) for path, meta in self._catalog.items()},
            }
            tmp = self.manifest_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            tmp.replace(self.manifest_path)
        except Exception:
            logger.debug("Modül manifest yazılamadı")

    def _module_id_for_file(self, file_path: Path) -> str:
        relative_path = file_path.relative_to(self.modules_dir)
        module_id = relative_path.with_suffix("").as_posix()
        if "/" not in module_id:
            module_id = f"uncategorized/{module_id}"
        return module_id

    def _should_skip_file(self, file_path: Path) -> bool:
        if file_path.name in _SUPPORT_FILENAMES:
            return True
        if "examples" in file_path.parts:
            return True
        return False

    def load_modules(self) -> None:
        """Modül kataloğunu diskten oluşturur (lazy; exec yok)."""
        self.modules.clear()
        self._catalog.clear()
        self._invalidate_path_cache()

        cached = self._load_manifest()
        plugin_mgr = self.plugin_manager

        for file_path in self.modules_dir.rglob("*.py"):
            if self._should_skip_file(file_path):
                continue

            try:
                stat = file_path.stat()
            except OSError:
                continue

            module_id = self._module_id_for_file(file_path)
            cached_meta = cached.get(module_id)

            if (
                cached_meta
                and cached_meta.mtime_ns == stat.st_mtime_ns
                and cached_meta.size == stat.st_size
            ):
                meta = cached_meta
                meta.file_path = str(file_path)
            else:
                try:
                    source = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                extracted = extract_module_meta_from_source(
                    source,
                    module_id,
                    file_path,
                    stat.st_mtime_ns,
                    stat.st_size,
                )
                if extracted is None:
                    continue
                meta = extracted

                is_payload = "payloads" in file_path.parts
                if not is_payload:
                    scan_result = scan_source(source, str(file_path), strict=False)
                    meta.scan_ok = scan_result.is_safe
                    if not scan_result.is_safe:
                        print(
                            f"[bold yellow]⚠ Güvenlik uyarısı:[/bold yellow] '{file_path.name}'"
                        )
                        print_scan_report(scan_result)

            if plugin_mgr:
                plugin_mgr.trigger_hook(
                    HookType.PRE_MODULE_LOAD,
                    module_path=module_id,
                    file_path=str(file_path),
                )

            stub = ModuleStub(meta)
            self._catalog[module_id] = meta
            self.modules[module_id] = stub

            if plugin_mgr:
                plugin_mgr.trigger_hook(
                    HookType.POST_MODULE_LOAD,
                    module_path=module_id,
                    module=stub,
                )

        self._save_manifest()
        self._invalidate_path_cache()
        logger.info(f"{len(self.modules)} modül indekslendi (lazy)")

    def _instantiate_from_file(self, module_path: str, file_path: Path) -> BaseModule | None:
        """Dosyayı import edip BaseModule örneği oluşturur."""
        is_payload = "payloads" in file_path.parts

        if plugin_mgr := self.plugin_manager:
            plugin_mgr.trigger_hook(
                HookType.PRE_MODULE_LOAD,
                module_path=module_path,
                file_path=str(file_path),
            )

        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            print(f"[bold red]Dosya okunamadı:[/bold red] {file_path} ({e})")
            return None

        if not is_payload and self._validation_pipeline:
            # Validation pipeline dosyayı kendi okur; keşifte zaten tarandı.
            vresult = self._validation_pipeline.validate_module_file(
                str(file_path), strict_scan=False, sandbox=self.restricted_exec
            )
            if not vresult.is_valid:
                print(f"[bold red]✗ Doğrulama hatası:[/bold red] '{file_path.name}'")
                print_validation_report(vresult)
                return None

        try:
            spec = importlib.util.spec_from_file_location(module_path, str(file_path))
            if spec is None or spec.loader is None:
                print(f"Modül spesifikasyonu alınamadı: {file_path}")
                return None

            module = importlib.util.module_from_spec(spec)

            if self.restricted_exec and not is_payload:
                sandbox = (
                    self._validation_pipeline.sandbox
                    if self._validation_pipeline
                    else None
                )
                if sandbox:
                    restricted_module = sandbox.exec_module_restricted(
                        source, str(file_path)
                    )
                    if restricted_module is None:
                        print(
                            f"[bold red]✗ Kısıtlı çalıştırma hatası:[/bold red] '{file_path.name}'"
                        )
                        return None
                    module.__dict__.update(restricted_module.__dict__)
                else:
                    spec.loader.exec_module(module)
            else:
                spec.loader.exec_module(module)

            for _name, obj in module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseModule)
                    and obj is not BaseModule
                    and obj is not ModuleStub
                ):
                    module_instance = obj()
                    if not module_instance.Category:
                        module_instance.Category = "uncategorized"
                    module_instance.Path = module_path

                    if (
                        module_instance.Name == "Default Module Name"
                        or not module_instance.Description
                        or module_instance.Description == "description for module"
                    ):
                        logger.warning(
                            f"Modül metadata değerleri varsayılan veya eksik: {file_path}."
                        )

                    if self.plugin_manager:
                        self.plugin_manager.trigger_hook(
                            HookType.POST_MODULE_LOAD,
                            module_path=module_path,
                            module=module_instance,
                        )
                    return module_instance

        except SyntaxError:
            print(
                f"[bold red]Sözdizimi hatası:[/bold red] '{file_path.name}' dosyasında hata var."
            )
            logger.exception(f"Modül yüklenirken sözdizimi hatası '{file_path}'")
        except ImportError as e:
            print(
                f"[bold red]İçe aktarma hatası:[/bold red] '{file_path.name}' - {e}"
            )
            logger.exception(f"Modül yüklenirken import hatası '{file_path}'")
        except AttributeError:
            print(
                f"[bold red]Öznitelik hatası:[/bold red] '{file_path.name}' - Modül sınıfı doğru tanımlanmamış."
            )
            logger.exception(f"Modül yüklenirken öznitelik hatası '{file_path}'")
        except Exception:
            print(
                f"[bold red]Beklenmeyen hata:[/bold red] '{file_path.name}' yüklenirken hata oluştu."
            )
            logger.exception(f"Modül yüklenirken beklenmeyen hata '{file_path}'")

        return None

    def ensure_loaded(self, module_path: str) -> BaseModule | None:
        """Stub ise gerçek modülü yükler ve cache'ler."""
        current = self.modules.get(module_path)
        if current is not None and not getattr(current, "_is_stub", False):
            return current

        meta = self._catalog.get(module_path)
        if meta is not None:
            file_path = Path(meta.file_path)
        else:
            file_path = self.modules_dir / f"{module_path}.py"
            if not file_path.exists() and module_path.startswith("uncategorized/"):
                file_path = self.modules_dir / f"{module_path.split('/', 1)[1]}.py"

        if not file_path.exists():
            # Katalogda ölü kayıt kalmasın
            self.modules.pop(module_path, None)
            self._catalog.pop(module_path, None)
            self._invalidate_path_cache()
            return None

        instance = self._instantiate_from_file(module_path, file_path)
        if instance is None:
            # Yükleme başarısız: stub ile yanıltıcı listelemeyi kaldır
            self.modules.pop(module_path, None)
            self._invalidate_path_cache()
            return None

        self.modules[module_path] = instance
        return instance

    def reload_module(self, module_path: str) -> bool:
        """Belirtilen modülü diskten yeniden yükler (hot-reload)."""
        self.modules.pop(module_path, None)
        self._catalog.pop(module_path, None)

        full_path = self.modules_dir / f"{module_path}.py"
        if not full_path.exists():
            print(f"[bold red]Modül dosyası bulunamadı:[/bold red] {full_path}")
            return False

        try:
            source = full_path.read_text(encoding="utf-8", errors="ignore")
            stat = full_path.stat()
            meta = extract_module_meta_from_source(
                source, module_path, full_path, stat.st_mtime_ns, stat.st_size
            )
            if meta:
                self._catalog[module_path] = meta
                self._save_manifest()
        except OSError:
            pass

        instance = self._instantiate_from_file(module_path, full_path)
        if instance is None:
            return False

        self.modules[module_path] = instance
        self._invalidate_path_cache()
        logger.info(f"Modül başarıyla yeniden yüklendi: {module_path}")
        return True

    def get_module(self, module_path: str) -> BaseModule | None:
        """Verilen yol ile eşleşen modülü döndürür (gerekirse lazy load)."""
        if module_path not in self.modules and module_path not in self._catalog:
            return None
        return self.ensure_loaded(module_path)

    def get_all_modules(self) -> dict[str, BaseModule]:
        """Katalogdaki tüm modülleri döndürür (stub veya loaded)."""
        return self.modules

    def get_modules_by_category(self) -> dict[str, dict[str, BaseModule]]:
        categorized_modules: dict[str, dict[str, BaseModule]] = {}
        for module_path, module_obj in self.modules.items():
            category = module_obj.Category.capitalize()
            if category not in categorized_modules:
                categorized_modules[category] = {}
            categorized_modules[category][module_path] = module_obj
        return categorized_modules

    def run_module(self, module_path: str) -> bool:
        module = self.get_module(module_path)

        if not module:
            print(f"Modül bulunamadı: {module_path}")
            logger.warning(f"Modül bulunamadı: {module_path}")
            return False

        if not module.check_required_options():
            logger.warning(f"Modül çalıştırılamadı (eksik seçenekler): {module_path}")
            return False

        if not module.check_dependencies():
            logger.warning(
                f"Modül çalıştırılamadı (eksik bağımlılıklar): {module_path}"
            )
            return False

        plugin_mgr = self.plugin_manager
        if plugin_mgr:
            plugin_mgr.trigger_hook(
                HookType.PRE_MODULE_RUN, module_path=module_path, module=module
            )

        success = False
        try:
            current_options = {
                name: opt.value for name, opt in module.get_options().items()
            }
            logger.info(f"Modül çalıştırılıyor: {module_path}")
            module.run(current_options)
            success = True
            return True

        except TypeError:
            print(
                "[bold red]Argüman hatası:[/bold red] Modüle yanlış seçenek değeri verildi."
            )
            logger.exception(f"Modül '{module_path}' çalıştırılırken TypeError")
            return False

        except KeyboardInterrupt:
            print("\nModül çalışması kullanıcı tarafından kesildi.")
            logger.info(f"Modül '{module_path}' kullanıcı tarafından kesildi")
            return False

        except Exception:
            print(
                f"[bold red]Kritik hata:[/bold red] '{module_path}' çalıştırılırken beklenmeyen hata."
            )
            logger.exception(f"Modül '{module_path}' çalıştırılırken beklenmeyen hata")
            return False

        finally:
            if plugin_mgr:
                plugin_mgr.trigger_hook(
                    HookType.POST_MODULE_RUN,
                    module_path=module_path,
                    module=module,
                    success=success,
                )

    def get_module_info(self, module_path: str) -> tuple[str, str, str, str] | None:
        # info için stub yeterli; gerekirse yüklü nesne kullan
        module = self.modules.get(module_path)
        if module is None:
            return None
        if getattr(module, "_is_stub", False):
            loaded = self.ensure_loaded(module_path)
            if loaded is None:
                return (module.Name, module.Description, module.Author, module.Category)
            module = loaded
        return (module.Name, module.Description, module.Author, module.Category)
