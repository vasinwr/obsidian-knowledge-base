"""Plugin registry and discovery."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from kb.plugins.base import SourcePlugin

_registry: list[SourcePlugin] = []


def register(plugin: SourcePlugin) -> None:
    """Register a plugin instance."""
    if plugin not in _registry:
        _registry.append(plugin)


def get_plugin_for(source: str) -> SourcePlugin | None:
    """Return the first registered plugin that can handle *source*."""
    for plugin in _registry:
        if plugin.can_handle(source):
            return plugin
    return None


def list_plugins() -> list[SourcePlugin]:
    """Return all registered plugins."""
    return list(_registry)


def load_builtin_plugins() -> None:
    """Import and register all built-in plugins."""
    from kb.plugins.markdown import MarkdownPlugin
    from kb.plugins.pdf import PdfPlugin
    from kb.plugins.twitter import TwitterPlugin
    from kb.plugins.web import WebPlugin

    for cls in (WebPlugin, PdfPlugin, TwitterPlugin, MarkdownPlugin):
        register(cls())


def load_external_plugins(directory: Path) -> None:
    """Discover and load plugins from a directory.

    Any ``.py`` file in *directory* that defines a module-level ``plugin``
    variable (which must be a :class:`SourcePlugin`) will be registered.
    """
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"kb_ext_{path.stem}", path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod.__name__] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            continue
        plugin = getattr(mod, "plugin", None)
        if isinstance(plugin, SourcePlugin):
            register(plugin)


def reset_registry() -> None:
    """Clear all registered plugins (useful for testing)."""
    _registry.clear()
