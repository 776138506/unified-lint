"""Chain rule plugin loader for spec_lint.

Plugins live in `.unified-lint/rules/*.py` under the specs directory.
Each plugin exports one or more functions decorated with `@chain_rule`.

The CLI tool will discover and run all loaded plugins.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable


def discover_plugins(specs_dir: Path) -> dict[str, Callable]:
    """Discover and load all chain rule plugins.

    Returns: dict mapping rule_id -> callable(index, specs_dir) -> list[Violation]
    """
    rules_dir = specs_dir / ".unified-lint" / "rules"
    if not rules_dir.exists():
        return {}
    loaded: dict[str, Callable] = {}
    # Add rules dir to path so plugins can import local helpers
    rules_dir_str = str(rules_dir.resolve())
    for f in sorted(rules_dir.glob("*.py")):
        module_name = f"_spec_rule_{f.stem}"
        spec = importlib.util.spec_from_file_location(module_name, f)
        if spec is None or spec.loader is None:
            continue
        # Prepend rules_dir to sys.path
        if rules_dir_str not in sys.path:
            sys.path.insert(0, rules_dir_str)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"  warn: failed to load plugin {f.name}: {e}", file=sys.stderr)
            continue
        for name in dir(mod):
            obj = getattr(mod, name)
            if callable(obj) and getattr(obj, "_is_chain_rule", False):
                rule_id = getattr(obj, "_rule_id", name)
                loaded[rule_id] = obj
    return loaded
