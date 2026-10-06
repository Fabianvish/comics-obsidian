"""Utilidades de notas Markdown: propiedades (frontmatter), listas, checkboxes."""

import re

from .texto import clave_de_numero


def propiedades_yaml(texto):
    coincidencia = re.match(r"^---\n(.*?)\n---", texto, re.S)
    return coincidencia.group(1) if coincidencia else ""


def leer_propiedad(texto, nombre_propiedad):
    coincidencia = re.search(rf"^{nombre_propiedad}:[ \t]*(.*)$", propiedades_yaml(texto), re.M)
    return coincidencia.group(1).strip().strip('"') if coincidencia else ""


def bloque_propiedad(texto, nombre_propiedad):
    """Las líneas YAML de una propiedad tal como están en la nota (la clave y sus líneas sangradas), o "" si no está.
    Sirve para copiar una propiedad de varias líneas sin interpretarla."""
    lineas = propiedades_yaml(texto).split("\n")
    for i, linea in enumerate(lineas):
        if re.match(rf"^{nombre_propiedad}:", linea):
            fin = i + 1
            while fin < len(lineas) and not re.match(r"^\S", lineas[fin]):
                fin += 1
            return "\n".join(lineas[i:fin]).rstrip("\n")
    return ""


def propiedad_texto_largo(nombre_propiedad, texto):
    """Una propiedad YAML con un texto de varias líneas (bloque literal con sangría fija de 2 espacios)."""
    if not texto:
        return f'{nombre_propiedad}: ""'
    return f"{nombre_propiedad}: |2-\n" + "\n".join(f"  {linea}" if linea else "" for linea in texto.split("\n"))


def agregar_propiedad(texto, lineas_yaml):
    """Agrega una propiedad (ya escrita en YAML) al final de las propiedades de una nota."""
    coincidencia = re.match(r"^---\n(.*?)\n---", texto, re.S)
    if not coincidencia:
        return f"---\n{lineas_yaml}\n---\n" + texto
    return "---\n" + coincidencia.group(1) + "\n" + lineas_yaml + "\n---" + texto[coincidencia.end() :]


def leer_propiedad_lista(texto, nombre_propiedad):
    propiedades = propiedades_yaml(texto)
    coincidencia = re.search(rf"^{nombre_propiedad}:[ \t]*(.*)$", propiedades, re.M)
    if not coincidencia:
        return []
    valor = coincidencia.group(1).strip()
    items = []
    if valor.startswith("["):
        interior = valor.strip("[]")
        items = re.findall(r'"([^"]*)"', interior) or [elemento.strip().strip("'") for elemento in interior.split(",")]
    elif valor.startswith("-"):
        items = [valor[1:].strip()]
    elif valor:
        items = [valor]
    for linea in propiedades[coincidencia.end() :].split("\n")[1:]:
        coincidencia_item = re.match(r"^[ \t]*-[ \t]*(.*)$", linea)
        if not coincidencia_item:
            break
        items.append(coincidencia_item.group(1).strip())
    items = [i.strip().strip('"').strip("'") for i in items if i.strip()]
    return [i for i in items if not re.match(r"^[\w-]+:\s", i) and i != "[]"]


def formatear_lista_yaml(items):
    return "[" + ", ".join('"' + i.replace('"', "") + '"' for i in items) + "]"


def id_bloque(numero):
    """Identificador de bloque de un número: '5.1' -> 'n5-2e-1'"""
    return "n" + re.sub(r"[^A-Za-z0-9]", lambda caracter: f"-{ord(caracter.group()):x}-", str(numero))


def leer_leidos_de_comic(texto, comic, anio_comic, numeros):
    numero_por_id_bloque = {id_bloque(numero): numero for numero in numeros}
    leidos = {}
    for linea in texto.splitlines():
        coincidencia = re.match(r"^\s*(?:>\s*)*- \[([ xX])\](.*)$", linea)  # también dentro del callout plegado
        if not coincidencia:
            continue
        coincidencia_id = re.search(r"\^(n[\w-]*)\s*$", coincidencia.group(2))
        if coincidencia_id and coincidencia_id.group(1) in numero_por_id_bloque:
            numero = numero_por_id_bloque[coincidencia_id.group(1)]
            leidos[clave_de_numero(comic, anio_comic, numero)] = coincidencia.group(1) != " "
    return leidos


def cuerpo_de_nota(texto):
    return "\n" + texto.split("---", 2)[2].lstrip("\n") if texto.count("---") >= 2 else ""


def linea_propiedad_banner(portada, previo):
    """Propiedad 'banner' para el plugin Pixel Banner. Si no hay portada nueva, conserva la que había."""
    enlace_banner = f"[[{portada}]]" if portada else leer_propiedad(previo, "banner")
    return f'banner: "{enlace_banner}"\n' if enlace_banner else ""


def linea_propiedad_imagen(previo):
    """Propiedad «imagen» de las notas de evento (la que usa Extended Graph). Siempre está presente y nunca se pisa."""
    return f'imagen: "{leer_propiedad(previo, "imagen")}"\n'


def fijar_propiedad_lista(texto, nombre_propiedad, items):
    """Reescribe una propiedad de lista en las propiedades de una nota, conserva todo lo demás."""
    coincidencia = re.match(r"^---\n(.*?)\n---", texto, re.S)
    if not coincidencia:
        return texto
    lineas, salida, i, puesta = coincidencia.group(1).split("\n"), [], 0, False
    while i < len(lineas):
        if re.match(rf"^{nombre_propiedad}:", lineas[i]):
            i += 1
            while i < len(lineas) and re.match(r"^\s*-", lineas[i]):
                i += 1
            salida.append(f"{nombre_propiedad}: {formatear_lista_yaml(items)}")
            puesta = True
            continue
        salida.append(lineas[i])
        i += 1
    if not puesta:
        salida.append(f"{nombre_propiedad}: {formatear_lista_yaml(items)}")
    return "---\n" + "\n".join(salida) + "\n---" + texto[coincidencia.end() :]
