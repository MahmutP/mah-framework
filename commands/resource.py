# Resource komutu - .rc dosyalarından komut çalıştırma
# Metasploit'teki resource komutu gibi çalışır
from pathlib import Path
from typing import Any, List
from core.command import Command
from core.shared_state import shared_state
from rich import print


class Resource(Command):
    """Resource dosyasından komutları çalıştıran komut.
    
    Metasploit'teki resource komutu gibi çalışır.
    .rc dosyasındaki her satırı sırayla çalıştırır.
    """
    
    Name = "resource"
    Description = "Bir kaynak dosyasından (.rc) komutları çalıştırır."
    Category = "core"
    Aliases = []
    Usage = "resource <dosya_yolu>"
    Examples = [
        "resource saldiri.rc      # Mevcut dizindeki dosyayı çalıştırır",
        "resource /yol/dosya.rc   # Tam yol ile çalıştırır",
        "resource scripts/test.rc # Görece yol ile çalıştırır"
    ]
    
    def __init__(self):
        """init fonksiyon"""
        super().__init__()
        self.completer_function = self._resource_completer
    
    def _resource_completer(self, text: str, word_before_cursor: str) -> List[str]:
        """Resource komutu otomatik tamamlaması - .rc dosyalarını önerir.
        
        Args:
            text (str): Yazılan metin
            word_before_cursor (str): İmleçten önceki kelime
            
        Returns:
            List[str]: Tamamlama önerileri
        """
        parts = text.split()
        
        if len(parts) == 1 and text.endswith(' '):
            # "resource " yazıldı, .rc dosyalarını listele
            return self._get_rc_files("")
        elif len(parts) == 2 and not text.endswith(' '):
            # "resource sal" gibi yazılıyor
            return self._get_rc_files(parts[1])
        
        return []
    
    def _get_rc_files(self, prefix: str) -> List[str]:
        """Belirtilen prefix ile başlayan .rc dosyalarını döndürür.
        
        Args:
            prefix: Dosya adı prefix'i
            
        Returns:
            .rc dosya listesi
        """
        rc_files = []
        
        try:
            # Mevcut dizindeki .rc dosyaları
            current_dir = Path(".")
            for f in current_dir.glob("*.rc"):
                if f.name.startswith(prefix) or prefix == "":
                    rc_files.append(f.name)
            
            # scripts/ klasöründeki .rc dosyaları
            scripts_dir = Path("scripts")
            if scripts_dir.exists():
                for f in scripts_dir.glob("*.rc"):
                    path = f"scripts/{f.name}"
                    if path.startswith(prefix) or f.name.startswith(prefix) or prefix == "":
                        rc_files.append(path)
        except Exception:
            pass
        
        return sorted(rc_files)
    
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Resource dosyasını çalıştırır.
        
        Args:
            args: Dosya yolu
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        if not args:
            print("[bold red]Hata:[/bold red] Dosya yolu belirtilmedi.")
            print("Kullanım: resource <dosya_yolu>")
            return False
        
        file_path = Path(args[0])
        
        if not file_path.exists():
            print(f"[bold red]Hata:[/bold red] Dosya bulunamadı: {file_path}")
            return False
        
        if not file_path.is_file():
            print(f"[bold red]Hata:[/bold red] '{file_path}' bir dosya değil.")
            return False
        
        return self.run_resource_file(file_path)
    
    def run_resource_file(self, file_path: Path) -> bool:
        """Resource dosyasındaki komutları çalıştırır.
        
        Args:
            file_path: .rc dosyasının yolu
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        print(f"\n[bold cyan]📜 Resource dosyası çalıştırılıyor:[/bold cyan] {file_path}\n")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"[bold red]Hata:[/bold red] Dosya okunamadı: {e}")
            return False
        
        command_manager = shared_state.command_manager
        if not command_manager:
            print("[bold red]Hata:[/bold red] CommandManager başlatılmamış.")
            return False
        
        success_count = 0
        error_count = 0
        
        for line_num, line in enumerate(lines, 1):
            # Boş satırları ve yorumları atla
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Komutu göster
            print(f"[dim]({line_num})[/dim] [bold yellow]>[/bold yellow] {line}")
            
            # Komutu çalıştır
            try:
                parts = line.split()
                if not parts:
                    continue
                
                command_name = parts[0].lower()
                command_args = parts[1:] if len(parts) > 1 else []
                
                # Komutu çöz (alias kontrolü dahil)
                resolved_name, _ = command_manager.resolve_command(command_name)
                
                if not resolved_name:
                    print(f"[bold red]  ✗ Bilinmeyen komut: {command_name}[/bold red]")
                    error_count += 1
                    continue
                
                # Komutu al ve çalıştır
                cmd_obj = command_manager.get_all_commands().get(resolved_name)
                if cmd_obj:
                    result = cmd_obj.execute(*command_args)
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    print(f"[bold red]  ✗ Komut objesi bulunamadı: {resolved_name}[/bold red]")
                    error_count += 1
                    
            except Exception as e:
                print(f"[bold red]  ✗ Hata: {e}[/bold red]")
                error_count += 1
        
        # Özet
        print(f"\n[bold cyan]📊 Özet:[/bold cyan] {success_count} başarılı, {error_count} hatalı komut")
        
        return error_count == 0
