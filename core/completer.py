# Terminal arayüzünde otomatik tamamlama (autocomplete) işlevini sağlayan modül.
# prompt_toolkit kütüphanesinin 'Completer' sınıfı temel alınarak geliştirilmiştir.

from collections.abc import Iterable
from typing import Any

from prompt_toolkit.completion import (  # Otomatik tamamlama için gerekli temel sınıflar
    Completer,
    Completion,
)
from prompt_toolkit.document import (
    Document,  # İmleç konumu ve mevcut metin hakkında bilgi sağlayan sınıf
)

from core.command import Command  # Komutların temel sınıfı
from core.module import BaseModule  # Modüllerin temel sınıfı
from core.shared_state import shared_state


class CLICompleter(Completer):
    """
    Komut satırı arayüzü (CLI) için özel otomatik tamamlama sınıfı.
    Kullanıcının yazdığı metne göre komutları, aliasları ve modül seçeneklerini tamamlar.
    """

    def __init__(self, command_manager: Any, module_manager: Any) -> None:
        """
        CLICompleter başlatıcı metod.

        Args:
            command_manager: Sistemdeki komutları yöneten nesne. Komut listesine erişim sağlar.
            module_manager: Sistemdeki modülleri yöneten nesne. Modül yollarına erişim sağlar.
        """
        self.command_manager = command_manager
        self.module_manager = module_manager

    def get_completions(
        self, document: Document, complete_event: Any
    ) -> Iterable[Completion]:
        """
        Kullanıcı 'Tab' tuşuna bastığında veya yazarken çağrılan ana metod.
        İmleçten önceki metne göre bağlama uygun otomatik tamamlama önerilerini üretir.

        Args:
            document (Document): Kullanıcının terminale girdiği metin ve imleç konumu bilgisini içeren nesne.
            complete_event: Tamamlama olayını tetikleyen bilgiler (prompt_toolkit tarafından sağlanır).

        Yields:
            Completion: 'prompt_toolkit' tarafından gösterilecek tamamlama önerileri.
        """
        text_before_cursor = document.text_before_cursor  # İmleçten önceki metin
        words = text_before_cursor.split()  # Metni kelimelere böl

        # Eğer henüz hiçbir şey yazılmamışsa veya sadece boşluk varsa, tüm komutları öner.
        if not text_before_cursor.strip():
            yield from self._get_command_completions("")
            return

        # Yorum satırı başlıyorsa (#), tamamlama yapma.
        if text_before_cursor.strip().startswith("#"):
            return

        # Eğer kullanıcı tek bir kelime yazıyorsa ve henüz boşluk bırakmamışsa
        # (yani komut adını yazmaya çalışıyorsa), komut tamamlamalarını öner.
        if len(words) == 1 and not text_before_cursor.endswith(" "):
            current_word = words[0]
            yield from self._get_command_completions(current_word)
        else:
            # Kullanıcı komut adını yazmış ve bir argümana geçmiş olabilir.
            command_name = words[0].lower()

            # Girilen ilk kelime bir komut mu yoksa alias mı kontrol et.
            resolved_command_name, _is_alias = self.command_manager.resolve_command(
                command_name
            )

            if resolved_command_name:
                # Komut nesnesini bul.
                command_obj: Command | None = (
                    self.command_manager.get_all_commands().get(resolved_command_name)
                )

                if command_obj:
                    # Eğer komutun kendine ait özel bir tamamlama fonksiyonu varsa (completer_function),
                    # kontrolü o fonksiyona devret. (Örn: 'use' komutu modül yollarını tamamlar)
                    if command_obj.completer_function:
                        completions = command_obj.get_completions(
                            text_before_cursor, document.get_word_before_cursor()
                        )
                        for comp in completions:
                            if isinstance(comp, Completion):
                                yield comp
                            else:
                                # Eğer fonksiyon sadece string listesi döndürdüyse, Completion nesnesine çevir.
                                word_len = len(document.get_word_before_cursor())
                                yield Completion(comp, start_position=-word_len)
                    else:
                        # Komutun özel bir tamamlayıcısı yoksa bir şey yapma.
                        pass
            else:
                # İlk kelime bilinen bir komut değilse tamamlama yapma.
                pass

    def _get_command_completions(self, current_word: str) -> Iterable[Completion]:
        """
        Girilen kelime parçasına uygun komut ve alias önerilerini üretir.
        """
        get_names = getattr(self.command_manager, "get_completion_names", None)
        if callable(get_names):
            all_names = get_names()
        else:
            all_names = sorted(
                set(self.command_manager.get_all_commands().keys())
                | set(self.command_manager.get_aliases().keys())
            )

        all_aliases = self.command_manager.get_aliases()
        all_commands = self.command_manager.get_all_commands()

        for name in all_names:
            if name.startswith(current_word):
                display_meta = ""
                if name in all_aliases:
                    display_meta = f"(alias for {all_aliases[name]})"
                elif name in all_commands:
                    display_meta = all_commands[name].Description

                yield Completion(
                    name, start_position=-len(current_word), display_meta=display_meta
                )

    def _get_module_paths_completions(self, current_word: str) -> list[str]:
        """Modül yollarını tamamlamak için yardımcı metod."""
        get_paths = getattr(self.module_manager, "get_module_paths", None)
        if callable(get_paths):
            module_paths = get_paths()
        else:
            module_paths = sorted(self.module_manager.get_all_modules().keys())
        return [path for path in module_paths if path.startswith(current_word)]

    def _get_module_options_completions(self, current_word: str) -> list[str]:
        """Aktif modülün seçeneklerini tamamlamak için yardımcı metod."""
        selected_module: BaseModule | None = shared_state.get_selected_module()
        if selected_module:
            option_names = sorted(selected_module.get_options().keys())
            return [name for name in option_names if name.startswith(current_word)]
        return []
