"""Dungeon Masters Guide - Core game engine package.

Module Registration System:
Makes commonly imported modules available as if they were top-level modules,
allowing existing absolute imports to work without sys.path pollution.
"""

import sys

# Register package modules in sys.modules so they can be imported as top-level
# This allows code like "from states import PlayState" to work from within the package


def _register_modules():
    """Register package modules as top-level imports."""
    package_name = __name__  # 'bedlam'

    # Core modules that are frequently imported as absolutes
    modules_to_register = [
        "states",
        "world",
        "time_manager",
        "camera",
        "pause_menu",
        "systems",
        "entities",
        "ui",
    ]

    for module_name in modules_to_register:
        full_module_name = f"{package_name}.{module_name}"

        # Only register if the full module path exists in sys.modules
        # This ensures we don't create broken references
        if full_module_name in sys.modules:
            sys.modules[module_name] = sys.modules[full_module_name]
        else:
            # Try to import it first, then register
            try:
                __import__(full_module_name)
                if full_module_name in sys.modules:
                    sys.modules[module_name] = sys.modules[full_module_name]
            except ImportError:
                # Skip modules that can't be imported (they may not be ready yet)
                pass


# Register modules when this package is imported
_register_modules()

# Clean up the registration function from the namespace
del _register_modules
