"""Lectura de lo que se escribe en la consola: Enter acepta y Esc cancela, en cualquier pregunta del programa."""

import codecs
import os
import sys


class Cancelado(KeyboardInterrupt):
    """Se presionó Esc. Hereda de KeyboardInterrupt para que los menús lo traten como «Cancelar»."""


def pedir_texto(pregunta=""):
    """Como input(), pero Esc cancela (lanza Cancelado). Si no hay una terminal, usa input() tal cual."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return input(pregunta)
    sys.stdout.write(pregunta)
    sys.stdout.flush()
    if os.name == "nt":
        return leer_linea_windows()
    return leer_linea_unix()


def escribir(texto):
    sys.stdout.write(texto)
    sys.stdout.flush()


def tecla_comun(caracter, caracteres):
    """Procesa una tecla que no es Esc. Devuelve True cuando la línea está terminada."""
    if caracter in ("\r", "\n"):
        escribir("\r\n")
        return True
    if caracter == "\x03":
        escribir("\r\n")
        raise KeyboardInterrupt
    if caracter == "\x04" and not caracteres:
        escribir("\r\n")
        raise EOFError
    if caracter in ("\x7f", "\x08"):
        if caracteres:
            caracteres.pop()
            escribir("\b \b")
    elif caracter.isprintable():
        caracteres.append(caracter)
        escribir(caracter)
    return False


def leer_linea_unix():
    import select
    import termios
    import tty

    descriptor = sys.stdin.fileno()
    configuracion_anterior = termios.tcgetattr(descriptor)
    decodificador = codecs.getincrementaldecoder("utf-8")(errors="ignore")
    caracteres = []

    def leer_caracteres():
        return decodificador.decode(os.read(descriptor, 64))

    try:
        tty.setraw(descriptor)
        pendientes = ""
        while True:
            if not pendientes:
                pendientes = leer_caracteres()
                continue
            caracter, pendientes = pendientes[0], pendientes[1:]
            if caracter == "\x1b":
                if not pendientes and select.select([descriptor], [], [], 0.05)[0]:
                    pendientes = leer_caracteres()
                if not pendientes:  # Esc solo
                    escribir("\r\n")
                    raise Cancelado
                pendientes = saltar_secuencia_de_escape(pendientes)
                continue
            if tecla_comun(caracter, caracteres):
                return "".join(caracteres)
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, configuracion_anterior)


def saltar_secuencia_de_escape(pendientes):
    """Quita una secuencia de flecha o tecla especial («[A», «OB», «[3~»…) del principio del texto pendiente."""
    if pendientes[:1] in ("[", "O"):
        i = 1
        while i < len(pendientes) and not ("@" <= pendientes[i] <= "~"):
            i += 1
        return pendientes[i + 1 :]
    return pendientes[1:]


def leer_linea_windows():
    import msvcrt

    caracteres = []
    while True:
        caracter = msvcrt.getwch()
        if caracter in ("\x00", "\xe0"):  # flechas y teclas especiales: llegan en dos partes
            msvcrt.getwch()
            continue
        if caracter == "\x1b":
            escribir("\r\n")
            raise Cancelado
        if tecla_comun(caracter, caracteres):
            return "".join(caracteres)
