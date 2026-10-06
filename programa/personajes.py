"""Personajes en las notas: nombres, propiedad «personajes» y qué eventos/cómics consultar."""

import re
from pathlib import Path

from .comicvine import ids_de_comic_vine
from .constantes import CARPETA_NOTAS_COMICS, CARPETA_NOTAS_EVENTOS, CARPETA_NOTAS_PERSONAJES
from .listas import carpeta_de_nota, leer_cbl, archivos_de_eventos
from .md import fijar_propiedad_lista, leer_propiedad_lista
from .texto import limpiar_nombre_de_nota, nombre_de_nota_comic, normalizar_nombre_comic, titulo_con_anio


def nombre_de_personaje(enlace):
    """«[[Spider-Man|Peter]]» → «spiderman»: para comparar personajes aunque se escriban distinto."""
    return normalizar_nombre_comic(re.sub(r"^\[\[|\]\]$", "", enlace).split("|")[0])


def sumar_personajes(actuales, nuevos):
    """Agrega a la lista los personajes que no estén ya (comparando por nombre)."""
    vistos = {nombre_de_personaje(enlace) for enlace in actuales}
    resultado = list(actuales)
    for enlace in nuevos:
        if nombre_de_personaje(enlace) not in vistos:
            vistos.add(nombre_de_personaje(enlace))
            resultado.append(enlace)
    return resultado


def destinos_para_personajes(config, catalogo):
    """Eventos y cómics sobre los que se pueden pedir personajes:
    [(etiqueta para la lista, nombre, ruta de la nota, ids de Comic Vine)]."""
    base = Path(config["notas"])
    destinos = []
    for archivo in archivos_de_eventos():
        nombre, nombre_visible, ejemplares = leer_cbl(archivo)
        nota = base / (carpeta_de_nota(archivo) or CARPETA_NOTAS_EVENTOS) / f"{nombre}.md"
        destinos.append((f"[Evento] {nombre_visible}", nombre_visible, nota, ids_de_comic_vine(ejemplares, catalogo)))
    for seguido in sorted(config.get("seguidos", []), key=lambda elemento: (elemento["comic"], elemento["anio_comic"])):
        titulo = titulo_con_anio(seguido["comic"], seguido["anio_comic"])
        ejemplares = [
            {"comic": seguido["comic"], "anio_comic": seguido["anio_comic"], "numero": numero}
            for numero in seguido["numeros"]
        ]
        nota = base / CARPETA_NOTAS_COMICS / f"{nombre_de_nota_comic(seguido['comic'], seguido['anio_comic'])}.md"
        destinos.append((f"[Cómic]  {titulo}", titulo, nota, ids_de_comic_vine(ejemplares, catalogo)))
    return destinos


def nombres_de_notas_de_personajes(config):
    base = Path(config["notas"])
    carpeta = base / CARPETA_NOTAS_PERSONAJES
    nombres = {nota.stem for nota in carpeta.glob("*.md")} if carpeta.is_dir() else set()
    return {normalizar_nombre_comic(nombre): nombre for nombre in nombres}


def nombre_para_nota(nombre_cv, existentes):
    """Si ya tienes una nota de ese personaje (aunque se escriba distinto: Spider-Man / Spiderman) usa su nombre."""
    return existentes.get(normalizar_nombre_comic(nombre_cv)) or limpiar_nombre_de_nota(nombre_cv)


def agregar_personajes_a_nota(ruta, nombres):
    """Suma personajes a la propiedad «personajes» de una nota. Devuelve cuántos eran nuevos."""
    if not ruta.exists():
        return 0
    texto = ruta.read_text(encoding="utf-8")
    actuales = leer_propiedad_lista(texto, "personajes")
    todos = sumar_personajes(actuales, [f"[[{nombre}]]" for nombre in nombres])
    if len(todos) > len(actuales):
        ruta.write_text(fijar_propiedad_lista(texto, "personajes", todos), encoding="utf-8")
    return len(todos) - len(actuales)
