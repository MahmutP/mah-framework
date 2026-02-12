from rich.console import Console
from rich.text import Text
import pyfiglet
import random

def print_banner():
    """Renders a colorful banner using a random font."""
    # Konsol çıktısı için Rich kütüphanesi başlatılıyor
    console = Console()
    
    # Okunabilir ve iyi boyutlandırılmış fontların özenle seçilmiş listesi.
    # Bu liste, çerçeve başlatıldığında kullanıcıya farklı görsel deneyimler sunmak için kullanılır.
    # Her font farklı bir ASCII sanat stili üretir.
    curated_fonts = [
        "slant", "standard", "doom", "big", "small", 
        "cybermedium", "smslant", "block", "digital", 
        "shadow", "speed", "lean", "mini", "script",
        "ivrit", "computer"
    ]
    
    # Listeden rastgele bir font seçiliyor.
    # Bu sayede her başlatmada farklı bir banner görünümü elde edilir.
    font = random.choice(curated_fonts)
    
    try:
        # Seçilen font kullanılarak "Mah Framework" metni ASCII sanatına dönüştürülüyor.
        # pyfiglet kütüphanesi bu işlemi gerçekleştirir.
        ascii_art = pyfiglet.figlet_format("Mah Framework", font=font)
    except Exception:
        # Eğer seçilen font ile oluşturma başarısız olursa (örneğin font dosyası eksikse),
        # varsayılan olarak "slant" fontu kullanılır. Bu bir hata yönetimi mekanizmasıdır.
        ascii_art = pyfiglet.figlet_format("Mah Framework", font="slant")
        font = "slant (fallback)"

    # Rich Text nessesi oluşturuluyor. Bu nesne, metni stillendirmek (renk, kalınlık vb.) için kullanılır.
    rich_text = Text()
    
    # Gökkuşağı efekti oluşturmak için kullanılacak renklerin listesi (Hex kodları).
    colors = [
        "#FF0000", "#FF7F00", "#FFFF00", "#00FF00", 
        "#0000FF", "#4B0082", "#9400D3"
    ]
    
    # ASCII sanat metni satır satır bölünüyor.
    lines = ascii_art.splitlines()
    for i, line in enumerate(lines):
        for j, char in enumerate(line):
            # Her karakter için bir renk indeksi hesaplanıyor.
            # (i + j / 2) formülü, renklerin çapraz (diagonal) bir gradyan oluşturmasını sağlar.
            # % len(colors) işlemi, renk listesinin sınırları içinde kalınmasını sağlar.
            color_index = int((i + j / 2) / 4) % len(colors)
            
            # Karakter, hesaplanan renk stiliyle Text nesnesine ekleniyor.
            rich_text.append(char, style=colors[color_index])
        # Her satırın sonuna yeni satır karakteri ekleniyor.
        rich_text.append("\n")
        
    # Oluşturulan renkli banner konsola yazdırılıyor.
    console.print(rich_text)
