"""Errores del programa y cómo mostrárselos a quien lo usa."""

import datetime
import json
import urllib.error
import xml.etree.ElementTree as ET

from .constantes import ARCHIVO_REGISTRO_ERRORES


class ErrorAmigable(Exception):
    """Un error esperable: se le muestra a quien usa el programa tal cual, sin detalle técnico."""

    icono = "❌"


class ErrorAPI(ErrorAmigable):
    pass


class LimiteAPI(ErrorAPI):
    icono = "⏳"


def reportar_error(error):
    """Muestra un mensaje claro, guarda el detalle técnico en un archivo y deja el programa abierto."""
    import socket
    import traceback

    if isinstance(error, ErrorAmigable):
        print(f"{error.icono} {error}")
        return
    try:
        previo = ARCHIVO_REGISTRO_ERRORES.read_text(encoding="utf-8") if ARCHIVO_REGISTRO_ERRORES.exists() else ""
        entrada = f"=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===\n{traceback.format_exc()}\n"
        ARCHIVO_REGISTRO_ERRORES.write_text((previo + entrada)[-200000:], encoding="utf-8")
    except Exception:
        pass
    print(f"\n😕 Se produjo un error: {error}")
    if isinstance(error, (urllib.error.URLError, socket.timeout)):
        print("   Parece un problema de conexión a internet. Conviene intentarlo de nuevo más tarde.")
    elif isinstance(error, (json.JSONDecodeError, ET.ParseError)):
        print(
            "   Un archivo de datos está dañado. Se puede recuperar una copia con «Configuración → Restaurar un respaldo»."
        )
    elif isinstance(error, FileNotFoundError) and "vistas" in str(error):
        print("   Falta la carpeta «vistas» junto a comics.py.")
    elif isinstance(error, OSError):
        print("   Verificar que el disco u OneDrive estén disponibles y que ningún programa tenga abierto ese archivo.")
    print(f"   El programa sigue abierto. El detalle técnico quedó en {ARCHIVO_REGISTRO_ERRORES.name}.")
