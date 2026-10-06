"""Genera y actualiza todas las notas del vault."""

import datetime
import json
import re
from collections import defaultdict

from .archivos import emparejar_archivos, guardar_portada
from .catalogo import cargar_catalogo
from .comicvine import cache_personajes, id_cv_de_ejemplar
from .config import guardar_config
from .configurar import carpeta_notas, carpetas_archivos_comics
from .rutas import guardar_json, leer_json, ruta_a_uri_windows, ruta_relativa_al_vault, RUTAS, unir_ruta
from .constantes import (
    CARPETA_ARCHIVADAS,
    CARPETA_NOTAS_COMICS,
    CARPETA_NOTAS_EVENTOS,
    CARPETA_NOTAS_PERSONAJES,
    CARPETA_PORTADAS,
    CARPETA_VISTAS_VAULT,
    CARPETAS_RESERVADAS,
    MARCA_FIN_NUMEROS,
    MARCA_INICIO_NUMEROS,
    ORDEN_PREFERIDO_DE_FUENTES,
)
from .listas import anios_de_evento, carpeta_de_nota, leer_cbl, archivos_de_eventos
from .md import (
    id_bloque,
    leer_leidos_de_comic,
    leer_propiedad_lista,
    linea_propiedad_banner,
    linea_propiedad_imagen,
    formatear_lista_yaml,
    leer_propiedad,
)
from .plantillas import (
    asegurar_consulta_personaje,
    cuerpo_comic,
    cuerpo_evento,
    escribir_si_cambia,
    leer_vista,
    plantilla_indice,
    plantilla_personaje,
    bloque_vista_dataview,
)
from .personajes import nombre_de_personaje, sumar_personajes
from .respaldo import respaldar
from .texto import (
    clave_de_comic,
    clave_de_numero,
    nombre_de_nota_comic,
    agrupar_en_rangos,
    limpiar_nombre_de_nota,
    normalizar_numero,
    normalizar_nombre_comic,
    clave_orden_natural,
    titulo_con_anio,
)


class GeneradorNotas:
    """Genera y actualiza las notas del vault. Cada etapa es un método, así se puede cambiar una sin tocar las demás:

    cargar_biblioteca → emparejar_archivos → sincronizar_leidos → personajes_de_eventos → notas_de_comics
    → notas_de_eventos → vistas → archivar_huerfanas → notas_de_personajes → pagina_de_inicio → revision → resumen
    """

    def __init__(self, config):
        self.config = config
        self.base = carpeta_notas(config)
        self.carpeta_notas_eventos = self.base / CARPETA_NOTAS_EVENTOS
        self.carpeta_notas_comics = self.base / CARPETA_NOTAS_COMICS
        self.carpeta_notas_personajes = self.base / CARPETA_NOTAS_PERSONAJES
        self.carpeta_vistas = self.base / CARPETA_VISTAS_VAULT
        self.base_relativa, self.eventos_relativa, self.comics_relativa = (
            ruta_relativa_al_vault(self.base),
            ruta_relativa_al_vault(self.carpeta_notas_eventos),
            ruta_relativa_al_vault(self.carpeta_notas_comics),
        )
        self.revision_comics, self.revision_eventos, self.personajes, self.notas_sin_portada = [], [], set(), []

    # ------------------------------------------------------------------ orden de las etapas
    def ejecutar(self):
        respaldar(self.base)
        self.preparar_carpetas()
        self.cargar_biblioteca()
        self.emparejar_archivos()
        self.sincronizar_leidos()
        self.personajes_de_eventos()
        self.notas_de_comics()
        self.notas_de_eventos()
        self.escribir_vistas()
        self.archivar_huerfanas()
        self.notas_de_personajes()
        self.pagina_de_inicio()
        self.escribir_revision()
        self.corregir_rutas()
        self.mostrar_resumen()

    # ------------------------------------------------------------------ preparación
    def preparar_carpetas(self):
        for carpeta in (
            self.carpeta_notas_eventos,
            self.carpeta_notas_comics,
            self.carpeta_notas_personajes,
            self.carpeta_vistas,
        ):
            carpeta.mkdir(parents=True, exist_ok=True)

    def cargar_biblioteca(self):
        """Eventos, cómics (los que sigues más los de tus eventos) y todos sus números."""
        self.catalogo = cargar_catalogo(descargar_si_falta=False)
        self.eventos = [(archivo, *leer_cbl(archivo)) for archivo in archivos_de_eventos()]
        self.carpeta_por_evento = {
            archivo: self.base / (carpeta_de_nota(archivo) or CARPETA_NOTAS_EVENTOS) for archivo, *_ in self.eventos
        }

        # Cada cómic de mis eventos pasa a ser un cómic seguido, con los números del evento
        seguidos_por_clave = {
            clave_de_comic(seguido["comic"], seguido["anio_comic"]): seguido
            for seguido in self.config.get("seguidos", [])
        }
        for _, _, _, ejemplares in self.eventos:
            for ejemplar in ejemplares:
                seguido = seguidos_por_clave.setdefault(
                    clave_de_comic(ejemplar["comic"], ejemplar["anio_comic"]),
                    {"comic": ejemplar["comic"], "anio_comic": ejemplar["anio_comic"], "numeros": []},
                )
                if normalizar_numero(ejemplar["numero"]) not in {
                    normalizar_numero(numero) for numero in seguido["numeros"]
                }:
                    seguido["numeros"].append(ejemplar["numero"])
        for seguido in seguidos_por_clave.values():
            seguido["numeros"] = sorted(seguido["numeros"], key=clave_orden_natural)
        self.seguidos = sorted(
            seguidos_por_clave.values(), key=lambda seguido: (seguido["comic"], seguido["anio_comic"])
        )
        self.config["seguidos"] = self.seguidos
        guardar_config(self.config)

        # número tal como quedó guardado en el cómic (para que evento y cómic usen el mismo identificador)
        self.numero_guardado = {}
        for seguido in self.seguidos:
            for numero in seguido["numeros"]:
                self.numero_guardado[clave_de_numero(seguido["comic"], seguido["anio_comic"], numero)] = numero

        # todos los números, por clave
        self.ejemplares = {}
        for _, _, _, ejemplares in self.eventos:
            for ejemplar in ejemplares:
                self.ejemplares.setdefault(
                    clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"]), ejemplar
                )
        for seguido in self.seguidos:
            for numero in seguido["numeros"]:
                self.ejemplares.setdefault(
                    clave_de_numero(seguido["comic"], seguido["anio_comic"], numero),
                    {
                        "comic": seguido["comic"],
                        "anio_comic": seguido["anio_comic"],
                        "anio_publicacion": "",
                        "numero": numero,
                    },
                )

    def emparejar_archivos(self):
        self.carpetas_archivos = carpetas_archivos_comics(self.config)
        self.archivos_por_ejemplar, self.archivos_sin_emparejar, self.archivos_por_aproximacion = emparejar_archivos(
            self.carpetas_archivos, self.ejemplares, self.config.get("emparejados")
        )

    # ------------------------------------------------------------------ leídos
    def sincronizar_leidos(self):
        """El checkbox vive solo en la nota del cómic; de ahí sale el historial de leídos."""
        historial_previo = leer_json(RUTAS.archivo_historial, {})
        vistos = defaultdict(set)
        for seguido in self.seguidos:
            nota = self.carpeta_notas_comics / f"{nombre_de_nota_comic(seguido['comic'], seguido['anio_comic'])}.md"
            if nota.exists():
                for clave_ejemplar, esta_leido in leer_leidos_de_comic(
                    nota.read_text(encoding="utf-8"), seguido["comic"], seguido["anio_comic"], seguido["numeros"]
                ).items():
                    vistos[clave_ejemplar].add(esta_leido)
        leido = {clave_ejemplar: bool(esta_leido) for clave_ejemplar, esta_leido in historial_previo.items()}
        for clave_ejemplar, valores in vistos.items():
            antes = leido.get(clave_ejemplar, False)
            leido[clave_ejemplar] = valores.pop() if len(valores) == 1 else (not antes)

        self.eventos_por_ejemplar = defaultdict(list)  # clave -> [(nombre, nombre visible, posición, total)]
        for _, nombre, nombre_visible, ejemplares in self.eventos:
            for posicion, ejemplar in enumerate(ejemplares, 1):
                self.eventos_por_ejemplar[
                    clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"])
                ].append((nombre, nombre_visible, posicion, len(ejemplares)))

        hoy = datetime.date.today().isoformat()
        self.historial_leidos = {}
        for clave_ejemplar, esta_leido in leido.items():
            if not esta_leido:
                continue
            info = historial_previo[clave_ejemplar] if isinstance(historial_previo.get(clave_ejemplar), dict) else {}
            ejemplar = self.ejemplares.get(clave_ejemplar)
            self.historial_leidos[clave_ejemplar] = {
                "descripcion": (
                    f"{titulo_con_anio(ejemplar['comic'], ejemplar['anio_comic'])} #{ejemplar['numero']}"
                    if ejemplar
                    else info.get("descripcion", clave_ejemplar)
                ),
                "comic": ejemplar["comic"] if ejemplar else info.get("comic", ""),
                "anio_comic": ejemplar["anio_comic"] if ejemplar else info.get("anio_comic", ""),
                "numero": ejemplar["numero"] if ejemplar else info.get("numero", ""),
                "leido_el": info.get("leido_el", hoy),
                "eventos": sorted({evento[1] for evento in self.eventos_por_ejemplar.get(clave_ejemplar, [])})
                or info.get("eventos", []),
            }
        guardar_json(RUTAS.archivo_historial, self.historial_leidos)

    # ------------------------------------------------------------------ ayudas
    def texto_del_numero(self, ejemplar, clave_ejemplar):
        archivo = self.archivos_por_ejemplar.get(clave_ejemplar)
        if archivo:
            return f"[#{ejemplar['numero']}](<{ruta_a_uri_windows(archivo)}>)"
        return f"#{ejemplar['numero']}" + (" ❌" if self.carpetas_archivos else "")

    def portada_del_primer_numero(self, archivos_candidatos, nombre):
        """Portada del primer número que tengas (guardada en Imagenes/portadas). None si no hay."""
        primero = next(iter(archivos_candidatos), None)
        portada = guardar_portada(primero, self.base / CARPETA_PORTADAS / nombre) if primero else None
        if primero and not portada:
            self.notas_sin_portada.append(nombre)
        return portada

    def marcas_de_eventos(self, clave_ejemplar):
        """Los eventos a los que pertenece un número: los del usuario y, si hay catálogo, otros (máximo 3)."""
        marcas, ya_incluidos = [], set()
        for nombre, nombre_visible, posicion, total in self.eventos_por_ejemplar.get(clave_ejemplar, []):
            marcas.append(f"[[{nombre}|{nombre_visible}]] (posición {posicion} de {total})")
            ya_incluidos.add(normalizar_nombre_comic(nombre_visible))
        if self.catalogo:
            refs = sorted(
                self.catalogo["eventos"].get(clave_ejemplar, []),
                key=lambda referencia: next(
                    (
                        j
                        for j, fuente in enumerate(ORDEN_PREFERIDO_DE_FUENTES)
                        if fuente in self.catalogo["listas"][referencia[0]]["categoria"]
                    ),
                    99,
                ),
            )
            for indice_lista, posicion in refs:
                lista_catalogo = self.catalogo["listas"][indice_lista]
                if len(marcas) >= 3 or normalizar_nombre_comic(lista_catalogo["nombre_visible"]) in ya_incluidos:
                    continue
                ya_incluidos.add(normalizar_nombre_comic(lista_catalogo["nombre_visible"]))
                marcas.append(
                    f"{lista_catalogo['nombre_visible']} (posición {posicion} de {lista_catalogo['cantidad']})"
                )
        return marcas

    # ------------------------------------------------------------------ personajes de los eventos
    def personajes_de_eventos(self):
        """Los personajes de cada evento pasan a las notas de sus cómics, pero solo a los cómics donde aparecen
        según lo ya consultado en Comic Vine (no hace consultas nuevas)."""
        self.nota_por_evento, self.personajes_por_comic = {}, defaultdict(list)
        cache = cache_personajes()["numeros"]
        for archivo_evento, nombre, _, ejemplares in self.eventos:
            nota = self.ubicar_nota_de_evento(self.carpeta_por_evento[archivo_evento], nombre)
            self.nota_por_evento[archivo_evento] = nota
            texto = nota.read_text(encoding="utf-8") if nota.exists() else ""
            enlaces = {nombre_de_personaje(enlace): enlace for enlace in leer_propiedad_lista(texto, "personajes")}
            if not enlaces:
                continue
            for ejemplar in ejemplares:
                personajes_cv = cache.get(id_cv_de_ejemplar(ejemplar, self.catalogo), [])
                comic = self.personajes_por_comic[clave_de_comic(ejemplar["comic"], ejemplar["anio_comic"])]
                for _, nombre_cv in personajes_cv:
                    enlace = enlaces.get(normalizar_nombre_comic(nombre_cv))
                    if enlace and enlace not in comic:
                        comic.append(enlace)

    # ------------------------------------------------------------------ notas de cómics (aquí viven los checkboxes)
    def notas_de_comics(self):
        self.notas_de_comics_vigentes = set()
        for seguido in self.seguidos:
            titulo = titulo_con_anio(seguido["comic"], seguido["anio_comic"])
            nombre_nota = nombre_de_nota_comic(seguido["comic"], seguido["anio_comic"])
            nota = self.carpeta_notas_comics / f"{nombre_nota}.md"
            self.notas_de_comics_vigentes.add(nota.name)
            previo = nota.read_text(encoding="utf-8") if nota.exists() else ""
            lineas, faltantes = [], []
            for numero in seguido["numeros"]:
                clave_ejemplar = clave_de_numero(seguido["comic"], seguido["anio_comic"], numero)
                ejemplar = self.ejemplares[clave_ejemplar]
                linea = f"- [{'x' if self.historial_leidos.get(clave_ejemplar) else ' '}] {titulo} {self.texto_del_numero(ejemplar, clave_ejemplar)}"
                marcas = self.marcas_de_eventos(clave_ejemplar)
                if marcas:
                    linea += " · 📌 " + " · ".join(marcas)
                lineas.append(f"{linea} ^{id_bloque(numero)}")
                if self.carpetas_archivos and clave_ejemplar not in self.archivos_por_ejemplar:
                    faltantes.append(f"#{numero}")
            personajes_nota = sumar_personajes(
                leer_propiedad_lista(previo, "personajes"),
                self.personajes_por_comic.get(clave_de_comic(seguido["comic"], seguido["anio_comic"]), []),
            )
            self.personajes.update(personajes_nota)
            portada = self.portada_del_primer_numero(
                (
                    self.archivos_por_ejemplar[clave_de_numero(seguido["comic"], seguido["anio_comic"], numero)]
                    for numero in seguido["numeros"]
                    if clave_de_numero(seguido["comic"], seguido["anio_comic"], numero) in self.archivos_por_ejemplar
                ),
                nombre_nota,
            )
            bloque = "\n".join([MARCA_INICIO_NUMEROS, *lineas, MARCA_FIN_NUMEROS])
            resumen, cuerpo = cuerpo_comic(previo, bloque, self.base_relativa)
            props = (
                f'---\ntipo: comic\ncómic: "{seguido["comic"]}"\naño: "{seguido["anio_comic"]}"\n'
                f"{linea_propiedad_banner(portada, previo)}personajes: {formatear_lista_yaml(personajes_nota)}\n"
                f"{resumen}\n---\n"
            )
            escribir_si_cambia(nota, props + cuerpo)
            self.revision_comics.append(
                {
                    "nombre": nombre_nota,
                    "nota": unir_ruta(self.comics_relativa, nombre_nota),
                    "total": len(seguido["numeros"]),
                    "con_archivo": len(seguido["numeros"]) - len(faltantes),
                    "faltan": (
                        [agrupar_en_rangos([numero_faltante.lstrip("#") for numero_faltante in faltantes])]
                        if faltantes
                        else []
                    ),
                }
            )

    # ------------------------------------------------------------------ notas de eventos (muestran los checkboxes de los cómics)
    def carpetas_elegidas_para_eventos(self):
        """Carpetas del vault (fuera de las del programa) que pueden tener notas de eventos propios."""
        return [
            carpeta
            for carpeta in self.base.iterdir()
            if carpeta.is_dir()
            and not carpeta.name.startswith(".")
            and carpeta.name.lower() not in CARPETAS_RESERVADAS
            and carpeta != self.carpeta_notas_eventos
        ]

    def ubicar_nota_de_evento(self, carpeta, nombre):
        """Ruta de la nota de un evento. Si estaba en otra carpeta de eventos (se cambió la carpeta), se mueve."""
        nota = carpeta / f"{nombre}.md"
        if not nota.exists():
            anterior = next(
                (
                    otra_carpeta / nota.name
                    for otra_carpeta in [self.carpeta_notas_eventos, *self.carpetas_elegidas_para_eventos()]
                    if otra_carpeta != carpeta and (otra_carpeta / nota.name).exists()
                ),
                None,
            )
            carpeta.mkdir(parents=True, exist_ok=True)
            if anterior:
                anterior.replace(nota)
                print(f"📁 Nota movida a {carpeta.name}: {nombre}")
        return nota

    def notas_de_eventos(self):
        self.datos_para_vistas = {"orden": [], "eventos": {}, "comics": self.comics_relativa}
        self.notas_de_eventos_vigentes = set()
        for orden, (archivo_evento, nombre, nombre_visible, ejemplares) in enumerate(self.eventos, 1):
            nota = self.nota_por_evento[archivo_evento]
            self.notas_de_eventos_vigentes.add(nota)
            ruta_nota = ruta_relativa_al_vault(nota.with_suffix(""))
            previo = nota.read_text(encoding="utf-8") if nota.exists() else ""
            numeros = []
            for ejemplar in ejemplares:
                clave_ejemplar = clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"])
                numeros.append(
                    [
                        unir_ruta(
                            self.comics_relativa, nombre_de_nota_comic(ejemplar["comic"], ejemplar["anio_comic"])
                        ),
                        id_bloque(self.numero_guardado.get(clave_ejemplar, ejemplar["numero"])),
                    ]
                )
            self.datos_para_vistas["orden"].append(nombre)
            self.datos_para_vistas["eventos"][nombre] = {
                "nombre_visible": nombre_visible,
                "nota": ruta_nota,
                "numeros": numeros,
            }

            personajes_nota = leer_propiedad_lista(previo, "personajes")
            self.personajes.update(personajes_nota)
            portada = self.portada_del_primer_numero(
                (
                    self.archivos_por_ejemplar[
                        clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"])
                    ]
                    for ejemplar in ejemplares
                    if clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"])
                    in self.archivos_por_ejemplar
                ),
                nombre,
            )
            inicio, fin = anios_de_evento(archivo_evento, ejemplares, self.catalogo)
            linea_años = f"año_inicio: {inicio}\naño_fin: {fin}\n" if inicio else ""
            self.datos_para_vistas["eventos"][nombre]["anios_evento"] = [inicio, fin] if inicio else []
            resumen, cuerpo = cuerpo_evento(previo, self.base_relativa, nombre)
            props = (
                f"---\norden: {orden}\ntipo: evento\n{linea_años}{linea_propiedad_banner(portada, previo)}{linea_propiedad_imagen(previo)}"
                f"personajes: {formatear_lista_yaml(personajes_nota)}\n{resumen}\n---\n"
            )
            escribir_si_cambia(nota, props + cuerpo)
            faltan_ev = defaultdict(list)
            for ejemplar in ejemplares:
                if (
                    clave_de_numero(ejemplar["comic"], ejemplar["anio_comic"], ejemplar["numero"])
                    not in self.archivos_por_ejemplar
                ):
                    faltan_ev[titulo_con_anio(ejemplar["comic"], ejemplar["anio_comic"])].append(ejemplar["numero"])
            self.revision_eventos.append(
                {
                    "nombre": nombre,
                    "nombre_visible": nombre_visible,
                    "nota": ruta_nota,
                    "total": len(ejemplares),
                    "con_archivo": len(ejemplares)
                    - sum(len(faltantes_del_comic) for faltantes_del_comic in faltan_ev.values()),
                    "faltan": [
                        f"{titulo} {agrupar_en_rangos(numeros_faltantes)}"
                        for titulo, numeros_faltantes in faltan_ev.items()
                    ],
                }
            )

    # ------------------------------------------------------------------ vistas de Dataview
    def escribir_vistas(self):
        """Se reescriben siempre: si cambian, no hay que borrar notas."""
        ruta_datos = unir_ruta(self.base_relativa, CARPETA_VISTAS_VAULT, "datos.json")
        escribir_si_cambia(
            self.carpeta_vistas / "datos.json", json.dumps(self.datos_para_vistas, indent=1, ensure_ascii=False)
        )
        ruta_revision = unir_ruta(self.base_relativa, CARPETA_VISTAS_VAULT, "revision.json")
        for nombre_js in ("evento", "comic", "indice", "personaje", "revision"):
            escribir_si_cambia(
                self.carpeta_vistas / f"{nombre_js}.js",
                leer_vista(nombre_js + ".js").replace("__DATOS__", ruta_datos).replace("__REVISION__", ruta_revision),
            )

    # ------------------------------------------------------------------ notas que ya no corresponden
    def archivar_huerfanas(self):
        notas_sobrantes = [
            nota for nota in self.carpeta_notas_comics.glob("*.md") if nota.name not in self.notas_de_comics_vigentes
        ] + [nota for nota in self.carpeta_notas_eventos.glob("*.md") if nota not in self.notas_de_eventos_vigentes]
        for carpeta in self.carpetas_elegidas_para_eventos():
            notas_sobrantes += [  # en una carpeta elegida solo se archivan notas de evento, nunca las propias
                nota
                for nota in carpeta.glob("*.md")
                if nota not in self.notas_de_eventos_vigentes
                and leer_propiedad(nota.read_text(encoding="utf-8"), "tipo") == "evento"
            ]
        for nota in notas_sobrantes:
            (self.base / CARPETA_ARCHIVADAS).mkdir(exist_ok=True)
            nota.replace(self.base / CARPETA_ARCHIVADAS / nota.name)
            print(f"📦 Archivada: {nota.stem}")

    # ------------------------------------------------------------------ personajes
    def notas_de_personajes(self):
        """Crea las notas que faltan y asegura la vista en TODAS (sin tocar sus propiedades)."""
        raiz = next(
            (personaje for personaje in [self.base, *self.base.parents] if (personaje / ".obsidian").is_dir()),
            self.base,
        )
        notas_pj = {nota.resolve() for nota in self.carpeta_notas_personajes.glob("*.md")}
        for personaje in re.findall(r"\[\[([^\]|]+)", " ".join(self.personajes)):
            nombre_pj = limpiar_nombre_de_nota(personaje)
            en_vault = [
                nota
                for nota in raiz.rglob(f"{nombre_pj}.md")
                if CARPETA_VISTAS_VAULT not in nota.parts
                and CARPETA_ARCHIVADAS not in nota.parts
                and not str(nota).startswith(str(self.carpeta_notas_comics))
                and not str(nota).startswith(str(self.carpeta_notas_eventos))
            ]
            if en_vault:
                notas_pj.add(en_vault[0].resolve())  # ya existe (quizás creada al hacer clic en el enlace)
            else:
                nota = self.carpeta_notas_personajes / f"{nombre_pj}.md"
                nota.write_text(plantilla_personaje(personaje, self.base_relativa), encoding="utf-8")
                notas_pj.add(nota.resolve())
        for nota in notas_pj:
            if asegurar_consulta_personaje(nota, self.base_relativa):
                print(f"👤 Consulta actualizada: {nota.stem}")

    # ------------------------------------------------------------------ página de inicio y revisión
    def pagina_de_inicio(self):
        inicio = self.base / "Mis lecturas.md"
        banner_inicio = leer_propiedad(inicio.read_text(encoding="utf-8"), "banner") if inicio.exists() else ""
        escribir_si_cambia(inicio, plantilla_indice(self.base_relativa, banner_inicio))

    def escribir_revision(self):
        """Datos de «Revisar mi biblioteca»: qué falta, qué no se emparejó y avisos."""
        avisos = []
        if self.notas_sin_portada:
            avisos.append(
                f"No se pudo obtener la portada de {len(self.notas_sin_portada)} nota(s): {', '.join(self.notas_sin_portada[:8])}"
                + ("…" if len(self.notas_sin_portada) > 8 else "")
                + ". Si son .cbr, instalar unrar en WSL: sudo apt install unrar"
            )
        if not self.catalogo:
            avisos.append(
                "Aún no se descargó el catálogo: no se muestran los 📌 de otros eventos ni los años de los eventos propios. Descargarlo en «Configuración → Actualizar el catálogo»."
            )
        for carpeta in self.carpetas_archivos:
            if not carpeta.is_dir():
                avisos.append(
                    f"No se encuentra la carpeta de cómics ({carpeta}). ¿Está conectado el disco? Se puede cambiar en «Configuración → Carpetas de cómics de este PC»."
                )
        datos_revision = {
            "generado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tiene_carpeta": bool(self.carpetas_archivos),
            "resumen": {
                "eventos": len(self.eventos),
                "comics": len(self.seguidos),
                "numeros": len(self.ejemplares),
                "con_archivo": len(self.archivos_por_ejemplar),
                "sin_emparejar": len(self.archivos_sin_emparejar),
                "aproximados": len(self.archivos_por_aproximacion),
            },
            "eventos": self.revision_eventos,
            "comics": self.revision_comics,
            "sin_emparejar": [archivo.name for archivo in self.archivos_sin_emparejar],
            "aproximados": [
                {"archivo": archivo.name, "destino": etiqueta} for archivo, etiqueta in self.archivos_por_aproximacion
            ],
            "avisos": avisos,
        }
        escribir_si_cambia(
            self.carpeta_vistas / "revision.json", json.dumps(datos_revision, indent=1, ensure_ascii=False)
        )
        escribir_si_cambia(
            self.base / "Revisar mi biblioteca.md", f"{bloque_vista_dataview(self.base_relativa, 'revision')}\n"
        )

    def corregir_rutas(self):
        """Si moviste la carpeta dentro del vault, corrige las rutas de las vistas."""
        for nota in self.base.rglob("*.md"):
            texto = nota.read_text(encoding="utf-8")
            texto_corregido = re.sub(
                r'dv\.view\("[^"]*' + re.escape(CARPETA_VISTAS_VAULT) + "/", f'dv.view("{unir_ruta(self.base_relativa, CARPETA_VISTAS_VAULT)}/', texto
            )
            if texto_corregido != texto:
                nota.write_text(texto_corregido, encoding="utf-8")

    def mostrar_resumen(self):
        if self.notas_sin_portada:
            print(
                f"🖼️  No se pudo obtener la portada de {len(self.notas_sin_portada)} nota(s). "
                "Si son .cbr, instalar unrar en WSL: sudo apt install unrar"
            )
        mensaje = f"✅ {len(self.eventos)} eventos, {len(self.seguidos)} cómics"
        if self.carpetas_archivos:
            mensaje += f", {len(self.archivos_por_ejemplar)} números enlazados a los archivos"
            if self.archivos_sin_emparejar or self.archivos_por_aproximacion:
                mensaje += f" ({len(self.archivos_sin_emparejar)} archivos sin emparejar, {len(self.archivos_por_aproximacion)} por aproximación: ver detalle en «Revisar mi biblioteca»)"
        if not self.catalogo:
            mensaje += " (sin catálogo: los 📌 de otros eventos aparecerán al descargarlo en «Configuración → Actualizar el catálogo»)"
        print(mensaje + ".")


def generar(config):
    """Actualiza todas las notas del vault («Actualizar notas», opción 1 del menú)."""
    GeneradorNotas(config).ejecutar()
