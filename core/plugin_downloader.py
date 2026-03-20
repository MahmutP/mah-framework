# core/plugin_downloader.py
# Uzak depolardan eklenti (plugin) indirme, imza doğrulama, bağımlılık kurma ve
# versiyon kontrolü işlemlerini yöneten sınıf.

import json
import shutil
import hashlib
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any, Tuple

from core.cont import REPOS_DIR, INSTALLED_PLUGINS_FILE, PLUGINS_DIR
from core import logger
from rich import print


class PluginDownloader:
    """
    Eklenti İndirici (Plugin Downloader) Sınıfı.

    Görevleri:
    1. Klonlanmış uzak depolardaki eklentileri (plugins) taramak ve listelemek.
    2. Eklentileri uzak depodan alıp plugins/ dizinine kurmak.
    3. SHA256 imza doğrulaması yapmak.
    4. Eklenti bağımlılıklarını (pip) otomatik kurmak.
    5. Kurulu eklentilerin versiyon kontrolünü yapmak ve güncelleme bildirmek.
    """

    def __init__(self, plugins_dir: str = PLUGINS_DIR) -> None:
        """
        PluginDownloader başlatıcı metod.

        Args:
            plugins_dir (str): Eklentilerin kurulacağı hedef dizin. Varsayılan olarak cont.py'den alınır.
        """
        self.repos_dir = Path(REPOS_DIR)
        self.plugins_dir = Path(plugins_dir)
        self.installed_file = Path(INSTALLED_PLUGINS_FILE)
        self.installed: Dict[str, Dict[str, Any]] = {}

        # Kurulum kayıt dosyasını hazırla ve yükle.
        self._ensure_installed_file()
        self.load_installed()

    def _ensure_installed_file(self) -> None:
        """
        Kurulu eklenti kayıt dosyasının (installed_plugins.json) varlığını kontrol eder.
        Yoksa boş bir JSON dosyası oluşturur.
        """
        if not self.installed_file.exists():
            self.installed_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.installed_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
            logger.info(f"Kurulu eklenti kayıt dosyası oluşturuldu: {INSTALLED_PLUGINS_FILE}")

    def load_installed(self) -> None:
        """
        Kurulu eklenti kayıtlarını JSON dosyasından belleğe yükler.
        """
        try:
            with open(self.installed_file, 'r', encoding='utf-8') as f:
                self.installed = json.load(f)
            logger.info(f"{len(self.installed)} kurulu eklenti kaydı yüklendi")
        except FileNotFoundError:
            logger.warning(f"Kurulu eklenti dosyası bulunamadı: {INSTALLED_PLUGINS_FILE}")
            self._ensure_installed_file()
            self.installed = {}
        except json.JSONDecodeError as e:
            logger.error(f"Kurulu eklenti dosyası okunamadı '{INSTALLED_PLUGINS_FILE}': {e}")
            print(f"[bold red]Hata:[/bold red] Kurulu eklenti kayıt dosyası bozuk: {e}")
            self.installed = {}

    def save_installed(self) -> None:
        """
        Kurulu eklenti kayıtlarını JSON dosyasına kaydeder.
        """
        try:
            with open(self.installed_file, 'w', encoding='utf-8') as f:
                json.dump(self.installed, f, indent=4, ensure_ascii=False)
        except PermissionError:
            print(f"[bold red]Hata:[/bold red] Kurulu eklenti dosyası yazma izni hatası: {INSTALLED_PLUGINS_FILE}")
            logger.exception("Kurulu eklenti dosyası yazma izni hatası")
        except IOError as e:
            print(f"[bold red]Hata:[/bold red] Kurulu eklenti dosyası yazma hatası: {e}")
            logger.exception("Kurulu eklenti dosyası yazma hatası")

    # =========================================================================
    # EKLENTİ TARAMA
    # =========================================================================

    def scan_repos(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Klonlanmış depolardaki eklentileri tarar ve listeler.
        BasePlugin alt sınıfı içeren .py dosyalarını bulur.

        Args:
            search_term (str, optional): Arama terimi. Eklenti adı veya açıklamasında aranır.

        Returns:
            List[Dict[str, Any]]: Bulunan eklentilerin bilgi listesi.
        """
        found_plugins: List[Dict[str, Any]] = []

        if not self.repos_dir.exists():
            logger.warning(f"Depo dizini bulunamadı: {self.repos_dir}")
            return found_plugins

        # Her klonlanmış depoyu tara
        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir():
                continue

            repo_name = repo_path.name

            # Depodaki tüm .py dosyalarını bul
            for py_file in repo_path.rglob("*.py"):
                if py_file.name == "__init__.py":
                    continue

                # .git dizini içindeki dosyaları atla
                if ".git" in py_file.parts:
                    continue

                plugin_info = self._extract_plugin_info(py_file, repo_name, repo_path)
                if plugin_info is None:
                    continue

                # Arama filtresi uygula
                if search_term:
                    term_lower = search_term.lower()
                    name_match = term_lower in plugin_info["name"].lower()
                    desc_match = term_lower in plugin_info["description"].lower()
                    path_match = term_lower in plugin_info["relative_path"].lower()
                    if not (name_match or desc_match or path_match):
                        continue

                found_plugins.append(plugin_info)

        return found_plugins

    def _extract_plugin_info(self, py_file: Path, repo_name: str, repo_path: Path) -> Optional[Dict[str, Any]]:
        """
        Bir Python dosyasından eklenti bilgilerini çıkarır.
        Dosyayı metin olarak okuyarak BasePlugin alt sınıfı olup olmadığını kontrol eder.

        Args:
            py_file (Path): Python dosyası yolu.
            repo_name (str): Depo adı.
            repo_path (Path): Depo kök dizini.

        Returns:
            Optional[Dict[str, Any]]: Eklenti bilgileri veya None.
        """
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None

        # BasePlugin alt sınıfı değilse atla
        if 'BasePlugin' not in content:
            return None

        # Template dosyalarını atla
        if '{{' in content and '}}' in content:
            return None

        relative_path = py_file.relative_to(repo_path).as_posix()

        name = self._extract_field(content, "Name")
        description = self._extract_field(content, "Description")
        version = self._extract_field(content, "Version") or "1.0"
        author = self._extract_field(content, "Author") or "Unknown"

        if not name or name == "Default Plugin":
            # Dosya adından isim türet
            name = py_file.stem.replace("_", " ").title()

        # SHA256 dosyası var mı kontrol et
        sha256_file = py_file.with_suffix(".sha256")
        has_signature = sha256_file.exists()

        return {
            "repo": repo_name,
            "name": name,
            "description": description or "Açıklama yok",
            "version": version,
            "author": author,
            "relative_path": relative_path,
            "full_path": str(py_file),
            "has_signature": has_signature,
        }

    def _extract_field(self, content: str, field_name: str) -> Optional[str]:
        """
        Python kaynak kodundan sınıf alanı değerini çıkarır.
        """
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{field_name}") and "=" in stripped:
                _, _, value_part = stripped.partition("=")
                value_part = value_part.strip()
                for quote in ['"', "'"]:
                    if value_part.startswith(quote):
                        end_idx = value_part.find(quote, 1)
                        if end_idx > 0:
                            return value_part[1:end_idx]
        return None

    # =========================================================================
    # EKLENTİ KURMA (INSTALL)
    # =========================================================================

    def install_plugin(self, plugin_identifier: str, force: bool = False) -> bool:
        """
        Uzak depodan bir eklentiyi plugins/ dizinine kurar.

        Args:
            plugin_identifier (str): '<repo_adı>/<eklenti_yolu>' formatında eklenti tanımlayıcı.
            force (bool): True ise mevcut eklentiyi üzerine yazar.

        Returns:
            bool: Kurulum başarılı ise True.
        """
        parts = plugin_identifier.split("/", 1)
        if len(parts) < 2:
            print("[bold red]Hata:[/bold red] Eklenti tanımlayıcı formatı: <depo_adı>/<eklenti_yolu>")
            print("   Örnek: plugins install myrepo/plugins/my_plugin.py")
            return False

        repo_name = parts[0].strip().lower()
        plugin_path = parts[1].strip()

        if not plugin_path.endswith(".py"):
            plugin_path += ".py"

        source_file = self.repos_dir / repo_name / plugin_path
        if not source_file.exists():
            print(f"[bold red]Hata:[/bold red] Eklenti dosyası bulunamadı: {source_file}")
            print(f"   Mevcut eklentileri aramak için: [bold]plugins search <terim>[/bold]")
            return False

        try:
            content = source_file.read_text(encoding='utf-8', errors='ignore')
            if 'BasePlugin' not in content:
                print(f"[bold red]Hata:[/bold red] Dosya geçerli bir Mah Framework eklentisi değil (BasePlugin bulunamadı).")
                return False
        except Exception as e:
            print(f"[bold red]Hata:[/bold red] Dosya okunamadı: {e}")
            return False

        sha256_file = source_file.with_suffix(".sha256")
        if sha256_file.exists():
            if not self._verify_sha256(source_file, sha256_file):
                print("[bold red]✗ İmza doğrulama başarısız![/bold red] Eklenti bütünlüğü tehlikede olabilir.")
                return False
            print("[bold green]✓[/bold green] SHA256 imza doğrulandı.")

        # Sadece dosya adını alalım, çünkü eklentiler genellikle plugins klasörünün doğrudan içine atılır.
        # Alternatif olarak klasörleri de koruyabiliriz. Basitlik için dosya adını kullanalım.
        dest_file = self.plugins_dir / Path(plugin_path).name
        plugin_key = dest_file.stem

        if dest_file.exists() and not force:
            if plugin_key in self.installed:
                print(f"[bold yellow]⚠[/bold yellow] Eklenti zaten kurulu: {plugin_key}")
                print(f"   Üzerine yazmak için: [bold]plugins install {plugin_identifier} --force[/bold]")
                return False
            else:
                print(f"[bold yellow]⚠[/bold yellow] Hedef dosya zaten mevcut: {dest_file}")
                print(f"   Üzerine yazmak için: [bold]plugins install {plugin_identifier} --force[/bold]")
                return False

        dest_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(str(source_file), str(dest_file))
        except Exception as e:
            print(f"[bold red]Hata:[/bold red] Dosya kopyalama hatası: {e}")
            return False

        plugin_info = self._extract_plugin_info(source_file, repo_name, self.repos_dir / repo_name)
        version = plugin_info.get("version", "1.0") if plugin_info else "1.0"

        file_hash = self._compute_sha256(dest_file)
        deps_installed = self._install_dependencies(source_file)

        self.installed[plugin_key] = {
            "repo": repo_name,
            "source_path": plugin_path,
            "version": version,
            "installed_at": datetime.now().isoformat(),
            "updated_at": None,
            "sha256": file_hash,
        }
        self.save_installed()

        logger.info(f"Eklenti kuruldu: {plugin_key} (repo: {repo_name}, version: {version})")
        print(f"[bold green]✓[/bold green] Eklenti başarıyla kuruldu: [bold]{plugin_key}[/bold]")
        print(f"   Kaynak: {repo_name}/{plugin_path}")
        print(f"   Versiyon: {version}")

        if deps_installed:
            print(f"   Bağımlılıklar kuruldu.")

        print(f"\n   Aktifleştirmek için: [bold]plugins enable {plugin_key}[/bold]")
        return True

    # =========================================================================
    # SHA256 İMZA DOĞRULAMA
    # =========================================================================

    def _compute_sha256(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _verify_sha256(self, file_path: Path, sha256_file: Path) -> bool:
        try:
            expected_hash = sha256_file.read_text(encoding='utf-8').strip().split()[0].lower()
            actual_hash = self._compute_sha256(file_path)
            return actual_hash == expected_hash
        except Exception as e:
            logger.error(f"SHA256 doğrulama hatası: {e}")
            return False

    def verify_plugin(self, plugin_key: str) -> Optional[bool]:
        """
        Kurulu bir eklentinin SHA256 bütünlük kontrolünü yapar.
        """
        if plugin_key not in self.installed:
            print(f"[bold red]Hata:[/bold red] '{plugin_key}' kurulu eklentiler arasında bulunamadı.")
            return None

        record = self.installed[plugin_key]
        plugin_file = self.plugins_dir / f"{plugin_key}.py"

        if not plugin_file.exists():
            print(f"[bold red]Hata:[/bold red] Eklenti dosyası bulunamadı: {plugin_file}")
            return None

        stored_hash = record.get("sha256")
        if not stored_hash:
            print(f"[bold yellow]⚠[/bold yellow] Kayıtlı SHA256 hash değeri bulunamadı.")
            return None

        actual_hash = self._compute_sha256(plugin_file)
        is_valid = actual_hash == stored_hash

        if is_valid:
            print(f"[bold green]✓[/bold green] Eklenti bütünlüğü doğrulandı: [bold]{plugin_key}[/bold]")
        else:
            print(f"[bold red]✗ Eklenti bütünlüğü BOZULMUŞ![/bold red] [bold]{plugin_key}[/bold]")

        return is_valid

    # =========================================================================
    # BAĞIMLILIK KURMA
    # =========================================================================

    def _install_dependencies(self, plugin_file: Path) -> bool:
        """
        Eklenti dosyasındaki Requirements alanından Python bağımlılıklarını kurar.
        """
        try:
            content = plugin_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return False

        python_deps = self._extract_requirements(content)
        if not python_deps:
            return False

        missing = []
        for dep in python_deps:
            if importlib.util.find_spec(dep) is None:
                missing.append(dep)

        if not missing:
            return False

        print(f"[bold cyan]📦 Eklenti bağımlılıkları kuruluyor:[/bold cyan] {', '.join(missing)}")

        try:
            result = subprocess.run(
                ["pip", "install"] + missing,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                print(f"[bold green]✓[/bold green] Bağımlılıklar başarıyla kuruldu.")
                logger.info(f"Eklenti bağımlılıkları kuruldu: {', '.join(missing)}")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Bilinmeyen hata"
                print(f"[bold red]✗[/bold red] Bağımlılık kurulumu başarısız: {error_msg}")
                logger.error(f"Bağımlılık kurulum hatası: {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            print("[bold yellow]⚠[/bold yellow] Bağımlılık kurulumu zaman aşımına uğradı.")
            return False
        except FileNotFoundError:
            print("[bold red]✗[/bold red] pip bulunamadı. Lütfen pip'in kurulu olduğundan emin olun.")
            return False
        except Exception as e:
            print(f"[bold red]✗[/bold red] Bağımlılık kurulumunda beklenmeyen hata: {e}")
            logger.exception("Bağımlılık kurulumu hatası")
            return False

    def _extract_requirements(self, content: str) -> List[str]:
        deps = []
        in_requirements = False
        in_python = False

        for line in content.splitlines():
            stripped = line.strip()

            if "Requirements" in stripped and "=" in stripped and "{" in stripped:
                in_requirements = True
                continue

            if in_requirements:
                if '"python"' in stripped or "'python'" in stripped:
                    in_python = True
                    if "[" in stripped:
                        bracket_content = stripped[stripped.index("["):stripped.index("]") + 1] if "]" in stripped else ""
                        for item in bracket_content.strip("[]").split(","):
                            item = item.strip().strip("'\"")
                            if item:
                                deps.append(item)
                        if "]" in stripped:
                            in_python = False
                    continue

                if in_python:
                    if "]" in stripped:
                        for item in stripped.replace("]", "").split(","):
                            item = item.strip().strip("'\"")
                            if item:
                                deps.append(item)
                        in_python = False
                        continue
                    for item in stripped.split(","):
                        item = item.strip().strip("'\"")
                        if item:
                            deps.append(item)

                if "}" in stripped and not in_python:
                    in_requirements = False

        return deps

    # =========================================================================
    # VERSİYON KONTROLÜ VE GÜNCELLEME
    # =========================================================================

    def check_updates(self, plugin_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Kurulu eklentilerin versiyon kontrolünü yapar.
        """
        updates_available = []

        modules_to_check = {plugin_key: self.installed[plugin_key]} if plugin_key and plugin_key in self.installed else self.installed.copy()

        if not modules_to_check:
            if plugin_key:
                print(f"[bold red]Hata:[/bold red] '{plugin_key}' kurulu eklentiler arasında bulunamadı.")
            else:
                 print("[dim]Kurulu eklenti bulunamadı.[/dim]")
            return updates_available

        for mod_key, record in modules_to_check.items():
            repo_name = record.get("repo", "")
            source_path = record.get("source_path", "")
            installed_version = record.get("version", "1.0")

            if not repo_name or not source_path:
                continue

            repo_module_file = self.repos_dir / repo_name / source_path
            if not repo_module_file.exists():
                continue

            repo_module_info = self._extract_plugin_info(
                repo_module_file, repo_name, self.repos_dir / repo_name
            )
            if not repo_module_info:
                continue

            repo_version = repo_module_info.get("version", "1.0")

            if self._is_newer_version(repo_version, installed_version):
                updates_available.append({
                    "plugin": mod_key,
                    "repo": repo_name,
                    "installed_version": installed_version,
                    "available_version": repo_version,
                    "source_path": source_path,
                })

        return updates_available

    def _is_newer_version(self, new_ver: str, old_ver: str) -> bool:
        try:
            new_parts = [int(x) for x in new_ver.split(".")]
            old_parts = [int(x) for x in old_ver.split(".")]

            max_len = max(len(new_parts), len(old_parts))
            new_parts.extend([0] * (max_len - len(new_parts)))
            old_parts.extend([0] * (max_len - len(old_parts)))

            return new_parts > old_parts
        except (ValueError, AttributeError):
            return new_ver != old_ver

    def update_plugin(self, plugin_key: str) -> bool:
        """
        Kurulu bir eklentiyi günceller.
        """
        if plugin_key not in self.installed:
            print(f"[bold red]Hata:[/bold red] '{plugin_key}' kurulu eklentiler arasında bulunamadı.")
            return False

        record = self.installed[plugin_key]
        repo_name = record.get("repo", "")
        source_path = record.get("source_path", "")

        if not repo_name or not source_path:
            print(f"[bold red]Hata:[/bold red] Eklenti kaynak bilgisi eksik.")
            return False

        identifier = f"{repo_name}/{source_path}"
        old_version = record.get("version", "?")

        if self.install_plugin(identifier, force=True):
            if plugin_key in self.installed:
                self.installed[plugin_key]["updated_at"] = datetime.now().isoformat()
                self.save_installed()

            new_version = self.installed.get(plugin_key, {}).get("version", "?")
            print(f"[bold cyan]📦 Güncelleme:[/bold cyan] {old_version} → {new_version}")
            return True

        return False

    # =========================================================================
    # KURULU EKLENTİ LİSTELEME
    # =========================================================================

    def list_installed(self) -> Dict[str, Dict[str, Any]]:
        return self.installed

    def get_installed_plugin_keys(self) -> List[str]:
        return list(self.installed.keys())

    def remove_plugin(self, plugin_key: str) -> bool:
        if plugin_key not in self.installed:
            print(f"[bold red]Hata:[/bold red] '{plugin_key}' kurulu eklentiler arasında bulunamadı.")
            return False
            
        plugin_file = self.plugins_dir / f"{plugin_key}.py"
        if plugin_file.exists():
            try:
                plugin_file.unlink()
            except Exception as e:
                print(f"[bold red]Hata:[/bold red] Dosya silinemedi: {e}")
                return False
                
        # Disable from plugin manager if it is running
        from core.shared_state import shared_state
        if hasattr(shared_state, "plugin_manager") and shared_state.plugin_manager:
            shared_state.plugin_manager.unload_plugin(plugin_key)
            
        del self.installed[plugin_key]
        self.save_installed()
        print(f"[bold green]✓[/bold green] Eklenti silindi: [bold]{plugin_key}[/bold]")
        logger.info(f"Eklenti silindi: {plugin_key}")
        return True
