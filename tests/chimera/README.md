# 🧪 Chimera Unit & Integration Test Suite

Bu dizin, Chimera Payload Sistemi'nin kapsamlı birim (unit) ve entegrasyon testlerini içerir.

---

## 📂 Dosya Yapısı

```
tests/chimera/
├── __init__.py                 # Python paketi
├── conftest.py                 # Pytest fixtures ve yardımcı fonksiyonlar
├── README.md                   # Bu dokümantasyon
│
├── 🔌 Unit Testler
│   ├── test_agent_connect.py   # Bağlantı kurma / kapatma / yeniden bağlanma
│   ├── test_protocol.py        # HTTP over TLS protokol parser testleri
│   ├── test_encryption.py      # SSL/TLS handshake ve şifreleme testleri
│   └── test_commands.py        # Her komut için birim testler
│
└── 🔗 Entegrasyon Testleri
    ├── test_full_workflow.py    # End-to-end senaryo (generate → connect → command → terminate)
    └── test_multi_session.py   # Çoklu oturum yönetimi ve handler testleri
```

---

## 🚀 Çalıştırma

### Ön Gereksinimler

```bash
# Virtual environment aktif olmalı
source venv/bin/activate

# pytest kurulumu (yoksa)
pip install pytest
```

### Tüm Chimera Testlerini Çalıştır

```bash
pytest tests/chimera/ -v
```

### Belirli Bir Test Dosyasını Çalıştır

```bash
# Bağlantı testleri
pytest tests/chimera/test_agent_connect.py -v

# Protokol testleri
pytest tests/chimera/test_protocol.py -v

# Şifreleme testleri
pytest tests/chimera/test_encryption.py -v

# Komut testleri
pytest tests/chimera/test_commands.py -v

# End-to-end workflow testi
pytest tests/chimera/test_full_workflow.py -v

# Çoklu oturum testleri
pytest tests/chimera/test_multi_session.py -v
```

### Belirli Bir Test Fonksiyonunu Çalıştır

```bash
# Sadece SSL handshake testini çalıştır
pytest tests/chimera/test_agent_connect.py::TestSSLHandshake::test_self_signed_cert_accepted -v

# Sadece terminate komut testini çalıştır
pytest tests/chimera/test_commands.py::TestSpecialCommands::test_terminate_stops_agent -v
```

### Kısa Çıktı ile Çalıştır

```bash
pytest tests/chimera/ -q
```

### Başarısız Testleri Yeniden Çalıştır

```bash
pytest tests/chimera/ --lf -v
```

---

## 📋 Test Kategorileri

### 1. `test_agent_connect.py` — Bağlantı Testleri

| Test Sınıfı            | Açıklama                                                                    |
| ---------------------- | --------------------------------------------------------------------------- |
| `TestAgentConnect`     | `connect()` fonksiyonu: SSL context oluşturma, timeout, başarı/başarısızlık |
| `TestAgentCloseSocket` | `close_socket()` güvenli kapatma: None kontrolü, exception handling         |
| `TestAgentReconnect`   | `reconnect()` yeniden bağlanma: retry mantığı, running flag kontrolü        |
| `TestSSLHandshake`     | SSL/TLS handshake: self-signed kabul, timeout, connection refused           |

**Toplam: ~20 test**

### 2. `test_protocol.py` — HTTP Protokol Parser Testleri

| Test Sınıfı                 | Açıklama                                                               |
| --------------------------- | ---------------------------------------------------------------------- |
| `TestSendData`              | `send_data()` HTTP POST formatı: header'lar, Content-Length, encoding  |
| `TestRecvData`              | `recv_data()` HTTP Response parsing: body çıkarma, unicode, disconnect |
| `TestProtocolCompatibility` | Agent↔Handler protokol uyumluluk doğrulaması                           |

**Toplam: ~18 test**

### 3. `test_encryption.py` — SSL/TLS Şifreleme Testleri

| Test Sınıfı              | Açıklama                                                              |
| ------------------------ | --------------------------------------------------------------------- |
| `TestSSLContextCreation` | SSL context yapılandırması: CERT_NONE, hostname, wrap_socket          |
| `TestSSLErrorScenarios`  | SSL hata durumları: cert verify, protocol mismatch, handshake timeout |
| `TestDataEncryption`     | Veri şifreleme yolu: SSL socket vs raw socket kullanımı               |

**Toplam: ~12 test**

### 4. `test_commands.py` — Komut Çalıştırma Testleri

| Test Sınıfı                    | Açıklama                                                           |
| ------------------------------ | ------------------------------------------------------------------ |
| `TestBasicCommands`            | Sistem komutları: echo, pipe, geçersiz komut, boş çıktı            |
| `TestSpecialCommands`          | Özel komutlar: terminate, sysinfo (hostname, user, python, detect) |
| `TestKeyloggerCommands`        | Keylogger: start (Windows/non-Windows), stop, dump                 |
| `TestClipboardCommands`        | Clipboard: get (base64 encoded), format doğrulama                  |
| `TestPersistenceCommands`      | Persistence: install, remove                                       |
| `TestInjectionCommands`        | Process injection: list, shellcode (eksik arg, geçersiz PID)       |
| `TestPortForwardingCommands`   | Port forwarding: list (boş), stop                                  |
| `TestNetworkScannerCommands`   | Network scan: argümansız çağrı                                     |
| `TestCommandCaseInsensitivity` | Büyük/küçük harf duyarsızlık                                       |

**Toplam: ~22 test**

### 5. `test_full_workflow.py` — End-to-End Workflow Testleri

| Test Sınıfı             | Açıklama                                                                          |
| ----------------------- | --------------------------------------------------------------------------------- |
| `TestPayloadGeneration` | Payload üretimi: placeholder, geçerli Python, sadece stdlib, ChimeraAgent sınıfı  |
| `TestAgentRunLoop`      | Agent.run() döngüsü: connect→sysinfo→cmd→terminate, reconnect                     |
| `TestBuilderPipeline`   | Builder pipeline: üretim→yükleme→instantiation, strip comments, özel parametreler |

**Toplam: ~12 test**

### 6. `test_multi_session.py` — Çoklu Oturum Yönetimi Testleri

| Test Sınıfı                 | Açıklama                                                   |
| --------------------------- | ---------------------------------------------------------- |
| `TestHandlerInitialization` | Handler başlatma: options saklama, BaseHandler miras       |
| `TestHandlerProtocol`       | Handler send/recv: HTTP Response/Request format            |
| `TestSessionManagement`     | Session: ID atama, SSL wrap, session manager güncelleme    |
| `TestMultipleAgents`        | Bağımsız agent durumları: ayrı state, ayrı modül listeleri |

**Toplam: ~12 test**

---

## 🏗️ Test Mimarisi

### conftest.py (Paylaşılan Fixtures)

```python
# Temel fixtures:
agent()                 # Temiz ChimeraAgent instance
agent_with_mock_sock()  # Mock socket'e sahip agent
mock_socket_data()      # HTTP Response oluşturucu
chimera_handler()       # Mock SSL ile Handler instance
payload_generator()     # Yapılandırılmış Payload generator
```

### Mock Stratejisi

- **Socket işlemleri**: `unittest.mock.MagicMock` ile gerçek ağ trafiği simülasyonu
- **SSL**: `patch("ssl.create_default_context")` ile sertifika gereksinimi bypass
- **Dosya I/O**: Builder testlerinde agent.py dosyası gerçek dosyastateChanged okunur
- **Subprocess**: Sistem komutları testlerde gerçek çalıştırılır (echo, true vb.)

---

## ⚠️ Bilinen Sınırlamalar

1. **Keylogger testleri**: Sadece Windows'ta çalışır, diğer platformlarda otomatik atlanır (`@pytest.mark.skipif`)
2. **Process injection testleri**: Sadece Windows'ta çalışır
3. **screenshot testi**: Ekran yakalaması platforma bağımlıdır
4. **Gerçek ağ testleri**: Mock ile simüle edilir, gerçek ağ trafiği oluşturulmaz
5. **Obfuscation testleri**: `test_full_workflow.py` içinde obfuscation pipeline'ı ayrıca test edilebilir

---

## 📊 Test Sonuçları Örneği

```
tests/chimera/test_agent_connect.py::TestAgentConnect::test_connect_returns_false_on_unreachable_host PASSED
tests/chimera/test_agent_connect.py::TestAgentConnect::test_connect_creates_ssl_context PASSED
tests/chimera/test_agent_connect.py::TestSSLHandshake::test_self_signed_cert_accepted PASSED
tests/chimera/test_protocol.py::TestSendData::test_send_data_http_post_format PASSED
tests/chimera/test_protocol.py::TestRecvData::test_recv_data_parses_body_correctly PASSED
tests/chimera/test_commands.py::TestSpecialCommands::test_terminate_stops_agent PASSED
tests/chimera/test_commands.py::TestSpecialCommands::test_sysinfo_returns_system_info PASSED
tests/chimera/test_full_workflow.py::TestPayloadGeneration::test_generate_produces_valid_python PASSED
tests/chimera/test_full_workflow.py::TestAgentRunLoop::test_run_connect_sysinfo_terminate PASSED
tests/chimera/test_multi_session.py::TestHandlerProtocol::test_send_data_http_response_format PASSED
...
========================= X passed, Y skipped in Z.ZZs =========================
```

---

## 🔧 Yeni Test Ekleme Rehberi

1. İlgili test dosyasına yeni bir test fonksiyonu ekleyin
2. `conftest.py`'dan mevcut fixture'ları kullanın
3. Mock stratejisini takip edin (gerçek ağ trafiği oluşturmayın)
4. Platform bağımlı testlere `@pytest.mark.skipif` ekleyin
5. Test isimlerini `test_` prefix'i ile başlatın
6. Docstring ile testin amacını Türkçe açıklayın

```python
class TestNewFeature:
    """Yeni özellik testleri."""

    def test_feature_basic_usage(self, agent):
        """Temel kullanım senaryosu."""
        result = agent.execute_command("new_command")
        assert "expected" in result
```
