"""Rutas y archivos JSON: dónde vive cada cosa y cómo se leen y guardan (sin preguntar nada al usuario)."""

import json
import re
from pathlib import Path
from pathlib import PureWindowsPath

from .constantes import CARPETA_ESTADO, ES_WSL


def convertir_ruta_windows_a_wsl(ruta):
    ruta = ruta.strip().strip('"').strip("'")
    coincidencia = re.match(r"^([a-zA-Z]):[\\/](.*)$", ruta)
    if coincidencia and ES_WSL:
        return Path(f"/mnt/{coincidencia.group(1).lower()}/{coincidencia.group(2).replace(chr(92), '/')}")
    return Path(ruta).expanduser()


def ruta_a_uri_windows(ruta):
    coincidencia = re.match(r"^/mnt/([a-zA-Z])/(.*)$", str(ruta.resolve()))
    if coincidencia:
        return PureWindowsPath(f"{coincidencia.group(1).upper()}:/{coincidencia.group(2)}").as_uri()
    return ruta.resolve().as_uri()


class Rutas:
    """Dónde vive el estado que viaja con el vault (la carpeta «_programa»). Se activa al arrancar."""

    estado_dir = carpeta_eventos = archivo_historial = archivo_estado = archivo_equipos = None

    def activar(self, base):
        self.estado_dir = base / CARPETA_ESTADO
        self.carpeta_eventos = self.estado_dir / "listas"
        self.archivo_historial = self.estado_dir / "leidos.json"
        self.archivo_estado = self.estado_dir / "estado.json"
        self.archivo_equipos = self.estado_dir / "equipos.json"


RUTAS = Rutas()


def leer_json(ruta, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return defecto


def guardar_json(ruta, datos):
    ruta.write_text(json.dumps(datos, indent=1, ensure_ascii=False), encoding="utf-8")


def ruta_relativa_al_vault(carpeta):
    """Ruta de una carpeta relativa a la raíz del vault ('' si es la raíz)."""
    for ancestro in [carpeta, *carpeta.parents]:
        if (ancestro / ".obsidian").is_dir():
            ruta_relativa = carpeta.relative_to(ancestro).as_posix()
            return "" if ruta_relativa == "." else ruta_relativa
    return carpeta.name


def unir_ruta(*partes):
    return "/".join(parte for parte in partes if parte)
