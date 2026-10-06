"""Tus archivos de cómics: emparejarlos con los números y sacar portadas (solo lectura)."""

import io
import re
import shutil
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path

from .constantes import EXTENSIONES_COMIC, EXTENSIONES_IMAGEN
from .texto import (
    contiene_secuencia,
    contiene_en_orden,
    normalizar_numero,
    normalizar_nombre_comic,
    clave_orden_natural,
    titulo_con_anio,
    separar_palabras_y_numeros,
)


def interpretar_nombre_de_archivo(archivo):
    anio = re.search(r"\((\d{4})\)", archivo.stem)
    limpio = re.sub(r"\(.*?\)|\[.*?\]|\{.*?\}", " ", archivo.stem).strip()
    limpio = re.sub(r"\s+of\s+\d+\s*$", "", limpio)
    coincidencia = re.match(r"^(.*?)[\s_#-]*#?(\d+(?:\.\d+)?)\s*$", limpio)
    if not coincidencia or not coincidencia.group(1).strip():
        return None
    return (
        normalizar_nombre_comic(coincidencia.group(1)),
        normalizar_numero(coincidencia.group(2)),
        anio.group(1) if anio else None,
    )


def limpiar_nombre_de_descarga(nombre_sin_extension):
    anio = re.search(r"\((\d{4})\)", nombre_sin_extension)
    texto = re.sub(r"\.[^\s]*\.(com|net|org|es|cl|info|blogspot)$", "", nombre_sin_extension, flags=re.I)
    texto = re.sub(r"\(.*?\)|\[.*?\]|\{.*?\}", " ", texto)
    texto = re.sub(r"^\s*\d+\s*-\s*", "", texto)
    texto = re.sub(r"(\d+)\s*de\s*\d+", r"\1", texto, flags=re.I)
    texto = re.sub(r"_\d+", " ", texto)
    return texto, anio.group(1) if anio else None


def archivos_de_comics(carpetas):
    """Los archivos de cómics de todas las carpetas que existan, sin repetir (una carpeta puede estar dentro de otra)."""
    vistos, archivos = set(), []
    for carpeta in carpetas:
        if not carpeta.is_dir():
            continue
        for archivo in sorted(carpeta.rglob("*")):
            if archivo.suffix.lower() in EXTENSIONES_COMIC and archivo.resolve() not in vistos:
                vistos.add(archivo.resolve())
                archivos.append(archivo)
    return archivos


def emparejar_archivos(carpetas_origen, ejemplares, manuales=None):
    """carpetas_origen: lista de carpetas donde buscar.
    ejemplares: {clave: ejemplar}. Devuelve ({clave: archivo}, [sin emparejar], [(archivo, etiqueta)]).
    manuales: {nombre de archivo: clave} con lo indicado a mano."""
    manuales = manuales or {}
    por_nombre_y_numero, por_numero, numeros_por_comic = defaultdict(list), defaultdict(list), defaultdict(set)
    for clave_ejemplar, ejemplar in ejemplares.items():
        numero = normalizar_numero(ejemplar["numero"])
        por_nombre_y_numero[(normalizar_nombre_comic(ejemplar["comic"]), numero)].append(clave_ejemplar)
        palabras = separar_palabras_y_numeros(ejemplar["comic"])[0]
        por_numero[numero].append((clave_ejemplar, palabras))
        numeros_por_comic[tuple(palabras)].add(numero)

    def filtrar_por_anio(candidatos, anio):
        if len(candidatos) > 1 and anio:
            return [
                clave_candidata
                for clave_candidata in candidatos
                if anio
                in (ejemplares[clave_candidata].get("anio_publicacion"), ejemplares[clave_candidata]["anio_comic"])
            ] or candidatos
        return candidatos

    archivos, sin_emparejar, por_aproximacion = {}, [], []
    for archivo in archivos_de_comics(carpetas_origen):
        if manuales.get(archivo.name) in ejemplares and manuales[archivo.name] not in archivos:
            archivos[manuales[archivo.name]] = archivo
            continue
        datos_nombre = interpretar_nombre_de_archivo(archivo)
        candidatos = (
            filtrar_por_anio(por_nombre_y_numero.get(datos_nombre[:2], []), datos_nombre[2]) if datos_nombre else []
        )
        if len(candidatos) == 1 and candidatos[0] not in archivos:
            archivos[candidatos[0]] = archivo
            continue
        limpio, anio = limpiar_nombre_de_descarga(archivo.stem)
        palabras, numeros = separar_palabras_y_numeros(limpio)
        numeros = [normalizar_numero(numero) for numero in numeros] or ["1"]
        mejores, mejor_puntaje = [], None
        for numero in numeros:
            for clave_ejemplar, palabras_comic in por_numero.get(numero, []):
                if not palabras_comic or not contiene_en_orden(palabras_comic, palabras):
                    continue
                if not re.search(r"\d", limpio) and numeros_por_comic[tuple(palabras_comic)] != {"1"}:
                    continue
                puntaje = (contiene_secuencia(palabras_comic, palabras), len(palabras_comic))
                if mejor_puntaje is None or puntaje > mejor_puntaje:
                    mejores, mejor_puntaje = [clave_ejemplar], puntaje
                elif puntaje == mejor_puntaje and clave_ejemplar not in mejores:
                    mejores.append(clave_ejemplar)
        mejores = filtrar_por_anio(mejores, anio)
        if len(mejores) == 1 and mejores[0] not in archivos:
            archivos[mejores[0]] = archivo
            ejemplar = ejemplares[mejores[0]]
            por_aproximacion.append(
                (archivo, f"{titulo_con_anio(ejemplar['comic'], ejemplar['anio_comic'])} #{ejemplar['numero']}")
            )
        else:
            sin_emparejar.append(archivo)
    return archivos, sin_emparejar, por_aproximacion


def _primera_imagen_de(nombres):
    imagenes = [
        nombre
        for nombre in nombres
        if Path(nombre).suffix.lower() in EXTENSIONES_IMAGEN
        and "__MACOSX" not in nombre
        and not Path(nombre).name.startswith(".")
    ]
    return sorted(imagenes, key=clave_orden_natural)[0] if imagenes else None


def _buscar_programa(*nombres):
    return next((nombre for nombre in nombres if shutil.which(nombre)), None)


def leer_portada(archivo):
    """Devuelve (bytes, extensión) de la primera página, sin modificar el archivo."""
    try:
        if zipfile.is_zipfile(archivo):
            with zipfile.ZipFile(archivo) as archivo_zip:
                nombre_imagen = _primera_imagen_de(archivo_zip.namelist())
                return (
                    (archivo_zip.read(nombre_imagen), Path(nombre_imagen).suffix.lower())
                    if nombre_imagen
                    else (None, None)
                )
        if archivo.suffix.lower() == ".pdf":
            return None, None
        unrar = _buscar_programa("unrar")
        if unrar:
            lista = subprocess.run([unrar, "lb", str(archivo)], capture_output=True, text=True, timeout=60).stdout
            nombre_imagen = _primera_imagen_de(lista.splitlines())
            if nombre_imagen:
                datos = subprocess.run(
                    [unrar, "p", "-inul", str(archivo), nombre_imagen], capture_output=True, timeout=60
                ).stdout
                return (datos, Path(nombre_imagen).suffix.lower()) if datos else (None, None)
        siete = _buscar_programa("7z", "7zz", "7za")
        if siete:
            lista = subprocess.run(
                [siete, "l", "-ba", "-slt", str(archivo)], capture_output=True, text=True, timeout=60
            ).stdout
            nombre_imagen = _primera_imagen_de(re.findall(r"^Path = (.+)$", lista, re.M))
            if nombre_imagen:
                datos = subprocess.run(
                    [siete, "e", "-so", str(archivo), nombre_imagen], capture_output=True, timeout=60
                ).stdout
                return (datos, Path(nombre_imagen).suffix.lower()) if datos else (None, None)
    except Exception:
        pass
    return None, None


def guardar_portada(archivo, destino_sin_ext):
    """Guarda la portada achicada (si está Pillow) y devuelve el nombre del archivo creado."""
    for extension in (".jpg", ".png", ".webp", ".gif", ".jpeg"):
        existente = destino_sin_ext.with_suffix(extension)
        if existente.exists():
            return existente.name
    datos, extension = leer_portada(archivo)
    if not datos:
        return None
    destino_sin_ext.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        imagen = Image.open(io.BytesIO(datos)).convert("RGB")
        imagen.thumbnail((600, 900))
        destino = destino_sin_ext.with_suffix(".jpg")
        imagen.save(destino, "JPEG", quality=85)
    except ImportError:
        destino = destino_sin_ext.with_suffix(extension)
        destino.write_bytes(datos)
    except Exception:
        return None
    return destino.name
