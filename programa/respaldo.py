"""Copias de seguridad de las notas y del estado."""

import datetime
import zipfile
from pathlib import Path

from .rutas import RUTAS
from .constantes import MAXIMO_RESPALDOS, CARPETA_RESPALDOS


def archivos_de_estado():
    if RUTAS.estado_dir is None or not RUTAS.estado_dir.is_dir():
        return []
    return [
        archivo
        for archivo in sorted(RUTAS.estado_dir.rglob("*"))
        if archivo.is_file() and archivo.stat().st_size < 20_000_000
    ]


def respaldar(base):
    """Copia comprimida de las notas (.md) y de lo que viaja con el vault (eventos, leídos, cómics que sigues).
    Guarda las últimas 10."""
    notas = [archivo for archivo in base.rglob("*.md")] if base.is_dir() else []
    estado = archivos_de_estado()
    if not notas and not estado:
        return
    CARPETA_RESPALDOS.mkdir(exist_ok=True)
    nombre = CARPETA_RESPALDOS / (datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".zip")
    with zipfile.ZipFile(nombre, "w", zipfile.ZIP_DEFLATED) as archivo_zip:
        for archivo in notas:
            archivo_zip.write(archivo, Path("notas") / archivo.relative_to(base))
        for archivo in estado:
            archivo_zip.write(archivo, Path("programa") / archivo.relative_to(RUTAS.estado_dir))
    for respaldo_antiguo in sorted(CARPETA_RESPALDOS.glob("*.zip"))[:-MAXIMO_RESPALDOS]:
        respaldo_antiguo.unlink()


def destino_de_archivo_del_respaldo(miembro, base):
    """Dónde va cada archivo de un respaldo (también entiende el formato de versiones anteriores)."""
    partes = Path(miembro).parts
    if not partes or ".." in partes or Path(miembro).is_absolute():
        return None
    if partes[0] == "notas" and len(partes) > 1:
        return base.joinpath(*partes[1:])
    if partes[0] == "programa" and len(partes) > 1:
        return RUTAS.estado_dir.joinpath(*partes[1:])
    if partes[0] == "listas" and len(partes) == 2:
        return RUTAS.carpeta_eventos / partes[1]
    if miembro == "leidos.json":
        return RUTAS.archivo_historial
    return None
