# 🛡️ Chimera Security & AV Bypass Testing Guide / Güvenlik ve AV Atlatma Test Rehberi

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

This guide provides the necessary methodology to test the **Chimera** payload system against modern Antivirus (AV) and Endpoint Detection and Response (EDR) solutions. The goal is to ensure the payload maintains stealth capabilities during static, dynamic, and network analysis.

### 1. Test Environment Preparation

To safely conduct malware and AV bypass testing, a controlled and isolated environment is strictly required.

*   **Virtual Machine (VM) Setup:** Install the target Operating Systems (e.g., Windows 10, Windows 11) using hypervisors like VMware Workstation or VirtualBox.
*   **Snapshot Management:** Take a clean "Snapshot" of the VM immediately after setting up the OS and the AV/EDR tool. Ensure you revert to this clean state before every single test to prevent skewed results.
*   **Network Isolation:** Configure the VM network adapter to **Host-Only** or an internal network to prevent the payload from inadvertently communicating with external networks or analyzing real production infrastructure.

### 2. Antivirus & EDR Test Matrix

Ensure that Chimera is verified against the following security solutions:

*   **Windows Defender** (Windows 10 / Windows 11 Built-in)
*   **Microsoft Defender for Endpoint** (MDE)
*   **CrowdStrike Falcon**
*   **Kaspersky Endpoint Security**
*   **BitDefender GravityZone**

### 3. Testing Procedures

The testing is broken down into three main analysis layers:

#### A. Static Analysis Test (Disk)
Testing how AV engines react to the file simply residing on disk.
*   **Procedure:** Generate the Chimera payload. Transfer it to the target VM's disk. Initiate a manual scan on the file and folder using the AV product.
*   **Focus:** Checking if known file signatures or strings are flagged.

#### B. Dynamic Analysis Test (Runtime)
Testing how AV/EDR engines react when the payload executes and resides in memory.
*   **Procedure:** Execute the payload on the VM. Attempt various operations (commands, module loading, shell spawning) directly from memory. Observe the behavioral alerts.
*   **Focus:** Checking memory scanning (AMSI), heuristic analysis, and behavioral blocking.

#### C. Network Analysis Test (Traffic)
Testing if Intrusion Detection Systems (IDS/IPS) detect the C2 communication.
*   **Procedure:** Run Snort or Suricata on the network boundary. Analyze the connection handshakes between Chimera and Mah-Framework handler.
*   **Focus:** Verifying that traffic patterns resemble benign HTTP and that encryption effectively masks payload strings.

### 4. Expected Results

*   **Baseline (Without Obfuscation):** If generated without any obfuscation (`set OBFUSCATE false`), the payload **must be detected** by static analysis. This confirms the AV is working.
*   **Obfuscated Generation:** If generated with full obfuscation (`set OBFUSCATE true`), the payload **should bypass** static analysis entirely and reside on the disk without alerts.
*   **Runtime Stealth:** During dynamic execution, the payload should not trigger heuristic alerts. While `process migration` or `hollowing` features (if utilized) can be inherently noisy, AMSI bypass strategies must allow arbitrary scripts and `loadmodule` abilities to run under the radar.

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu rehber, **Chimera** payload sisteminin modern Antivirüs (AV) ve Uç Nokta Tespit ve Yanıt (EDR) çözümlerine karşı test edilmesi için gereken metodolojiyi sağlar. Temel amaç, payload'un statik, dinamik ve ağ analizi sırasında gizlilik yeteneklerini koruduğunu doğrulamaktır.

### 1. Test Ortamı Hazırlığı

Zararlı yazılım ve AV atlatma testlerini güvenli bir şekilde yürütmek için izole edilmiş kontrollü bir ortam kesinlikle şarttır.

*   **Sanal Makine (VM) Kurulumu:** VMware Workstation veya VirtualBox gibi sanallaştırma yazılımları kullanarak hedef işletim sistemlerini (örn. Windows 10, Windows 11) kurun.
*   **Snapshot Yönetimi:** OS ve AV/EDR aracı kurulduktan hemen sonra temiz bir "Snapshot" (Anlık Görüntü) alın. Sonuçların sapmasını önlemek için her bir testten önce mutlaka bu temiz duruma geri dönün.
*   **Ağ İzolasyonu:** Payload'un yanlışlıkla dış ağlarla iletişim kurmasını veya gerçek üretim altyapısını etkilemesini önlemek için VM ağ bağdaştırıcısını **Host-Only** (Sadece Ana Makine) veya yalıtılmış bir iç ağ olarak yapılandırın.

### 2. Antivirüs ve EDR Test Matrisi

Chimera'nın aşağıdaki güvenlik çözümlerine karşı test edilip doğrulandığından emin olun:

*   **Windows Defender** (Windows 10 / Windows 11 Yerleşik)
*   **Microsoft Defender for Endpoint** (MDE)
*   **CrowdStrike Falcon**
*   **Kaspersky Endpoint Security**
*   **BitDefender GravityZone**

### 3. Test Prosedürleri

Testler üç ana analiz katmanına ayrılmıştır:

#### A. Statik Analiz Testi (Disk)
AV motorlarının yalnızca diskte duran bir dosyaya nasıl tepki verdiğinin test edilmesi.
*   **Prosedür:** Chimera payload'unu oluşturun (`generate`). Dosyayı hedef VM'in diskine aktarın. AV ürünü ile dosya ve klasör üzerinde manuel olarak sağ tık taraması başlatın.
*   **Odak Noktası:** Bilinen dosya imzalarının (signature) veya statik stringlerin bayraklanıp (flag) bayraklanmadığını kontrol etmek.

#### B. Dinamik Analiz Testi (Çalışma Zamanı / Runtime)
Payload çalıştırıldığında ve belirteçler belleğe (RAM) yüklendiğinde AV/EDR motorlarının nasıl tepki verdiğinin test edilmesi.
*   **Prosedür:** Payload'u VM üzerinde çalıştırın. Doğrudan bellek üzerinden çeşitli komutlar yürütmeyi (shell, modül yükleme vb.) deneyin. Davranışsal uyarıları gözlemleyin.
*   **Odak Noktası:** Bellek tarama (AMSI), sezgisel (heuristic) analiz ve davranışsal engellemeleri kontrol etmek.

#### C. Ağ Analiz Testi (Trafik)
Saldırı Tespit Sistemlerinin (IDS/IPS) C2 iletişimini tespit edip edemediğinin test edilmesi.
*   **Prosedür:** Ağ sınırında Snort veya Suricata çalıştırın. Chimera ile Mah-Framework handler modülü arasındaki bağlantı trafiklerini analiz edin.
*   **Odak Noktası:** Trafik desenlerinin zararsız HTTP trafiğine benzediğini ve şifrelemenin payload verilerini başarıyla maskelediğini doğrulamak.

### 4. Beklenen Sonuçlar

*   **Temel Durum (Obfuscation Olmadan):** Obfuscation devre dışı bırakılarak üretilirse (`set OBFUSCATE false`), payload statik analiz tarafından **mutlaka tespit edilmelidir**. Bu, AV'nin düzgün çalıştığını doğrular.
*   **Obfuscate Edilmiş Durum:** Tam obfuscation ile üretilirse (`set OBFUSCATE true`), payload statik analizi **tamamen atlatmalı** ve herhangi bir uyarı vermeden doğrudan diskte barındırılabilmelidir.
*   **Çalışma Zamanı (Runtime) Gizliliği:** Dinamik çalışma sırasında payload sezgisel uyarıları tetiklememelidir. Process migration veya process hollowing gibi özellikler yapıları gereği gürültülü (tespit edilebilir) olabilse de, AMSI atlatma stratejileri `loadmodule` yeteneklerinin ve standart komutların radarın altında çalışmasına izin vermelidir.
