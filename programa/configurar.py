"""Preguntas de configuración: carpeta de notas, carpetas de cómics de este PC y clave de Comic Vine.
Las usan el arranque, el generador (la primera vez) y el menú Configuración."""

import platform
from pathlib import Path

from .config import guardar_config
from .constantes import ES_WSL
from .equipos import equipo_actual, leer_equipos, ruta_para_este_sistema
from .rutas import convertir_ruta_windows_a_wsl
from .teclado import pedir_texto
from .ui import pedir, por_numero


def ejemplo_ruta(*partes):
    if platform.system() == "Windows" or ES_WSL:
        return "C:\\Users\\TuUsuario\\" + "\\".join(partes)
    return "~/" + "/".join(partes)


def pedir_ruta(config, clave_config, pregunta, ejemplo):
    while clave_config not in config:
        texto = pedir_texto(f"{pregunta}\n  (ejemplo: {ejemplo})\n> ").strip()
        if not texto:
            continue
        config[clave_config] = str(convertir_ruta_windows_a_wsl(texto))
        guardar_config(config)
    return Path(config[clave_config])


def carpeta_notas(config):
    if "notas" not in config:
        print("\n👋 Se necesita indicar dónde guardar las notas.")
        print("   Puede ser el vault de Obsidian o una carpeta dentro de él.")
    base = pedir_ruta(config, "notas", "¿Carpeta para las notas?", ejemplo_ruta("Obsidian", "MiVault", "Comics"))
    if not any((carpeta / ".obsidian").is_dir() for carpeta in [base, *base.parents]):
        print(
            "⚠️  No se encontró un vault de Obsidian en esa ruta (carpeta .obsidian). "
            "Las notas se crearán igual; conviene abrir la carpeta como vault o moverla dentro de uno."
        )
    return base


def pedir_carpeta_de_comics(pregunta="¿Carpeta de cómics?", permitir_ninguna=False):
    """Pide una carpeta que exista. Con permitir_ninguna, «N» = ninguna por ahora (devuelve None). Para cancelar, Esc."""
    salida = "N = ninguna por ahora" if permitir_ninguna else "Esc = cancelar"
    while True:
        texto = pedir(f"{pregunta}\n  (ejemplo: {ejemplo_ruta('Comics')}; {salida})\n> ")
        if permitir_ninguna and texto.lower() == "n":
            return None
        ruta = convertir_ruta_windows_a_wsl(texto)
        if ruta.is_dir():
            return ruta
        print("❌ Esa carpeta no existe. Revisar la ruta.")


def carpetas_archivos_comics(config):
    """Carpetas donde buscar los archivos de cómics en este PC (pueden ser varias).
    La primera vez ofrece usar las de otro PC donde se lee, o pregunta por una."""
    if isinstance(config.get("comics"), str):  # versiones anteriores guardaban una sola carpeta
        config["comics"] = [config["comics"]] if config["comics"] else []
        guardar_config(config)
    if "comics" not in config:
        print(f"\n📁 ¿Dónde están los cómics en este PC ({equipo_actual()})?")
        otros = {
            nombre: datos
            for nombre, datos in leer_equipos().items()
            if nombre != equipo_actual() and datos.get("comics")
        }
        nombres = sorted(otros, key=str.lower)
        if nombres:
            print("   Carpetas de los otros PC donde lees:")
            for posicion, nombre in enumerate(nombres, 1):
                print(f"  {posicion}. {nombre}: {', '.join(otros[nombre]['comics'])}")
            print("   0. Ninguno: indicar otras carpetas")
            respuesta = pedir("¿Usar aquí las carpetas de alguno? (solo se copian las rutas, no los archivos)\n> ")
            while respuesta != "0" and not por_numero(respuesta, nombres):
                respuesta = pedir(f"Elegir un número de 0 a {len(nombres)}: ")
            nombre = por_numero(respuesta, nombres)
            if nombre:
                config["comics"] = [str(ruta_para_este_sistema(carpeta)) for carpeta in otros[nombre]["comics"]]
                guardar_config(config)
                return [Path(carpeta) for carpeta in config["comics"]]
        print("   Si todavía no hay, escribir N (se pueden agregar después en «Configuración → Carpetas de cómics de este PC»).")
        ruta = pedir_carpeta_de_comics(permitir_ninguna=True)
        config["comics"] = [str(ruta)] if ruta else []
        guardar_config(config)
    return [Path(carpeta) for carpeta in config["comics"]]


def pedir_clave_api(config, forzar=False):
    if config.get("clave_api") and not forzar:
        return config["clave_api"]
    print("\nPara consultar los personajes se necesita una clave gratuita de Comic Vine:")
    print("  1. Crear una cuenta gratuita en https://comicvine.gamespot.com (requiere una cuenta de GameSpot).")
    print("  2. Entrar a https://comicvine.gamespot.com/api y copiar la clave.")
    print("La clave queda solo en este computador (no se sube al vault).")
    clave_ = pedir("Pegar la clave (Esc = cancelar): ")
    config["clave_api"] = clave_
    guardar_config(config)
    return clave_
