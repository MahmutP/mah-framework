# =============================================================================
# Auxiliary: Web Crawler
# =============================================================================
# Hedef web sitesini tarayarak link, form ve meta etiketlerini toplayan modül.
#
# KULLANIM:
#   1. use auxiliary/utils/web_crawler
#   2. set TARGET_URL http://example.com
#   3. set MAX_DEPTH 2
#   4. set MAX_PAGES 50
#   5. run
# =============================================================================

from typing import Any
from urllib.parse import urljoin, urlparse

import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option


class web_crawler(BaseModule):
    """Basit Web Tarayıcı ve Bilgi Toplama Modülü

    Belirtilen URL'den başlayarak iç linkleri takip eder, sayfaları ayrıştırır
    ve bulunan URL'leri, formları, meta etiketlerini ve başlıkları raporlar.

    Özellikler:
        - Derinlik seviyeli tarama (BFS)
        - Form action ve input keşfi
        - Meta etiket çıkarma (title, description, keywords)
        - Robots.txt kontrolü
        - Aynı domain sınırlaması (dış linkler ayrı listelenir)
    """

    # ── META ──────────────────────────────────────────────────────────────────
    Name = "Web Crawler"
    Description = "Hedef web sitesini tarayarak link, form ve meta bilgisi toplar"
    Author = "Mahmut P."
    Category = "auxiliary/utils"
    Version = "1.0"

    Requirements = {"python": ["requests", "beautifulsoup4"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "TARGET_URL": Option(
                name="TARGET_URL",
                value="http://127.0.0.1",
                required=True,
                description="Taranacak hedef URL (http/https ile başlamalı)",
            ),
            "MAX_DEPTH": Option(
                name="MAX_DEPTH",
                value=2,
                required=False,
                description="Maksimum tarama derinliği",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "MAX_PAGES": Option(
                name="MAX_PAGES",
                value=50,
                required=False,
                description="Taranacak maksimum sayfa sayısı",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "TIMEOUT": Option(
                name="TIMEOUT",
                value=5,
                required=False,
                description="HTTP istek zaman aşımı (saniye)",
                regex_check=True,
                regex=r"^\d+$",
            ),
            "USER_AGENT": Option(
                name="USER_AGENT",
                value="MahFramework-Crawler/1.0",
                required=False,
                description="HTTP User-Agent başlığı",
            ),
            "CHECK_ROBOTS": Option(
                name="CHECK_ROBOTS",
                value="true",
                required=False,
                description="Robots.txt kontrol et (true/false)",
                choices=["true", "false"],
            ),
        }
        for opt_name, opt_obj in self.Options.items():
            setattr(self, opt_name, opt_obj.value)

        self.console = Console()

    # ── YARDIMCI ─────────────────────────────────────────────────────────────

    @staticmethod
    def _same_domain(base_url: str, target_url: str) -> bool:
        """İki URL aynı domain'e mi ait?"""
        return urlparse(base_url).netloc == urlparse(target_url).netloc

    @staticmethod
    def _normalize_url(url: str) -> str:
        """URL'den fragment (#) kısmını çıkarır."""
        parsed = urlparse(url)
        return parsed._replace(fragment="").geturl()

    def _fetch_page(self, url: str, timeout: int, user_agent: str) -> tuple[str, int]:
        """Sayfa HTML içeriğini ve HTTP durum kodunu döner."""
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": user_agent},
                allow_redirects=True,
                verify=False,
            )
            return resp.text, resp.status_code
        except Exception:
            return "", 0

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """HTML'den tüm <a href> linklerini çıkarır."""
        links: list[str] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all("a", href=True):
                href = tag["href"]
                full = urljoin(base_url, href)
                full = self._normalize_url(full)
                if full.startswith(("http://", "https://")):
                    links.append(full)
        except Exception:
            pass
        return links

    def _extract_forms(self, html: str, base_url: str) -> list[dict[str, Any]]:
        """HTML'den form bilgilerini çıkarır."""
        forms: list[dict[str, Any]] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for form in soup.find_all("form"):
                action = form.get("action", "")
                method = form.get("method", "GET").upper()
                full_action = urljoin(base_url, action) if action else base_url
                inputs: list[dict[str, str]] = []
                for inp in form.find_all(["input", "textarea", "select"]):
                    inputs.append(
                        {
                            "name": inp.get("name", ""),
                            "type": inp.get("type", "text"),
                            "value": inp.get("value", ""),
                        }
                    )
                forms.append(
                    {
                        "action": full_action,
                        "method": method,
                        "inputs": inputs,
                    }
                )
        except Exception:
            pass
        return forms

    def _extract_meta(self, html: str) -> dict[str, str]:
        """HTML'den başlık ve meta etiketlerini çıkarır."""
        meta: dict[str, str] = {}
        try:
            soup = BeautifulSoup(html, "html.parser")
            title_tag = soup.find("title")
            if title_tag:
                meta["title"] = title_tag.get_text(strip=True)
            for tag in soup.find_all("meta"):
                name = tag.get("name", tag.get("property", ""))
                content = tag.get("content", "")
                if name and content:
                    meta[name.lower()] = content[:120]
        except Exception:
            pass
        return meta

    def _check_robots(self, base_url: str, timeout: int, user_agent: str) -> list[str]:
        """Robots.txt içeriğini çeker ve disallow kurallarını döner."""
        robots_url = urljoin(base_url, "/robots.txt")
        disallows: list[str] = []
        try:
            resp = requests.get(
                robots_url,
                timeout=timeout,
                headers={"User-Agent": user_agent},
                verify=False,
            )
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith("disallow:"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            disallows.append(path)
        except Exception:
            pass
        return disallows

    # ── RUN ──────────────────────────────────────────────────────────────────

    def run(self, options: dict[str, Any]) -> bool:
        target_url = str(options.get("TARGET_URL", ""))
        max_depth = int(options.get("MAX_DEPTH", 2))
        max_pages = int(options.get("MAX_PAGES", 50))
        timeout = int(options.get("TIMEOUT", 5))
        user_agent = str(options.get("USER_AGENT", "MahFramework-Crawler/1.0"))
        check_robots = str(options.get("CHECK_ROBOTS", "true")).lower() == "true"

        if not target_url.startswith(("http://", "https://")):
            print(
                "[bold red][-] TARGET_URL http:// veya https:// ile başlamalıdır.[/bold red]"
            )
            return False

        logger.info(f"Web crawler başlatıldı: {target_url}")

        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]🕸️  WEB CRAWLER — Bilgi Toplama[/bold cyan]",
                border_style="cyan",
            )
        )

        # ── Robots.txt ───────────────────────────────────────────────────
        if check_robots:
            disallows = self._check_robots(target_url, timeout, user_agent)
            if disallows:
                tbl = Table(
                    title="🤖 Robots.txt — Disallow Kuralları", border_style="yellow"
                )
                tbl.add_column("Yol", style="white")
                for d in disallows:
                    tbl.add_row(d)
                self.console.print(tbl)
                self.console.print()

        # ── BFS Tarama ────────────────────────────────────────────────────
        visited: set[str] = set()
        external_links: set[str] = set()
        all_forms: list[dict[str, Any]] = []
        page_info: list[dict[str, str]] = []

        queue: list[tuple[str, int]] = [(self._normalize_url(target_url), 0)]

        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)
            if url in visited or depth > max_depth:
                continue
            visited.add(url)

            html, status = self._fetch_page(url, timeout, user_agent)
            if not html or status == 0:
                continue

            # Meta
            meta = self._extract_meta(html)
            page_info.append(
                {
                    "url": url,
                    "status": str(status),
                    "title": meta.get("title", "-")[:60],
                }
            )

            # Formlar
            forms = self._extract_forms(html, url)
            all_forms.extend(forms)

            # Linkler
            links = self._extract_links(html, url)
            for link in links:
                if self._same_domain(target_url, link):
                    normalized = self._normalize_url(link)
                    if normalized not in visited:
                        queue.append((normalized, depth + 1))
                else:
                    external_links.add(link)

        # ── Sonuçları Göster ──────────────────────────────────────────────
        # Sayfalar
        tbl = Table(
            title=f"📄 Taranan Sayfalar ({len(page_info)})", border_style="blue"
        )
        tbl.add_column("#", style="dim", justify="right")
        tbl.add_column("URL", style="white", max_width=55)
        tbl.add_column("Status", justify="center")
        tbl.add_column("Başlık", style="cyan", max_width=40)

        for idx, p in enumerate(page_info, 1):
            color = "green" if p["status"] == "200" else "yellow"
            tbl.add_row(
                str(idx), p["url"], f"[{color}]{p['status']}[/{color}]", p["title"]
            )
        self.console.print(tbl)
        self.console.print()

        # Formlar
        if all_forms:
            tbl = Table(
                title=f"📝 Bulunan Formlar ({len(all_forms)})", border_style="red"
            )
            tbl.add_column("#", style="dim", justify="right")
            tbl.add_column("Action", style="white", max_width=50)
            tbl.add_column("Method", justify="center")
            tbl.add_column("Input Sayısı", justify="right")

            for idx, f in enumerate(all_forms, 1):
                tbl.add_row(str(idx), f["action"], f["method"], str(len(f["inputs"])))
            self.console.print(tbl)
            self.console.print()

        # Dış Linkler
        if external_links:
            tbl = Table(
                title=f"🔗 Dış Linkler ({len(external_links)})", border_style="dim"
            )
            tbl.add_column("#", style="dim", justify="right")
            tbl.add_column("URL", style="white", max_width=70)

            for idx, link in enumerate(sorted(external_links)[:30], 1):
                tbl.add_row(str(idx), link)
            if len(external_links) > 30:
                self.console.print(
                    f"  [dim]... ve {len(external_links) - 30} daha.[/dim]"
                )
            self.console.print(tbl)
            self.console.print()

        # Özet
        self.console.print(
            Panel.fit(
                f"[green]Sayfa:[/green] {len(page_info)}  |  "
                f"[yellow]Form:[/yellow] {len(all_forms)}  |  "
                f"[blue]Dış Link:[/blue] {len(external_links)}",
                title="📊 Özet",
                border_style="green",
            )
        )

        logger.info("Web crawler taraması tamamlandı")
        return True
