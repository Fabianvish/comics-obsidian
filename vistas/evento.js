
const DATOS = "__DATOS__";

// ================= Utilidades =================
const raiz = dv.container;
const paginaActual = dv.current();
const CLAVE = (typeof input !== "undefined" && input && input.evento) ? input.evento : paginaActual.file.name;   // nombre del evento en los datos
const ESTADO_ENTRE_REFRESCOS = (window.__vistaEvento ||= {});                         // recuerda vista, página y filtros al refrescar
const estadoVista = (ESTADO_ENTRE_REFRESCOS[paginaActual.file.path] ||= { vista: "orden", pagina: null, paginaComics: 0, filtro: "todo", consulta: "" });
const POR_PAGINA = 12;                                                // tramos por página
const ESTILO_CAJA = "background:var(--background-secondary);border:1px solid var(--background-modifier-border);border-radius:12px";

function normalizarTexto(texto) { return (texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); }

function urlDeImagen(valor) {
  if (!valor) return null;
  const rutaEnlace = (typeof valor === "object" && valor.path) ? valor.path
          : String(valor).replace(/^!?\[\[|\]\]$/g, "").split("|")[0];
  if (!rutaEnlace) return null;
  const archivo = app.metadataCache.getFirstLinkpathDest(rutaEnlace, "");
  return archivo ? app.vault.getResourcePath(archivo) : null;
}

function crearEnlaceInterno(padre, ruta, texto, estilo) {
  const ancla = padre.createEl("a", { text: texto, cls: "internal-link", href: ruta });
  ancla.setAttr("data-href", ruta);
  if (estilo) ancla.setAttr("style", estilo);
  ancla.onclick = (clic) => { clic.preventDefault(); app.workspace.openLinkText(ruta, "", false); };
  return ancla;
}

function abrirArchivo(uri) {
  try { require("electron").shell.openExternal(uri); } catch (error) { window.open(uri); }
}

async function alternarLeido(tarea) {                                          // marca o desmarca un número en la nota de su cómic
  const archivo = app.vault.getAbstractFileByPath(tarea.path);
  if (!archivo) return;
  const idBloque = tarea.blockId || ((tarea.text || "").match(/\^([\w-]+)\s*$/) || [])[1];
  await app.vault.process(archivo, (texto) => {
    const lineas = texto.split("\n");
    const esTarea = (linea) => /^\s*(>\s*)*- \[[ xX]\]/.test(linea || "");
    let indiceLinea = (typeof tarea.line === "number" && esTarea(lineas[tarea.line]) && (!idBloque || lineas[tarea.line].includes("^" + idBloque))) ? tarea.line : -1;
    if (indiceLinea < 0 && idBloque) indiceLinea = lineas.findIndex(linea => esTarea(linea) && linea.includes("^" + idBloque));
    if (indiceLinea >= 0) lineas[indiceLinea] = /^\s*(>\s*)*- \[ \]/.test(lineas[indiceLinea]) ? lineas[indiceLinea].replace("- [ ]", "- [x]") : lineas[indiceLinea].replace(/- \[[xX]\]/, "- [ ]");
    return lineas.join("\n");
  });
}


async function marcarVariosLeidos(tareas) {                                  // marca como leídos varios números, un solo guardado por nota
  const porNota = new Map();
  for (const tarea of tareas) {
    if (!porNota.has(tarea.path)) porNota.set(tarea.path, []);
    porNota.get(tarea.path).push(tarea);
  }
  for (const [ruta, tareasDeLaNota] of porNota) {
    const archivo = app.vault.getAbstractFileByPath(ruta);
    if (!archivo) continue;
    await app.vault.process(archivo, (texto) => {
      const lineas = texto.split("\n");
      for (const tarea of tareasDeLaNota) {
        const idBloque = tarea.blockId || ((tarea.text || "").match(/\^([\w-]+)\s*$/) || [])[1];
        let indiceLinea = (typeof tarea.line === "number" && /^\s*(>\s*)*- \[ \]/.test(lineas[tarea.line] || "") && (!idBloque || lineas[tarea.line].includes("^" + idBloque))) ? tarea.line : -1;
        if (indiceLinea < 0 && idBloque) indiceLinea = lineas.findIndex(linea => /^\s*(>\s*)*- \[ \]/.test(linea) && linea.includes("^" + idBloque));
        if (indiceLinea >= 0) lineas[indiceLinea] = lineas[indiceLinea].replace("- [ ]", "- [x]");
      }
      return lineas.join("\n");
    });
  }
}

function confirmar(texto) {
  try { return window.confirm(texto); } catch (error) { return true; }
}

function agruparEnRangos(elementos, prefijo) {                                     // ["22","23","24","30"] -> "#22–#24, #30"
  const enteros = elementos.filter(texto => /^\d+$/.test(texto)).map(Number).sort((primero, segundo) => primero - segundo);
  const otros = elementos.filter(texto => !/^\d+$/.test(texto));
  const partes = [];
  let inicio = null, anterior = null;
  for (const numero of enteros) {
    if (inicio === null) { inicio = anterior = numero; }
    else if (numero === anterior + 1) { anterior = numero; }
    else { partes.push(inicio === anterior ? `${prefijo}${inicio}` : `${prefijo}${inicio}–${prefijo}${anterior}`); inicio = anterior = numero; }
  }
  if (inicio !== null) partes.push(inicio === anterior ? `${prefijo}${inicio}` : `${prefijo}${inicio}–${prefijo}${anterior}`);
  return [...partes, ...otros.map(numero => prefijo + numero)].join(", ");
}

function dibujarPaginador(padre, numeroPaginaActual, paginas, irAPagina) {
  if (paginas <= 1) return;
  const navegacion = padre.createDiv({ attr: { style: "display:flex;align-items:center;justify-content:center;gap:12px;margin-top:12px" } });
  const botonAnterior = navegacion.createEl("button", { text: "◀ Anterior" });
  botonAnterior.disabled = numeroPaginaActual === 0;
  botonAnterior.onclick = () => irAPagina(numeroPaginaActual - 1);
  navegacion.createSpan({ text: `Página ${numeroPaginaActual + 1} de ${paginas}`, attr: { style: "font-size:0.85em;color:var(--text-muted)" } });
  const botonSiguiente = navegacion.createEl("button", { text: "Siguiente ▶" });
  botonSiguiente.disabled = numeroPaginaActual >= paginas - 1;
  botonSiguiente.onclick = () => irAPagina(numeroPaginaActual + 1);
}

function dibujarBarraDeProgreso(padre, leidos, total, alto) {
  const fondo = padre.createDiv({ attr: { style: `height:${alto}px;border-radius:${alto / 2}px;background:var(--background-modifier-border);overflow:hidden` } });
  fondo.createDiv({ attr: { style: `height:100%;width:${total ? Math.round(100 * leidos / total) : 0}%;background:var(--interactive-accent)` } });
}

// ================= Tarjeta «Mi resumen» (el texto vive en la propiedad «resumen» de la nota) =================
function tarjetaResumen(padre) {
  const archivo = app.vault.getAbstractFileByPath(paginaActual.file.path);
  const borradores = (window.__borradorResumen ||= {});                 // lo escrito sin guardar sobrevive si la vista se redibuja
  const tarjeta = padre.createDiv({ attr: { style: ESTILO_CAJA + ";padding:12px 16px;margin-bottom:18px" } });
  const leerResumen = () => String(((app.metadataCache.getFileCache(archivo) || {}).frontmatter || {}).resumen ?? "");
  function mostrar(texto) {
    tarjeta.empty();
    const cabecera = tarjeta.createDiv({ attr: { style: "display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px" } });
    cabecera.createEl("strong", { text: "📝 Mi resumen" });
    cabecera.createEl("button", { text: "✏️ Editar" }).onclick = () => editar(texto);
    if (texto.trim()) dv.el("div", texto, { container: tarjeta });
    else tarjeta.createDiv({ text: "Todavía no escribiste un resumen.", attr: { style: "color:var(--text-muted);font-size:0.9em" } });
  }
  function editar(texto) {
    tarjeta.empty();
    tarjeta.createEl("strong", { text: "📝 Mi resumen" });
    const cuadro = tarjeta.createEl("textarea", { attr: { rows: "8", style: "display:block;width:100%;margin:8px 0;resize:vertical;font-family:inherit" } });
    cuadro.value = texto;
    cuadro.oninput = () => { borradores[archivo.path] = cuadro.value; };
    const botones = tarjeta.createDiv({ attr: { style: "display:flex;gap:8px;justify-content:flex-end" } });
    botones.createEl("button", { text: "Cancelar" }).onclick = () => { delete borradores[archivo.path]; mostrar(leerResumen()); };
    botones.createEl("button", { text: "💾 Guardar", cls: "mod-cta" }).onclick = async () => {
      const nuevo = cuadro.value.replace(/\s+$/, "");
      await app.fileManager.processFrontMatter(archivo, (propiedades) => { propiedades.resumen = nuevo; });
      delete borradores[archivo.path];
      mostrar(nuevo);
    };
    cuadro.focus();
  }
  if (borradores[archivo.path] !== undefined) editar(borradores[archivo.path]);
  else mostrar(leerResumen());
}
tarjetaResumen(raiz);

// ================= Programa principal =================
let datos = null;
try { datos = JSON.parse(await dv.io.load(DATOS)); } catch (error) { datos = null; }
const evento = datos && datos.eventos ? datos.eventos[CLAVE] : null;

if (!evento) {
  raiz.createDiv({ text: "⚠️ No encuentro este evento en los datos del programa. Elige «Actualizar notas» (opción 1) en el programa, o revisa la ruta DATOS al inicio del código.",
                   attr: { style: ESTILO_CAJA + ";padding:12px" } });
} else {
  // ---- Los números del evento, en su orden de lectura (cada uno vive en la nota de su cómic)
  const cache = {};
  function leerNotaDeComic(nota) {
    if (!cache[nota]) {
      const paginaComic = dv.page(nota);
      const mapa = new Map();
      if (paginaComic) for (const tarea of (paginaComic.file.tasks.array ? paginaComic.file.tasks.array() : [...paginaComic.file.tasks])) {
        const idBloqueTarea = tarea.blockId || ((tarea.text || "").match(/\^([\w-]+)\s*$/) || [])[1];
        if (idBloqueTarea) mapa.set(idBloqueTarea, tarea);
      }
      cache[nota] = { p: paginaComic, mapa };
    }
    return cache[nota];
  }
  const ejemplares = [];
  evento.numeros.forEach(([nota, idBloque], indice) => {
    const datosDelComic = leerNotaDeComic(nota);
    const tarea = datosDelComic.mapa.get(idBloque);
    if (!tarea) return;
    const texto = tarea.text || "";
    const coincidenciaNumero = texto.match(/\[#([^\]]+)\]|\s#([^\s\]]+)/);
    ejemplares.push({ posicion: indice + 1, nota, nombre: datosDelComic.p ? datosDelComic.p.file.name : nota.split("/").pop(), portada: datosDelComic.p && datosDelComic.p.banner, tarea,
                 numero: coincidenciaNumero ? (coincidenciaNumero[1] || coincidenciaNumero[2]) : "?", uriArchivo: (texto.match(/\]\(<(file:[^>]+)>\)/) || [])[1] || null, leido: !!tarea.completed });
  });
  const perdidos = evento.numeros.length - ejemplares.length;

  const bloques = [];                                                 // números seguidos del mismo cómic
  for (const ejemplar of ejemplares) {
    const ultimoTramo = bloques[bloques.length - 1];
    if (ultimoTramo && ultimoTramo.nota === ejemplar.nota) ultimoTramo.ejemplares.push(ejemplar);
    else bloques.push({ nota: ejemplar.nota, nombre: ejemplar.nombre, portada: ejemplar.portada, ejemplares: [ejemplar] });
  }
  const comicsMapa = new Map();                                       // un registro por cómic
  for (const ejemplar of ejemplares) {
    if (!comicsMapa.has(ejemplar.nota)) comicsMapa.set(ejemplar.nota, { nota: ejemplar.nota, nombre: ejemplar.nombre, portada: ejemplar.portada, ejemplares: [] });
    comicsMapa.get(ejemplar.nota).ejemplares.push(ejemplar);
  }
  const comics = [...comicsMapa.values()];

  function calcularProgreso() {
    const indiceSiguiente = ejemplares.findIndex(ejemplar => !ejemplar.leido);
    return { siguiente: indiceSiguiente >= 0 ? ejemplares[indiceSiguiente] : null, leidos: ejemplares.filter(ejemplar => ejemplar.leido).length };
  }
  async function alternarLeidoEjemplar(ejemplar) {                                    // actualiza la vista al instante y guarda en la nota
    ejemplar.leido = !ejemplar.leido;
    dibujarTodo();
    await alternarLeido(ejemplar.tarea);
  }

  // ---- Estructura (en orden de aparición)
  const zonaCab = raiz.createDiv();
  const tabs = raiz.createDiv({ attr: { style: "display:flex;gap:8px;margin:18px 0 8px;flex-wrap:wrap" } });
  const bOrden = tabs.createEl("button", { text: "📖 Orden de lectura" });
  const bComics = tabs.createEl("button", { text: `📚 Cómics del evento (${comics.length})` });
  const controles = raiz.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px" } });
  const buscador = controles.createEl("input", { attr: { type: "search", placeholder: "🔎 Buscar cómic o número…", style: "flex:1;min-width:160px" } });
  const filtro = controles.createEl("select", { cls: "dropdown" });
  for (const [valor, texto] of [["todo", "Todos"], ["pendientes", "⏳ Por leer"], ["leidos", "✅ Leídos"], ["sinarchivo", "❌ Sin archivo"]]) {
    filtro.createEl("option", { text: texto, attr: { value: valor } });
  }
  buscador.value = estadoVista.consulta;
  filtro.value = estadoVista.filtro;
  const zonaLeyenda = raiz.createDiv({ attr: { style: "font-size:0.75em;color:var(--text-muted);margin-bottom:8px" } });
  const zonaCuerpo = raiz.createDiv();

  // ---- Tarjeta principal
  function dibujarCabecera() {
    zonaCab.empty();
    const { siguiente, leidos } = calcularProgreso();
    const total = ejemplares.length;
    const porcentaje = total ? Math.round(100 * leidos / total) : 0;
    const tarjetaCabecera = zonaCab.createDiv({ attr: { style: ESTILO_CAJA + ";display:flex;gap:18px;padding:16px;align-items:center;flex-wrap:wrap" } });
    const contenedorPortada = tarjetaCabecera.createDiv({ attr: { style:
      "width:110px;min-width:110px;aspect-ratio:2/3;border-radius:8px;overflow:hidden;background:var(--background-modifier-border);" +
      "display:flex;align-items:center;justify-content:center;font-size:2.5em" } });
    const portada = urlDeImagen(paginaActual.banner) || urlDeImagen(ejemplares.length && ejemplares[0].portada);
    if (portada) contenedorPortada.createEl("img", { attr: { src: portada, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
    else contenedorPortada.setText("⚡");

    const columnaInfo = tarjetaCabecera.createDiv({ attr: { style: "display:flex;flex-direction:column;gap:8px;flex:1;min-width:220px" } });
    columnaInfo.createDiv({ text: `EVENTO · ${comics.length} CÓMICS · ${total} NÚMEROS`, attr: { style: "font-size:0.75em;letter-spacing:0.12em;color:var(--text-muted)" } });
    columnaInfo.createDiv({ text: evento.nombre_visible || CLAVE, attr: { style: "font-size:1.35em;font-weight:700;line-height:1.2" } });
    if (evento.anios_evento && evento.anios_evento[0]) {
      columnaInfo.createDiv({ text: "📅 " + (evento.anios_evento[0] === evento.anios_evento[1] ? evento.anios_evento[0] : `${evento.anios_evento[0]}–${evento.anios_evento[1]}`),
                       attr: { style: "font-size:0.9em;color:var(--text-muted)" } });
    }
    const filaPorcentaje = columnaInfo.createDiv({ attr: { style: "display:flex;align-items:baseline;gap:10px" } });
    filaPorcentaje.createDiv({ text: `${porcentaje}%`, attr: { style: "font-size:1.8em;font-weight:700" } });
    filaPorcentaje.createDiv({ text: `${leidos} de ${total} leídos`, attr: { style: "color:var(--text-muted)" } });
    dibujarBarraDeProgreso(columnaInfo, leidos, total, 10);

    const chips = columnaInfo.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:6px" } });
    const sinArchivo = ejemplares.filter(ejemplar => !ejemplar.uriArchivo).length;
    for (const texto of [`✅ ${leidos} leídos`, `⏳ ${total - leidos} por leer`, sinArchivo ? `❌ ${sinArchivo} sin archivo` : null].filter(Boolean)) {
      chips.createSpan({ text: texto, attr: { style: "font-size:0.75em;padding:2px 8px;border-radius:10px;background:var(--background-modifier-border)" } });
    }

    if (siguiente) {
      columnaInfo.createDiv({ text: `▶ Siguiente (posición ${siguiente.posicion} de ${total}): ${siguiente.nombre} #${siguiente.numero}`, attr: { style: "font-size:0.9em" } });
      const botones = columnaInfo.createDiv({ attr: { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center" } });
      if (siguiente.uriArchivo) {
        const botonLeer = botones.createEl("button", { text: "📖 Leer", cls: "mod-cta" });
        botonLeer.onclick = () => abrirArchivo(siguiente.uriArchivo);
      }
      const marcar = botones.createEl("button", { text: "✔ Marcar como leído" });
      marcar.onclick = () => { estadoVista.pagina = null; alternarLeidoEjemplar(siguiente); };      // la lista salta a la página del siguiente pendiente
      if (!siguiente.uriArchivo) botones.createSpan({ text: "❌ No tienes este archivo", attr: { style: "font-size:0.85em;color:var(--text-muted)" } });
    } else {
      columnaInfo.createDiv({ text: "🎉 Terminaste este evento", attr: { style: "font-weight:600" } });
    }
    if (ejemplares.some(ejemplar => !ejemplar.leido)) {                                  // ponerse al corriente de un salto
      const fila2 = columnaInfo.createDiv({ attr: { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:0.85em" } });
      fila2.createSpan({ text: "Ponerme al corriente: marcar hasta la posición", attr: { style: "color:var(--text-muted)" } });
      const hasta = fila2.createEl("input", { attr: { type: "text", placeholder: `1–${total}`, style: "width:70px" } });
      const botonMarcarHasta = fila2.createEl("button", { text: "Marcar hasta aquí" });
    const aviso = fila2.createSpan({ attr: { style: "color:var(--text-error)" } });
      botonMarcarHasta.onclick = async () => {
      aviso.setText("");
        const posicionHasta = parseInt(hasta.value.trim().replace(/^#/, ""), 10);
        if (!(posicionHasta >= 1 && posicionHasta <= total)) { aviso.setText(`Escribir una posición entre 1 y ${total}.`); return; }
        const pendientes = ejemplares.filter(ejemplar => ejemplar.posicion <= posicionHasta && !ejemplar.leido);
        if (!pendientes.length) { aviso.setText("Ya estaban todos marcados."); return; }
        if (!confirmar(`¿Marcar ${pendientes.length} número(s) como leídos, hasta la posición ${posicionHasta}?`)) return;
        pendientes.forEach(ejemplar => { ejemplar.leido = true; });
        estadoVista.pagina = null;
        dibujarTodo();
        await marcarVariosLeidos(pendientes.map(ejemplar => ejemplar.tarea));
      };
    }
    if (perdidos > 0) {
      columnaInfo.createDiv({ text: `⚠️ ${perdidos} número(s) del evento no aparecen en las notas de sus cómics. Elige «Actualizar notas» (opción 1) en el programa.`,
                       attr: { style: "font-size:0.8em;color:var(--text-muted)" } });
    }

    const personajesDelEvento = paginaActual.personajes ? [].concat(paginaActual.personajes.array ? paginaActual.personajes.array() : paginaActual.personajes) : [];
    if (personajesDelEvento.length) {
      const filaPersonajes = columnaInfo.createDiv({ attr: { style: "display:flex;gap:10px;flex-wrap:wrap;margin-top:4px" } });
      for (const enlacePersonaje of personajesDelEvento) {
        const ruta = (enlacePersonaje && enlacePersonaje.path) ? enlacePersonaje.path : String(enlacePersonaje).replace(/^\[\[|\]\]$/g, "");
        const nombre = ruta.replace(/\.md$/, "").split("/").pop();
        const paginaPersonaje = dv.page(ruta) || dv.pages().where(ejemplar => ejemplar.file.name === nombre).first();
        const recuadroPersonaje = filaPersonajes.createDiv({ attr: { title: nombre, style: "display:flex;align-items:center;gap:6px;cursor:pointer" } });
        const circuloPersonaje = recuadroPersonaje.createDiv({ attr: { style: "width:34px;height:34px;border-radius:50%;overflow:hidden;background:var(--background-modifier-border);display:flex;align-items:center;justify-content:center;border:2px solid var(--interactive-accent)" } });
        const imagen = urlDeImagen(paginaPersonaje && paginaPersonaje.imagen);
        if (imagen) circuloPersonaje.createEl("img", { attr: { src: imagen, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
        else circuloPersonaje.setText(nombre.charAt(0));
        recuadroPersonaje.createSpan({ text: nombre, attr: { style: "font-size:0.8em" } });
        recuadroPersonaje.onclick = () => app.workspace.openLinkText(paginaPersonaje ? paginaPersonaje.file.path : ruta, "", false);
      }
    }
  }

  // ---- Filtros comunes a las dos vistas
  function coincideConFiltro(registro) {                                              // c: {nombre, items}
    const consulta = normalizarTexto(buscador.value.trim().replace(/^#/, ""));
    const filtroElegido = filtro.value || "todo";
    return (!consulta || normalizarTexto(registro.nombre).includes(consulta) || registro.ejemplares.some(ejemplar => ejemplar.numero.startsWith(consulta))) && (
      filtroElegido === "todo" || (filtroElegido === "pendientes" && registro.ejemplares.some(ejemplar => !ejemplar.leido)) || (filtroElegido === "leidos" && registro.ejemplares.every(ejemplar => ejemplar.leido)) ||
      (filtroElegido === "sinarchivo" && registro.ejemplares.some(ejemplar => !ejemplar.uriArchivo)));
  }

  // ---- Vista 1: orden de lectura (tramos de números seguidos del mismo cómic)
  function dibujarOrden() {
    zonaLeyenda.setText("▶ siguiente · ✔ leído · ❌ sin archivo · clic en el número abre el cómic · clic en ○ lo marca como leído");
    const { siguiente } = calcularProgreso();
    const tramosFiltrados = bloques.filter(coincideConFiltro);
    const paginas = Math.max(1, Math.ceil(tramosFiltrados.length / POR_PAGINA));
    if (estadoVista.pagina === null) {
      const indicePendiente = tramosFiltrados.findIndex(tramo => tramo.ejemplares.some(ejemplar => !ejemplar.leido));
      estadoVista.pagina = indicePendiente >= 0 ? Math.floor(indicePendiente / POR_PAGINA) : 0;
    }
    estadoVista.pagina = Math.min(estadoVista.pagina, paginas - 1);
    const nNumeros = tramosFiltrados.reduce((suma, idBloqueTarea) => suma + idBloqueTarea.ejemplares.length, 0);
    zonaCuerpo.createDiv({ text: tramosFiltrados.length ? `${nNumeros} número${nNumeros === 1 ? "" : "s"}` : "No hay resultados",
                           attr: { style: "font-size:0.8em;color:var(--text-muted);margin-bottom:8px" } });
    const contenedorLista = zonaCuerpo.createDiv({ attr: { style: "display:flex;flex-direction:column;gap:8px" } });
    for (const tramo of tramosFiltrados.slice(estadoVista.pagina * POR_PAGINA, (estadoVista.pagina + 1) * POR_PAGINA)) {
      const tieneSig = siguiente && tramo.ejemplares.includes(siguiente);
      const filaTramo = contenedorLista.createDiv({ attr: { style: ESTILO_CAJA + ";padding:10px;display:flex;gap:12px;align-items:center;flex-wrap:wrap" +
                                         (tieneSig ? ";border:2px solid var(--interactive-accent)" : "") } });
      const bloquePosicion = filaTramo.createDiv({ attr: { style: "min-width:48px;text-align:center;line-height:1.2" } });
      bloquePosicion.createDiv({ text: "POS.", attr: { style: "font-size:0.6em;letter-spacing:0.1em;color:var(--text-muted)" } });
      bloquePosicion.createDiv({ text: agruparEnRangos(tramo.ejemplares.map(ejemplar => String(ejemplar.posicion)), ""), attr: { style: "font-weight:700" } });
      const contenedorPortada = filaTramo.createDiv({ attr: { style: "width:44px;min-width:44px;aspect-ratio:2/3;border-radius:6px;overflow:hidden;background:var(--background-modifier-border);display:flex;align-items:center;justify-content:center;cursor:pointer" } });
      const imagen = urlDeImagen(tramo.portada);
      if (imagen) contenedorPortada.createEl("img", { attr: { src: imagen, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
      else contenedorPortada.setText("📚");
      contenedorPortada.onclick = () => app.workspace.openLinkText(tramo.nota, "", false);
      const cuerpo = filaTramo.createDiv({ attr: { style: "flex:1;min-width:200px;display:flex;flex-direction:column;gap:6px" } });
      const cabecera = cuerpo.createDiv({ attr: { style: "display:flex;justify-content:space-between;gap:8px;align-items:baseline" } });
      crearEnlaceInterno(cabecera, tramo.nota, tramo.nombre, "font-weight:600");
      cabecera.createSpan({ text: `${tramo.ejemplares.filter(ejemplar => ejemplar.leido).length}/${tramo.ejemplares.length}`, attr: { style: "font-size:0.8em;color:var(--text-muted)" } });
      const chips = cuerpo.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:6px" } });
      for (const ejemplar of tramo.ejemplares) {
        const esSig = siguiente === ejemplar;
        const colorFondo = ejemplar.leido ? "var(--interactive-accent)" : "var(--background-secondary)";
        const colorTexto = ejemplar.leido ? "var(--text-on-accent)" : "var(--text-normal)";
        const chip = chips.createDiv({ attr: { title: `Posición ${ejemplar.posicion} de ${ejemplares.length}` + (ejemplar.uriArchivo ? "" : " · sin archivo"), style:
          `display:inline-flex;align-items:stretch;border-radius:8px;overflow:hidden;border:${esSig ? "2px solid var(--interactive-accent)" : "1px solid var(--background-modifier-border)"};` +
          `opacity:${(ejemplar.uriArchivo || ejemplar.leido) ? 1 : 0.65}` } });
        const botonNumero = chip.createDiv({ text: `#${ejemplar.numero}${ejemplar.uriArchivo ? "" : " ❌"}${esSig ? " ▶" : ""}`, attr: { style:
          `padding:4px 8px;font-weight:600;background:${colorFondo};color:${colorTexto};cursor:${ejemplar.uriArchivo ? "pointer" : "default"}` } });
        botonNumero.onclick = () => { if (ejemplar.uriArchivo) abrirArchivo(ejemplar.uriArchivo); };
        const casillaLeido = chip.createDiv({ text: ejemplar.leido ? "✔" : "○", attr: { title: ejemplar.leido ? "Marcar como no leído" : "Marcar como leído", style:
          `padding:4px 7px;cursor:pointer;background:${colorFondo};color:${colorTexto};border-left:1px solid var(--background-modifier-border)` } });
        casillaLeido.onclick = () => alternarLeidoEjemplar(ejemplar);
      }
    }
    dibujarPaginador(zonaCuerpo, estadoVista.pagina, paginas, (numeroPagina) => { estadoVista.pagina = numeroPagina; dibujarCuerpo(); });
  }

  // ---- Vista 2: los cómics que forman el evento
  function dibujarComics() {
    zonaLeyenda.setText("Los cómics que forman este evento, con los números que aparecen en él · clic en la portada abre la nota del cómic");
    const comicsFiltrados = comics.filter(coincideConFiltro);
    const tamanoPagina = 24;
    const paginas = Math.max(1, Math.ceil(comicsFiltrados.length / tamanoPagina));
    estadoVista.paginaComics = Math.min(estadoVista.paginaComics, paginas - 1);
    zonaCuerpo.createDiv({ text: comicsFiltrados.length ? `${comicsFiltrados.length} cómic${comicsFiltrados.length === 1 ? "" : "s"}` : "No hay resultados",
                           attr: { style: "font-size:0.8em;color:var(--text-muted);margin-bottom:8px" } });
    const contenedorLista = zonaCuerpo.createDiv({ attr: { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:14px" } });
    for (const comicDelEvento of comicsFiltrados.slice(estadoVista.paginaComics * tamanoPagina, (estadoVista.paginaComics + 1) * tamanoPagina)) {
      const leidos = comicDelEvento.ejemplares.filter(ejemplar => ejemplar.leido).length;
      const tarjetaComic = contenedorLista.createDiv({ attr: { style: "background:var(--background-secondary);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;position:relative" } });
      if (leidos === comicDelEvento.ejemplares.length) tarjetaComic.createDiv({ text: "✅ Completo", attr: { style: "position:absolute;top:6px;left:6px;font-size:0.65em;padding:2px 6px;border-radius:6px;background:var(--background-primary);opacity:0.9" } });
      const contenedorPortada = tarjetaComic.createDiv({ attr: { style: "aspect-ratio:2/3;background:var(--background-modifier-border);display:flex;align-items:center;justify-content:center;font-size:2em;cursor:pointer" } });
      const imagen = urlDeImagen(comicDelEvento.portada);
      if (imagen) contenedorPortada.createEl("img", { attr: { src: imagen, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
      else contenedorPortada.setText("📚");
      contenedorPortada.onclick = () => app.workspace.openLinkText(comicDelEvento.nota, "", false);
      const columnaInfo = tarjetaComic.createDiv({ attr: { style: "padding:6px 8px 8px;display:flex;flex-direction:column;gap:4px" } });
      crearEnlaceInterno(columnaInfo, comicDelEvento.nota, comicDelEvento.nombre, "font-size:0.8em;font-weight:600;line-height:1.25");
      columnaInfo.createDiv({ text: agruparEnRangos(comicDelEvento.ejemplares.map(ejemplar => ejemplar.numero), "#"), attr: { style: "font-size:0.75em;color:var(--text-muted)" } });
      const filaBarra = columnaInfo.createDiv({ attr: { style: "display:flex;align-items:center;gap:6px;font-size:0.75em;color:var(--text-muted)" } });
      const fondo = filaBarra.createDiv({ attr: { style: "flex:1;height:6px;border-radius:3px;background:var(--background-modifier-border);overflow:hidden" } });
      fondo.createDiv({ attr: { style: `height:100%;width:${Math.round(100 * leidos / comicDelEvento.ejemplares.length)}%;background:var(--interactive-accent)` } });
      filaBarra.createSpan({ text: `${leidos}/${comicDelEvento.ejemplares.length}` });
    }
    dibujarPaginador(zonaCuerpo, estadoVista.paginaComics, paginas, (numeroPagina) => { estadoVista.paginaComics = numeroPagina; dibujarCuerpo(); });
  }

  // ---- Dibujar
  function dibujarCuerpo() {
    zonaCuerpo.empty();
    if (estadoVista.vista === "orden") { bOrden.addClass("mod-cta"); bComics.removeClass("mod-cta"); dibujarOrden(); }
    else { bComics.addClass("mod-cta"); bOrden.removeClass("mod-cta"); dibujarComics(); }
  }
  function dibujarTodo() { dibujarCabecera(); dibujarCuerpo(); }

  bOrden.onclick = () => { estadoVista.vista = "orden"; dibujarCuerpo(); };
  bComics.onclick = () => { estadoVista.vista = "comics"; dibujarCuerpo(); };
  buscador.oninput = () => { estadoVista.consulta = buscador.value; estadoVista.pagina = 0; estadoVista.paginaComics = 0; dibujarCuerpo(); };
  filtro.onchange = () => { estadoVista.filtro = filtro.value; estadoVista.pagina = 0; estadoVista.paginaComics = 0; dibujarCuerpo(); };
  dibujarTodo();
}
