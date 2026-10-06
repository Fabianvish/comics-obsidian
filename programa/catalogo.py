"""Catálogo local de listas de lectura (descarga desde GitHub y búsqueda)."""

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

from .rutas import guardar_json, leer_json
from .constantes import ARCHIVO_INDICE_CATALOGO, ARCHIVO_CATALOGO_ZIP, VERSION_INDICE, URL_REPOSITORIO_ZIP
from .texto import (
    clave_de_numero,
    nombre_visible_evento,
    nombre_de_archivo_evento,
    clave_de_comic,
    clave_orden_natural,
)


def actualizar_catalogo(config=None):
    print("⬇️  Descargando el catálogo completo de listas (unos 12 MB)...")
    try:
        peticion = urllib.request.Request(URL_REPOSITORIO_ZIP, headers={"User-Agent": "comics-obsidian"})
        datos = urllib.request.urlopen(peticion, timeout=120).read()
    except Exception as error:
        print(f"❌ No se pudo descargar el catálogo: {error}")
        return None
    ARCHIVO_CATALOGO_ZIP.write_bytes(datos)
    return construir_indice()


def construir_indice():
    print("🗂️  Ordenando el catálogo...")
    archivo_zip = zipfile.ZipFile(ARCHIVO_CATALOGO_ZIP)
    listas, eventos_por_num, titulos = [], defaultdict(list), {}
    rutas = sorted(
        (
            nombre_archivo
            for nombre_archivo in archivo_zip.namelist()
            if nombre_archivo.endswith(".cbl") and "/Marvel/" in nombre_archivo
        ),
        key=clave_orden_natural,
    )
    for ruta in rutas:
        try:
            raiz = ET.fromstring(archivo_zip.read(ruta))
        except Exception:
            continue
        elementos_libro = list(raiz.iter("Book"))
        ruta_relativa = ruta.split("/Marvel/", 1)[1]
        categoria = "/".join(ruta_relativa.split("/")[:-1])
        nombre = raiz.findtext("Name") or Path(ruta).stem
        i = len(listas)
        listas.append(
            {
                "ruta": ruta,
                "nombre": nombre_de_archivo_evento(nombre),
                "nombre_visible": nombre_visible_evento(nombre),
                "categoria": categoria,
                "cantidad": len(elementos_libro),
            }
        )
        es_evento = ruta_relativa.startswith("Events/")
        for posicion, elemento_libro in enumerate(elementos_libro, 1):
            comic, anio_comic, numero = (
                elemento_libro.get("Series") or "",
                elemento_libro.get("Volume") or "",
                elemento_libro.get("Number") or "",
            )
            if not comic or not numero:
                continue
            titulo_catalogo = titulos.setdefault(
                clave_de_comic(comic, anio_comic),
                {
                    "comic": comic,
                    "anio_comic": anio_comic,
                    "numeros": set(),
                    "anios_publicacion": {},
                    "id_cv": {},
                    "id_cv_comic": "",
                },
            )
            titulo_catalogo["numeros"].add(numero)
            if (elemento_libro.get("Year") or "").isdigit():
                titulo_catalogo["anios_publicacion"].setdefault(numero, int(elemento_libro.get("Year")))
            for base_de_datos in elemento_libro.findall("Database"):
                if base_de_datos.get("Name") == "cv" and base_de_datos.get("Issue"):
                    titulo_catalogo["id_cv"].setdefault(numero, base_de_datos.get("Issue"))
                    titulo_catalogo["id_cv_comic"] = titulo_catalogo["id_cv_comic"] or (
                        base_de_datos.get("Series") or ""
                    )
            if es_evento:
                eventos_por_num[clave_de_numero(comic, anio_comic, numero)].append([i, posicion])
    for titulo_catalogo in titulos.values():
        titulo_catalogo["numeros"] = sorted(titulo_catalogo["numeros"], key=clave_orden_natural)
    indice = {"version": VERSION_INDICE, "listas": listas, "eventos": eventos_por_num, "titulos": titulos}
    guardar_json(ARCHIVO_INDICE_CATALOGO, indice)
    print(
        f"✅ Catálogo listo: {len(listas)} listas, "
        f"{sum(1 for lista_catalogo in listas if lista_catalogo['categoria'].startswith('Events'))} eventos, {len(titulos)} cómics."
    )
    return indice


def cargar_catalogo(descargar_si_falta=True):
    if ARCHIVO_INDICE_CATALOGO.exists():
        indice = leer_json(ARCHIVO_INDICE_CATALOGO, None)
        if indice and indice.get("version") == VERSION_INDICE:
            return indice
        if ARCHIVO_CATALOGO_ZIP.exists():  # índice de una versión anterior: se vuelve a armar (unos segundos)
            return construir_indice()
        return indice
    if ARCHIVO_CATALOGO_ZIP.exists():
        return construir_indice()
    return actualizar_catalogo() if descargar_si_falta else None


def leer_lista_del_catalogo(ruta):
    return zipfile.ZipFile(ARCHIVO_CATALOGO_ZIP).read(ruta)


def descargar_url(url):
    peticion = urllib.request.Request(url, headers={"User-Agent": "comics-obsidian"})
    return urllib.request.urlopen(peticion, timeout=30).read()


def descargar_listas_de_github(enlace):
    coincidencia = re.match(r"https?://github\.com/([^/]+)/([^/]+)/(tree|blob)/([^/]+)/(.+)", enlace)
    if not coincidencia:
        raise ValueError("No parece un enlace de GitHub a un archivo o carpeta")
    dueño, repo, tipo, rama, ruta = coincidencia.groups()
    ruta = urllib.parse.unquote(ruta).rstrip("/")
    if tipo == "blob":
        rutas = [ruta]
    else:
        arbol = json.loads(descargar_url(f"https://api.github.com/repos/{dueño}/{repo}/git/trees/{rama}?recursive=1"))
        rutas = sorted(
            (
                elemento["path"]
                for elemento in arbol["tree"]
                if elemento["type"] == "blob"
                and elemento["path"].startswith(ruta + "/")
                and elemento["path"].endswith(".cbl")
            ),
            key=clave_orden_natural,
        )
    listas_descargadas = []
    for ruta_lista in rutas:
        datos = descargar_url(
            f"https://raw.githubusercontent.com/{dueño}/{repo}/{rama}/" + urllib.parse.quote(ruta_lista)
        )
        listas_descargadas.append((nombre_de_archivo_evento(ET.fromstring(datos).findtext("Name")), datos))
    return listas_descargadas
