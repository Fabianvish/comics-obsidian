"""Utilidades de texto: nombres, números de cómics, claves y búsqueda."""

import re
import unicodedata


def limpiar_nombre_de_nota(nombre):
    return re.sub(r"\s+", " ", re.sub(r'[#\[\]|^:\\/*?"<>]', "", nombre)).strip()


def nombre_de_archivo_evento(nombre_original):
    """Nombre de archivo/nota de un evento: '[Marvel] X-Men- Second Coming (WEB-CBRO)' -> sin '[Marvel]'."""
    return limpiar_nombre_de_nota(re.sub(r"^\[Marvel\]\s*", "", nombre_original or "lista"))


def nombre_visible_evento(nombre_original):
    """'[Marvel] X-Men- Second Coming (WEB-CBRO)' -> 'X-Men: Second Coming'"""
    texto = re.sub(r"^\[Marvel\]\s*", "", nombre_original or "")
    texto = re.sub(r"^[\[(]\d{4}(?:-\d{2,4})?[\])]\s*", "", texto)
    texto = re.sub(r"\s*\((?:Marvel Comics|WEB-[\w ]+|MG|CBH|CBT|LoCG|Official|Community)\)", "", texto)
    texto = re.sub(r"(\w)- ", r"\1: ", texto)
    return texto.strip() or nombre_original


def clave_orden_natural(texto):
    return [int(trozo) if trozo.isdigit() else trozo.lower() for trozo in re.split(r"(\d+)", str(texto))]


def normalizar_nombre_comic(nombre):
    nombre = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    nombre = nombre.lower().replace("&", "and")
    nombre = re.sub(r"\b(vol\.?|v)\s*\d+\b", "", nombre)
    nombre = re.sub(r"^the\s+", "", nombre.strip())
    return re.sub(r"[^a-z0-9]", "", nombre)


def normalizar_numero(numero):
    parte_entera, _, parte_decimal = str(numero).strip().lstrip("#").partition(".")
    parte_entera = str(int(parte_entera)) if parte_entera.isdigit() else parte_entera.lower()
    return f"{parte_entera}.{parte_decimal}" if parte_decimal else parte_entera


def clave_de_comic(comic, anio_comic):
    """Identidad de un cómic, igual sin importar cómo se escriba su nombre."""
    return f"{normalizar_nombre_comic(comic)}|{anio_comic}"


def clave_de_numero(comic, anio_comic, numero):
    """Identidad de un número, igual sin importar de dónde venga."""
    return f"{clave_de_comic(comic, anio_comic)}|{normalizar_numero(numero)}"


def separar_palabras_y_numeros(texto):
    texto_ascii = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    texto_ascii = texto_ascii.replace("&", " and ")
    texto_ascii = re.sub(r"\bv(ol)?\.?\s*\d+\b", " ", texto_ascii)
    return [palabra for palabra in re.findall(r"[a-z]+", texto_ascii) if palabra != "the"], re.findall(
        r"\d+(?:\.\d+)?", texto_ascii
    )


def nombre_de_nota_comic(comic, anio_comic):
    """Nombre de la nota de un cómic."""
    return limpiar_nombre_de_nota(titulo_con_anio(comic, anio_comic))


def titulo_con_anio(comic, anio_comic):
    return f"{comic} ({anio_comic})" if anio_comic else comic


def describir_numeros(numeros, max_partes=4):
    """['1'..'20','5.1','300'..'317','1000'] -> '40 números: #1–#20, #300–#317, #1000 y 1 especial (#5.1)'"""
    enteros = sorted({int(numero) for numero in numeros if normalizar_numero(numero).isdigit()})
    especiales = [numero for numero in numeros if not normalizar_numero(numero).isdigit()]
    tramos, inicio = [], None
    for i, numero in enumerate(enteros):
        if inicio is None:
            inicio = numero
        if i + 1 == len(enteros) or enteros[i + 1] != numero + 1:
            tramos.append(f"#{inicio}" if inicio == numero else f"#{inicio}–#{numero}")
            inicio = None
    texto = ", ".join(tramos[:max_partes]) + (" …" if len(tramos) > max_partes else "")
    if especiales:
        texto += (
            (" y " if texto else "")
            + f"{len(especiales)} especial{'es' if len(especiales) > 1 else ''} ({', '.join('#' + especial for especial in especiales[:3])})"
        )
    total = len(numeros)
    return f"{total} número{'s' if total != 1 else ''}: {texto}"


def interpretar_numeros_elegidos(texto, numeros_catalogo):
    """'1-20,300-317' -> números. Incluye especiales del catálogo dentro de cada rango."""
    elegidos = []
    for parte in texto.replace(" ", "").split(","):
        coincidencia = re.fullmatch(r"#?(\d+)(?:-#?(\d+))?", parte)
        if not coincidencia:
            return None
        desde = int(coincidencia.group(1))
        hasta = int(coincidencia.group(2) or desde)
        elegidos += [str(numero) for numero in range(min(desde, hasta), max(desde, hasta) + 1)]
        elegidos += [
            numero
            for numero in numeros_catalogo
            if not normalizar_numero(numero).isdigit()
            and re.match(r"^\d+", numero)
            and min(desde, hasta) <= int(re.match(r"^\d+", numero).group()) <= max(desde, hasta)
        ]
    return sorted(set(elegidos), key=clave_orden_natural)


def interpretar_posiciones(texto, maximo):
    """'1,3-5' -> [1,3,4,5]"""
    posiciones = []
    for parte in texto.replace(" ", "").split(","):
        if re.fullmatch(r"\d+-\d+", parte):
            desde, hasta = map(int, parte.split("-"))
            posiciones += list(range(desde, hasta + 1))
        elif parte.isdigit():
            posiciones.append(int(parte))
    return [posicion for posicion in dict.fromkeys(posiciones) if 1 <= posicion <= maximo]


def buscar_por_palabras(texto, candidatos):
    """candidatos: [(texto_buscable, objeto)] -> objetos que contienen todas las palabras."""
    palabras = separar_palabras_y_numeros(texto)[0] + separar_palabras_y_numeros(texto)[1]
    encontrados = []
    for buscable, objeto in candidatos:
        palabras_candidato, numeros_candidato = separar_palabras_y_numeros(buscable)
        todas = set(palabras_candidato) | set(numeros_candidato)
        if palabras and all(
            any(palabra == elemento or elemento.startswith(palabra) for elemento in todas) for palabra in palabras
        ):
            encontrados.append(objeto)
    return encontrados


def contiene_secuencia(corta, larga):
    largo = len(corta)
    return any(larga[i : i + largo] == corta for i in range(len(larga) - largo + 1))


def contiene_en_orden(corta, larga):
    iterador = iter(larga)
    return all(palabra in iterador for palabra in corta)


def agrupar_en_rangos(numeros):
    """['22','23','24','30'] -> '#22–#24, #30'. Si no están en orden, los deja como están."""
    if numeros != sorted(set(numeros), key=clave_orden_natural):
        return ", ".join("#" + numero for numero in numeros)
    enteros = [int(numero) for numero in numeros if numero.isdigit()]
    otros = [numero for numero in numeros if not numero.isdigit()]
    partes, inicio, anterior = [], None, None
    for numero in enteros:
        if inicio is None:
            inicio = anterior = numero
        elif numero == anterior + 1:
            anterior = numero
        else:
            partes.append(f"#{inicio}" if inicio == anterior else f"#{inicio}–#{anterior}")
            inicio = anterior = numero
    if inicio is not None:
        partes.append(f"#{inicio}" if inicio == anterior else f"#{inicio}–#{anterior}")
    return ", ".join(partes + ["#" + numero for numero in otros])
