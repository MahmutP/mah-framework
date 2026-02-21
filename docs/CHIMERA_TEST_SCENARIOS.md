# 🧪 Chimera Test Scenarios / Chimera Test Senaryoları Dokümantasyonu

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

This document provides a comprehensive list of test scenarios for verifying all functionalities of the **Chimera** payload system. Each scenario describes the steps to execute and the expected result.

### 🔌 Core Connection Tests

**Scenario 1.1: Basic Reverse TCP Connection Test**
*   **Steps:** Start the handler module -> Execute the agent on the target machine -> Check connection in the framework.
*   **Expected Result:** A successful SSL handshake occurs, and the `sysinfo` is automatically retrieved and printed upon the opening of a new session.

**Scenario 1.2: Reconnection Test**
*   **Steps:** Disconnect the session forcibly (`kill`) or close the handler -> Wait for the agent to attempt to reconnect.
*   **Expected Result:** The agent retries connecting in the background up to the configured `MAX_RECONNECT` limit. If the handler comes back online before the limit is reached, a new session is established.

**Scenario 1.3: HTTP Obfuscation Verification**
*   **Steps:** Capture the network traffic between the agent and handler using Wireshark. Analyze the data packets.
*   **Expected Result:** The initial connection resembles normal HTTP web traffic (GET/POST headers). Following the handshake, the encrypted data stream begins.

---

### 💻 Command Execution & Shell Tests

**Scenario 2.1: Basic Command Execution**
*   **Commands:** `whoami`, `hostname`, `ipconfig` (Windows) or `ifconfig` (Linux).
*   **Expected Result:** The commands are executed on the target system, and their output is retrieved encrypted.

**Scenario 2.2: Shell Spawning Test**
*   **Steps:** Type the `shell` command -> Enter interactive commands (`pwd`, `dir`, `cat /etc/passwd`) -> Type `exit`.
*   **Expected Result:** An interactive, real-time system terminal is provided. The `exit` command gracefully closes the system shell and returns the user to the `chimera` prompt.

**Scenario 2.3: In-Memory Module Loading Test**
*   **Steps:** Run `loadmodule <some_python_file>` -> Run `runmodule <module_name>`.
*   **Expected Result:** The python module operates correctly entirely from memory. Checking the target's disk must confirm that no intermediate `.py` files were created.

---

### 📁 File Operations Tests

**Scenario 3.1: File Upload Test**
*   **Steps:** Execute `upload test_local.txt /tmp/test_remote.txt` (or equivalent Windows path) -> Verify file existence on the target.
*   **Expected Result:** The file is completely transferred using chunking (even if it's large) and successfully saved at the destination.

**Scenario 3.2: File Download Test**
*   **Steps:** Execute `download C:\Windows\System32\drivers\etc\hosts ./target_hosts.txt` -> Check the local file.
*   **Expected Result:** The exact file is securely downloaded to the attacker's machine. The hash of the downloaded file matches the original.

**Scenario 3.3: Directory Navigation Test**
*   **Steps:** Use commands like `cd /tmp`, `ls`, `mkdir test_dir`, `rm test_dir`.
*   **Expected Result:** The current working directory updates correctly. Folders are created and deleted as requested.

---

### 👁️ Surveillance Tests

**Scenario 4.1: Screenshot Capture**
*   **Steps:** Enter the `screenshot` command -> Check the output file on the local machine.
*   **Expected Result:** A clean image of the target's display is downloaded directly over RAM without dropping an image file on the target machine's disk.

**Scenario 4.2: Keylogger Test**
*   **Steps:** Enter `keylogger_start` -> Type some keys on the target machine -> Enter `keylogger_dump` -> Enter `keylogger_stop`.
*   **Expected Result:** The keystrokes typed during the active logging session are successfully dumped. The process terminates correctly after the stop command.

---

### 🛡️ Evasion & Persistence Tests

**Scenario 5.1: AMSI Bypass Verification (Windows Only)**
*   **Steps:** Type `amsi_bypass` -> Enter the `shell` -> Attempt to run a PowerShell command that normally trips Windows Defender (e.g., loading a known signature).
*   **Expected Result:** The AMSI patch allows the execution of the command without being blocked or triggering a Defender alert.

**Scenario 5.2: Persistence Installation Test**
*   **Steps:** Run `persistence_install` -> Restart the target machine -> Have the handler listening.
*   **Expected Result:** After the reboot, the payload runs via the established backdoor (e.g., Registry key or Cron), and a new session drops into the handler.

---

### 🌐 Networking Tests

**Scenario 6.1: Port Forwarding Test**
*   **Steps:** Execute `portfwd add -l 8080 -p 80 -r 127.0.0.1` -> Browse to `http://localhost:8080` locally.
*   **Expected Result:** The port tunneling successful connects you to the target machine's local port 80. Data moves smoothly.

**Scenario 6.2: Network Scanning Test**
*   **Steps:** Run an internal network scan via `netscan sweep 192.168.1.0/24`.
*   **Expected Result:** Live IP addresses and potentially open ports from the target's connected internal network are listed.

---
---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu belge, **Chimera** payload sisteminin tüm işlevlerini doğrulamak için hazırlanmış kapsamlı test senaryolarını içerir. Her senaryo, izlenecek adımları ve beklenen sonucu açıklar.

### 🔌 Temel Bağlantı Testleri

**Senaryo 1.1: Basit Reverse TCP Bağlantı Testi**
*   **Adımlar:** Handler'ı başlatın -> Hedef makinede agent'ı çalıştırın -> Framework'te bağlantıyı kontrol edin.
*   **Beklenen Sonuç:** Başarılı bir SSL/TLS handshake gerçekleşir, yeni oturum (session) açıldığı an hedefin `sysinfo` bilgisi otomatik olarak alınır ve ekrana basılır.

**Senaryo 1.2: Yeniden Bağlanma (Reconnect) Testi**
*   **Adımlar:** Handler'ı kapatın veya `kill` komutuyla session'ı düşürün -> Agent'ın yeniden bağlanmasını bekleyin.
*   **Beklenen Sonuç:** Agent, ayarlanan `MAX_RECONNECT` limiti kadar arka planda bağlantı denemeye devam eder. Limit dolmadan handler tekrar açılırsa, bağlantı başarıyla tekrar kurulur.

**Senaryo 1.3: HTTP Obfuscation Doğrulama**
*   **Adımlar:** Wireshark kullanarak agent ve handler arasındaki ağ trafiğini izleyin. Veri paketlerini analiz edin.
*   **Beklenen Sonuç:** İlk bağlantı (SSL anlaşması öncesi payload stage) sıradan bir HTTP web trafiği (GET/POST) gibi görünür. Handshake sonrasında veriler AES ile tamamen şifrelenmiş akar.

---

### 💻 Komut Yürütme & Shell Testleri

**Senaryo 2.1: Basit Komut Çalıştırma**
*   **Komutlar:** `whoami`, `hostname`, `ipconfig` (Windows) veya `ifconfig` (Linux).
*   **Beklenen Sonuç:** Sistem komutları hedef cihazda başarıyla native olarak işletilir ve şifrelenmiş komut çıktısı okunarak ekrana gelir.

**Senaryo 2.2: Shell Spawning Testi**
*   **Adımlar:** `shell` yazıp enter'a basın -> Etkileşimli komutlar girin (`pwd`, `dir`, `cat vb.`) -> `exit` yazın.
*   **Beklenen Sonuç:** Gerçek zamanlı ve interaktif sistem terminali açılır (`bash` veya `cmd`). `exit` komutu shell processini güvenli bir şekilde kapatarak sizi tekrar `chimera` prompt satırına döndürür.

**Senaryo 2.3: In-Memory Modül Yükleme (Disk İzsiz)**
*   **Adımlar:** `loadmodule ornek_modul.py` komutuyla dosyayı yükleyin -> `runmodule ornek_modul` diyerek çalıştırın.
*   **Beklenen Sonuç:** Yüklenen Python modülü sadece hedefin RAM hafızasında çalışır. İşlem sırasında hedefin diskine herhangi bir `py` dosyası yazılmamalıdır.

---

### 📁 Dosya İşlemleri Testleri

**Senaryo 3.1: Dosya Yükleme (Upload) Testi**
*   **Adımlar:** `upload yerel.txt /tmp/hedef.txt` (veya uygun Windows yolu) komutunu yürütün -> Hedef diskte kontrol edin.
*   **Beklenen Sonuç:** Dosya parça parça (chunk) iletilir. Boyutu büyük olsa bile sorunsuzca hedef dizine kaydedilir.

**Senaryo 3.2: Dosya İndirme (Download) Testi**
*   **Adımlar:** `download C:\Windows\System32\drivers\etc\hosts ./yerel_hosts.txt` komutunu uygulayın -> İndirilen dosyayı kontrol edin.
*   **Beklenen Sonuç:** Talep edilen dosya eksiksiz indirilir. Dosya hash (özeti) hedefteki orijinal dosya ile birebir aynı olur.

**Senaryo 3.3: Dizin Gezinme Testi**
*   **Adımlar:** `cd /tmp`, `ls`, `mkdir testklasor`, `rm testklasor` gibi komutlarla klasör işlemleri yapın.
*   **Beklenen Sonuç:** Geçerli çalışma yolu doğru şekilde güncellenir. İstenen klasörler oluşturulur ve silinir.

---

### 👁️ Gözetleme Testleri

**Senaryo 4.1: Ekran Görüntüsü Alma (Screenshot)**
*   **Adımlar:** `screenshot` komutunu verin -> Kendi makinenizde indirilen resmi kontrol edin.
*   **Beklenen Sonuç:** Kullanıcı ekranının o anki anlık durumu hedefin diskine hiçbir PNG veya JPG kaydedilmeden doğrudan RAM üzerinden saldırganın makinesine ulaştırılır.

**Senaryo 4.2: Keylogger Testi**
*   **Adımlar:** `keylogger_start` komutunu verin -> Kurban makinede birkaç tuşa basın -> `keylogger_dump` komutu ile logları çekin -> `keylogger_stop` komutu ile durdurun.
*   **Beklenen Sonuç:** Yazılan tüm tuş vuruşları başarıyla exfiltre edilir. Stop komutu sonrasında kayıt işlemi kesinlikle durarak bellekte bırakılmaz.

---

### 🛡️ Gizlenme & Kalıcılık Testleri

**Senaryo 5.1: AMSI Bypass Doğrulama (Windows Özel)**
*   **Adımlar:** Cihazda `amsi_bypass` komutunu kullanıp belleği yamalayın -> `shell` içerisine girin -> Windows Defender'ın imzasına sahip yasaklı bir PowerShell kodu (Mimikatz load vb.) çalıştırmayı deneyin.
*   **Beklenen Sonuç:** Powershell komutu Defender tarafından tespit edilmez veya engellenmeden başarı ile yürütülür.

**Senaryo 5.2: Kalıcılık (Persistence) Kurulumu Testi**
*   **Adımlar:** `persistence_install` çalıştırın -> Hedef bilgisayarı yeniden başlatın (Dört gözle `handler` açık)
*   **Beklenen Sonuç:** Bilgisayar yeniden başlar başlamaz (veya kullanıcı girişinde) yerleştirilen kalıcılık yöntemi tetiklenir ve yeni sistem oturumu `handler` üzerine eklenir.

---

### 🌐 Ağ İşlemleri Testleri

**Senaryo 6.1: Port Forwarding Testi**
*   **Adımlar:** `portfwd add -l 8080 -p 80 -r 127.0.0.1` çalıştırıp port tünelini açın -> Kendi bilgisayarınızda bir tarayıcıdan `http://localhost:8080` adresine gidin.
*   **Beklenen Sonuç:** Trafik Chimera ajanı üzerinden kurban makinenin lokal port 80 bağlantısına yönlendirilir, yanıt görüntülenir.

**Senaryo 6.2: Network Scanning (Ağ Taraması) Testi**
*   **Adımlar:** Kurbanın bulunduğu ağ genelinde tarama yapmak için `netscan sweep 192.168.1.0/24` tetikleyin.
*   **Beklenen Sonuç:** O alt-ağ üzerinde aktif olan IP adresleri ve tespit edilen açık bağlantı noktaları konsolda düzgün yapılandırılmış halde listelenir.
