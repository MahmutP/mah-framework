"""
Uzak shell oturumu üzerinde komut çalıştırma yardımcıları.

Marker tabanlı komut gönderme protokolünün TEK uygulaması buradadır.
`remote_download`, `remote_creds` ve `remote_enum` modülleri bu yardımcıları
kullanır; böylece PTY/echo kaynaklı hatalar bir yer düzeltilir.

Neden özel bir protokol gerekli?
--------------------------------
Shell'e komut gönderip çıktıyı toplarken iki tuzak vardır:

1. **Prompt karışması**: PTY'li oturumlarda her çıktı satırının başına shell
   prompt'u eklenir ("bash-5.2$ <çıktı>"). Bu yüzden marker satırı,
   "satırın sonunda marker var mı" diye aranır; tam eşitlik işe yaramaz.

2. **Echo**: Terminal echo'su açıksa gönderdiğimiz komutun kendisi geri
   yazılır. Yankı satırı da marker'ları içerir. Yankı, komut ÇALIŞMADAN ÖNCE
   geldiği için "son geçen START" her zaman gerçek çıktının başıdır.
"""

import contextlib
import time
import uuid
from typing import Any

__all__ = [
    "drain_socket",
    "exec_on_session",
    "extract_marked",
    "has_marker_line",
    "probe_echo",
    "set_remote_echo",
    "split_lines",
    "wait_quiet",
]


def split_lines(data: bytes) -> list[str]:
    """Ham veriyi satırlara böler; PTY'nin eklediği \\r temizlenir."""
    return [
        line.rstrip("\r")
        for line in data.decode("utf-8", errors="replace").split("\n")
    ]


def is_marker_line(line: str, marker: str) -> bool:
    """
    Bu satır gerçek bir marker çıktısı mı?

    PTY'li oturumlarda terminal echo'su açıksa, gönderdiğimiz komutun
    KENDİSİ de satır sonunda marker ile biter ("... ; echo __MAH_x__END").
    Yalnızca "satır marker ile bitiyor" kontrolü bu satırı gerçek çıktı
    sanır ve komutun çıktısı yanlış kesilir.

    Ayırt edici özellik: gerçek marker çıktısında marker'san önce yalnızca
    PROMPT bulunur; yankı satırında ise mutlaka "echo " vardır.
    """
    if not line.endswith(marker):
        return False
    return "echo" not in line[: -len(marker)]


def has_marker_line(data: bytes, marker: str) -> bool:
    """Veri içinde marker ile BİTEN gerçek bir çıktı satırı var mı?"""
    return any(is_marker_line(line, marker) for line in split_lines(data))


def extract_marked(data: bytes, start_marker: str, end_marker: str) -> str:
    """START/END marker'ları arasındaki gerçek çıktıyı döndürür."""
    lines = split_lines(data)

    # Echo varsa komutun kendisi de marker ile biter; ama echo, komutun
    # ÇALIŞMASINDAN ÖNCE gelir. Bu yüzden son geçen START gerçek çıktıdır.
    last_start = -1
    for i, line in enumerate(lines):
        if is_marker_line(line, start_marker):
            last_start = i

    if last_start == -1:
        return "[Hata: yanit alinamadi] " + "\n".join(lines).strip()

    first_end = -1
    for i in range(last_start + 1, len(lines)):
        if is_marker_line(lines[i], end_marker):
            first_end = i
            break

    if first_end == -1:
        # END basılmadı → komut hata verdi veya zaman aşımına uğradı
        return (
            "[Hata: komut tamamlanmadi] "
            + "\n".join(lines[last_start + 1:]).strip()
        ).strip()

    return "\n".join(lines[last_start + 1:first_end]).strip()


def exec_on_session(sock: Any, command: str, timeout: float = 10.0) -> str:
    """Shell oturumuna komut gönderir ve marker tabanlı çıktıyı yakalar.

    Args:
        sock: Aktif oturum soketi.
        command: Uzak shell'de çalıştırılacak komut.
        timeout: Yanıt beklenecek en fazla saniye.

    Returns:
        str: START/END arasındaki çıktı. Hata durumunda "[Hata: ...]" ile
        dönmeye başlar, böylece çağıranlar `if "[Hata" in out` ile
        yakalayabilir.
    """
    marker = f"__MAH_{uuid.uuid4().hex[:12]}__"
    start_marker = f"{marker}START"
    end_marker = f"{marker}END"

    # Ayraç olarak ';' kullanılır, '&&' DEĞİL: keşif komutlarının çoğu
    # çıktı üretse de sıfır dışı kodla biter (`which dpkg apt brew`,
    # bulunamayan dosya, `grep` eşleşmemesi...). '&&' kullanılsaydı END
    # hiç basılmaz ve GEÇERLİ çıktı tamamen kaybolurdu.
    #
    # Çıkış koduna göre hata ÜRETİLMEZ: `grep`in eşleşme bulmaması da hata
    # değildir, boş sonuçtur. "[Hata ...]" yalnızca taşıma sorunlarını
    # (yanıt gelmemesi, komutun tamamlanmaması) bildirir.
    wrapped = f"echo {start_marker} ; {command} 2>/dev/null ; echo {end_marker}\n"

    try:
        _flush_input(sock)

        # Gönderim de zaman aşımına tabidir. `timeout` yalnızca yanıt
        # beklemesini kapsıyordu: hedef okumayı bırakırsa (kilitli shell,
        # dolu PTY satır tamponu, takılmış süreç) bloklayan `sendall`
        # handler thread'ini sonsuza kadar asılı tutuyordu. Böyle bir
        # oturum "canlı" görünür ama hiçbir komut alamaz.
        with contextlib.suppress(OSError):
            previous = sock.gettimeout()
            sock.settimeout(timeout)
            try:
                sock.sendall(wrapped.encode("utf-8", errors="replace"))
            except TimeoutError as exc:
                return f"[Hata: komut gonderilemedi ({type(exc).__name__})]"
            finally:
                sock.settimeout(previous)

        sock.settimeout(timeout)
        response = b""
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                response += chunk
                if has_marker_line(response, end_marker):
                    # Son çıktıyı da almak için kısa bir bekleme. Burada
                    # komutun TAM zaman aşımı kullanılırsa, uzak taraftan
                    # ek veri gelmediğinde her komut saniyelerce boşa
                    # bekler (20 komut = dakikalar). Ekranın kısa tutulması
                    # bu maliyeti 0.2s'e indirir.
                    time.sleep(0.05)
                    with contextlib.suppress(OSError):
                        previous = sock.gettimeout()
                        sock.settimeout(0.2)
                        try:
                            extra = sock.recv(65536)
                            if extra:
                                response += extra
                        finally:
                            sock.settimeout(previous)
                    break
            except TimeoutError:
                break
            except (BlockingIOError, OSError):
                break

        sock.settimeout(None)

        if not has_marker_line(response, end_marker):
            # END gelmedi: komut zaman aşımına uğradı ya da hata verdi.
            # Uzak shell hâlâ çalışıyor olabilir; sessizliğe kadar bekleyip
            # biriken çıktıyı alıyoruz. Aksi halde OTURUM SENKRONİZE OLMAZ
            # ve sonraki her komut, kuyrukta bekleyen çıktının içinde kalır
            # (tek bir yavaş komut zincirleme hatalara yol açar).
            with contextlib.suppress(OSError):
                _drain_until_quiet(sock, idle=0.5, max_wait=max(3.0, timeout / 2))

        return extract_marked(response, start_marker, end_marker)
    except Exception as exc:
        # Çağıranlar hatayı metin olarak görmeli: hata ayrı yolda yutulmaz.
        return f"[Hata: {exc}]"


def _drain_until_quiet(sock: Any, idle: float, max_wait: float) -> None:
    """Uzak taraf susana kadar okur; oturumu bir sonraki komuta hazırlar."""
    previous = sock.gettimeout()
    try:
        sock.settimeout(idle)
        end = time.time() + max_wait
        while time.time() < end:
            try:
                if not sock.recv(65536):
                    return
            except (TimeoutError, BlockingIOError):
                return
            except OSError:
                return
    finally:
        with contextlib.suppress(OSError):
            sock.settimeout(previous)


def _flush_input(sock: Any) -> None:
    """Sokette bekleyen eski veriyi atar (bloklamadan)."""
    try:
        sock.setblocking(False)
        try:
            while True:
                if not sock.recv(4096):
                    break
        except (BlockingIOError, OSError):
            pass
        sock.setblocking(True)
    except OSError:
        pass


def drain_socket(sock: Any, max_bytes: int = 262144) -> int:
    """
    Gönderim sırasında uzak tarafın echo/input çıktısını boşaltır.

    PTY/canonical echo açıksa uzak, gönderdiğimiz veriyi geri yazar; biz
    okumazsak receive buffer dolar ve iki taraf da bloklanır (deadlock).
    """
    drained = 0
    previous_timeout = None
    try:
        previous_timeout = sock.gettimeout()
        sock.settimeout(0)
        while drained < max_bytes:
            try:
                chunk = sock.recv(8192)
            except (BlockingIOError, InterruptedError, OSError):
                break
            if not chunk:
                break
            drained += len(chunk)
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            sock.settimeout(previous_timeout)
    return drained


def wait_quiet(sock: Any, idle: float = 0.3, max_wait: float = 30.0) -> None:
    """
    Uzak taraf veri göndermeyi bırakana kadar bekler (sessizlik penceresi).

    PTY'li oturumlarda her komutun echo'su gecikmeli dönebilir; yeni komutu
    bu sırada göndermek marker'ları echo çıktısının içinde kaybettirir.
    'idle' saniye boyunca veri gelmezse oturum sessiz sayılır.
    """
    previous_timeout = None
    deadline = time.time() + max_wait
    try:
        previous_timeout = sock.gettimeout()
        sock.settimeout(idle)
        while time.time() < deadline:
            try:
                if not sock.recv(65536):
                    return
            except (TimeoutError, BlockingIOError, OSError):
                return
    finally:
        with contextlib.suppress(OSError):
            sock.settimeout(previous_timeout)


def probe_echo(sock: Any, timeout: float = 5.0) -> bool:
    """
    PTY yankısının (echo) açık olup olmadığını ham akıştan doğrular.

    Tek bir token yankılanırsa stream'de İKİ kez görünür. `stty -echo`
    sessizce başarısız olabildiği için (örn. uzak tarafta `stty` yoksa)
    büyük veri göndermeden önce bu kontrol yapılmalıdır: yankı açıkken
    yığınsal gönderim, readline redisplay'i yüzünden uzak shell'in komut
    satırlarını bozar (hatta shell'i kapatır).

    Returns:
        bool: Yankı AÇIKSA True.
    """
    token = f"MAHEPROBE{uuid.uuid4().hex[:8]}"
    needle = token.encode()
    buffer = b""
    try:
        _flush_input(sock)
        sock.sendall(f"echo {token}\n".encode())
        sock.settimeout(timeout)
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                chunk = sock.recv(4096)
            except (TimeoutError, BlockingIOError, OSError):
                break
            if not chunk:
                break
            buffer += chunk
            if buffer.count(needle) >= 2:
                break
            if needle in buffer:
                # Yankı gecikmeli gelebilir, kısa bir süre daha dinle.
                # Bu recv KISA zaman aşımlı olmalı: yanıt zaten tamamsa
                # (token göründü) ek veri gelmeyecek ve tam `timeout`
                # kadar bloklanacaktık. Uzak taraf tek pakette yanıt
                # verdiğinde (reverse shell'de normal durum) her modül
                # koşusu 10 saniye kaybediyordu.
                time.sleep(0.2)
                with contextlib.suppress(OSError):
                    previous = sock.gettimeout()
                    sock.settimeout(0.2)
                    try:
                        extra = sock.recv(4096)
                        if extra:
                            buffer += extra
                    finally:
                        sock.settimeout(previous)
                break
        sock.settimeout(None)
    except OSError:
        return False
    return buffer.count(needle) > 1


def set_remote_echo(sock: Any, enabled: bool, timeout: float = 10.0) -> bool:
    """
    PTY'li oturumlarda uzak terminal echo'sunu kapatır/açar.

    Echo açıkken gönderdiğimiz her komut geri yazılır; bu hem çıktıyı
    kirletir hem de büyük yüklemelerde receive buffer'ı doldurup iki tarafı
    da bloklar. Socket tabanlı (PTY'siz) oturumlarda komut sessizce
    başarısız olur, bu yüzden hata yutulur.

    Returns:
        bool: echo kapatma isteği başarılıysa True.
    """
    command = "stty echo" if enabled else "stty -echo"

    # Bu komut BİLEREK marker ayrıştırmasıyla gönderilmez. Echo açıkken
    # marker protokolü güvenilir değildir (yankı satırı da marker ile
    # biter) — bu bir tavuk-yumurta sorunudur: echo'yu kapatmak için
    # marker'a ihtiyaç duyulursa hiçbir zaman kapanamaz. `stty` tek başına
    # çalışan kısa bir komuttur; yanıtı şekil olarak değil, sessizlik
    # ölçütüyle bekleriz. Doğrulama aşağıdaki probe ile yapılır.
    with contextlib.suppress(OSError):
        _flush_input(sock)
        sock.sendall(f"{command}\n".encode())
        _drain_until_quiet(sock, idle=0.4, max_wait=min(timeout, 5.0))

    if enabled:
        return True
    return not probe_echo(sock, timeout)


def prepare_remote(
    sock: Any, timeout: float = 10.0, warn: Any = None
) -> bool:
    """
    Transfer öncesi uzak oturumu hazırlar: echo'yu kapatır ve doğrular.

    Args:
        sock: Aktif oturum soketi.
        timeout: `stty`/probe zaman aşımı.
        warn: Echo kapanmadıysa çağrılacak uyarı fonksiyonu (opsiyonel).

    Returns:
        bool: Yankı kapalıysa (veya zaten yoksa) True.
    """
    set_remote_echo(sock, False, timeout)
    echo_on = probe_echo(sock, timeout)
    if echo_on and callable(warn):
        warn()
    return not echo_on
