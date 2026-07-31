# Remote Repositories & Download / Uzak Depolar ve İndirme

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

Mah Framework can pull extra modules (and plugins) from remote Git repositories without baking them into the core tree.

### Concepts

| Piece | Role |
| ----- | ---- |
| **Repo** | A Git remote registered with `repo add` and cloned under `config/repos/` |
| **download** | Search / install / update / verify modules from those clones |
| **installed_modules.json** | Registry of modules installed via `download` |
| **installed_plugins.json** | Registry of plugins installed via `plugins install` |

Config files:

* `config/repos.json` — registered remotes
* `config/repos/<name>/` — local checkout
* `config/installed_modules.json`
* `config/installed_plugins.json`

### Workflow Overview

```text
repo add <name> <git-url>
repo update
download search <keyword>
download install <repo>/<path/to/module.py>
download list
download verify <module/path>
```

### `repo` Command

```bash
repo list                                    # Show registered repos
repo add myrepo https://github.com/user/repo.git
repo update                                  # Update all
repo update myrepo                           # Update one
repo info myrepo                             # Details
repo remove myrepo                           # Unregister + remove clone
```

Notes:

* URL should be a Git clone URL (HTTPS or SSH).
* After `add`, the framework clones into `config/repos/<name>/`.
* The remote layout should expose modules in a discoverable path (typically mirroring `modules/...` structure).

### `download` Command

```bash
download search nmap
download install myrepo/auxiliary/scanner/x.py
download update
download update auxiliary/scanner/x
download list
download verify auxiliary/scanner/x
```

| Subcommand | Purpose |
| ---------- | ------- |
| `search` | Find modules across cloned repos |
| `install` | Copy/install module into local `modules/` tree and register it |
| `update` | Refresh installed modules when remotes changed |
| `list` | Show installed (downloaded) modules |
| `verify` | SHA256 integrity check against recorded hash |

After install, use the module like any built-in one:

```bash
reload
use auxiliary/scanner/x
show options
run
```

### Plugins From Remotes

Plugins use the `plugins` command rather than `download`:

```bash
plugins search <term>
plugins install <source>
plugins update [name]
plugins remove "Name"
plugins list
```

See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

### Recommended Hygiene

1. Prefer trusted repositories only.
2. Run `download verify` after install/update.
3. Review new module source before `run` in sensitive environments.
4. Keep remotes updated with `repo update` periodically.
5. Do not commit secrets into custom module repos.

### Troubleshooting

| Symptom | Likely fix |
| ------- | ---------- |
| `RepoManager` / `ModuleDownloader` not loaded | Restart framework; check startup logs in `config/logs/` |
| `repo add` fails | Validate Git URL, network, and `git` availability |
| `download search` empty | Run `repo update`; confirm module paths in the clone |
| Module not in `search` after install | `reload` or restart; check install path under `modules/` |
| Verify fails | Re-install from updated remote or inspect local edits |

### Related Docs

* [COMMANDS.md](COMMANDS.md) — CLI summary
* [MODULES.md](MODULES.md) — built-in catalog
* [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — authoring modules for a public repo

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Mah Framework, ekstra modül (ve plugin) kaynaklarını çekirdek ağaca gömmeden uzak Git depolarından çekebilir.

### Kavramlar

| Parça | Rol |
| ----- | --- |
| **Repo** | `repo add` ile kayıtlı, `config/repos/` altına klonlanan Git kaynağı |
| **download** | Bu klonlardan modül arama / kurma / güncelleme / doğrulama |
| **installed_modules.json** | `download` ile kurulan modül kaydı |
| **installed_plugins.json** | `plugins install` ile kurulan plugin kaydı |

Yapılandırma:

* `config/repos.json` — kayıtlı uzaklar
* `config/repos/<ad>/` — yerel checkout
* `config/installed_modules.json`
* `config/installed_plugins.json`

### İş Akışı Özeti

```text
repo add <ad> <git-url>
repo update
download search <anahtar>
download install <repo>/<modül/yolu.py>
download list
download verify <modül/yolu>
```

### `repo` Komutu

```bash
repo list
repo add myrepo https://github.com/user/repo.git
repo update
repo update myrepo
repo info myrepo
repo remove myrepo
```

Notlar:

* URL bir Git klon adresi olmalı (HTTPS veya SSH).
* `add` sonrası klon `config/repos/<ad>/` altına gelir.
* Uzak depo düzeni keşfedilebilir olmalı (genelde `modules/...` aynası).

### `download` Komutu

```bash
download search nmap
download install myrepo/auxiliary/scanner/x.py
download update
download update auxiliary/scanner/x
download list
download verify auxiliary/scanner/x
```

| Alt komut | Amaç |
| --------- | ---- |
| `search` | Klonlanmış depolarda ara |
| `install` | Modülü yerel `modules/` ağacına kur ve kaydet |
| `update` | Kurulu modülleri uzak değişikliklere göre yenile |
| `list` | İndirilmiş modülleri listele |
| `verify` | Kayıtlı hash ile SHA256 doğrulama |

Kurulumdan sonra yerleşik modül gibi kullanın:

```bash
reload
use auxiliary/scanner/x
show options
run
```

### Uzaktan Plugin

Pluginler `download` yerine `plugins` komutuyla yönetilir:

```bash
plugins search <terim>
plugins install <kaynak>
plugins update [isim]
plugins remove "İsim"
plugins list
```

Bkz. [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

### Önerilen Hijyen

1. Yalnızca güvendiğiniz depoları ekleyin.
2. Kurulum/güncelleme sonrası `download verify` çalıştırın.
3. Hassas ortamlarda `run` öncesi kaynak kodu inceleyin.
4. Periyodik `repo update` yapın.
5. Özel modül depolarına sır sızdırmayın.

### Sorun Giderme

| Belirti | Muhtemel çözüm |
| ------- | -------------- |
| RepoManager / ModuleDownloader yok | Framework'ü yeniden başlatın; `config/logs/` kontrol edin |
| `repo add` başarısız | Git URL, ağ ve `git` kurulumunu doğrulayın |
| `download search` boş | `repo update`; klondaki modül yollarını kontrol edin |
| Kurulum sonrası `search`'te yok | `reload` veya restart; `modules/` yolunu kontrol edin |
| Verify başarısız | Uzaktan yeniden kurun veya yerel değişiklikleri inceleyin |

### İlgili Belgeler

* [COMMANDS.md](COMMANDS.md) — CLI özeti
* [MODULES.md](MODULES.md) — yerleşik katalog
* [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — public repo için modül yazma
