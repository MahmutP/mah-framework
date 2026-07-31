# Commands Reference / Komut Referansı

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

Complete reference for built-in Mah Framework CLI commands. Inside the console, use `help` or `help <command>` for live docs.

### Core

| Command | Aliases | Usage | Description |
| ------- | ------- | ----- | ----------- |
| `help` | `?` | `help [command]` | List commands or show details |
| `exit` | `quit` | `exit` | Quit the framework |
| `show` | — | `show <modules\|options\|info>` | List modules / options / info |
| `search` | — | `search <term>` | Search modules by keyword |
| `resource` | — | `resource <file.rc>` | Execute commands from a resource file |
| `reload` | — | `reload [module_path]` | Reload all components or one module |
| `sessions` | — | `sessions [options]` | List / interact / kill sessions |
| `plugins` | — | `plugins <sub> ...` | Manage plugins |

#### `sessions` options

```bash
sessions                 # Same as list
sessions -l              # List active sessions
sessions list
sessions -g              # Group by host IP
sessions -i <id>         # Interact with session
sessions -k <id>         # Kill session
```

#### `plugins` subcommands

```bash
plugins list
plugins info "Name"
plugins enable "Name"
plugins disable "Name"
plugins search <term>
plugins install <source>
plugins update [name]
plugins remove "Name"
```

#### `show` values

```bash
show modules             # All loaded modules
show options             # Options of current module
show info                # Detailed info of current module
```

---

### Module Workflow

| Command | Aliases | Usage | Description |
| ------- | ------- | ----- | ----------- |
| `use` | — | `use <category/module>` | Select a module |
| `back` | — | `back` | Leave current module context |
| `info` | — | `info` | Show selected module metadata |
| `set` | — | `set <OPTION> <value>` | Set an option |
| `unset` | — | `unset <OPTION>` | Reset option to default |
| `run` | `exploit`, `execute` | `run` | Execute selected module |

Typical sequence:

```bash
use auxiliary/scanner/port_scanner
set RHOST 10.0.0.5
set RPORTS 1-1024
show options
run
back
```

---

### System

| Command | Aliases | Usage | Description |
| ------- | ------- | ----- | ----------- |
| `alias` | — | `alias <add\|list\|remove> ...` | Manage command shortcuts |
| `banner` | — | `banner` | Print a random banner |
| `clear` | `cls` | `clear` | Clear the screen |
| `history` | `hist` | `history [limit]` | Show command history |
| `shell` | `!` | `shell [cmd]` | Drop to OS shell or run one command |
| `record` | `makro` | `record <start\|stop\|status> [file]` | Macro recording |
| `checkupdate` | `update`, `check` | `checkupdate [-a] [-b]` | Check / apply updates |
| `repo` | — | `repo <add\|update\|list\|remove\|info> ...` | Remote repository management |
| `download` | — | `download <search\|install\|update\|list\|verify> ...` | Install modules from repos |

#### `alias`

```bash
alias list
alias add h help
alias add s search
alias remove h
```

Stored in `config/aliases.json`.

#### `record`

```bash
record start
record status
record stop my_macro          # Writes my_macro.rc
record stop                   # Print only, do not save
```

See [usage_guide_macro.md](usage_guide_macro.md).

#### `checkupdate`

```bash
checkupdate                   # Check only
checkupdate --apply           # Apply update
checkupdate -a -b             # Apply with backup
```

#### `repo` / `download`

See [REPO_AND_DOWNLOAD.md](REPO_AND_DOWNLOAD.md).

```bash
repo add myrepo https://github.com/user/repo.git
repo list
repo update
download search nmap
download install myrepo/auxiliary/scanner/x.py
download list
```

---

### Keyboard Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `Tab` | Completion |
| `Ctrl+R` | Reverse history search |
| `Ctrl+C` | Interrupt current input / operation (context-dependent) |
| `Up` / `Down` | Navigate history |

---

### Categories Summary

| Category | Commands |
| -------- | -------- |
| **core** | `help`, `exit`, `show`, `search`, `resource`, `reload`, `sessions`, `plugins` |
| **module** | `use`, `back`, `info`, `set`, `unset`, `run` |
| **system** | `alias`, `banner`, `clear`, `history`, `shell`, `record`, `checkupdate`, `repo`, `download` |

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Mah Framework yerleşik CLI komutlarının tam referansı. Konsolda canlı yardım için `help` veya `help <komut>` kullanın.

### Çekirdek (Core)

| Komut | Alias | Kullanım | Açıklama |
| ----- | ----- | -------- | -------- |
| `help` | `?` | `help [komut]` | Komutları listele veya detay göster |
| `exit` | `quit` | `exit` | Framework'ten çık |
| `show` | — | `show <modules\|options\|info>` | Modül / seçenek / bilgi listele |
| `search` | — | `search <terim>` | Modüllerde ara |
| `resource` | — | `resource <dosya.rc>` | Resource dosyasından komut çalıştır |
| `reload` | — | `reload [modül_yolu]` | Tüm bileşenleri veya bir modülü yeniden yükle |
| `sessions` | — | `sessions [seçenekler]` | Oturum listele / etkileşim / öldür |
| `plugins` | — | `plugins <alt> ...` | Plugin yönetimi |

#### `sessions` seçenekleri

```bash
sessions                 # Liste ile aynı
sessions -l              # Aktif oturumlar
sessions list
sessions -g              # IP'ye göre grupla
sessions -i <id>         # Oturuma gir
sessions -k <id>         # Oturumu sonlandır
```

#### `plugins` alt komutları

```bash
plugins list
plugins info "İsim"
plugins enable "İsim"
plugins disable "İsim"
plugins search <terim>
plugins install <kaynak>
plugins update [isim]
plugins remove "İsim"
```

#### `show` değerleri

```bash
show modules             # Yüklü tüm modüller
show options             # Seçili modül seçenekleri
show info                # Seçili modül detayı
```

---

### Modül İş Akışı

| Komut | Alias | Kullanım | Açıklama |
| ----- | ----- | -------- | -------- |
| `use` | — | `use <kategori/modül>` | Modül seç |
| `back` | — | `back` | Modül bağlamından çık |
| `info` | — | `info` | Seçili modül meta verisi |
| `set` | — | `set <SEÇENEK> <değer>` | Seçenek ayarla |
| `unset` | — | `unset <SEÇENEK>` | Varsayılana sıfırla |
| `run` | `exploit`, `execute` | `run` | Seçili modülü çalıştır |

Tipik sıra:

```bash
use auxiliary/scanner/port_scanner
set RHOST 10.0.0.5
set RPORTS 1-1024
show options
run
back
```

---

### Sistem

| Komut | Alias | Kullanım | Açıklama |
| ----- | ----- | -------- | -------- |
| `alias` | — | `alias <add\|list\|remove> ...` | Kısayol yönetimi |
| `banner` | — | `banner` | Rastgele banner |
| `clear` | `cls` | `clear` | Ekranı temizle |
| `history` | `hist` | `history [limit]` | Komut geçmişi |
| `shell` | `!` | `shell [komut]` | OS kabuğuna düş veya tek komut çalıştır |
| `record` | `makro` | `record <start\|stop\|status> [dosya]` | Makro kaydı |
| `checkupdate` | `update`, `check` | `checkupdate [-a] [-b]` | Güncelleme kontrol / uygula |
| `repo` | — | `repo <add\|update\|list\|remove\|info> ...` | Uzak depo yönetimi |
| `download` | — | `download <search\|install\|update\|list\|verify> ...` | Depodan modül kur |

#### `alias`

```bash
alias list
alias add h help
alias add s search
alias remove h
```

`config/aliases.json` içinde saklanır.

#### `record`

```bash
record start
record status
record stop makrom            # makrom.rc yazar
record stop                   # Sadece ekrana bas, kaydetme
```

Bkz. [usage_guide_macro.md](usage_guide_macro.md).

#### `checkupdate`

```bash
checkupdate                   # Sadece kontrol
checkupdate --apply           # Uygula
checkupdate -a -b             # Yedekleyerek uygula
```

#### `repo` / `download`

Bkz. [REPO_AND_DOWNLOAD.md](REPO_AND_DOWNLOAD.md).

```bash
repo add myrepo https://github.com/user/repo.git
repo list
repo update
download search nmap
download install myrepo/auxiliary/scanner/x.py
download list
```

---

### Klavye Kısayolları

| Kısayol | İşlev |
| ------- | ----- |
| `Tab` | Tamamlama |
| `Ctrl+R` | Geçmişte ters arama |
| `Ctrl+C` | Girişi / işlemi kes (bağlama göre) |
| `Yukarı` / `Aşağı` | Geçmişte gezin |

---

### Kategori Özeti

| Kategori | Komutlar |
| -------- | -------- |
| **core** | `help`, `exit`, `show`, `search`, `resource`, `reload`, `sessions`, `plugins` |
| **module** | `use`, `back`, `info`, `set`, `unset`, `run` |
| **system** | `alias`, `banner`, `clear`, `history`, `shell`, `record`, `checkupdate`, `repo`, `download` |
