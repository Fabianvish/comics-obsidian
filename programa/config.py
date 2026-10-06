"""Configuración: lo de este computador (comics_config.json) y lo que viaja con el vault (_programa/estado.json)."""

import datetime
import platform
from pathlib import Path

from .constantes import ARCHIVO_CONFIG_LOCAL, CLAVES_LOCALES, ES_WSL
from .equipos import actualizar_equipo, equipo_actual, leer_equipos, ruta_guardable, ruta_para_este_sistema
from .rutas import RUTAS, guardar_json, leer_json


def leer_config_local():
    """comics_config.json: la clave de la API y, por cada equipo, dónde están sus notas
    (por si la carpeta del programa se comparte entre varios PC)."""
    guardado = leer_json(ARCHIVO_CONFIG_LOCAL, {})
    config = {clave: valor for clave, valor in guardado.items() if clave != "equipos"}
    config.update(guardado.get("equipos", {}).get(equipo_actual(), {}))
    return config


def guardar_config(config):
    """Separa lo de este computador (comics_config.json), las carpetas de cómics de cada PC
    (_programa/equipos.json) y lo que viaja con el vault (_programa/estado.json)."""
    equipos_locales = leer_json(ARCHIVO_CONFIG_LOCAL, {}).get("equipos", {})
    propio = equipos_locales.setdefault(equipo_actual(), {})
    if "notas" in config:
        propio["notas"] = config["notas"]
    else:
        propio.pop("notas", None)
    if RUTAS.archivo_estado is None:  # todavía no sabemos dónde está el vault: se guarda todo aquí
        todo = {clave: valor for clave, valor in config.items() if clave != "notas"}
        guardar_json(ARCHIVO_CONFIG_LOCAL, {**todo, "equipos": equipos_locales})
        return
    guardar_json(RUTAS.archivo_estado, {clave: valor for clave, valor in config.items() if clave not in CLAVES_LOCALES})
    locales = {clave: config[clave] for clave in CLAVES_LOCALES if clave in config and clave not in ("notas", "comics")}
    guardar_json(ARCHIVO_CONFIG_LOCAL, {**locales, "equipos": equipos_locales})
    datos_equipo = {"sistema": "WSL" if ES_WSL else platform.system()}
    if "notas" in config:
        datos_equipo["notas"] = ruta_guardable(config["notas"])
    if isinstance(config.get("comics"), list):
        datos_equipo["comics"] = [ruta_guardable(carpeta) for carpeta in config["comics"]]
    actualizar_equipo(equipo_actual(), **datos_equipo)


def activar_estado(config):
    """Apunta el programa a la carpeta «_programa» del vault y carga de ahí lo que viaja con el vault."""
    RUTAS.activar(Path(config["notas"]))
    RUTAS.carpeta_eventos.mkdir(parents=True, exist_ok=True)
    for clave in [clave for clave in config if clave not in CLAVES_LOCALES]:  # lo portable siempre sale del vault
        del config[clave]
    config.update(leer_json(RUTAS.archivo_estado, {}))
    propio = leer_equipos().get(equipo_actual(), {})
    # las carpetas de cómics de este PC salen del vault (si aún no están, se migran las de comics_config.json)
    if "comics" in propio:
        config["comics"] = [str(ruta_para_este_sistema(carpeta)) for carpeta in propio["comics"]]
    elif isinstance(config.get("comics"), str):
        config["comics"] = [config["comics"]] if config["comics"] else []
    guardar_config(config)
    actualizar_equipo(equipo_actual(), ultimo_uso=datetime.date.today().isoformat())
