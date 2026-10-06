"""Eventos guardados como listas .cbl (los del catálogo y los propios)."""

import re
import xml.etree.ElementTree as ET

from .rutas import RUTAS
from .texto import clave_de_numero, nombre_visible_evento, nombre_de_archivo_evento, clave_de_comic


def archivos_de_eventos():
    RUTAS.carpeta_eventos.mkdir(exist_ok=True)
    return sorted(RUTAS.carpeta_eventos.glob("*.cbl"))


def nombre_sin_orden(archivo):
    """«003 - Civil War.cbl» → «Civil War»."""
    return re.sub(r"^\d+\s*-\s*", "", archivo.stem)


def insertar_eventos(nuevos, posicion):
    """Agrega eventos nuevos en una posición del orden de lectura y renumera todos.
    nuevos: [(nombre de archivo, función que escribe el .cbl en la ruta que recibe)].
    Devuelve las rutas finales de los nuevos, en el mismo orden."""
    actuales = archivos_de_eventos()
    temporales = []
    for indice, (nombre, escribir) in enumerate(nuevos):
        archivo = RUTAS.carpeta_eventos / f"__nuevo{indice:04d} - {nombre}.cbl"
        escribir(archivo)
        temporales.append(archivo)
    actuales[posicion - 1 : posicion - 1] = temporales
    renumerar_archivos_de_eventos(actuales)
    finales = {nombre_sin_orden(archivo): archivo for archivo in archivos_de_eventos()}
    return [finales[nombre] for nombre, _ in nuevos]


def renumerar_archivos_de_eventos(archivos):
    temporales = []
    for i, archivo in enumerate(archivos):
        archivo_temporal = archivo.with_name(f"__tmp{i}.cbl")
        archivo.rename(archivo_temporal)
        temporales.append((archivo_temporal, re.sub(r"^(\d+|__nuevo\d*)\s*-\s*", "", archivo.name)))
    for i, (archivo_temporal, nombre) in enumerate(temporales, 1):
        archivo_temporal.rename(RUTAS.carpeta_eventos / f"{i:03d} - {nombre}")


def leer_ejemplares_de_cbl(raiz):
    """Ejemplares de una lista .cbl ya leída, y aparte el identificador de cómic de Comic Vine de cada uno."""
    ejemplares, ids_comic = [], []
    for elemento_libro in raiz.iter("Book"):
        if not (elemento_libro.get("Series") and elemento_libro.get("Number")):
            continue
        base_de_datos_cv = next(
            (
                base_de_datos
                for base_de_datos in elemento_libro.findall("Database")
                if base_de_datos.get("Name") == "cv"
            ),
            None,
        )
        ejemplares.append(
            {
                "comic": elemento_libro.get("Series") or "",
                "anio_comic": elemento_libro.get("Volume") or "",
                "anio_publicacion": elemento_libro.get("Year") or "",
                "numero": elemento_libro.get("Number") or "",
                "id_cv": (base_de_datos_cv.get("Issue") or "") if base_de_datos_cv is not None else "",
            }
        )
        ids_comic.append((base_de_datos_cv.get("Series") or "") if base_de_datos_cv is not None else "")
    return ejemplares, ids_comic


def leer_cbl(ruta):
    raiz = ET.parse(ruta).getroot()
    nombre_original = raiz.findtext("Name") or ruta.stem
    ejemplares = leer_ejemplares_de_cbl(raiz)[0]
    nombre_visible = (
        nombre_original.strip() if raiz.find("Propio") is not None else nombre_visible_evento(nombre_original)
    )
    return nombre_de_archivo_evento(nombre_original), nombre_visible, ejemplares


def es_evento_propio(ruta):
    """True si es un evento propio (creado, copiado o importado; no viene del catálogo)."""
    try:
        return ET.parse(ruta).getroot().find("Propio") is not None
    except Exception:
        return False


def anios_indicados_a_mano(ruta):
    """Años de inicio y fin que escribiste a mano para un evento propio ((None, None) si no hay)."""
    try:
        raiz = ET.parse(ruta).getroot()
        inicio, fin = raiz.findtext("AnioInicio"), raiz.findtext("AnioFin")
        return (int(inicio) if inicio and inicio.isdigit() else None, int(fin) if fin and fin.isdigit() else None)
    except Exception:
        return None, None


def anios_de_evento(ruta, ejemplares, catalogo=None):
    """(inicio, fin) del evento: lo que pusiste a mano o, si no, el año de publicación de sus números."""
    inicio, fin = anios_indicados_a_mano(ruta)
    if inicio or fin:
        return inicio or fin, fin or inicio
    anios = [
        int(ejemplar["anio_publicacion"])
        for ejemplar in ejemplares
        if (ejemplar.get("anio_publicacion") or "").isdigit()
    ]
    if not anios and catalogo:
        for ejemplar in ejemplares:
            titulo_catalogo = catalogo["titulos"].get(
                clave_de_comic(ejemplar["comic"], ejemplar["anio_comic"])
            )
            if titulo_catalogo and ejemplar["numero"] in titulo_catalogo["anios_publicacion"]:
                anios.append(int(titulo_catalogo["anios_publicacion"][ejemplar["numero"]]))
    return (min(anios), max(anios)) if anios else (None, None)


def nombre_original_del_evento(ruta):
    return (ET.parse(ruta).getroot().findtext("Name") or ruta.stem).strip()


def carpeta_de_nota(ruta):
    """Carpeta de Obsidian elegida para la nota de un evento propio ("" = la de siempre, «Eventos»)."""
    try:
        return (ET.parse(ruta).getroot().findtext("Carpeta") or "").strip()
    except Exception:
        return ""


def escribir_cbl(ruta, nombre, numeros_evento, anios=(None, None), carpeta=""):
    """Guarda un evento propio como archivo .cbl (el mismo formato que usa el catálogo)."""
    raiz = ET.Element("ReadingList")
    ET.SubElement(raiz, "Name").text = nombre
    ET.SubElement(raiz, "Propio").text = "1"
    if carpeta:
        ET.SubElement(raiz, "Carpeta").text = carpeta
    if anios[0]:
        ET.SubElement(raiz, "AnioInicio").text = str(anios[0])
    if anios[1]:
        ET.SubElement(raiz, "AnioFin").text = str(anios[1])
    elemento_libros = ET.SubElement(raiz, "Books")
    for ejemplar in numeros_evento:
        atributos = {"Series": ejemplar["comic"], "Number": str(ejemplar["numero"]), "Volume": ejemplar["anio_comic"]}
        if ejemplar.get("anio_publicacion"):
            atributos["Year"] = ejemplar["anio_publicacion"]
        elemento_libro = ET.SubElement(elemento_libros, "Book", atributos)
        if ejemplar.get("id_cv"):
            ET.SubElement(elemento_libro, "Database", {"Name": "cv", "Issue": str(ejemplar["id_cv"])})
    ET.SubElement(raiz, "Matchers")
    if hasattr(ET, "indent"):
        ET.indent(raiz)
    ET.ElementTree(raiz).write(ruta, encoding="utf-8", xml_declaration=True)


def agregar_numeros_evento(numeros_evento, comic, anio_comic, numeros, extra=None, posicion=None):
    """Agrega números a un evento sin repetir los que ya están. Devuelve (agregados, repetidos)."""
    extra = extra or {}
    ya_existentes = {
        clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"]) for ejemplar in numeros_evento
    }
    agregados = []
    for numero in numeros:
        clave_ejemplar = clave_de_numero(comic, anio_comic, numero)
        if clave_ejemplar not in ya_existentes:
            ya_existentes.add(clave_ejemplar)
            agregados.append(
                {
                    "comic": comic,
                    "anio_comic": anio_comic,
                    "anio_publicacion": str(extra.get("anios_publicacion", {}).get(str(numero), "")),
                    "numero": str(numero),
                    "id_cv": extra.get("id_cv", {}).get(str(numero), ""),
                }
            )
    i = len(numeros_evento) if posicion is None else max(0, min(posicion - 1, len(numeros_evento)))
    numeros_evento[i:i] = agregados
    return len(agregados), len(numeros) - len(agregados)


def nombres_de_eventos():
    return {nombre_sin_orden(archivo) for archivo in archivos_de_eventos()}


def reunir_ejemplares(config):
    """Todos los números de tus eventos y cómics, por clave (igual que lo hace generar)."""
    ejemplares = {}
    for archivo in archivos_de_eventos():
        for ejemplar in leer_cbl(archivo)[2]:
            ejemplares.setdefault(
                clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"]), ejemplar
            )
    for seguido in config.get("seguidos", []):
        for numero in seguido["numeros"]:
            ejemplares.setdefault(
                clave_de_numero(seguido["comic"], seguido["anio_comic"], numero),
                {
                    "comic": seguido["comic"],
                    "anio_comic": seguido["anio_comic"],
                    "anio_publicacion": "",
                    "numero": numero,
                },
            )
    return ejemplares


def claves_de_numeros_cbl(raiz):
    return [
        clave_de_numero(
            elemento_libro.get("Series") or "", elemento_libro.get("Volume") or "", elemento_libro.get("Number") or ""
        )
        for elemento_libro in raiz.iter("Book")
        if elemento_libro.get("Series") and elemento_libro.get("Number")
    ]
