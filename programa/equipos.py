"""Los PC donde se lee: nombre de este PC, sus carpetas de cómics (_programa/equipos.json) y rutas entre WSL y Windows."""

import platform
import re
from pathlib import Path

from .rutas import RUTAS, convertir_ruta_windows_a_wsl, guardar_json, leer_json


def equipo_actual():
    """Nombre de este PC. WSL y Windows en el mismo PC dan el mismo nombre y comparten sus rutas."""
    return platform.node() or "este PC"


def ruta_guardable(ruta):
    """Cómo se guarda una ruta en equipos.json: las de Windows vistas desde WSL (/mnt/c/...) como C:\\...,
    así la misma entrada sirve al ejecutar el programa en WSL o directo en Windows."""
    coincidencia = re.match(r"^/mnt/([a-zA-Z])(?:/(.*))?$", str(ruta))
    if coincidencia:
        return f"{coincidencia.group(1).upper()}:\\" + (coincidencia.group(2) or "").replace("/", "\\")
    return str(ruta)


def ruta_para_este_sistema(texto):
    """Lo contrario de ruta_guardable: C:\\... → /mnt/c/... en WSL, /mnt/c/... → C:\\... en Windows."""
    coincidencia = re.match(r"^/mnt/([a-zA-Z])(?:/(.*))?$", texto)
    if coincidencia and platform.system() == "Windows":
        return Path(f"{coincidencia.group(1).upper()}:/{coincidencia.group(2) or ''}")
    return convertir_ruta_windows_a_wsl(texto)


def leer_equipos():
    """Los PC donde se lee, con sus carpetas de cómics (_programa/equipos.json, viaja con el vault)."""
    return leer_json(RUTAS.archivo_equipos, {}) if RUTAS.archivo_equipos else {}


def actualizar_equipo(nombre, **datos):
    """Cambia solo la entrada de un equipo. Se relee justo antes, por si otro PC cambió el archivo
    y OneDrive ya lo sincronizó."""
    equipos = leer_equipos()
    entrada = equipos.setdefault(nombre, {})
    if all(entrada.get(clave) == valor for clave, valor in datos.items()):
        return
    entrada.update(datos)
    guardar_json(RUTAS.archivo_equipos, equipos)


def olvidar_equipo(nombre):
    equipos = leer_equipos()
    if equipos.pop(nombre, None) is not None:
        guardar_json(RUTAS.archivo_equipos, equipos)
