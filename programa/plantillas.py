"""Cómo se escriben las notas: plantillas, orden de sus partes y llamadas a las vistas de Dataview."""

import json
import re

from .rutas import unir_ruta
from .constantes import MARCA_FIN_NUMEROS, MARCA_INICIO_NUMEROS, CARPETA_VISTAS, CARPETA_VISTAS_VAULT
from .md import agregar_propiedad, bloque_propiedad, cuerpo_de_nota, propiedad_texto_largo

LEYENDA_NOTA_COMIC = "📌 = ese número es parte de un evento.\n❌ = No se encontró el archivo\n\n"


ENCABEZADO_LISTA_COMPLETA = "## 📋 Lista completa"


ENCABEZADO_RESUMEN = "## 📝 Mi resumen"


def patron_vista(nombre):
    """Reconoce el bloque que llama a una vista en una nota, sea cual sea la ruta del vault."""
    return re.compile(
        r'```dataviewjs\nawait dv\.view\("[^"\n]*' + re.escape(CARPETA_VISTAS_VAULT) + "/" + nombre + r'"[^\n]*\)\n```'
    )


PATRON_VISTA_COMIC = patron_vista("comic")


PATRON_VISTA_PERSONAJE = patron_vista("personaje")


PATRON_VISTA_EVENTO = patron_vista("evento")


def bloque_vista_dataview(base_relativa, nombre, parametros=None):
    extra = f", {json.dumps(parametros, ensure_ascii=False)}" if parametros else ""
    return f'```dataviewjs\nawait dv.view("{unir_ruta(base_relativa, CARPETA_VISTAS_VAULT, nombre)}"{extra})\n```'


CABECERA_LISTA = "> [!abstract]- " + ENCABEZADO_LISTA_COMPLETA.lstrip("# ")  # callout cerrado al abrir la nota


PATRON_LISTA_PLEGADA = re.compile(r"^" + re.escape(CABECERA_LISTA) + r"[^\n]*\n(?:>[^\n]*(?:\n|$))*", re.M)


PATRON_LISTA_SIN_PLEGAR = re.compile(  # formato anterior: la lista como sección suelta al final de la nota
    r"^" + re.escape(ENCABEZADO_LISTA_COMPLETA) + r"[^\n]*\n[\s\S]*?" + re.escape(MARCA_FIN_NUMEROS) + r"[^\n]*(?:\n|$)", re.M
)


PATRON_BLOQUE_NUMEROS = re.compile(re.escape(MARCA_INICIO_NUMEROS) + r"[\s\S]*?" + re.escape(MARCA_FIN_NUMEROS) + r"[^\n]*\n?")


def lista_plegada(bloque):
    """Las casillas de un cómic (con su leyenda) dentro de un callout cerrado: siguen en la nota, pero no estorban."""
    lineas = LEYENDA_NOTA_COMIC.rstrip("\n").split("\n") + [""] + bloque.split("\n")
    return "\n".join([CABECERA_LISTA] + [f"> {linea}" if linea else ">" for linea in lineas])


def texto_del_usuario(cuerpo, patron_vista):
    """Lo que escribió el usuario en una nota: todo menos la llamada a la vista, el encabezado del resumen y la lista."""
    for patron in (patron_vista, PATRON_LISTA_PLEGADA, PATRON_LISTA_SIN_PLEGAR, PATRON_BLOQUE_NUMEROS):
        cuerpo = patron.sub("", cuerpo, count=1)
    cuerpo = re.sub(r"^" + re.escape(ENCABEZADO_RESUMEN) + r"[ \t]*\n", "", cuerpo, count=1, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", cuerpo).strip("\n").rstrip()  # sin los huecos que dejan las partes quitadas


def resumen_y_cuerpo(previo, patron_vista, *partes):
    """Devuelve (propiedad «resumen», cuerpo) de una nota. El resumen vive en la propiedad y lo muestra la vista.
    La primera vez, el texto que el usuario escribió en el cuerpo pasa a la propiedad; después se respeta lo que haya:
    la propiedad se copia tal cual y el texto que se escriba en el cuerpo queda debajo de la vista."""
    texto = texto_del_usuario(cuerpo_de_nota(previo), patron_vista)
    propiedad = bloque_propiedad(previo, "resumen")
    if not propiedad:
        propiedad, texto = propiedad_texto_largo("resumen", texto), ""
    return propiedad, "\n" + "\n\n".join([partes[0], *([texto] if texto else []), *partes[1:]]) + "\n"


def cuerpo_evento(previo, base_relativa, nombre):
    """(propiedad «resumen», cuerpo) de la nota de un evento, nueva o existente."""
    vista = bloque_vista_dataview(base_relativa, "evento", {"evento": nombre})
    return resumen_y_cuerpo(previo, PATRON_VISTA_EVENTO, vista)


def cuerpo_comic(previo, bloque, base_relativa):
    """(propiedad «resumen», cuerpo) de la nota de un cómic, nueva o existente."""
    vista = bloque_vista_dataview(base_relativa, "comic")
    return resumen_y_cuerpo(previo, PATRON_VISTA_COMIC, vista, lista_plegada(bloque))


def plantilla_personaje(nombre, base_relativa):
    return f'---\ntipo: personaje\nimagen: ""\nbanner: ""\nresumen: ""\n---\n\n{bloque_vista_dataview(base_relativa, "personaje")}\n'


def plantilla_indice(base_relativa, banner=""):
    return f'---\nbanner: "{banner}"\n---\n\n{bloque_vista_dataview(base_relativa, "indice")}\n'


def leer_vista(nombre):
    """Lee una vista de Obsidian (archivo .js de la carpeta 'vistas', junto a este programa)."""
    archivo = CARPETA_VISTAS / nombre
    if not archivo.exists():
        raise FileNotFoundError(
            f"Falta el archivo de la vista «{nombre}» en {CARPETA_VISTAS}. "
            "Copiar la carpeta 'vistas' junto a comics.py."
        )
    return archivo.read_text(encoding="utf-8")


def escribir_si_cambia(ruta, contenido):
    """Escribe solo si el contenido cambió: así no se altera la fecha de modificación de la nota
    (la tarjeta 'Continuar leyendo' la usa) ni se vuelve a sincronizar todo en OneDrive."""
    try:
        if ruta.read_text(encoding="utf-8") == contenido:
            return False
    except FileNotFoundError:
        pass
    ruta.write_text(contenido, encoding="utf-8")
    return True


def asegurar_propiedades_personaje(texto):
    """Agrega las propiedades que falten en la nota de un personaje (sin tocar las que ya tiene)."""
    coincidencia = re.match(r"^---\n(.*?)\n---\n?", texto, re.S)
    if not coincidencia:
        return '---\ntipo: personaje\nimagen: ""\nbanner: ""\n---\n' + texto
    if re.search(r"^banner:", coincidencia.group(1), re.M):
        return texto
    return "---\n" + coincidencia.group(1) + '\nbanner: ""\n---\n' + texto[coincidencia.end() :]


def asegurar_consulta_personaje(nota, base_relativa):
    """Deja la nota de un personaje con la vista actual, sin tocar tus propiedades ni tu texto.
    La primera vez, el texto escrito en la nota pasa a la propiedad «resumen» (la vista lo muestra en su tarjeta).
    Devuelve True si la nota cambió."""
    original = nota.read_text(encoding="utf-8")
    texto = asegurar_propiedades_personaje(original)
    llamada = bloque_vista_dataview(base_relativa, "personaje")
    texto_nuevo = re.sub(
        r"```dataview\n[^`]*?contains\(personajes, this\.file\.link\)[^`]*?```", lambda _: llamada, texto, flags=re.S
    )  # consultas antiguas de Dataview
    texto_nuevo = PATRON_VISTA_PERSONAJE.sub(lambda _: llamada, texto_nuevo)  # vista de otra ruta o versión
    apariciones = [aparicion for aparicion in re.finditer(re.escape(llamada), texto_nuevo)]
    for aparicion in reversed(apariciones[1:]):  # una sola vista
        texto_nuevo = texto_nuevo[: aparicion.start()] + texto_nuevo[aparicion.end() :]
    texto_nuevo = re.sub(
        r"^## (▶️ Siguiente pendiente|Lecturas|Eventos donde aparece|Eventos y cómics donde aparece)[ \t]*\n",
        "",
        texto_nuevo,
        flags=re.M,
    )  # títulos de versiones anteriores
    texto_nuevo = re.sub(
        rf"^# {re.escape(nota.stem)}[ \t]*\n+", "", texto_nuevo, count=1, flags=re.M
    )  # el título ya lo muestra Obsidian
    if llamada not in texto_nuevo:
        texto_nuevo = texto_nuevo.rstrip("\n") + "\n\n" + llamada + "\n"
    if not bloque_propiedad(texto_nuevo, "resumen"):
        resumen = texto_del_usuario(cuerpo_de_nota(texto_nuevo), PATRON_VISTA_PERSONAJE)
        propiedades = re.match(r"^---\n.*?\n---", texto_nuevo, re.S).group(0)
        texto_nuevo = agregar_propiedad(f"{propiedades}\n\n{llamada}\n", propiedad_texto_largo("resumen", resumen))
    if texto_nuevo != original:
        nota.write_text(texto_nuevo, encoding="utf-8")
        return True
    return False
