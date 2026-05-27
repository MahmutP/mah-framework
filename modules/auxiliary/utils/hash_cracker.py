# =============================================================================
# Auxiliary: Hash Cracker
# =============================================================================
# Yaygın hash tiplerini dictionary attack ile çözmeye çalışan modül.
#
# KULLANIM:
#   1. use auxiliary/utils/hash_cracker
#   2. set HASH 5d41402abc4b2a76b9719d911017c592
#   3. set HASH_TYPE auto
#   4. set WORDLIST config/wordlists/passwords/common_passwords.txt
#   5. run
# =============================================================================

import hashlib
import os
import time
from typing import Any

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option

# ── Hash tipi → uzunluk eşlemesi ────────────────────────────────────────────
HASH_LENGTHS: dict[int, list[str]] = {
    32: ["md5"],
    40: ["sha1"],
    64: ["sha256"],
    128: ["sha512"],
}


class hash_cracker(BaseModule):
    """Hash Kırıcı — Dictionary Attack Modülü

    Verilen hash değerini wordlist (sözlük) saldırısı ile çözmeye çalışır.

    Desteklenen Hash Tipleri:
        - MD5  (32 karakter)
        - SHA1 (40 karakter)
        - SHA256 (64 karakter)
        - SHA512 (128 karakter)

    Otomatik tip algılama veya manuel seçim desteklenir.
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "Hash Cracker"
    Description = (
        "Yaygın hash tiplerini dictionary attack ile çözme (MD5, SHA1, SHA256, SHA512)"
    )
    Author = "Mahmut P."
    Category = "auxiliary/utils"
    Version = "1.0"

    Requirements: dict[str, list[str]] = {}

    def __init__(self):
        super().__init__()
        self.Options = {
            "HASH": Option(
                name="HASH",
                value="",
                required=False,
                description="Kırılacak tek hash değeri",
            ),
            "HASH_FILE": Option(
                name="HASH_FILE",
                value="",
                required=False,
                description="Kırılacak hash listesi dosya yolu (her satırda bir hash)",
                completion_dir=".",
                completion_extensions=[".txt"],
            ),
            "HASH_TYPE": Option(
                name="HASH_TYPE",
                value="auto",
                required=False,
                description="Hash tipi: auto, md5, sha1, sha256, sha512",
                choices=["auto", "md5", "sha1", "sha256", "sha512"],
            ),
            "WORDLIST": Option(
                name="WORDLIST",
                value="config/wordlists/passwords/common_passwords.txt",
                required=True,
                description="Wordlist dosya yolu",
                completion_dir="config/wordlists/passwords",
                completion_extensions=[".txt"],
            ),
        }
        for opt_name, opt_obj in self.Options.items():
            setattr(self, opt_name, opt_obj.value)

        self.console = Console()

    # ── YARDIMCI ─────────────────────────────────────────────────────────────

    @staticmethod
    def detect_hash_type(hash_value: str) -> str | None:
        """Hash uzunluğuna göre tip algılama."""
        hash_value = hash_value.strip().lower()
        length = len(hash_value)
        candidates = HASH_LENGTHS.get(length)
        if candidates:
            return candidates[0]
        return None

    @staticmethod
    def compute_hash(word: str, hash_type: str) -> str:
        """Bir kelime için belirtilen tipte hash hesaplar."""
        h = hashlib.new(hash_type)
        h.update(word.encode("utf-8", errors="replace"))
        return h.hexdigest()

    def _load_wordlist(self, path: str) -> list[str]:
        """Wordlist dosyasını satır satır okur."""
        words: list[str] = []
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    word = line.strip()
                    if word:
                        words.append(word)
        except FileNotFoundError:
            print(f"[bold red][-] Wordlist bulunamadı: {path}[/bold red]")
        except Exception as e:
            print(f"[bold red][-] Wordlist okuma hatası: {e}[/bold red]")
        return words

    def _load_hashes(self, options: dict[str, Any]) -> list[str]:
        """HASH veya HASH_FILE'dan hash listesini yükler."""
        hashes: list[str] = []

        single = str(options.get("HASH", "")).strip()
        if single:
            hashes.append(single.lower())

        hash_file = str(options.get("HASH_FILE", "")).strip()
        if hash_file and os.path.isfile(hash_file):
            try:
                with open(hash_file) as f:
                    for line in f:
                        h = line.strip().lower()
                        if h:
                            hashes.append(h)
            except Exception:
                pass

        return hashes

    def _crack_hash(
        self, target_hash: str, hash_type: str, words: list[str]
    ) -> str | None:
        """Tek bir hash'i wordlist üzerinde dener."""
        target_hash = target_hash.lower()
        for word in words:
            if self.compute_hash(word, hash_type) == target_hash:
                return word
        return None

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        wordlist_path = str(options.get("WORDLIST", ""))
        hash_type_opt = str(options.get("HASH_TYPE", "auto")).lower()

        logger.info("Hash cracker başlatıldı")

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]🔓 HASH CRACKER — Dictionary Attack[/bold cyan]",
                border_style="cyan",
            )
        )

        # Hash'leri yükle
        hashes = self._load_hashes(options)
        if not hashes:
            print(
                "[bold red][-] Kırılacak hash belirtilmedi. HASH veya HASH_FILE ayarlayın.[/bold red]"
            )
            return False

        # Wordlist yükle
        words = self._load_wordlist(wordlist_path)
        if not words:
            return False

        self.console.print(f"  [cyan]Hash sayısı  :[/cyan] {len(hashes)}")
        self.console.print(f"  [cyan]Wordlist     :[/cyan] {len(words)} kelime")
        self.console.print()

        # Sonuç tablosu
        results: list[tuple[str, str, str | None]] = []
        start_time = time.time()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Kırılıyor...", total=len(hashes))

            for target_hash in hashes:
                # Tip algılama
                if hash_type_opt == "auto":
                    detected = self.detect_hash_type(target_hash)
                    if not detected:
                        results.append((target_hash, "?", None))
                        progress.advance(task)
                        continue
                    ht = detected
                else:
                    ht = hash_type_opt

                # Saldırı
                found = self._crack_hash(target_hash, ht, words)
                results.append((target_hash, ht, found))
                progress.advance(task)

        elapsed = time.time() - start_time

        # ── Sonuçları Göster ──────────────────────────────────────────────
        tbl = Table(title="🔑 Kırma Sonuçları", border_style="green")
        tbl.add_column("#", style="dim", justify="right")
        tbl.add_column("Hash", style="white", max_width=48)
        tbl.add_column("Tip", justify="center")
        tbl.add_column("Sonuç", style="bold")

        cracked = 0
        for idx, (h, ht, pwd) in enumerate(results, 1):
            if pwd:
                tbl.add_row(str(idx), h, ht.upper(), f"[green]{pwd}[/green]")
                cracked += 1
            else:
                tbl.add_row(str(idx), h, ht.upper(), "[red]Bulunamadı[/red]")

        self.console.print(tbl)
        self.console.print()
        self.console.print(
            Panel.fit(
                f"[green]Kırılan:[/green] {cracked}/{len(hashes)}  |  "
                f"[cyan]Süre:[/cyan] {elapsed:.2f}s  |  "
                f"[dim]Wordlist:[/dim] {len(words)} kelime",
                title="📊 Özet",
                border_style="green",
            )
        )

        logger.info(f"Hash cracker tamamlandı: {cracked}/{len(hashes)} kırıldı")
        return True
