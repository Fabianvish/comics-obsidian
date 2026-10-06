#!/usr/bin/env python3
"""Gestor de lectura de cómics para Obsidian.

Uso:  python3 comics.py        (en Windows: python comics.py)

Requisitos: Python 3.8 o superior y el plugin Dataview (con «Enable JavaScript Queries») en Obsidian.
El programa vive en la carpeta «programa» (un módulo por tema) y las vistas de Obsidian en «vistas».
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from programa.menu_principal import main  # noqa: E402

if __name__ == "__main__":
    main()
