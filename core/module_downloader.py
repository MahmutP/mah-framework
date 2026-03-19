# core/module_downloader.py
# Uzak depolardan modül indirme, imza doğrulama, bağımlılık kurma ve
# versiyon kontrolü işlemlerini yöneten sınıf.

import json
import shutil
import hashlib
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any, Tuple

from core.cont import REPOS_DIR, INSTALLED_MODULES_FILE
from core import logger
from rich import print


class ModuleDownloader:
    """
    Modül İndirici (Module Downloader) Sınıfı.

    Görevleri:
    1. Klonlanmış uzak depolardaki modülleri taramak ve listelemek.
    2. Modülleri uzak depodan alıp modules/ dizinine kurmak.
    3. SHA256 imza doğrulaması yapmak.
    4. Modül bağımlılıklarını (pip) otomatik kurmak.
    5. Kurulu modüllerin versiyon kontrolünü yapmak ve güncelleme bildirmek.
    """

    def __init__(self, modules_dir: str = "modules") -> None:
        """
        ModuleDownloader başlatıcı metod.

        Args:
            modules_dir (str): Modüllerin kurulacağı hedef dizin.
        """
        self.repos_dir = Path(REPOS_DIR)
        self.modules_dir = Path(modules_dir)
        self.installed_file = Path(INSTALLED_MODULES_FILE)
        self.installed: Dict[str, Dict[str, Any]] = {}

        # Kurulum kayıt dosyasını hazırla ve yükle.
        self._ensure_installed_file()
        self.load_installed()

    def _ensure_installed_file(self) -> None:
        """
        Kurulu modül kayıt dosyasının (installed_modules.json) varlığını kontrol eder.
        Yoksa boş bir JSON dosyası oluşturur.
        """
        if not self.installed_file.exists():
            self.installed_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.installed_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
            logger.info(f"Kurulu modül kayıt dosyası oluşturuldu: {INSTALLED_MODULES_FILE}")

    def load_installed(self) -> None:
        """
        Kurulu modül kayıtlarını JSON dosyasından belleğe yükler.
        """
        try:
            with open(self.installed_file, 'r', encoding='utf-8') as f:
                self.installed = json.load(f)
            logger.info(f"{len(self.installed)} kurulu modül kaydı yüklendi")
        except FileNotFoundError:
            logger.warning(f"Kurulu modül dosyası bulunamadı: {INSTALLED_MODULES_FILE}")
            self._ensure_installed_file()
            self.installed = {}
        except json.JSONDecodeError as e:
            logger.error(f"Kurulu modül dosyası okunamadı '{INSTALLED_MODULES_FILE}': {e}")
            print(f"[bold red]Hata:[/bold red] Kurulu modül kayıt dosyası bozuk: {e}")
            self.installed = {}

    def save_installed(self) -> None:
        """
        Kurulu modül kayıtlarını JSON dosyasına kaydeder.
        """
        try:
            with open(self.installed_file, 'w', encoding='utf-8') as f:
                json.dump(self.installed, f, indent=4, ensure_ascii=False)
        except PermissionError:
            print(f"[bold red]Hata:[/bold red] Kurulu modül dosyası yazma izni hatası: {INSTALLED_MODULES_FILE}")
            logger.exception("Kurulu modül dosyası yazma izni hatası")
        except IOError as e:
            print(f"[bold red]Hata:[/bold red] Kurulu modül dosyası yazma hatası: {e}")
            logger.exception("Kurulu modül dosyası yazma hatası")

    # =========================================================================
    # MODÜL TARAMA
    # =========================================================================

    def scan_repos(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Klonlanmış depolardaki modülleri tarar ve listeler.
        BaseModule alt sınıfı içeren .py dosyalarını bulur.

        Args:
            search_term (str, optional): Arama terimi. Modül adı veya açıklamasında aranır.

        Returns:
            List[Dict[str, Any]]: Bulunan modüllerin bilgi listesi.
        """
        found_modules: List[Dict[str, Any]] = []

        if not self.repos_dir.exists():
            logger.warning(f"Depo dizini bulunamadı: {self.repos_dir}")
            return found_modules

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

                module_info = self._extract_module_info(py_file, repo_name, repo_path)
                if module_info is None:
                    continue

                # Arama filtresi uygula
                if search_term:
                    term_lower = search_term.lower()
                    name_match = term_lower in module_info["name"].lower()
                    desc_match = term_lower in module_info["description"].lower()
                    path_match = term_lower in module_info["relative_path"].lower()
                    if not (name_match or desc_match or path_match):
                        continue

                found_modules.append(module_info)

        return found_modules

    def _extract_module_info(self, py_file: Path, repo_name: str, repo_path: Path) -> Optional[Dict[str, Any]]:
        """
        Bir Python dosyasından modül bilgilerini çıkarır.
        Dosyayı metin olarak okuyarak BaseModule alt sınıfı olup olmadığını kontrol eder.

        Args:
            py_file (Path): Python dosyası yolu.
            repo_name (str): Depo adı.
            repo_path (Path): Depo kök dizini.

        Returns:
            Optional[Dict[str, Any]]: Modül bilgileri veya None.
        """
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None

        # BaseModule alt sınıfı değilse atla
        if 'BaseModule' not in content:
            return None

        # Template dosyalarını atla (şablon ama modül değil)
        if '{{' in content and '}}' in content:
            return None

        relative_path = py_file.relative_to(repo_path).as_posix()

        # Modül bilgilerini çıkarmak için basit metin ayrıştırma
        name = self._extract_field(content, "Name")
        description = self._extract_field(content, "Description")
        version = self._extract_field(content, "Version") or "1.0"
        author = self._extract_field(content, "Author") or "Unknown"
        category = self._extract_field(content, "Category") or "uncategorized"

        if not name or name == "Default Module Name":
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
            "category": category,
            "relative_path": relative_path,
            "full_path": str(py_file),
            "has_signature": has_signature,
        }

    def _extract_field(self, content: str, field_name: str) -> Optional[str]:
        """
        Python kaynak kodundan sınıf alanı değerini çıkarır.
        Basit regex-siz metin ayrıştırma kullanır.

        Args:
            content (str): Dosya içeriği.
            field_name (str): Alan adı (örn: 'Name', 'Description').

        Returns:
            Optional[str]: Bulunan değer veya None.
        """
        # "Name = " veya "Name: str = " kalıplarını ara
        for line in content.splitlines():
            stripped = line.strip()
            # "Name = \"...\"" veya "Name = '...'" formatı
            if stripped.startswith(f"{field_name}") and "=" in stripped:
                # Eşittir işaretinden sonrasını al
                _, _, value_part = stripped.partition("=")
                value_part = value_part.strip()
                # String değerini çıkar
                for quote in ['"', "'"]:
                    if value_part.startswith(quote):
                        end_idx = value_part.find(quote, 1)
                        if end_idx > 0:
                            return value_part[1:end_idx]
        return None

    # =========================================================================
    # MODÜL KURMA (INSTALL)
    # =========================================================================

    def install_module(self, module_identifier: str, force: bool = False) -> bool:
        """
        Uzak depodan bir modülü modules/ dizinine kurar.

        Args:
            module_identifier (str): '<repo_adı>/<modül_yolu>' formatında modül tanımlayıcı.
            force (bool): True ise mevcut modülü üzerine yazar.

        Returns:
            bool: Kurulum başarılı ise True.
        """
        # Tanımlayıcıyı ayrıştır
        parts = module_identifier.split("/", 1)
        if len(parts) < 2:
            print("[bold red]Hata:[/bold red] Modül tanımlayıcı formatı: <depo_adı>/<modül_yolu>")
            print("   Örnek: download install myrepo/auxiliary/scanner/my_scanner.py")
            return False

        repo_name = parts[0].strip().lower()
        module_path = parts[1].strip()

        # .py uzantısını ekle (yoksa)
        if not module_path.endswith(".py"):
            module_path += ".py"

        # Kaynak dosyayı bul
        source_file = self.repos_dir / repo_name / module_path
        if not source_file.exists():
            print(f"[bold red]Hata:[/bold red] Modül dosyası bulunamadı: {source_file}")
            print(f"   Mevcut modülleri aramak için: [bold]download search <terim>[/bold]")
            return False

        # BaseModule kontrol
        try:
            content = source_file.read_text(encoding='utf-8', errors='ignore')
            if 'BaseModule' not in content:
                print(f"[bold red]Hata:[/bold red] Dosya geçerli bir Mah Framework modülü değil (BaseModule bulunamadı).")
                return False
        except Exception as e:
            print(f"[bold red]Hata:[/bold red] Dosya okunamadı: {e}")
            return False

        # SHA256 doğrulama (imza dosyası varsa)
        sha256_file = source_file.with_suffix(".sha256")
        if sha256_file.exists():
            if not self._verify_sha256(source_file, sha256_file):
                print("[bold red]✗ İmza doğrulama başarısız![/bold red] Modül bütünlüğü tehlikede olabilir.")
                print("   Yine de kurmak isterseniz: Öncelikle kaynağı doğrulayın.")
                return False
            print("[bold green]✓[/bold green] SHA256 imza doğrulandı.")

        # Hedef yolu belirle
        dest_file = self.modules_dir / module_path
        module_key = Path(module_path).with_suffix("").as_posix()

        # Zaten kurulu mu kontrol et
        if dest_file.exists() and not force:
            if module_key in self.installed:
                print(f"[bold yellow]⚠[/bold yellow] Modül zaten kurulu: {module_key}")
                print(f"   Üzerine yazmak için: [bold]download install {module_identifier} --force[/bold]")
                return False
            else:
                print(f"[bold yellow]⚠[/bold yellow] Hedef dosya zaten mevcut: {dest_file}")
                print(f"   Üzerine yazmak için: [bold]download install {module_identifier} --force[/bold]")
                return False

        # Hedef dizini oluştur
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        # Dosyayı kopyala
        try:
            shutil.copy2(str(source_file), str(dest_file))
        except Exception as e:
            print(f"[bold red]Hata:[/bold red] Dosya kopyalama hatası: {e}")
            return False

        # Modül bilgilerini çıkar
        module_info = self._extract_module_info(source_file, repo_name, self.repos_dir / repo_name)
        version = module_info.get("version", "1.0") if module_info else "1.0"

        # SHA256 hesapla
        file_hash = self._compute_sha256(dest_file)

        # Bağımlılıkları kur
        deps_installed = self._install_dependencies(source_file)

        # Kurulum kaydını oluştur
        self.installed[module_key] = {
            "repo": repo_name,
            "source_path": module_path,
            "version": version,
            "installed_at": datetime.now().isoformat(),
            "updated_at": None,
            "sha256": file_hash,
        }
        self.save_installed()

        logger.info(f"Modül kuruldu: {module_key} (repo: {repo_name}, version: {version})")
        print(f"[bold green]✓[/bold green] Modül başarıyla kuruldu: [bold]{module_key}[/bold]")
        print(f"   Kaynak: {repo_name}/{module_path}")
        print(f"   Versiyon: {version}")

        if deps_installed:
            print(f"   Bağımlılıklar kuruldu.")

        print(f"\n   Kullanmak için: [bold]use {module_key}[/bold]")
        return True

    # =========================================================================
    # SHA256 İMZA DOĞRULAMA
    # =========================================================================

    def _compute_sha256(self, file_path: Path) -> str:
        """
        Bir dosyanın SHA256 hash değerini hesaplar.

        Args:
            file_path (Path): Hash hesaplanacak dosya.

        Returns:
            str: Hexadecimal SHA256 hash değeri.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _verify_sha256(self, file_path: Path, sha256_file: Path) -> bool:
        """
        Dosyanın SHA256 hash değerini .sha256 dosyasındaki değerle karşılaştırır.

        Args:
            file_path (Path): Doğrulanacak dosya.
            sha256_file (Path): Beklenen hash değerini içeren dosya.

        Returns:
            bool: Hash'ler eşleşirse True.
        """
        try:
            expected_hash = sha256_file.read_text(encoding='utf-8').strip().split()[0].lower()
            actual_hash = self._compute_sha256(file_path)
            return actual_hash == expected_hash
        except Exception as e:
            logger.error(f"SHA256 doğrulama hatası: {e}")
            return False

    def verify_module(self, module_key: str) -> Optional[bool]:
        """
        Kurulu bir modülün SHA256 bütünlük kontrolünü yapar.

        Args:
            module_key (str): Modül yolu (örn: auxiliary/scanner/my_scanner).

        Returns:
            Optional[bool]: True=geçerli, False=geçersiz, None=kayıt bulunamadı.
        """
        if module_key not in self.installed:
            print(f"[bold red]Hata:[/bold red] '{module_key}' kurulu modüller arasında bulunamadı.")
            return None

        record = self.installed[module_key]
        module_file = self.modules_dir / f"{module_key}.py"

        if not module_file.exists():
            print(f"[bold red]Hata:[/bold red] Modül dosyası bulunamadı: {module_file}")
            return None

        stored_hash = record.get("sha256")
        if not stored_hash:
            print(f"[bold yellow]⚠[/bold yellow] Kayıtlı SHA256 hash değeri bulunamadı.")
            return None

        actual_hash = self._compute_sha256(module_file)
        is_valid = actual_hash == stored_hash

        if is_valid:
            print(f"[bold green]✓[/bold green] Modül bütünlüğü doğrulandı: [bold]{module_key}[/bold]")
            print(f"   SHA256: {actual_hash}")
        else:
            print(f"[bold red]✗ Modül bütünlüğü BOZULMUŞ![/bold red] [bold]{module_key}[/bold]")
            print(f"   Beklenen: {stored_hash}")
            print(f"   Mevcut:   {actual_hash}")

        return is_valid

    # =========================================================================
    # BAĞIMLILIK KURMA
    # =========================================================================

    def _install_dependencies(self, module_file: Path) -> bool:
        """
        Modül dosyasındaki Requirements alanından Python bağımlılıklarını
        algılayıp pip ile kurar.

        Args:
            module_file (Path): Modül dosyası yolu.

        Returns:
            bool: Bağımlılık kurulduysa True.
        """
        try:
            content = module_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return False

        # Requirements dict'inden python bağımlılıklarını çıkar
        python_deps = self._extract_requirements(content)
        if not python_deps:
            return False

        # Eksik bağımlılıkları kontrol et
        missing = []
        for dep in python_deps:
            if importlib.util.find_spec(dep) is None:
                missing.append(dep)

        if not missing:
            return False

        print(f"[bold cyan]📦 Bağımlılıklar kuruluyor:[/bold cyan] {', '.join(missing)}")

        try:
            result = subprocess.run(
                ["pip", "install"] + missing,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                print(f"[bold green]✓[/bold green] Bağımlılıklar başarıyla kuruldu.")
                logger.info(f"Bağımlılıklar kuruldu: {', '.join(missing)}")
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
        """
        Modül kaynak kodundan Requirements dict'indeki python bağımlılıklarını çıkarır.
        Basit metin ayrıştırma kullanır.

        Args:
            content (str): Dosya içeriği.

        Returns:
            List[str]: Python paket isimleri listesi.
        """
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
                    # Aynı satırda liste varsa çıkar
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
                        # Kapanış köşeli parantez öncesindeki öğeler
                        for item in stripped.replace("]", "").split(","):
                            item = item.strip().strip("'\"")
                            if item:
                                deps.append(item)
                        in_python = False
                        continue
                    # Liste elemanları
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

    def check_updates(self, module_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Kurulu modüllerin versiyon kontrolünü yapar.
        Depodaki modülle karşılaştırarak güncellenebilir olanları bulur.

        Args:
            module_key (str, optional): Belirli bir modülü kontrol et.
                                        None ise tüm kurulu modülleri kontrol eder.

        Returns:
            List[Dict[str, Any]]: Güncellenebilir modüllerin listesi.
        """
        updates_available = []

        if module_key:
            if module_key not in self.installed:
                print(f"[bold red]Hata:[/bold red] '{module_key}' kurulu modüller arasında bulunamadı.")
                return updates_available
            modules_to_check = {module_key: self.installed[module_key]}
        else:
            modules_to_check = self.installed.copy()

        if not modules_to_check:
            print("[dim]Kurulu modül bulunamadı.[/dim]")
            return updates_available

        for mod_key, record in modules_to_check.items():
            repo_name = record.get("repo", "")
            source_path = record.get("source_path", "")
            installed_version = record.get("version", "1.0")

            if not repo_name or not source_path:
                continue

            # Depodaki modülü kontrol et
            repo_module_file = self.repos_dir / repo_name / source_path
            if not repo_module_file.exists():
                continue

            repo_module_info = self._extract_module_info(
                repo_module_file, repo_name, self.repos_dir / repo_name
            )
            if not repo_module_info:
                continue

            repo_version = repo_module_info.get("version", "1.0")

            # Basit versiyon karşılaştırması
            if self._is_newer_version(repo_version, installed_version):
                updates_available.append({
                    "module": mod_key,
                    "repo": repo_name,
                    "installed_version": installed_version,
                    "available_version": repo_version,
                    "source_path": source_path,
                })

        return updates_available

    def _is_newer_version(self, new_ver: str, old_ver: str) -> bool:
        """
        İki versiyon numarasını karşılaştırır (basit semver).

        Args:
            new_ver (str): Yeni versiyon (örn: '2.1').
            old_ver (str): Eski versiyon (örn: '1.0').

        Returns:
            bool: new_ver > old_ver ise True.
        """
        try:
            new_parts = [int(x) for x in new_ver.split(".")]
            old_parts = [int(x) for x in old_ver.split(".")]

            # Uzunlukları eşitle
            max_len = max(len(new_parts), len(old_parts))
            new_parts.extend([0] * (max_len - len(new_parts)))
            old_parts.extend([0] * (max_len - len(old_parts)))

            return new_parts > old_parts
        except (ValueError, AttributeError):
            return new_ver != old_ver

    def update_module(self, module_key: str) -> bool:
        """
        Kurulu bir modülü günceller (depodaki son hali ile değiştirir).

        Args:
            module_key (str): Modül yolu (örn: auxiliary/scanner/my_scanner).

        Returns:
            bool: Güncelleme başarılı ise True.
        """
        if module_key not in self.installed:
            print(f"[bold red]Hata:[/bold red] '{module_key}' kurulu modüller arasında bulunamadı.")
            return False

        record = self.installed[module_key]
        repo_name = record.get("repo", "")
        source_path = record.get("source_path", "")

        if not repo_name or not source_path:
            print(f"[bold red]Hata:[/bold red] Modül kaynak bilgisi eksik.")
            return False

        # Mevcut kaydı sil ve yeniden kur (force)
        identifier = f"{repo_name}/{source_path}"
        old_version = record.get("version", "?")

        if self.install_module(identifier, force=True):
            # Güncelleme tarihini kaydet
            if module_key in self.installed:
                self.installed[module_key]["updated_at"] = datetime.now().isoformat()
                self.save_installed()

            new_version = self.installed.get(module_key, {}).get("version", "?")
            print(f"[bold cyan]📦 Güncelleme:[/bold cyan] {old_version} → {new_version}")
            return True

        return False

    # =========================================================================
    # KURULU MODÜL LİSTELEME
    # =========================================================================

    def list_installed(self) -> Dict[str, Dict[str, Any]]:
        """
        Kurulu tüm modüllerin kayıtlarını döndürür.

        Returns:
            Dict[str, Dict[str, Any]]: Modül yolu -> Modül kayıt bilgileri.
        """
        return self.installed

    def get_installed_module_keys(self) -> List[str]:
        """
        Kurulu tüm modüllerin anahtar (yol) listesini döndürür.

        Returns:
            List[str]: Modül yolları listesi.
        """
        return list(self.installed.keys())
