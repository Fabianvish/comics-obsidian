
// ================= Utilidades =================
const raiz = dv.container;
const paginaActual = dv.current();
const ESTADO_ENTRE_REFRESCOS = (window.__vistaComic ||= {});                       // recuerda página y filtros al refrescar
const estadoVista = (ESTADO_ENTRE_REFRESCOS[paginaActual.file.path] ||= { pagina: null, filtro: "todo", consulta: "" });
const POR_PAGINA = 60;                                              // números por página
const ESTILO_CAJA = "background:var(--background-secondary);border:1px solid var(--background-modifier-border);border-radius:12px";

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

function abrirArchivo(uriArchivo) {
  try { require("electron").shell.openExternal(uriArchivo); } catch (error) { window.open(uriArchivo); }
}

async function alternarLeido(tarea) {                                        // marca o desmarca un número en la nota
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

function agruparEnRangos(elementos, prefijo) {                                   // ["22","23","24","30"] -> "#22–#24, #30"
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

// ================= Datos de la nota =================
function analizarMarcaDeEvento(texto) {                                         // "[[Nota|Evento]] (posición 2 de 28)"  (también entiende el formato antiguo «cap.»)
  const coincidencia = texto.match(/^\[\[([^\]|]+)\|?([^\]]*)\]\]\s*(.*)$/);
  const resto = coincidencia ? coincidencia[3] : texto;
  const coincidenciaPosicion = resto.match(/(?:posición|cap\.) (\d+) de (\d+)/);
  return { ruta: coincidencia ? coincidencia[1] : null, nombre: coincidencia ? (coincidencia[2] || coincidencia[1]) : texto.replace(/\s*\((?:posición|cap\.).*$/, "").trim(),
           posicion: coincidenciaPosicion ? coincidenciaPosicion[1] : null, total: coincidenciaPosicion ? Number(coincidenciaPosicion[2]) : null };
}

const tareas = paginaActual.file.tasks.array ? paginaActual.file.tasks.array() : [...paginaActual.file.tasks];
const ejemplares = tareas.map((tarea) => {
  const texto = tarea.text || "";
  const coincidenciaNumero = texto.match(/\[#([^\]]+)\]|\s#([^\s\]]+)/);
  const uriArchivo = (texto.match(/\]\(<(file:[^>]+)>\)/) || [])[1] || null;
  const pines = texto.includes("· 📌 ")
    ? texto.split("· 📌 ").slice(1).join("").replace(/\s*\^[\w-]+\s*$/, "").split(" · ").map(texto => texto.trim()).filter(Boolean).map(analizarMarcaDeEvento)
    : [];
  return { tarea, numero: coincidenciaNumero ? (coincidenciaNumero[1] || coincidenciaNumero[2]) : "?", uriArchivo, leido: !!tarea.completed, marcasDeEventos: pines };
});

function calcularProgreso() {
  const indiceSiguiente = ejemplares.findIndex(ejemplar => !ejemplar.leido);
  return { idx: indiceSiguiente, siguiente: indiceSiguiente >= 0 ? ejemplares[indiceSiguiente] : null, leidos: ejemplares.filter(ejemplar => ejemplar.leido).length };
}

async function alternarLeidoEjemplar(ejemplar) {                                    // actualiza la vista al instante y guarda en la nota
  ejemplar.leido = !ejemplar.leido;
  dibujarTodo();
  await alternarLeido(ejemplar.tarea);
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

// ================= Estructura (en orden de aparición) =================
const zonaCab = raiz.createDiv();
const zonaAviso = raiz.createDiv();
const tituloNum = raiz.createEl("h2", { attr: { style: "margin-top:1.4em" } });
const controles = raiz.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px" } });
const buscador = controles.createEl("input", { attr: { type: "search", placeholder: "🔎 Buscar número…", style: "flex:1;min-width:140px" } });
const filtro = controles.createEl("select", { cls: "dropdown" });
for (const [valor, texto] of [["todo", "Todos"], ["pendientes", "⏳ Por leer"], ["leidos", "✅ Leídos"],
                       ["eventos", "📌 En eventos"], ["sinarchivo", "❌ Sin archivo"]]) {
  filtro.createEl("option", { text: texto, attr: { value: valor } });
}
buscador.value = estadoVista.consulta;
filtro.value = estadoVista.filtro;
raiz.createDiv({ text: "▶ siguiente · ✔ leído · 📌 parte de un evento · ❌ sin archivo · clic en el número abre el cómic · clic en ○ lo marca como leído",
                 attr: { style: "font-size:0.75em;color:var(--text-muted);margin-bottom:8px" } });
const zonaGrid = raiz.createDiv();
const zonaEv = raiz.createDiv();

// ================= Tarjeta principal =================
function dibujarCabecera() {
  zonaCab.empty();
  const { siguiente, leidos } = calcularProgreso();
  const total = ejemplares.length;
  const porcentaje = total ? Math.round(100 * leidos / total) : 0;
  const tarjetaCabecera = zonaCab.createDiv({ attr: { style: ESTILO_CAJA + ";display:flex;gap:18px;padding:16px;align-items:center;flex-wrap:wrap" } });
  const contenedorPortada = tarjetaCabecera.createDiv({ attr: { style:
    "width:110px;min-width:110px;aspect-ratio:2/3;border-radius:8px;overflow:hidden;background:var(--background-modifier-border);" +
    "display:flex;align-items:center;justify-content:center;font-size:2.5em" } });
  const portada = urlDeImagen(paginaActual.banner);
  if (portada) contenedorPortada.createEl("img", { attr: { src: portada, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
  else contenedorPortada.setText("📚");

  const columnaInfo = tarjetaCabecera.createDiv({ attr: { style: "display:flex;flex-direction:column;gap:8px;flex:1;min-width:220px" } });
  columnaInfo.createDiv({ text: "CÓMIC" + ((paginaActual["año"] || paginaActual.volumen) ? " · DESDE " + (paginaActual["año"] || paginaActual.volumen) : ""),
                   attr: { style: "font-size:0.75em;letter-spacing:0.12em;color:var(--text-muted)" } });
  const filaPorcentaje = columnaInfo.createDiv({ attr: { style: "display:flex;align-items:baseline;gap:10px" } });
  filaPorcentaje.createDiv({ text: `${porcentaje}%`, attr: { style: "font-size:1.8em;font-weight:700" } });
  filaPorcentaje.createDiv({ text: `${leidos} de ${total} leídos`, attr: { style: "color:var(--text-muted)" } });
  const fondo = columnaInfo.createDiv({ attr: { style: "height:10px;border-radius:5px;background:var(--background-modifier-border);overflow:hidden" } });
  fondo.createDiv({ attr: { style: `height:100%;width:${porcentaje}%;background:var(--interactive-accent)` } });

  const chips = columnaInfo.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:6px" } });
  const enEventos = ejemplares.filter(ejemplar => ejemplar.marcasDeEventos.length).length;
  const sinArchivo = ejemplares.filter(ejemplar => !ejemplar.uriArchivo).length;
  for (const texto of [`✅ ${leidos} leídos`, `⏳ ${total - leidos} por leer`, enEventos ? `📌 ${enEventos} en eventos` : null, sinArchivo ? `❌ ${sinArchivo} sin archivo` : null].filter(Boolean)) {
    chips.createSpan({ text: texto, attr: { style: "font-size:0.75em;padding:2px 8px;border-radius:10px;background:var(--background-modifier-border)" } });
  }

  const botones = columnaInfo.createDiv({ attr: { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:2px" } });
  if (siguiente) {
    if (siguiente.uriArchivo) {
      const botonLeer = botones.createEl("button", { text: `📖 Leer #${siguiente.numero}`, cls: "mod-cta" });
      botonLeer.onclick = () => abrirArchivo(siguiente.uriArchivo);
    }
    const marcar = botones.createEl("button", { text: `✔ Marcar #${siguiente.numero} como leído` });
    marcar.onclick = () => alternarLeidoEjemplar(siguiente);
    if (!siguiente.uriArchivo) botones.createSpan({ text: "❌ No tienes este archivo", attr: { style: "font-size:0.85em;color:var(--text-muted)" } });
  } else {
    botones.createDiv({ text: "🎉 Ya leíste todos los números", attr: { style: "font-weight:600" } });
  }
  if (ejemplares.some(ejemplar => !ejemplar.leido)) {                                    // ponerse al corriente de un salto
    const fila2 = columnaInfo.createDiv({ attr: { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:0.85em" } });
    fila2.createSpan({ text: "Ponerme al corriente: marcar hasta el #", attr: { style: "color:var(--text-muted)" } });
    const hasta = fila2.createEl("input", { attr: { type: "text", placeholder: "N°", style: "width:70px" } });
    const botonMarcarHasta = fila2.createEl("button", { text: "Marcar hasta aquí" });
    const aviso = fila2.createSpan({ attr: { style: "color:var(--text-error)" } });
    botonMarcarHasta.onclick = async () => {
      aviso.setText("");
      const indiceHasta = ejemplares.findIndex(ejemplar => ejemplar.numero === hasta.value.trim().replace(/^#/, ""));
      if (indiceHasta < 0) { aviso.setText("No encuentro ese número en este cómic."); return; }
      const pendientes = ejemplares.slice(0, indiceHasta + 1).filter(ejemplar => !ejemplar.leido);
      if (!pendientes.length) { aviso.setText("Ya estaban todos marcados."); return; }
      if (!confirmar(`¿Marcar ${pendientes.length} número(s) como leídos, hasta el #${ejemplares[indiceHasta].numero}?`)) return;
      pendientes.forEach(ejemplar => { ejemplar.leido = true; });
      estadoVista.pagina = null;
      dibujarTodo();
      await marcarVariosLeidos(pendientes.map(ejemplar => ejemplar.tarea));
    };
  }

  // Personajes de este cómic
  const personajesDelComic = paginaActual.personajes ? [].concat(paginaActual.personajes.array ? paginaActual.personajes.array() : paginaActual.personajes) : [];
  if (personajesDelComic.length) {
    const filaPersonajes = columnaInfo.createDiv({ attr: { style: "display:flex;gap:10px;flex-wrap:wrap;margin-top:4px" } });
    for (const enlacePersonaje of personajesDelComic) {
      const ruta = (enlacePersonaje && enlacePersonaje.path) ? enlacePersonaje.path : String(enlacePersonaje).replace(/^\[\[|\]\]$/g, "");
      const nombre = ruta.replace(/\.md$/, "").split("/").pop();
      const paginaPersonaje = dv.page(ruta) || dv.pages().where(pagina => pagina.file.name === nombre).first();
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

// ================= Aviso: se viene un evento =================
function dibujarAviso() {
  zonaAviso.empty();
  const { idx: indiceSiguiente, siguiente } = calcularProgreso();
  if (!siguiente) return;
  const indiceEvento = ejemplares.findIndex((ejemplar, j) => j >= indiceSiguiente && !ejemplar.leido && ejemplar.marcasDeEventos.length);
  if (indiceEvento < 0) return;
  const marca = ejemplares[indiceEvento].marcasDeEventos[0];
  const cajaAviso = zonaAviso.createDiv({ attr: { style: ESTILO_CAJA + ";padding:10px 14px;margin-top:10px;font-size:0.95em" } });
  if (indiceEvento === indiceSiguiente) cajaAviso.appendText(`📌 El siguiente número (#${ejemplares[indiceEvento].numero}) ya es parte de `);
  else cajaAviso.appendText("📍 Se viene un evento: ");
  if (marca.ruta) crearEnlaceInterno(cajaAviso, marca.ruta, marca.nombre); else cajaAviso.appendText(marca.nombre);
  if (indiceEvento === indiceSiguiente) { if (marca.posicion) cajaAviso.appendText(` (posición ${marca.posicion} de ${marca.total})`); }
  else {
    const faltan = ejemplares.slice(indiceSiguiente, indiceEvento).filter(ejemplar => !ejemplar.leido).length;
    cajaAviso.appendText(` — este cómic entra en el #${ejemplares[indiceEvento].numero} (faltan ${faltan} número${faltan === 1 ? "" : "s"})`);
  }
}

// ================= Cuadrícula de números =================
function dibujarCuadriculaDeNumeros() {
  zonaGrid.empty();
  const { siguiente } = calcularProgreso();
  const consulta = buscador.value.trim().replace(/^#/, "");
  const archivo = filtro.value || "todo";
  const ejemplaresFiltrados = ejemplares.filter(ejemplar => (!consulta || ejemplar.numero.includes(consulta)) && (
    archivo === "todo" || (archivo === "pendientes" && !ejemplar.leido) || (archivo === "leidos" && ejemplar.leido) ||
    (archivo === "eventos" && ejemplar.marcasDeEventos.length) || (archivo === "sinarchivo" && !ejemplar.uriArchivo)));
  const paginas = Math.max(1, Math.ceil(ejemplaresFiltrados.length / POR_PAGINA));
  if (estadoVista.pagina === null) {
    const indicePendiente = ejemplaresFiltrados.findIndex(ejemplar => !ejemplar.leido);
    estadoVista.pagina = indicePendiente >= 0 ? Math.floor(indicePendiente / POR_PAGINA) : 0;
  }
  estadoVista.pagina = Math.min(estadoVista.pagina, paginas - 1);

  zonaGrid.createDiv({ text: ejemplaresFiltrados.length ? `${ejemplaresFiltrados.length} número${ejemplaresFiltrados.length === 1 ? "" : "s"}` : "No hay resultados",
                       attr: { style: "font-size:0.8em;color:var(--text-muted);margin-bottom:8px" } });
  const cuadricula = zonaGrid.createDiv({ attr: { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(76px,1fr));gap:8px" } });
  for (const ejemplar of ejemplaresFiltrados.slice(estadoVista.pagina * POR_PAGINA, (estadoVista.pagina + 1) * POR_PAGINA)) {
    const esSig = siguiente === ejemplar;
    const fondo = ejemplar.leido ? "var(--interactive-accent)" : "var(--background-secondary)";
    const color = ejemplar.leido ? "var(--text-on-accent)" : "var(--text-normal)";
    const borde = esSig ? "2px solid var(--interactive-accent)"
                : (ejemplar.uriArchivo ? "1px solid var(--background-modifier-border)" : "1px dashed var(--background-modifier-border)");
    const textoAyuda = `#${ejemplar.numero}` + (ejemplar.marcasDeEventos.length ? " · 📌 " + ejemplar.marcasDeEventos.map(marca => marca.nombre + (marca.posicion ? ` (posición ${marca.posicion} de ${marca.total})` : "")).join(" · ") : "")
                + (ejemplar.uriArchivo ? "" : " · sin archivo");
    const recuadro = cuadricula.createDiv({ attr: { title: textoAyuda, style:
      `position:relative;padding:10px 4px 8px;border-radius:10px;text-align:center;background:${fondo};color:${color};border:${borde};` +
      `cursor:${ejemplar.uriArchivo ? "pointer" : "default"};opacity:${(ejemplar.uriArchivo || ejemplar.leido) ? 1 : 0.6}` } });
    recuadro.createDiv({ text: "#" + ejemplar.numero, attr: { style: "font-weight:700;font-size:1.05em" } });
    recuadro.createDiv({ text: [ejemplar.marcasDeEventos.length ? "📌" : "", ejemplar.uriArchivo ? "" : "❌", esSig ? "▶" : ""].filter(Boolean).join(" ") || "\u00a0",
                  attr: { style: "font-size:0.75em;min-height:1.3em" } });
    const casillaLeido = recuadro.createDiv({ text: ejemplar.leido ? "✔" : "○", attr: { title: ejemplar.leido ? "Marcar como no leído" : "Marcar como leído",
                              style: "position:absolute;top:3px;right:6px;font-size:0.85em;cursor:pointer;opacity:0.9" } });
    casillaLeido.onclick = (clic) => { clic.stopPropagation(); alternarLeidoEjemplar(ejemplar); };
    recuadro.onclick = () => { if (ejemplar.uriArchivo) abrirArchivo(ejemplar.uriArchivo); };
  }
  dibujarPaginador(zonaGrid, estadoVista.pagina, paginas, (numeroPagina) => { estadoVista.pagina = numeroPagina; dibujarCuadriculaDeNumeros(); });
}

// ================= Eventos relacionados =================
function dibujarEventos() {
  zonaEv.empty();
  const mapa = new Map();
  for (const ejemplar of ejemplares) for (const marca of ejemplar.marcasDeEventos) {
    const claveEvento = marca.ruta || marca.nombre;
    if (!mapa.has(claveEvento)) mapa.set(claveEvento, { ...marca, numeros: [], posiciones: [] });
    const registroEvento = mapa.get(claveEvento);
    registroEvento.numeros.push(ejemplar);
    if (marca.posicion) registroEvento.posiciones.push(marca.posicion);
  }
  if (!mapa.size) return;
  zonaEv.createEl("h2", { text: `📌 Eventos relacionados (${mapa.size})`, attr: { style: "margin-top:1.6em" } });
  const cuadricula = zonaEv.createDiv({ attr: { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px" } });
  for (const registroEvento of mapa.values()) {
    const tarjetaEvento = cuadricula.createDiv({ attr: { style: ESTILO_CAJA + ";padding:12px;display:flex;flex-direction:column;gap:6px" } });
    const titulo = tarjetaEvento.createDiv({ attr: { style: "font-weight:700" } });
    if (registroEvento.ruta) crearEnlaceInterno(titulo, registroEvento.ruta, registroEvento.nombre); else titulo.setText(registroEvento.nombre);
    if (!registroEvento.ruta) tarjetaEvento.createDiv({ text: "Evento que no tienes agregado", attr: { style: "font-size:0.75em;color:var(--text-muted)" } });
    tarjetaEvento.createDiv({ text: "En este cómic: " + agruparEnRangos(registroEvento.numeros.map(ejemplar => ejemplar.numero), "#"), attr: { style: "font-size:0.85em" } });
    if (registroEvento.posiciones.length) tarjetaEvento.createDiv({ text: `Posiciones en el evento: ${agruparEnRangos(registroEvento.posiciones, "")} de ${registroEvento.total}`, attr: { style: "font-size:0.8em;color:var(--text-muted)" } });
    const leidos = registroEvento.numeros.filter(ejemplar => ejemplar.leido).length;
    const filaBarra = tarjetaEvento.createDiv({ attr: { style: "display:flex;align-items:center;gap:6px;font-size:0.75em;color:var(--text-muted)" } });
    const fondo = filaBarra.createDiv({ attr: { style: "flex:1;height:6px;border-radius:3px;background:var(--background-modifier-border);overflow:hidden" } });
    fondo.createDiv({ attr: { style: `height:100%;width:${Math.round(100 * leidos / registroEvento.numeros.length)}%;background:var(--interactive-accent)` } });
    filaBarra.createSpan({ text: `${leidos}/${registroEvento.numeros.length}` });
  }
}

// ================= Dibujar =================
function dibujarTodo() {
  tituloNum.setText(`Números (${ejemplares.length})`);
  dibujarCabecera();
  dibujarAviso();
  dibujarCuadriculaDeNumeros();
  dibujarEventos();
}
buscador.oninput = () => { estadoVista.consulta = buscador.value; estadoVista.pagina = 0; dibujarCuadriculaDeNumeros(); };
filtro.onchange = () => { estadoVista.filtro = filtro.value; estadoVista.pagina = 0; dibujarCuadriculaDeNumeros(); };
dibujarTodo();
