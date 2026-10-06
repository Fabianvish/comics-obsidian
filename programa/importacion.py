"""Importar un orden de lectura (.cbl) de cualquier origen y reconocer sus cómics contra el catálogo."""

import xml.etree.ElementTree as ET
from collections import Counter

from .catalogo import descargar_listas_de_github, descargar_url
from .rutas import convertir_ruta_windows_a_wsl
from .errores import ErrorAmigable
from .texto import clave_de_numero, clave_orden_natural, clave_de_comic


def leer_origen(origen):
    """Archivo .cbl, carpeta con .cbl o enlace -> [(nombre_original, raiz_xml)]. El origen no se modifica."""
    if origen.startswith("http"):
        try:
            if "github.com/" in origen:
                listas_descargadas = [datos for _, datos in descargar_listas_de_github(origen)]
            else:
                listas_descargadas = [descargar_url(origen)]
        except Exception as error:
            raise ErrorAmigable(f"No se pudo descargar: {error}")
        if not listas_descargadas:
            raise ErrorAmigable("En ese enlace no hay archivos .cbl.")
        contenidos = [(origen, datos) for datos in listas_descargadas]
    else:
        ruta = convertir_ruta_windows_a_wsl(origen)
        if ruta.is_dir():
            archivos = sorted(ruta.glob("*.cbl"), key=lambda archivo: clave_orden_natural(archivo.name))
            if not archivos:
                raise ErrorAmigable(f"En esa carpeta no hay archivos .cbl:\n   {ruta}")
        elif ruta.is_file():
            archivos = [ruta]
        else:
            raise ErrorAmigable(f"No se encuentra el archivo o la carpeta:\n   {ruta}")
        contenidos = [(archivo.stem, archivo.read_bytes()) for archivo in archivos]
    listas_leidas = []
    for nombre_por_defecto, datos in contenidos:
        try:
            raiz = ET.fromstring(datos)
        except ET.ParseError:
            raise ErrorAmigable(f"No es un archivo .cbl válido: {nombre_por_defecto}")
        listas_leidas.append(((raiz.findtext("Name") or nombre_por_defecto).strip(), raiz))
    return listas_leidas


def reconocer_comics(ejemplares, ids_comic, catalogo):
    """Busca cada cómic del archivo en el catálogo: primero por identificador de Comic Vine, luego por nombre y año.
    Devuelve (reconocidos, no_reconocidos): reconocidos va de (comic, anio_comic) al título del catálogo;
    no_reconocidos es [((comic, anio_comic), cantidad_de_numeros)] en el orden en que aparecen."""
    titulos = (catalogo or {}).get("titulos", {})
    clave_por_id_numero, clave_por_id_comic = {}, {}
    for clave_titulo, titulo_catalogo in titulos.items():
        for id_cv in titulo_catalogo.get("id_cv", {}).values():
            clave_por_id_numero.setdefault(str(id_cv), clave_titulo)
        if titulo_catalogo.get("id_cv_comic"):
            clave_por_id_comic.setdefault(str(titulo_catalogo["id_cv_comic"]), clave_titulo)

    votos_por_comic, cantidad_por_comic = {}, Counter()
    for ejemplar, id_comic in zip(ejemplares, ids_comic):
        comic_del_archivo = (ejemplar["comic"], ejemplar["anio_comic"])
        cantidad_por_comic[comic_del_archivo] += 1
        votos = votos_por_comic.setdefault(comic_del_archivo, Counter())
        clave_titulo = clave_por_id_numero.get(str(ejemplar["id_cv"])) or clave_por_id_comic.get(id_comic)
        if clave_titulo:
            votos[clave_titulo] += 1

    reconocidos, no_reconocidos = {}, []
    for comic_del_archivo, votos in votos_por_comic.items():
        clave_titulo = votos.most_common(1)[0][0] if votos else None
        clave_titulo = clave_titulo or clave_de_comic(comic_del_archivo[0], comic_del_archivo[1])
        if clave_titulo in titulos:
            reconocidos[comic_del_archivo] = titulos[clave_titulo]
        else:
            no_reconocidos.append((comic_del_archivo, cantidad_por_comic[comic_del_archivo]))
    return reconocidos, no_reconocidos


def aplicar_reconocimiento(ejemplares, reconocidos, quitados=()):
    """Pone el nombre y el año del catálogo a los cómics reconocidos, completa años e identificadores que falten,
    quita los cómics descartados y los números repetidos (conservando el orden de lectura)."""
    resultado, ya_incluidos = [], set()
    for ejemplar in ejemplares:
        comic_del_archivo = (ejemplar["comic"], ejemplar["anio_comic"])
        if comic_del_archivo in quitados:
            continue
        ejemplar = dict(ejemplar)
        titulo_catalogo = reconocidos.get(comic_del_archivo)
        if titulo_catalogo:
            ejemplar["comic"], ejemplar["anio_comic"] = titulo_catalogo["comic"], titulo_catalogo["anio_comic"]
            numero = ejemplar["numero"]
            if not ejemplar["anio_publicacion"] and numero in titulo_catalogo.get("anios_publicacion", {}):
                ejemplar["anio_publicacion"] = str(titulo_catalogo["anios_publicacion"][numero])
            if not ejemplar["id_cv"]:
                ejemplar["id_cv"] = str(titulo_catalogo.get("id_cv", {}).get(numero, ""))
        clave_ejemplar = clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"])
        if clave_ejemplar not in ya_incluidos:
            ya_incluidos.add(clave_ejemplar)
            resultado.append(ejemplar)
    return resultado

