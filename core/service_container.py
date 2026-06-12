# Servis konteyneri (Service Container) - Dependency Injection için merkezi kayıt ve çözümleme noktası.
# SharedState singleton yerine geçecek, test edilebilir ve izole edilebilir servis yönetimi sağlar.

from typing import Any, TypeVar, Callable
from threading import Lock

T = TypeVar("T")


class ServiceContainer:
    """
    Bağımlılık Enjeksiyon (DI) Konteyneri.

    Servisleri kaydetmek, çözmek (resolve) ve yaşam döngülerini yönetmek için kullanılır.
    Singleton pattern yerine geçerek test izolasyonunu ve paralelliği destekler.
    """

    def __init__(self) -> None:
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Callable[[], Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._lock = Lock()

    def register(self, service_type: type[T], instance: T) -> None:
        """
        Bir servis örneğini doğrudan kaydeder (singleton olarak).

        Args:
            service_type: Servisin tipi (interface veya concrete class).
            instance: Kaydedilecek servis örneği.
        """
        with self._lock:
            self._services[service_type] = instance

    def register_factory(self, service_type: type[T], factory: Callable[[], T]) -> None:
        """
        Bir servis için factory (fabrik) fonksiyonu kaydeder.
        Her resolve çağrısında yeni bir örnek oluşturulur (transient).

        Args:
            service_type: Servisin tipi.
            factory: Servis örneği üreten fonksiyon.
        """
        with self._lock:
            self._factories[service_type] = factory

    def register_singleton(self, service_type: type[T], factory: Callable[[], T]) -> None:
        """
        Bir servis için singleton factory kaydeder.
        İlk resolve çağrısında oluşturulur, sonraki çağrılarda aynı örnek döner.

        Args:
            service_type: Servisin tipi.
            factory: Servis örneği üreten fonksiyon.
        """
        with self._lock:
            self._singletons[service_type] = factory

    def resolve(self, service_type: type[T]) -> T:
        """
        Kayıtlı bir servisi çözümler (getirir).

        Öncelik sırası:
        1. Doğrudan kaydedilmiş instance (_services)
        2. Singleton factory (_singletons) - ilk çağrıda oluşturur, cache'ler
        3. Factory (_factories) - her çağrıda yeni örnek oluşturur

        Args:
            service_type: Çözümlenecek servis tipi.

        Returns:
            Servis örneği.

        Raises:
            KeyError: Servis kayıtlı değilse.
        """
        with self._lock:
            # 1. Doğrudan instance
            if service_type in self._services:
                return self._services[service_type]

            # 2. Singleton factory
            if service_type in self._singletons:
                factory = self._singletons[service_type]
                instance = factory()
                # Cache'e taşı (bir sonraki çağrılarda doğrudan instance olarak dönsün)
                self._services[service_type] = instance
                del self._singletons[service_type]
                return instance

            # 3. Transient factory
            if service_type in self._factories:
                factory = self._factories[service_type]
                return factory()

            raise KeyError(f"Servis bulunamadı: {service_type}")

    def try_resolve(self, service_type: type[T]) -> T | None:
        """
        Servisi çözmeye çalışır, bulunamazsa None döner (exception fırlatmaz).

        Args:
            service_type: Çözümlenecek servis tipi.

        Returns:
            Servis örneği veya None.
        """
        try:
            return self.resolve(service_type)
        except KeyError:
            return None

    def is_registered(self, service_type: type) -> bool:
        """
        Bir servisin kayıtlı olup olmadığını kontrol eder.

        Args:
            service_type: Kontrol edilecek servis tipi.

        Returns:
            Kayıtlıysa True, değilse False.
        """
        with self._lock:
            return (
                service_type in self._services
                or service_type in self._singletons
                or service_type in self._factories
            )

    def clear(self) -> None:
        """Tüm kayıtları temizler (testler için)."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()

    def create_scope(self) -> "ServiceContainer":
        """
        Yeni bir alt kapsam (child scope) oluşturur.
        Parent'taki kayıtları miras alır, kendi kayıtları izole eder.

        Returns:
            Yeni ServiceContainer örneği.
        """
        child = ServiceContainer()
        with self._lock:
            # Parent'taki kayıtları kopyala (shallow copy)
            child._services = self._services.copy()
            child._factories = self._factories.copy()
            child._singletons = self._singletons.copy()
        return child


# Global konteyner örneği (uygulama başlangıcında initialize edilir)
# Testlerde bu yerine mock konteyner enjekte edilebilir.
container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    """Global konteyner örneğini döndürür."""
    global container
    if container is None:
        container = ServiceContainer()
    return container


def set_container(new_container: ServiceContainer) -> None:
    """Global konteyneri değiştirir (testler için)."""
    global container
    container = new_container


def reset_container() -> None:
    """Global konteyneri sıfırlar (testler için)."""
    global container
    container = ServiceContainer()