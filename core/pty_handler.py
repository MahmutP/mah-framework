# PTY Shell oturum yöneticisi.
# Penelope (brightio/penelope) tarzında tam etkileşimli PTY oturumları sağlar.
#
# Temel özellikler:
#   - Yerel terminali raw moda alarak Ctrl+C, Ctrl+Z, Tab, ok tuşlarını
#     uzak tarafa iletir (framework'ü sonlandırmaz).
#   - Terminal pencere boyutunu (TIOCGWINSZ) uzak tarafa senkronize eder.
#   - Uzak shell'i PTY'ye yükseltmek (upgrade) için birden fazla teknik dener.
#   - Güvenli çıkış: yerel terminal ayarları her durumda geri yüklenir.
#
# Bu dosya tamamen etik siber güvenlik amaçlıdır.

from __future__ import annotations

import contextlib
import fcntl
import os
import select
import signal
import struct
import sys
import termios
import time
import tty
from typing import Any

from rich import print


# ────────────────────────────────────────────────────────
# Upgrade Yardımcıları — Uzak shell'i PTY'ye yükseltir
# ────────────────────────────────────────────────────────

# Hedef sistemde PTY elde etmek için sırayla denenecek komutlar.
# İlk başarılı olan kullanılır.
UPGRADE_COMMANDS: list[dict[str, str]] = [
    {
        "name": "python3",
        "cmd": (
            "python3 -c '"
            "import pty; pty.spawn(\"/bin/bash\")'"
        ),
    },
    {
        "name": "python2",
        "cmd": (
            "python -c '"
            "import pty; pty.spawn(\"/bin/bash\")'"
        ),
    },
    {
        "name": "script",
        "cmd": "/usr/bin/script -qc /bin/bash /dev/null",
    },
    {
        "name": "socat",
        "cmd": (
            "socat exec:'bash -li',pty,stderr,setsid,sigint,sane -"
        ),
    },
    {
        "name": "perl",
        "cmd": (
            "perl -e '"
            "use POSIX; setsid(); "
            "exec {\"/bin/bash\"} \"bash\" "
            "or die \"exec: $!\";'"
        ),
    },
    {
        "name": "expect",
        "cmd": 'expect -c \'spawn bash; interact\'',
    },
]

# PTY upgrade sonrası uzak terminali yapılandırmak için gönderilecek komutlar.
PTY_NORMALIZE_COMMANDS: list[str] = [
    "export TERM=xterm-256color",
    "export SHELL=/bin/bash",
    "export HISTFILE=/dev/null",
    # stty satırları get_terminal_size() ile dinamik üretilir
]


def get_terminal_size() -> tuple[int, int]:
    """Yerel terminalin satır ve sütun sayısını döndürür."""
    try:
        result = fcntl.ioctl(
            sys.stdout.fileno(),
            termios.TIOCGWINSZ,
            b"\x00" * 8,
        )
        rows, cols = struct.unpack("HHHH", result)[:2]
        if rows > 0 and cols > 0:
            return rows, cols
    except (OSError, struct.error):
        pass
    # Yedek: ortam değişkenleri veya varsayılan
    try:
        cols, rows = os.get_terminal_size()
        return rows, cols
    except OSError:
        return 24, 80


def build_stty_command() -> str:
    """Mevcut terminal boyutuna göre 'stty rows .. cols ..' komutu üretir."""
    rows, cols = get_terminal_size()
    return f"stty rows {rows} cols {cols}"


def send_upgrade_payload(
    sock: Any,
    method: str | None = None,
    timeout: float = 2.0,
) -> bool:
    """
    Uzak shell'e PTY upgrade komutu gönderir.

    Args:
        sock: Uzak bağlantının soket nesnesi.
        method: Kullanılacak upgrade yöntemi (python3, python2, script, socat, perl, expect).
                None ise tüm yöntemler sırayla denenir.
        timeout: Her deneme için bekleme süresi (sn).

    Returns:
        True: Upgrade komutu başarıyla gönderildi (gerçek doğrulama
              interaktif oturumda yapılır).
    """
    commands = UPGRADE_COMMANDS
    if method:
        commands = [c for c in UPGRADE_COMMANDS if c["name"] == method]
        if not commands:
            print(f"[!] Bilinmeyen upgrade yöntemi: {method}")
            return False

    for entry in commands:
        try:
            payload = entry["cmd"] + "\n"
            sock.sendall(payload.encode("utf-8", errors="replace"))
            print(f"[*] PTY upgrade gönderildi ({entry['name']})")

            # Kısa süre bekle ve yanıt gelip gelmediğini kontrol et
            time.sleep(timeout)

            # Ortam değişkenlerini ve stty boyutunu ayarla
            normalize_cmds = PTY_NORMALIZE_COMMANDS + [build_stty_command()]
            for cmd in normalize_cmds:
                sock.sendall((cmd + "\n").encode("utf-8", errors="replace"))
                time.sleep(0.1)

            # clear ile ekranı temizle (opsiyonel, PTY varsa çalışır)
            sock.sendall(b"clear\n")
            return True

        except (OSError, BrokenPipeError) as exc:
            print(f"[!] Upgrade gönderme hatası ({entry['name']}): {exc}")
            continue

    return False


# ────────────────────────────────────────────────────────
# PTY Shell Döngüsü — Raw Terminal I/O
# ────────────────────────────────────────────────────────

# Oturum çıkış tuş kombinasyonu: Ctrl+] (0x1d — telnet escape key)
# Bu tuşa basıldığında PTY döngüsünden çıkılır (oturum açık kalır).
ESCAPE_CHAR = b"\x1d"  # Ctrl+]


class PTYSession:
    """
    Tam etkileşimli PTY oturumu.

    Yerel terminali raw moda alır, böylece Ctrl+C (\\x03), Ctrl+Z (\\x1a),
    Tab (\\x09), ok tuşları vb. doğrudan uzak tarafa iletilir.
    Framework sonlanmaz; oturumdan çıkmak için Ctrl+] (escape) kullanılır.

    Kullanım:
        pty_session = PTYSession(sock, session_id=1)
        pty_session.start()
    """

    def __init__(
        self,
        sock: Any,
        session_id: int | None = None,
        escape_char: bytes = ESCAPE_CHAR,
    ) -> None:
        self.sock = sock
        self.session_id = session_id
        self.escape_char = escape_char
        self.running = False

        # Orijinal terminal ayarları (geri yükleme için)
        self._old_tty_attrs: list[Any] | None = None
        self._old_sigwinch: Any = None
        self._old_sigint: Any = None
        self._old_sigtstp: Any = None

    def _save_terminal(self) -> None:
        """Mevcut terminal ayarlarını kaydeder."""
        if sys.stdin.isatty():
            self._old_tty_attrs = termios.tcgetattr(sys.stdin.fileno())

    def _restore_terminal(self) -> None:
        """Kaydedilmiş terminal ayarlarını geri yükler."""
        if self._old_tty_attrs is not None:
            with contextlib.suppress(termios.error):
                termios.tcsetattr(
                    sys.stdin.fileno(),
                    termios.TCSADRAIN,
                    self._old_tty_attrs,
                )
            self._old_tty_attrs = None

    def _set_raw_mode(self) -> None:
        """Terminali raw moda geçirir — tüm tuşlar aynen iletilir."""
        if sys.stdin.isatty():
            tty.setraw(sys.stdin.fileno())

    def _send_window_size(self) -> None:
        """Terminal boyutunu uzak tarafa bildirir."""
        try:
            rows, cols = get_terminal_size()
            stty_cmd = f"stty rows {rows} cols {cols}\n"
            self.sock.sendall(stty_cmd.encode("utf-8", errors="replace"))
        except (OSError, BrokenPipeError):
            pass

    def _on_sigwinch(self, signum: int, frame: Any) -> None:
        """Terminal yeniden boyutlandırıldığında pencere boyutunu iletir."""
        self._send_window_size()

    def _install_signal_handlers(self) -> None:
        """
        Sinyal yöneticilerini özelleştirir:
        - SIGWINCH: pencere boyutu değişikliği → uzak tarafa ilet
        - SIGINT (Ctrl+C): raw modda zaten socket'e gider, yine de güvence
        - SIGTSTP (Ctrl+Z): görmezden gel (raw modda gitmeyecek zaten)
        """
        self._old_sigwinch = signal.getsignal(signal.SIGWINCH)
        self._old_sigint = signal.getsignal(signal.SIGINT)
        self._old_sigtstp = signal.getsignal(signal.SIGTSTP)

        signal.signal(signal.SIGWINCH, self._on_sigwinch)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    def _restore_signal_handlers(self) -> None:
        """Orijinal sinyal yöneticilerini geri yükler."""
        if self._old_sigwinch is not None:
            signal.signal(signal.SIGWINCH, self._old_sigwinch)
        if self._old_sigint is not None:
            signal.signal(signal.SIGINT, self._old_sigint)
        if self._old_sigtstp is not None:
            signal.signal(signal.SIGTSTP, self._old_sigtstp)

    def start(self) -> None:
        """
        PTY oturumunu başlatır.
        Terminal raw moda alınır, sinyal yöneticileri kurulur ve
        stdin ↔ socket arasında byte düzeyinde çift yönlü aktarım başlar.

        Background alma:
          - Ctrl+]  (0x1d)  → oturum arka plana alınır, framework'e dönülür
          - Ctrl+Z  (0x1a)  → aynı (uzak PTY'ye Ctrl+Z göndermek için \\x1a\\x1a)
        """
        if not sys.stdin.isatty():
            print("[!] Stdin bir terminal değil — PTY oturumu başlatılamaz.")
            print("[*] Standart shell döngüsüne düşülüyor.")
            return

        label = f"Session {self.session_id}" if self.session_id else "PTY"
        sid_hint = (
            f"sessions -i {self.session_id}" if self.session_id is not None
            else "sessions -i <id>"
        )
        print(f"[*] PTY oturumu aktif ({label}).")
        print(f"[*] Background: Ctrl+]  veya  Ctrl+Z")
        print(f"[*] Geri dönünce: {sid_hint}")
        print(f"[*] Kapatmak için: sessions -k {self.session_id}" if self.session_id else "")
        print("-" * 55)

        self.running = True
        self._backgrounded = False
        self._save_terminal()
        try:
            self._install_signal_handlers()
            self._set_raw_mode()
            self._send_window_size()
            self._io_loop()
        finally:
            self.running = False
            self._restore_terminal()
            self._restore_signal_handlers()
            print()
            if getattr(self, "_backgrounded", False):
                print(f"[*] Oturum arka plana alındı ({label}).")
                if self.session_id is not None:
                    print(f"[*] Geri dönmek için: sessions -i {self.session_id}")
                    print(f"[*] Kapatmak için:    sessions -k {self.session_id}")
            else:
                print(f"[*] PTY oturumundan çıkıldı ({label}).")
                if self.session_id is not None:
                    print(f"[*] Oturum hâlâ açıksa: sessions -i {self.session_id}")

    def _io_loop(self) -> None:
        """
        Ana I/O döngüsü — byte düzeyinde stdin ↔ socket aktarımı.

        Escape tuşları (background yapar, oturumu kapatmaz):
          - Ctrl+]  0x1d  → PTY'den çık, framework'e dön
          - Ctrl+Z  0x1a  → aynı (raw modda SIGTSTP göndermez, background yapar)
            Not: Uzak PTY'ye Ctrl+Z göndermek istiyorsan iki kez bas: Ctrl+Z Ctrl+Z

        Ctrl+C (0x03) → doğrudan uzak tarafa gönderilir (uzak işlemi durdurur).
        """
        # Background escape karakterleri
        BG_CHARS = {b"\x1d", b"\x1a"}  # Ctrl+], Ctrl+Z

        stdin_fd = sys.stdin.fileno()
        _ctrlz_count = 0   # Ctrl+Z çift basma sayacı

        try:
            while self.running:
                try:
                    rlist, _, xlist = select.select(
                        [stdin_fd, self.sock], [], [self.sock], 0.5
                    )
                except (ValueError, OSError):
                    break

                if xlist:
                    # Soket exceptional state — bağlantı koptu
                    break

                for fd in rlist:
                    if fd == self.sock:
                        # ── Uzaktan gelen veri → stdout ──────────────────
                        try:
                            data = self.sock.recv(4096)
                        except (OSError, ConnectionError):
                            data = b""
                        if not data:
                            # Uzak shell kapandı (exit yazıldı vs.)
                            # _backgrounded False kalıyor → handler thread
                            # session_manager'ı temizleyecek.
                            os.write(
                                sys.stdout.fileno(),
                                "\r\n[!] Uzak shell kapandı.\r\n".encode("utf-8"),
                            )
                            self.running = False
                            break
                        os.write(sys.stdout.fileno(), data)

                    elif fd == stdin_fd:
                        # ── Yerel klavye → soket ─────────────────────────
                        try:
                            data = os.read(stdin_fd, 1024)
                        except OSError:
                            break

                        if not data:
                            # stdin kapandı
                            self._backgrounded = True
                            self.running = False
                            break

                        # Ctrl+] → her zaman background
                        if b"\x1d" in data:
                            self._backgrounded = True
                            self.running = False
                            break

                        # Ctrl+Z → çift basınca background, tekse uzak tarafa gönder
                        if data == b"\x1a":
                            _ctrlz_count += 1
                            if _ctrlz_count >= 2:
                                # İkinci Ctrl+Z → background
                                self._backgrounded = True
                                self.running = False
                                break
                            # İlk Ctrl+Z → uzak tarafa gönder (uzak işlemi durdurur)
                            try:
                                self.sock.sendall(data)
                            except (OSError, BrokenPipeError):
                                self.running = False
                                break
                            continue
                        else:
                            _ctrlz_count = 0  # Ctrl+Z sayacını sıfırla

                        try:
                            self.sock.sendall(data)
                        except (OSError, BrokenPipeError):
                            self.running = False
                            break

        except Exception as exc:
            self._last_error = str(exc)

    def stop(self) -> None:
        """Oturumu dışarıdan durdurmak için kullanılır."""
        self.running = False


# ────────────────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ────────────────────────────────────────────────────────

def upgrade_and_interact(
    sock: Any,
    session_id: int | None = None,
    method: str | None = None,
    auto_upgrade: bool = True,
) -> None:
    """
    Oturumu PTY'ye yükseltir (opsiyonel) ve tam etkileşimli PTY döngüsüne girer.

    Args:
        sock: Uzak bağlantının soket nesnesi.
        session_id: Oturum numarası.
        method: Upgrade yöntemi (None = otomatik dene).
        auto_upgrade: True ise upgrade payload'u gönderilir.
    """
    if auto_upgrade:
        print("[*] Shell PTY'ye yükseltiliyor...")
        success = send_upgrade_payload(sock, method=method)
        if not success:
            print("[!] PTY upgrade başarısız olabilir — yine de devam ediliyor.")

    session = PTYSession(sock, session_id=session_id)
    session.start()


def detect_shell_type(sock: Any, timeout: float = 3.0) -> str | None:
    """
    Uzak shell'in türünü tespit etmeye çalışır.
    'echo $SHELL' göndererek yanıtı okur.

    Returns:
        Shell yolu (örn: /bin/bash) veya None.
    """
    try:
        # Önce buffer'daki verileri temizle
        sock.setblocking(False)
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
        except (BlockingIOError, OSError):
            pass
        sock.setblocking(True)

        sock.sendall(b"echo __MAH_SHELL_DETECT__${SHELL}__MAH_END__\n")
        sock.settimeout(timeout)
        response = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b"__MAH_END__" in response:
                    break
            except TimeoutError:
                break

        sock.settimeout(None)
        decoded = response.decode("utf-8", errors="replace")
        if "__MAH_SHELL_DETECT__" in decoded and "__MAH_END__" in decoded:
            start = decoded.index("__MAH_SHELL_DETECT__") + len(
                "__MAH_SHELL_DETECT__"
            )
            end = decoded.index("__MAH_END__")
            shell_path = decoded[start:end].strip()
            if shell_path and "/" in shell_path:
                return shell_path
    except Exception:
        pass
    return None
