# ⏱️ Chimera Performance and Stability Testing Guide / Performans ve Stabilite Test Rehberi

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

This document defines the testing scenarios intended to evaluate the performance, stability, and resource management capabilities of the **Chimera** payload system under extreme conditions.

### 1. Long-Term Connection Test

Targeted at proving the agent can survive continuously over a long period without degrading system performance.

*   **24-Hour Continuous Connection:**
    *   **Procedure:** Keep a payload session actively connected to the framework handler for at least 24 uninterrupted hours. Occasionally execute passive commands (like `sysinfo` or `pwd`) to confirm it is alive.
    *   **Expected Result:** The connection must not drop spontaneously. If network interruption occurs, it must auto-reconnect successfully within limits.
*   **Memory Leak Check:**
    *   **Procedure:** Monitor the RAM usage of the agent process throughout the 24-hour test period.
    *   **Expected Result:** Memory consumption should stay stable. Any continuous or drastic increase in RAM (Memory Leak) indicates an issue in the C2 loop.
*   **CPU Usage Monitoring:**
    *   **Procedure:** Check the target's task manager (or `top`) while the agent is idle and while it is processing active interactive shells.
    *   **Expected Result:** CPU usage must remain near 0% while the agent is idle. It should not cause CPU spikes during basic operations to remain stealthy.

### 2. Load and Stress Test

Targeted at determining how the agent behaves under heavy stress and intensive I/O operations.

*   **Large File Transfer (1GB+):**
    *   **Procedure:** Use the `upload` and `download` commands to transfer a single file larger than 1 Gigabyte in a single operation.
    *   **Expected Result:** The chunking mechanism handles the transfer correctly without running out of memory, and the final file hash matches the original.
*   **Bulk Command Execution (1000+ Commands):**
    *   **Procedure:** Script the handler to automatically dispatch 1000+ sequential commands (like `dir` or `whoami`) rapidly over the active session.
    *   **Expected Result:** The agent queues and executes all commands in order without crashing or dropping the connection.
*   **Concurrent Multi-Session Testing (10+ Sessions):**
    *   **Procedure:** Execute the agent on 10 different target machines (or VMs) simultaneously, connecting back to a single framework handler.
    *   **Expected Result:** The handler must accept, list (`sessions -l`), and manage interaction loops for all 10 clients without mixing the streams or freezing the framework.

### 3. Network Latency and Disruption Test

Targeted at verifying the agent's resilience against poor network infrastructure.

*   **High Ping Connections (100ms+, 500ms+):**
    *   **Procedure:** Use network shaping tools (like Linux `tc` or Clumsy on Windows) to simulate artificial latency.
    *   **Expected Result:** Commands might take longer to return, but the TLS/AES handshake and packet structure must not fail or corrupt due to slow arrival.
*   **Packet Loss Simulation:**
    *   **Procedure:** Simulate 10% to 20% packet loss on the connection route.
    *   **Expected Result:** The underlying TCP protocol should manage retransmissions without permanently stalling the agent's main loop. If the connection breaks entirely, the `MAX_RECONNECT` routine must gracefully trigger.

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu belge, **Chimera** payload sisteminin aşırı koşullar altındaki performansını, genel kararlılığını (stabilitesini) ve kaynak yönetimi becerilerini değerlendirmek için tasarlanan test senaryolarını tanımlar.

### 1. Uzun Süreli Bağlantı Testi

Ajanın uzun bir süre boyunca sistem performansını düşürmeden sürekli olarak hayatta kalabileceğini kanıtlamayı hedefler.

*   **24 Saat Kesintisiz Bağlantı:**
    *   **Prosedür:** Bir payload oturumunu en az 24 saat boyunca kesintisiz olarak framework handler'ına bağlı tutun. Hayatta olduğunu doğrulamak için ara sıra pasif komutlar (`sysinfo` veya `pwd` vb.) çalıştırın.
    *   **Beklenen Sonuç:** Bağlantı kendiliğinden kopmamalıdır. Ağ kesintisi olursa, limitler dahilinde başarıyla otomatik yeniden bağlanmalıdır.
*   **Memory Leak (Bellek Sızıntısı) Kontrolü:**
    *   **Prosedür:** 24 saatlik test süresi boyunca ajan görevinin (process) RAM kullanımını izleyin.
    *   **Beklenen Sonuç:** Bellek tüketimi stabil kalmalıdır. RAM kullanımında sürekli veya ani bir artış (Bellek Sızıntısı), C2 haberleşme döngüsünde bir sorun olduğunu gösterir.
*   **CPU Kullanımı İzleme:**
    *   **Prosedür:** Ajan boşta (idle) durumdayken ve aktif etkileşimli kabuk (shell) işlemleri yaparken hedefin görev yöneticisini (veya `top`) kontrol edin.
    *   **Beklenen Sonuç:** Ajan boşta beklerken CPU kullanımı %0'a yakın olmalıdır. Gizliliği korumak adına temel işlemlerde CPU'yu tavan yaptırmamalıdır (spike).

### 2. Yük ve Stres Testi

Ajanın yoğun stres ve yoğun G/Ç (I/O) işlemleri altında nasıl davrandığını belirlemeyi hedefler.

*   **Büyük Dosya Transferi (1GB+):**
    *   **Prosedür:** Tek bir işlemde 1 Gigabyte'tan büyük bir dosyayı aktarmak için `upload` ve `download` komutlarını kullanın.
    *   **Beklenen Sonuç:** Parçalı gönderim (chunking) mekanizması, yetersiz bellek hatası (OOM) vermeden transferi doğru şekilde yönetir ve biten dosyanın hashi orijinaliyle eşleşir.
*   **Çok Sayıda Komut Yürütme (1000+ Komut):**
    *   **Prosedür:** Handler'ı, aktif oturum üzerinden arka arkaya hızla 1000'den fazla sıralı komut (örn: `dir` veya `whoami`) gönderecek şekilde script (otomasyon) ile çalıştırın.
    *   **Beklenen Sonuç:** Ajan, çökmeksizin tüm komutları sıraya alır (kuyruk), yürütür ve bağlantıyı düşürmeden çıktıları geri gönderir.
*   **Eş Zamanlı Çoklu Oturum Testi (10+ Oturum):**
    *   **Prosedür:** Ajanı 10 farklı hedef makinede (veya VM'de) aynı anda çalıştırarak tek bir framework handler'ına bağlanmalarını sağlayın.
    *   **Beklenen Sonuç:** Handler; framework donmadan veya veri akışları birbirine karışmadan, 10 istemcinin tamamı için oturum açabilmeli, listeleyebilmeli (`sessions -l`) ve veri işleyebilmelidir.

### 3. Ağ Gecikmesi ve Kesinti Testi

Ajanın zayıf veya sağlıksız ağ altyapılarına karşı dayanıklılığını doğrulamayı hedefler.

*   **Yüksek Ping ile Bağlantı (100ms+, 500ms+):**
    *   **Prosedür:** Yapay gecikme simüle etmek için trafik şekillendirme (network shaping) araçlarını (Linux `tc` veya Windows'ta Clumsy gibi) kullanın.
    *   **Beklenen Sonuç:** Komutların dönüş süresi uzayabilir ancak yavaş aktarım nedeniyle TLS/AES el sıkışması başarısız olmamalı ve paketler bozulmamalıdır.
*   **Paket Kaybı Simülasyonu:**
    *   **Prosedür:** Bağlantı rotası (%route) üzerinde %10 ila %20 arasında paket kaybı simüle edin.
    *   **Beklenen Sonuç:** Alt katmandaki TCP protokolü, ajanın ana dinleme döngüsünü kalıcı olarak dondurmadan (stall) veri tekrarlarını yönetmelidir. Bağlantı tamamen koparsa, `MAX_RECONNECT` yordamı pürüzsüzce devreye girmelidir.
