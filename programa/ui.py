"""Piezas reutilizables de la interfaz de texto (menús, páginas, preguntas)."""

from .teclado import pedir_texto
from .constantes import RESULTADOS_POR_PAGINA
from .errores import reportar_error


def confirmar(pregunta):
    """Pregunta de sí o no. Solo «s» cuenta como sí."""
    return pedir_texto(pregunta).strip().lower() == "s"


class Opcion:
    """Una línea de un menú: la tecla que se escribe, su texto y lo que ejecuta.
    El texto puede ser una función (sin argumentos) si cambia con el tiempo, por ejemplo un contador."""

    def __init__(self, tecla, texto, accion):
        self.tecla, self.texto, self.accion = str(tecla), texto, accion

    def etiqueta(self):
        return self.texto() if callable(self.texto) else self.texto


class Menu:
    """Menú de texto reutilizable: muestra las opciones, ejecuta la que elijas y protege el programa de errores.
    Para agregar una opción nueva basta con sumar una Opcion a la lista (o llamar a agregar)."""

    def __init__(self, titulo, opciones=(), salir="Volver", cancelado="↩️  Cancelado."):
        self.titulo, self.salir, self.cancelado = titulo, salir, cancelado
        self.opciones = list(opciones)

    def agregar(self, tecla, texto, accion):
        self.opciones.append(Opcion(tecla, texto, accion))
        return self

    def __call__(self, config):
        return self.ejecutar(config)

    def ejecutar(self, config):
        ancho = max(len(opcion.tecla) for opcion in self.opciones + [Opcion("0", "", None)])
        por_tecla = {opcion.tecla: opcion for opcion in self.opciones}
        while True:
            print(f"\n═══ {self.titulo} ═══")
            for opcion in self.opciones:
                print(f" {opcion.tecla:>{ancho}}. {opcion.etiqueta()}")
            print(f" {'0':>{ancho}}. {self.salir}")
            try:
                respuesta = pedir_texto("> ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if respuesta == "0":
                return
            if respuesta in por_tecla:
                try:
                    por_tecla[respuesta].accion(config)
                except KeyboardInterrupt:
                    print(f"\n{self.cancelado}")
                except Exception as error:
                    reportar_error(error)


def pedir(pregunta):
    """Pide un texto que no quede vacío: Enter sin escribir nada vuelve a preguntar. Para cancelar, Esc."""
    while True:
        texto = pedir_texto(pregunta).strip()
        if texto:
            return texto


def paginar(resultados, formato, pregunta, opcion_cero=None, numerar=True, tamano_pagina=RESULTADOS_POR_PAGINA):
    """Muestra resultados por páginas, con S = siguiente y A = anterior. Devuelve lo que escribió el usuario
    (nunca vacío; para cancelar, Esc). Con numerar=False las líneas se muestran sin número (listas para leer)."""
    pagina, total = 0, len(resultados)
    paginas = max(1, -(-total // tamano_pagina))
    while True:
        inicio, fin = pagina * tamano_pagina, min(pagina * tamano_pagina + tamano_pagina, total)
        print(f"\nPágina {pagina + 1} de {paginas} ({inicio + 1}–{fin} de {total}):")
        for j in range(inicio, fin):
            print(f"  {j + 1:2d}. {formato(resultados[j])}" if numerar else f"  {formato(resultados[j])}")
        if opcion_cero:
            print(f"   0. {opcion_cero}")
        navegacion = (["S = siguiente"] if fin < total else []) + (["A = anterior"] if pagina > 0 else [])
        respuesta = pedir(
            f"{pregunta}"
            + ("".join(f", {texto_navegacion}" for texto_navegacion in navegacion))
            + ", Esc = cancelar\n> "
        )
        if respuesta.lower() == "s":
            if fin < total:
                pagina += 1
            else:
                print("No hay más páginas.")
            continue
        if respuesta.lower() == "a":
            if pagina > 0:
                pagina -= 1
            else:
                print("Esta es la primera página.")
            continue
        return respuesta


def por_numero(respuesta, items):
    """El elemento que corresponde a un número escrito (contando desde 1), o None si no es válido."""
    respuesta = respuesta.strip()
    return items[int(respuesta) - 1] if respuesta.isdigit() and 1 <= int(respuesta) <= len(items) else None


CERO = object()  # lo que devuelve elegir() cuando se elige la opción 0 (opcion_cero)


def elegir(
    items, formato=str, pregunta="¿Cuál?", paginado=False, opcion_cero=None, tamano_pagina=RESULTADOS_POR_PAGINA
):
    """Muestra una lista numerada y devuelve el elemento elegido (o CERO si se elige la opción 0).
    Insiste hasta recibir un número válido; para cancelar, Esc.
    Las listas largas (o con paginado=True) se muestran por páginas, con S = siguiente y A = anterior."""
    if not (paginado or opcion_cero or len(items) > tamano_pagina):
        for posicion, item in enumerate(items, 1):
            print(f"  {posicion:2d}. {formato(item)}")
    while True:
        if paginado or opcion_cero or len(items) > tamano_pagina:
            respuesta = paginar(items, formato, pregunta, opcion_cero=opcion_cero, tamano_pagina=tamano_pagina)
        else:
            respuesta = pedir(f"{pregunta} (Esc = cancelar): ")
        if opcion_cero and respuesta == "0":
            return CERO
        elegido = por_numero(respuesta, items)
        if elegido is not None:
            return elegido
        print(f"❌ Escribir un número de la lista (1 a {len(items)}).")


def ver_paginado(items, formato=str, tamano_pagina=RESULTADOS_POR_PAGINA):
    """Muestra una lista para leer. Si no cabe en una página, se navega con S / A y se sigue con 0."""
    if len(items) <= tamano_pagina:
        for item in items:
            print(f"  {formato(item)}")
        return
    while paginar(items, formato, "0 = continuar", numerar=False, tamano_pagina=tamano_pagina) != "0":
        pass


def pedir_posicion(pregunta, maximo, defecto):
    """Pide una posición entre 1 y maximo. Enter (o algo no válido) = defecto."""
    respuesta = pedir_texto(f"{pregunta} [Enter = al final ({defecto})]: ").strip()
    return int(respuesta) if respuesta.isdigit() and 1 <= int(respuesta) <= maximo else defecto
