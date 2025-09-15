#!/usr/bin/env python3
__version__ = "0.0.1"

# Keep __init__ lightweight. Do not import submodules here to avoid side effects
# when running modules via `python -m`, which may lead to runpy warnings.
__all__ = ["__version__"]
