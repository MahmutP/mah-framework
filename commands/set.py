import difflib
import os
from typing import Any

from rich import print

from core.command import Command
from core.module import BaseModule
from core.shared_state import shared_state


def _active_session_ids() -> list[str]:
    """Aktif oturum ID'lerini listeler (SESSION tamamlama/ipuçları için)."""
    sm = shared_state.session_manager
    if not sm:
        return []
    try:
        return [str(sid) for sid in sorted(sm.get_all_sessions().keys())]
    except Exception:
        return []


def _session_label(session_id: str) -> str:
    """Oturum için kısa açıklama üretir (host:port veya tip)."""
    sm = shared_state.session_manager
    if not sm:
        return ""
    try:
        session = sm.get_session(int(session_id)) or {}
    except (TypeError, ValueError):
        return ""
    info = session.get("info", {}) or {}
    host = info.get("host", "")
    port = info.get("port", "")
    if host and port:
        return f"{host}:{port}"
    return str(info.get("type", "") or "")


class Set(Command):
    """option'ları değiştirmeye yarıyan komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """

    Name = "set"
    Description = "Seçili modülün seçeneklerini ayarlar."
    Category = "module"
    Aliases = []
    Usage = "set <seçenek_adı> <değer>"
    Examples = [
        "set RHOSTS 192.168.1.1",
        "set RPORT 21",
        'set TEXT "test mesajı"',
        "set ALGORITHM sha256",
    ]

    def __init__(self) -> None:
        """init fonksiyon"""
        super().__init__()
        self.completer_function = self._set_completer

    def _get_path_completions(
        self, current_input: str, default_dir: str = ".", extensions: list | None = None
    ) -> list[str]:
        """Dosya yolu tamamlama mantığı.

        Args:
            current_input: Kullanıcının girdiği kısmi yol.
            default_dir: Varsayılan dizin.
            extensions: Sadece bu uzantılara sahip dosyaları göster (örn: ['.jpg', '.png']).
                        None ise tüm dosyalar gösterilir. Dizinler her zaman gösterilir.
        """
        # Eğer input boşsa varsayılan dizini kullan
        if not current_input:
            path = default_dir
        else:
            path = current_input

        dirname, basename = os.path.split(path)
        if not dirname:
            dirname = "."

        suggestions = []
        try:
            if os.path.isdir(dirname):
                for name in os.listdir(dirname):
                    # Uzantı filtresi aktifse gizli dosyaları (. ile başlayan) atla
                    if extensions and name.startswith("."):
                        continue

                    if name.startswith(basename):
                        full_path = os.path.join(dirname, name)
                        # Eğer varsayılan dizin "." ise ve input boşsa "./" ekleme
                        if dirname == ".":
                            full_path = name

                        actual_path = os.path.join(dirname, name)
                        if os.path.isdir(actual_path):
                            suggestions.append(full_path + "/")
                        else:
                            # Uzantı filtresi varsa kontrol et
                            if extensions:
                                _, ext = os.path.splitext(name)
                                if ext.lower() not in extensions:
                                    continue
                            suggestions.append(full_path)
        except Exception:
            pass

        return sorted(suggestions)

    def _set_completer(self, text: str, word_before_cursor: str) -> list[str]:
        """set komutunun otomatik tamamlaması.

        Args:
            text (str): text girdi.
            word_before_cursor (str): imlecin solundaki text.

        Returns:
            List[str]: otomatik tamamlama listesi.
        """
        parts = text.split()
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            return []
        options = selected_module.get_options()

        # "set " yazıldığında option isimlerini göster
        if len(parts) == 1 and text.endswith(" "):
            return sorted(list(options.keys()))

        # "set TEX" yazıldığında option isimlerini tamamla
        elif len(parts) == 2 and not text.endswith(" "):
            current_arg = parts[1]
            exact = [name for name in options if name.startswith(current_arg)]
            if exact:
                return sorted(exact)
            # Büyük/küçük harf ve Türkçe harf duyarsız öneri (SESS -> SESSION)
            prefix = selected_module._normalize_option_key(current_arg)
            if prefix:
                return sorted(
                    name
                    for name in options
                    if selected_module._normalize_option_key(name).startswith(prefix)
                )
            return []

        # "set OPTION_NAME " yazıldığında değeri tamamla
        elif len(parts) == 2 and text.endswith(" "):
            option_name = parts[1]
            if option_name in options:
                opt = options[option_name]

                # 1. Dosya yolu tamamlama önceliği: Option içinde tanımlı dizin
                if hasattr(opt, "completion_dir") and opt.completion_dir:
                    exts = getattr(opt, "completion_extensions", None)
                    return self._get_path_completions(
                        "", default_dir=opt.completion_dir, extensions=exts
                    )

                # 2. Choices varsa (Öncelikli)
                if opt.choices:
                    return [str(c) for c in opt.choices]

                # 2b. SESSION gibi seçenekler: aktif oturum ID'lerini öner
                if "SESSION" in option_name.upper():
                    return _active_session_ids()

                # 3. İsim bazlı tahmin (Fallback)
                if "WORDLIST" in option_name.upper():
                    return self._get_path_completions(
                        "", default_dir="config/wordlists/"
                    )
                elif any(x in option_name.upper() for x in ["FILE", "PATH"]):
                    return self._get_path_completions("")

                # 3. Boolean tahmin
                current_val = str(opt.value).lower()
                if current_val in ["true", "false", "0", "1", "yes", "no"]:
                    return ["true", "false"]
            return []

        # "set OPTION_NAME deger" yazıldığında
        elif len(parts) >= 3:
            option_name = parts[1]
            current_value = parts[2] if len(parts) > 2 else ""

            if option_name in options:
                opt = options[option_name]

                # 1. Dosya yolu tamamlama
                if hasattr(opt, "completion_dir") and opt.completion_dir:
                    exts = getattr(opt, "completion_extensions", None)
                    return self._get_path_completions(
                        current_value, default_dir=opt.completion_dir, extensions=exts
                    )

                choices = []
                if opt.choices:
                    choices = [str(c) for c in opt.choices]
                else:
                    # İsim bazlı tahmin (Fallback) - Sadece choices yoksa bak
                    if "WORDLIST" in option_name.upper():
                        return self._get_path_completions(
                            current_value, default_dir="config/wordlists/"
                        )
                    elif any(x in option_name.upper() for x in ["FILE", "PATH"]):
                        return self._get_path_completions(current_value)
                    elif "SESSION" in option_name.upper():
                        return sorted(
                            c for c in _active_session_ids()
                            if c.startswith(current_value)
                        )

                    current_val = str(opt.value).lower()
                    if current_val in ["true", "false", "0", "1", "yes", "no"]:
                        choices = ["true", "false"]
                return sorted(
                    [c for c in choices if c.lower().startswith(current_value.lower())]
                )
            return []

        return []

    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalıştırılacak çalışacak kod.

        Returns:
            bool: Başarılı olup olmadığının sonucu.
        """
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            print(
                "Herhangi bir modül seçili değil. Lütfen önce 'use <modül_yolu>' komutunu kullanın."
            )
            return False
        if len(args) < 1:
            print("Kullanım: set <seçenek_adı> <değer>")
            return False

        # 'set SESSION 1' ve 'set SESSION=1' sözdizimlerinin ikisini de kabul et
        if len(args) == 1 and "=" in args[0]:
            option_name, _, option_value = args[0].partition("=")
        elif len(args) >= 2:
            option_name = args[0]
            option_value = " ".join(args[1:])
        else:
            print("Kullanım: set <seçenek_adı> <değer>")
            return False

        options = selected_module.get_options()

        if option_name in options or selected_module.resolve_option_name(option_name):
            if selected_module.set_option_value(option_name, option_value):
                # Çıktı formatı ve rengi düzeltildi
                print(f"{option_name} => {option_value}")
                return True
            else:
                print(
                    f"Seçenek '{option_name}' değeri '{option_value}' olarak ayarlanamadı. Regex kontrolü başarısız olabilir."
                )
                return False

        # ── Seçenek bulunamadı: yardımcı ipuçları ver ──────────────────
        print(
            f"Seçenek '{option_name}' bulunamadı. "
            "'show options' ile mevcut seçenekleri listeleyebilirsiniz."
        )

        # Büyük/küçük harf ya da yazım hatasına yakın öneri (SESSION/sesion/SESİON)
        close = difflib.get_close_matches(
            option_name, list(options.keys()), n=3, cutoff=0.6
        )
        if not close:
            close = difflib.get_close_matches(
                selected_module._normalize_option_key(option_name),
                [selected_module._normalize_option_key(o) for o in options],
                n=3,
                cutoff=0.6,
            )
        if close:
            print(
                "  [dim]Bunu mu demek istediniz? "
                + ", ".join(f"[cyan]{c}[/cyan]" for c in close)
                + f"  →  set {close[0]} <değer>[/dim]"
            )

        # SESSION özelinde aktif oturumları göster (yoksa en sık hata nedeni)
        if "SESSION" in option_name.upper() or any(
            "SESSION" in c.upper() for c in close
        ):
            session_ids = _active_session_ids()
            if session_ids:
                details = [
                    f"[cyan]{sid}[/cyan]"
                    + (f" [dim]({_session_label(sid)})[/dim]" if _session_label(sid) else "")
                    for sid in session_ids
                ]
                print(
                    "  [green]Aktif oturumlar:[/green] "
                    + "  ".join(details)
                    + f"\n  →  set SESSION {session_ids[0]}"
                )
            else:
                print(
                    "  [yellow]Aktif oturum yok.[/yellow] "
                    "Önce bir payload çalıştırın, sonra 'sessions -l' ile listeleyin."
                )
        return False
