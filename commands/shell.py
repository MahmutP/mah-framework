import os
import shlex
import subprocess
from typing import Any

from rich import print

from core.command import Command


class Shell(Command):
    """terminal komutları çalıştırmaya yarıyan komut

    Args:
        Command (_type_): Ana komut sınıfı

    Returns:
        _type_: _description_
    """

    Name = "shell"
    Description = "Sistem kabuğuna düşer."
    Category = "system"
    Aliases = ["!"]
    Usage = "shell [komut]"
    Examples = [
        "shell                    # Interaktif shell oturumu açar",
        "shell ls -la             # 'ls -la' komutunu çalıştırır",
        "shell whoami             # Mevcut kullanıcı adını gösterir",
        "! pwd                    # Mevcut dizini gösterir (alias)",
    ]

    def execute(self, *args: str, **kwargs: Any) -> bool:
        """komut çalıştırılınca çalışacak fonksiyon.

        Returns:
            bool: _description_
        """
        command_to_execute = " ".join(args)
        if not command_to_execute:
            print("Sistem kabuğuna düşülüyor. Çıkmak için 'exit' yazın.")
            try:
                if os.name == "nt":
                    subprocess.run("cmd.exe", shell=True, check=True)
                    # subprocess.run("powershell.exe", shell=True, check=True)
                    # "shell komut" metodunda komutu powershell de çalıştırabilirsem powershelle geçieceğim.
                else:
                    subprocess.run("/bin/bash", shell=True, check=True)
                print("Sistem kabuğundan çıkıldı.")
            except subprocess.CalledProcessError as e:
                print(f"Sistem kabuğu hatası: {e}")
                return False
            except Exception as e:
                print(f"Sistem kabuğuna düşerken beklenmedik hata: {e}")
                return False
        else:
            print(f"Sistem komutu çalıştırılıyor: {command_to_execute}")
            try:
                cmd_list = shlex.split(command_to_execute)
                result = subprocess.run(
                    cmd_list,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                if result.stdout:
                    print(result.stdout.strip())
                if result.stderr:
                    print(f"Komut hata çıktısı: {result.stderr.strip()}")
                return True
            except subprocess.CalledProcessError as e:
                print(
                    f"Komut '{command_to_execute}' çalıştırılırken hata oluştu (Çıkış kodu: {e.returncode}): {e.stderr.strip()}"
                )
                return False
            except FileNotFoundError:
                print(
                    f"Komut bulunamadı: '{command_to_execute}'. Sistem PATH'inde olduğundan emin olun."
                )
                return False
            except ValueError as e:
                print(f"Komut ayrıştırma hatası: {e}")
                return False
            except Exception as e:
                print(f"Sistem komutu çalıştırılırken beklenmedik hata: {e}")
                return False
        return True
