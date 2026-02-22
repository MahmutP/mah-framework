# ⚠️ Chimera Edge Cases & Error Handling Guide / Hata Durumları ve Kenar Senaryolar Rehberi

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

This document covers the edge cases, failure conditions, and unexpected scenarios that the **Chimera** payload system may encounter during operation. For each scenario, the expected agent behavior (graceful degradation, automatic recovery, and error logging) is defined.

---

### 1. Network and Connectivity Failures

#### 1.1. Sudden Network Disconnection

**Scenario:** The network cable is pulled, Wi-Fi drops, or the NAT session expires mid-session.

**Expected Behavior:**
- `recv_data()` or `send_data()` raises a `socket.error` / `ssl.SSLError`.
- The main loop (`run()`) catches the exception and immediately calls `reconnect()`.
- `reconnect()` closes the broken socket via `close_socket()` and enters a retry loop.
- It waits `RECONNECT_DELAY` seconds between each attempt, up to `MAX_RECONNECT` retries.
- If `MAX_RECONNECT` is set to `-1`, the agent retries indefinitely until the network returns.
- If the retry limit is exceeded, the agent exits cleanly without leaving orphan threads.

**Verification Steps:**
1. Establish a live Chimera session.
2. Disable the network interface on the target machine.
3. Observe the handler — it should report the session as `dead`.
4. Re-enable the network interface.
5. Confirm the agent automatically reconnects and a new session appears.

---

#### 1.2. Handler Crash / Restart

**Scenario:** The framework (handler) process crashes or is intentionally restarted on the attacker machine.

**Expected Behavior:**
- `connect()` returns `False` on the next attempt because the server port is no longer listening.
- The `reconnect()` loop continues trying at `RECONNECT_DELAY` intervals.
- Once the handler is restarted and re-listening, the agent successfully reconnects.
- `send_sysinfo()` is called again after reconnection, re-registering the agent identity.

**Verification Steps:**
1. Start a session. Then kill the handler process (`Ctrl+C` or `kill <pid>`).
2. Wait and observe the agent's reconnect loop (visible via process monitor or debug log).
3. Restart the handler.
4. Confirm session is re-established and `sysinfo` data is received.

---

#### 1.3. Firewall / Port Blocking

**Scenario:** A host-based or network firewall starts blocking the agent's outbound port mid-session.

**Expected Behavior:**
- `connect()` raises a `ConnectionRefusedError` or times out after 30 seconds (`sock.settimeout(30)`).
- The exception is caught; `reconnect()` cycles with the configured delay.
- The agent does **not** crash, does **not** loop infinitely without sleeping, and does **not** consume 100% CPU.
- If the firewall rule is later removed, the next `connect()` attempt succeeds.

**Verification Steps:**
1. Establish a session.
2. On the target, add a firewall rule blocking outbound traffic on `LPORT`.
3. Confirm session drops, and agent enters reconnect loop silently.
4. Remove the firewall rule.
5. Confirm session is automatically restored.

---

### 2. Resource Exhaustion

#### 2.1. Insufficient Disk Space

**Scenario:** Commands like `download` (writing received data to disk) or `screenshot` are executed when the target's disk is full.

**Expected Behavior:**
- File write operations raise `IOError` / `OSError` with `errno.ENOSPC`.
- The relevant command handler catches the exception and returns a descriptive error string to the handler (e.g., `[!] Error: No space left on device`).
- The agent **does not crash**; the main C2 loop continues normally.
- The session remains alive and subsequent commands continue to work.

**Verification Steps:**
1. Fill the target's disk to 100% (e.g., `dd if=/dev/zero of=/tmp/filler bs=1M` on Linux).
2. From the handler, issue a `download /etc/passwd out.txt` command.
3. Confirm an error message is returned to the handler, not a crash.
4. Issue `sysinfo` next — confirm the session is still active.

---

#### 2.2. High CPU / RAM Utilization

**Scenario:** The target system's CPU or RAM is near or at 100% from other processes.

**Expected Behavior:**
- The Chimera agent is designed to be lightweight; it only performs I/O-bound operations in its main loop (waiting on `recv_data()`).
- Under high CPU load, command execution may be slow, but the agent must not timeout or crash.
- Shell spawning (`shell` command) and in-memory module loading (`loadmodule`) may take longer but must return results eventually.
- The agent must **not** add to CPU pressure; idle CPU usage must remain near **0%**.

**Verification Steps:**
1. Stress the target CPU using a load tool (e.g., `stress --cpu 8` or a CPU-intensive script).
2. Issue several Chimera commands from the handler.
3. Confirm the session remains active and commands return results (with possible delay).
4. Stop the stress load and confirm response times normalize.

---

### 3. Antivirus / EDR Interference

#### 3.1. Process Termination by Antivirus

**Scenario:** The AV/EDR product detects and terminates the Chimera agent process.

**Expected Behavior:**
- Once the process is killed, the connection drops and the session in the handler becomes `dead`.
- There is no built-in resurrection mechanism at kernel level for this scenario — the agent process is gone.
- **Mitigation strategy:** Use `persistence_install` before AV activity occurs so the agent is relaunched after the next reboot or scheduled trigger.
- **Detection:** Handler should notify the operator when a session drops unexpectedly.

**Verification Steps:**
1. Establish a session (use obfuscated build: `set OBFUSCATE true`).
2. Manually terminate the agent process from Task Manager (simulating AV kill).
3. Confirm session shows as `dead` in handler.
4. Verify persistence: reboot the target and confirm the agent reconnects automatically.

---

#### 3.2. Memory Scan During `loadmodule`

**Scenario:** An EDR product scans process memory while an in-memory module is being executed via `exec()`.

**Expected Behavior:**
- The in-memory execution (`exec()` + `types.ModuleType`) leaves no disk artifact.
- The code resides in the agent's process memory only while running.
- If the EDR terminates the process, the session drops (same as 3.1).
- **Mitigation:** Obfuscate module content before passing to `loadmodule`. Module strings should be encrypted.

---

### 4. Privilege and Permission Errors

#### 4.1. Running as Unprivileged User

**Scenario:** The agent runs as a low-privilege user and attempts operations requiring elevated rights (e.g., `amsi_bypass`, `persistence_install` to system paths, `process_inject` into protected processes).

**Expected Behavior:**
- Each privileged operation includes a `try/except PermissionError` (or `AccessDenied` on Windows).
- A user-friendly error is returned to the handler:
  ```
  [!] Permission denied: This operation requires elevated privileges.
  ```
- The agent must **not** crash. It must remain connected and responsive.
- Non-privileged commands (`sysinfo`, `shell`, `download`, `screenshot`, etc.) must continue to work normally.

**Verification Steps:**
1. Run the agent as a standard (non-admin / non-root) user.
2. Issue `amsi_bypass` — expect a permission error, not a crash.
3. Issue `persistence_install` targeting a system path — expect a permission error.
4. Confirm `sysinfo` still works, demonstrating the agent is alive.

---

#### 4.2. Restricted Directories

**Scenario:** Commands like `cd` or `download` target paths the agent has no read/execute permission on (e.g., `/root/`, `C:\Windows\System32\` as a low-priv user).

**Expected Behavior:**
- `os.chdir()` or `open()` raises `PermissionError`.
- The exception is caught and the error is sent back to the handler.
- `pwd` still reflects the last valid working directory.

---

### 5. Protocol and Data Integrity Issues

#### 5.1. Corrupted or Truncated Data Packet

**Scenario:** A network anomaly causes a partial or corrupted AES-encrypted packet to arrive at the agent.

**Expected Behavior:**
- AES-256-GCM authentication tag verification fails (tag mismatch) → `ValueError` or `InvalidTag` exception.
- The agent discards the packet and does **not** attempt to execute corrupted data.
- The connection is flagged as potentially unstable; the agent may trigger `reconnect()` to establish a fresh session.
- This prevents arbitrary code execution from corrupted command streams.

---

#### 5.2. Empty or `None` Command Received

**Scenario:** `recv_data()` returns an empty string or `None` (e.g., handler closed the connection gracefully with `FIN`).

**Expected Behavior (from `run()`):**
```python
cmd = self.recv_data()
if not cmd:
    # Connection dropped, trigger reconnect
    if not self.reconnect():
        break
    continue
```
- The agent does **not** try to execute an empty command.
- `reconnect()` is called immediately.

---

### 6. Summary Table

| Scenario                     | Agent Behavior                       | Session Survives?           |
| ---------------------------- | ------------------------------------ | --------------------------- |
| Sudden network disconnection | Reconnect loop (`MAX_RECONNECT`)     | Yes (if network returns)    |
| Handler crash / restart      | Reconnect loop, re-sends sysinfo     | Yes (after handler returns) |
| Firewall blocking port       | Reconnect loop with sleep            | Yes (if firewall removed)   |
| Disk full during download    | Error sent to handler                | Yes                         |
| High CPU/RAM on target       | Slower responses, no crash           | Yes                         |
| AV kills the process         | Session dead, persistence relaunches | Only if persistence is set  |
| Command as low-priv user     | PermissionError returned             | Yes                         |
| Corrupted data packet        | Packet discarded, reconnect          | Yes                         |
| Empty command received       | Reconnect triggered                  | Yes                         |

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu belge, **Chimera** payload sisteminin çalışması sırasında karşılaşabileceği kenar (edge case) senaryolarını, hata durumlarını ve beklenmedik koşulları kapsamaktadır. Her senaryo için beklenen ajan davranışı (zarif bozulma, otomatik kurtarma ve hata kaydı) tanımlanmaktadır.

---

### 1. Ağ ve Bağlantı Hataları

#### 1.1. Ani Ağ Bağlantısı Kopması

**Senaryo:** Ağ kablosunun çekilmesi, Wi-Fi'nin düşmesi veya NAT oturumunun oturum ortasında sona ermesi.

**Beklenen Davranış:**
- `recv_data()` veya `send_data()` bir `socket.error` / `ssl.SSLError` hatası fırlatır.
- Ana döngü (`run()`), istisnayı yakalar ve hemen `reconnect()` metodunu çağırır.
- `reconnect()`, bozuk soketi `close_socket()` ile kapatır ve yeniden deneme döngüsüne girer.
- Her deneme arasında `RECONNECT_DELAY` saniye bekler; en fazla `MAX_RECONNECT` kez dener.
- `MAX_RECONNECT` `-1` olarak ayarlanmışsa, ajan ağ geri gelene kadar süresiz yeniden bağlanmayı dener.
- Yeniden deneme limiti aşılırsa, ajan artık iş parçacığı (thread) bırakmadan temiz biçimde sonlanır.

**Doğrulama Adımları:**
1. Aktif bir Chimera oturumu başlatın.
2. Hedef makinede ağ arayüzünü devre dışı bırakın.
3. Handler'ı izleyin — oturumun `dead` (ölü) olarak görünmesi gerekir.
4. Ağ arayüzünü yeniden etkinleştirin.
5. Ajanın otomatik olarak yeniden bağlandığını ve yeni bir oturumun göründüğünü doğrulayın.

---

#### 1.2. Handler Çökmesi / Yeniden Başlatılması

**Senaryo:** Framework (handler) sürecinin çökmesi veya saldırgan makinesinde kasıtlı olarak yeniden başlatılması.

**Beklenen Davranış:**
- Sunucu portu artık dinlemediği için `connect()`, bir sonraki denemede `False` döndürür.
- `reconnect()` döngüsü `RECONNECT_DELAY` aralıklarıyla denemeye devam eder.
- Handler yeniden başlatıldığında ve dinlemeye geçtiğinde ajan başarıyla yeniden bağlanır.
- Yeniden bağlantının ardından `send_sysinfo()` tekrar çağrılarak ajanın kimliği yeniden kaydedilir.

**Doğrulama Adımları:**
1. Bir oturum başlatın. Ardından handler sürecini sonlandırın (`Ctrl+C` veya `kill <pid>`).
2. Ajanın yeniden bağlanma döngüsünü izleyin.
3. Handler'ı yeniden başlatın.
4. Oturumun yeniden kurulduğunu ve `sysinfo` verisinin alındığını doğrulayın.

---

#### 1.3. Güvenlik Duvarı / Port Engeli

**Senaryo:** Oturum sırasında ana makine tabanlı veya ağ güvenlik duvarının ajanın giden portunu engellemeye başlaması.

**Beklenen Davranış:**
- `connect()`, `ConnectionRefusedError` fırlatır veya 30 saniye sonra zaman aşımına uğrar (`sock.settimeout(30)`).
- İstisna yakalanır; `reconnect()`, yapılandırılmış gecikmeyle döngülenir.
- Ajan **çökmez**, uyumadan sonsuz döngüye girmez ve CPU'yu %100 tüketmez.
- Güvenlik duvarı kuralı daha sonra kaldırılırsa, bir sonraki `connect()` denemesi başarılı olur.

---

### 2. Kaynak Tükenmesi

#### 2.1. Yetersiz Disk Alanı

**Senaryo:** Hedefin diski dolu olduğunda `download` veya `screenshot` gibi komutların çalıştırılması.

**Beklenen Davranış:**
- Dosya yazma işlemleri `IOError` / `OSError` (`errno.ENOSPC`) fırlatır.
- İlgili komut işleyicisi (handler) istisnayı yakalar ve handler'a açıklayıcı bir hata mesajı gönderir (ör: `[!] Hata: Cihazda alan kalmadı`).
- Ajan **çökmez**; ana C2 döngüsü normal şekilde devam eder.
- Oturum açık kalır ve sonraki komutlar çalışmaya devam eder.

---

#### 2.2. Yüksek CPU / RAM Kullanımı

**Senaryo:** Hedef sistemin CPU veya RAM'inin diğer süreçler tarafından %100'e yakın kullanılması.

**Beklenen Davranış:**
- Chimera ajanı hafif olacak şekilde tasarlanmıştır; ana döngüsünde yalnızca G/Ç (I/O) beklemesi yapar (`recv_data()`'dan bekler).
- Yüksek CPU yükü altında komut yürütme yavaş olabilir, ancak ajan zaman aşımına uğramalı veya çökmemelidir.
- Kabuk (`shell` komutu) ve bellek içi modül yükleme (`loadmodule`) daha uzun sürebilir, ancak sonunda sonuç döndürmelidir.
- Ajan boşta beklerken CPU kullanımı **%0**'a yakın olmalıdır.

---

### 3. Antivirüs / EDR Müdahalesi

#### 3.1. Antivirüs Tarafından Sürecin Sonlandırılması

**Senaryo:** AV/EDR ürününün Chimera ajanı sürecini tespit edip sonlandırması.

**Beklenen Davranış:**
- Süreç öldürüldüğünde bağlantı düşer ve handler'daki oturum `dead` olur.
- Bu senaryo için çekirdek düzeyinde yerleşik bir yeniden diriltme mekanizması yoktur.
- **Hafifletme stratejisi:** AV etkinliği gerçekleşmeden önce `persistence_install` kullanılarak ajanın bir sonraki yediden başlatmada veya zamanlanmış tetikleyicide yeniden başlatılması sağlanır.

---

### 4. Yetki ve İzin Hataları

#### 4.1. Yetersiz Yetkili Kullanıcı Olarak Çalışma

**Senaryo:** Ajanın düşük yetkili bir kullanıcı olarak çalışması ve yükseltilmiş hak gerektiren işlemleri denemesi (ör: `amsi_bypass`, sistem dizinlerine `persistence_install`, korumalı süreçlere `process_inject`).

**Beklenen Davranış:**
- Her ayrıcalıklı işlem `try/except PermissionError` içerir.
- Handler'a anlaşılır bir hata döndürülür:
  ```
  [!] İzin reddedildi: Bu işlem yükseltilmiş ayrıcalıklar gerektirir.
  ```
- Ajan **çökmez**; bağlantılı ve duyarlı olmaya devam eder.
- Ayrıcalık gerektirmeyen komutlar (`sysinfo`, `shell`, `download`, `screenshot` vb.) normal çalışmaya devam eder.

---

### 5. Protokol ve Veri Bütünlüğü Sorunları

#### 5.1. Bozuk veya Eksik Veri Paketi

**Senaryo:** Bir ağ anomalisi nedeniyle kısmi veya bozuk bir AES-şifreli paketin ajana ulaşması.

**Beklenen Davranış:**
- AES-256-GCM kimlik doğrulama etiketi (authentication tag) doğrulaması başarısız olur → `ValueError` veya `InvalidTag` istisnası.
- Ajan paketi atar ve bozuk veriyi **yürütmeye çalışmaz**.
- Bağlantı kararsız olarak işaretlenir; ajan taze bir oturum oluşturmak için `reconnect()` tetikleyebilir.
- Bu, bozuk komut akışlarından kaynaklanan rastgele kod çalıştırmayı önler.

#### 5.2. Boş veya `None` Komut Alınması

**Senaryo:** `recv_data()` boş string veya `None` döndürür (ör: handler bağlantıyı `FIN` ile kapattığında).

**Beklenen Davranış (`run()` içinden):**
```python
cmd = self.recv_data()
if not cmd:
    # Bağlantı düştü, yeniden bağlan
    if not self.reconnect():
        break
    continue
```
- Ajan boş bir komutu yürütmeye çalışmaz.
- `reconnect()` anında çağrılır.

---

### 6. Özet Tablosu

| Senaryo                            | Ajan Davranışı                              | Oturum Devam Eder mi?             |
| ---------------------------------- | ------------------------------------------- | --------------------------------- |
| Ani ağ bağlantısı kopması          | Yeniden bağlantı döngüsü (`MAX_RECONNECT`)  | Evet (ağ geri gelirse)            |
| Handler çökmesi / yeniden başlatma | Yeniden bağlantı, sysinfo tekrar gönderilir | Evet (handler geri gelirse)       |
| Güvenlik duvarı port engeli        | Uyku aralıklı yeniden bağlantı döngüsü      | Evet (kural kaldırılırsa)         |
| Download sırasında disk dolu       | Hata mesajı handler'a gönderilir            | Evet                              |
| Hedefte yüksek CPU/RAM             | Daha yavaş yanıtlar, çöküş yok              | Evet                              |
| AV süreci öldürür                  | Oturum ölür, persistence yeniden başlatır   | Yalnızca persistence ayarlandıysa |
| Düşük yetkili kullanıcı komutu     | PermissionError döndürülür                  | Evet                              |
| Bozuk veri paketi                  | Paket atılır, yeniden bağlan                | Evet                              |
| Boş komut alındı                   | Yeniden bağlantı tetiklenir                 | Evet                              |
