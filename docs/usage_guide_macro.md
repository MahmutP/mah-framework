# Macro Recording System Guide / Makro Kayıt Sistemi Rehberi

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

> Docs index: [README.md](README.md) · Full CLI: [COMMANDS.md](COMMANDS.md) · Quick Start: [QUICKSTART.md](QUICKSTART.md)

---

<a name="-english"></a>
## 🇬🇧 English

This guide explains how to use and test the Macro Recording System (`record` command) in Mah Framework. This feature allows you to record your console commands and save them as a resource file (`.rc`), which can be replayed later.

### 📋 Prerequisites

Ensure you are running the latest version of the framework.

```bash
python main.py
```

### 🧪 Usage Scenarios

#### Scenario 1: Basic Recording and Playback

In this scenario, we will record a few commands, save them to a file, and then run that file.

**Step 1: Start Recording**

Enter the following command in the framework console:

```bash
mah > record start
```

**Expected Output:**
> ✔ Makro kaydı başlatıldı. (Macro recording started.)

**Step 2: Run Commands**

Execute the commands you want to record. For example:

```bash
mah > show options
mah > help
mah > use exploit/vsftpd_234_backdoor
mah > set RHOST 192.168.1.1
```

*(Note: The commands are recorded regardless of whether they succeed or fail.)*

**Step 3: Check Recording Status**

```bash
mah > record status
```

**Expected Output:**
> ● Kayıt DEVAM EDİYOR. (Recording IN PROGRESS.)
> ...

**Step 4: Stop Recording and Save**

Stop the recording and save it to `test_macro.rc`. If you don't provide an extension, `.rc` will be added automatically.

```bash
mah > record stop test_macro
```

**Expected Output:**
> ✔ Kayıt durduruldu ve 'test_macro.rc' dosyasına yazıldı. (Recording stopped and saved to 'test_macro.rc')

**Step 5: Verify File Content**

You can verify the file creation using the shell command:

```bash
mah > shell cat test_macro.rc
```

**Step 6: Playback (Run the Macro)**

Now, execute the recorded macro using the `resource` command:

```bash
mah > resource test_macro.rc
```

**Result:** The framework will automatically execute all the commands in the file sequentially.

#### Scenario 2: Stopping Without Saving

If you want to stop recording but check what was recorded without saving to a file:

1.  Start recording: `record start`
2.  Run some commands.
3.  Stop without a filename: `record stop`

**Result:** The system will display the recorded commands on the screen but will not write them to a file.

#### Scenario 3: Startup Execution

You can run your recorded macro automatically when starting the framework.

```bash
python main.py -r test_macro.rc
```

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu rehber, Mah Framework içerisindeki Makro Kayıt Sisteminin (`record` komutu) nasıl kullanılacağını ve test edileceğini açıklar. Bu özellik, konsol komutlarınızı kaydetmenize ve daha sonra tekrar oynatılabilmesi için bir kaynak dosyası (`.rc`) olarak saklamanıza olanak tanır.

### 📋 Ön Hazırlık

Framework'ün güncel sürümünü çalıştırdığınızdan emin olun.

```bash
python main.py
```

### 🧪 Kullanım Senaryoları

#### Senaryo 1: Temel Kayıt ve Oynatma

Bu senaryoda basit komutları kaydedip, bir dosyaya yazdıracak ve ardından bu dosyayı tekrar çalıştıracağız.

**Adım 1: Kaydı Başlatın**

Framework konsolunda aşağıdaki komutu girin:

```bash
mah > record start
```

**Beklenen Çıktı:**
> ✔ Makro kaydı başlatıldı.

**Adım 2: Komutları Çalıştırın**

Kaydetmek istediğiniz komutları sırayla çalıştırın. Örneğin:

```bash
mah > show options
mah > help
mah > use exploit/vsftpd_234_backdoor
mah > set RHOST 192.168.1.1
```

*(Not: Komutların başarılı olup olmaması önemli değildir, çalıştırılan her komut kaydedilir.)*

**Adım 3: Kayıt Durumunu Kontrol Edin**

```bash
mah > record status
```

**Beklenen Çıktı:**
> ● Kayıt DEVAM EDİYOR.
> Şu ana kadar kaydedilen komut sayısı: ...

**Adım 4: Kaydı Durdurun ve Kaydedin**

Kaydı bitirip `test_makro.rc` adlı dosyaya kaydedelim. Eğer `.rc` uzantısını yazmazsanız sistem otomatik olarak ekleyecektir.

```bash
mah > record stop test_makro
```

**Beklenen Çıktı:**
> ✔ Kayıt durduruldu ve 'test_makro.rc' dosyasına yazıldı.

**Adım 5: Dosyayı Kontrol Edin**

Framework'ten çıkmadan shell komutu ile dosyanın içeriğini görebilirsiniz:

```bash
mah > shell cat test_makro.rc
```

**Adım 6: Makroyu Çalıştırın (Playback)**

Şimdi kaydettiğimiz makroyu `resource` komutu ile tekrar çalıştıralım:

```bash
mah > resource test_makro.rc
```

**Sonuç:** Framework, dosyadaki tüm komutları sırayla otomatik olarak çalıştıracaktır.

#### Senaryo 2: Kaydetmeden Durdurma

Bazen kaydı iptal etmek veya sadece ne kaydettiğinizi görmek isteyebilirsiniz.

1.  Kaydı başlatın: `record start`
2.  Birkaç komut girin.
3.  Dosya adı vermeden durdurun: `record stop`

**Sonuç:** Sistem, kaydettiğiniz komutları ekrana basacak ancak bir dosyaya yazmayacaktır.

#### Senaryo 3: Başlangıçta Otomatik Çalıştırma

Kaydettiğiniz bir makro dosyasını framework açılırken otomatik olarak çalıştırabilirsiniz.

```bash
python main.py -r test_makro.rc
```
