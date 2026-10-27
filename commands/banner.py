# temel komut banner, banner ve modül bilgisi basacak.
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text

from core.banner import print_banner
from core.command import Command
from core.shared_state import shared_state


class BannerCommand(Command):
    """Banner basmaya yarıyan komut."""

    Name = "banner"
    Description = "Rastgele bir banner basar."
    Category = "system"
    Aliases = []
    Usage = "banner"
    Examples = ["banner                   # Rastgele ASCII art banner gösterir"]

    def execute(self, *args: str, **kwargs: Any) -> bool:
        try:
            console = Console()

            # Banner'ı bas
            print_banner()

            base_dir = Path(__file__).parent.parent

            # Managers
            command_manager = getattr(shared_state, "command_manager", None)
            module_manager = getattr(shared_state, "module_manager", None)
            plugin_manager = getattr(shared_state, "plugin_manager", None)

            total_commands = 0
            if command_manager:
                try:
                    total_commands = len(command_manager.get_all_commands())
                except Exception:
                    total_commands = 0
            else:
                # Fallback: count command files
                try:
                    cmd_dir = base_dir / "commands"
                    total_commands = len(
                        [
                            f
                            for f in cmd_dir.glob("*.py")
                            if f.name != "__init__.py" and "__pycache__" not in str(f)
                        ]
                    )
                except Exception:
                    total_commands = 0

            total_modules = 0
            category_counts: dict[str, int] = {}
            if module_manager:
                try:
                    categorized_modules = module_manager.get_modules_by_category()
                    for category, modules in categorized_modules.items():
                        count = len(modules)
                        total_modules += count
                        top_level_category = (
                            category.split("/")[0] if "/" in category else category
                        )
                        display_name = top_level_category.capitalize()
                        if display_name in category_counts:
                            category_counts[display_name] += count
                        else:
                            category_counts[display_name] = count
                except Exception:
                    pass
            else:
                # Fallback: count modules by directories
                try:
                    modules_dir = base_dir / "modules"
                    for sub in ["auxiliary", "example", "exploit", "payloads", "post"]:
                        p = modules_dir / sub
                        if p.exists():
                            count = len(
                                [
                                    f
                                    for f in p.rglob("*.py")
                                    if f.name != "__init__.py"
                                    and "__pycache__" not in str(f)
                                ]
                            )
                            if count > 0:
                                cat = sub.capitalize()
                                category_counts[cat] = category_counts.get(cat, 0) + count
                                total_modules += count
                    # Also count anything else
                except Exception:
                    pass

            plugin_count = 0
            if plugin_manager:
                try:
                    plugin_count = len(plugin_manager.get_all_plugins())
                except Exception:
                    plugin_count = 0
            else:
                try:
                    plg_dir = base_dir / "plugins"
                    if plg_dir.exists():
                        plugin_count = len(
                            [
                                f
                                for f in plg_dir.glob("*.py")
                                if f.name != "__init__.py" and "__pycache__" not in str(f)
                            ]
                        )
                except Exception:
                    plugin_count = 0

            # Versiyon
            try:
                from main import _get_cached_framework_version

                version = _get_cached_framework_version(base_dir)
                if version:
                    version_line = (
                        f"[dim]       =[[/dim] [bold cyan]Mah Framework[/bold cyan] "
                        f"[bold]{version}[/bold] [dim]]=[/dim]"
                    )
                else:
                    version_line = (
                        "[dim]       =[[/dim] [bold cyan]Mah Framework[/bold cyan] [dim]]=[/dim]"
                    )
            except Exception:
                version_line = (
                    "[dim]       =[[/dim] [bold cyan]Mah Framework[/bold cyan] [dim]]=[/dim]"
                )

            # Satır 1
            line1 = f"[green]{total_modules}[/green] modules - [yellow]{total_commands}[/yellow] commands"
            if plugin_count > 0:
                line1 += f" - [magenta]{plugin_count}[/magenta] plugins"

            category_parts = []
            colors = ["green", "yellow", "magenta", "cyan", "blue", "red"]
            for idx, (cat_name, count) in enumerate(sorted(category_counts.items())):
                color = colors[idx % len(colors)]
                category_parts.append(f"[{color}]{count}[/{color}] {cat_name.lower()}")

            lines_to_print = []
            lines_to_print.append(line1)
            for i in range(0, len(category_parts), 3):
                chunk = category_parts[i : i + 3]
                lines_to_print.append(" - ".join(chunk))

            max_len = 0
            line_lengths = []
            for line in lines_to_print:
                text_obj = Text.from_markup(line)
                visible_len = len(text_obj)
                line_lengths.append(visible_len)
                if visible_len > max_len:
                    max_len = visible_len

            console.print()
            console.print(version_line)
            for i, line in enumerate(lines_to_print):
                padding = " " * (max_len - line_lengths[i])
                console.print(f"[dim]+ -- --=[[/dim] {line}{padding} [dim]]=--[/dim]")
            console.print()

            return True
        except Exception as e:
            print(f"Banner basılırken hata oluştu: {e}")
            return False
