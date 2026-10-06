
// ================= Utilidades =================
const datos = JSON.parse(await dv.io.load("__DATOS__"));
const raiz = dv.container;

function tareasDelEvento(evento) {
  const resultado = [];
  for (const [nota, idBloque] of evento.numeros) {
    const paginaComic = dv.page(nota);
    const tarea = paginaComic ? paginaComic.file.tasks.find(tarea => tarea.blockId === idBloque || (tarea.text || "").includes("^" + idBloque)) : null;
    if (tarea) resultado.push(tarea);
  }
  return resultado;
}

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

function dibujarBarraDeProgreso(padre, leidos, total) {
  const filaBarra = padre.createDiv({ attr: { style: "display:flex;align-items:center;gap:6px;font-size:0.75em;color:var(--text-muted)" } });
  const fondo = filaBarra.createDiv({ attr: { style: "flex:1;height:6px;border-radius:3px;background:var(--background-modifier-border);overflow:hidden" } });
  const porcentaje = total ? Math.round(100 * leidos / total) : 0;
  fondo.createDiv({ attr: { style: `height:100%;width:${porcentaje}%;background:var(--interactive-accent)` } });
  filaBarra.createSpan({ text: `${leidos}/${total}` });
}

function textoNumero(tarea) {
  return (tarea.text || "")
    .replace(/\s*·\s*📌.*$/, "")
    .replace(/\[([^\]]+)\]\(<[^>]*>\)/g, "$1")
    .replace(/\s*❌/, "")
    .replace(/\s*\^[\w-]+\s*$/, "")
    .trim();
}

function uriDelNumero(tarea) {
  const coincidencia = (tarea.text || "").match(/\]\(<(file:[^>]+)>\)/);
  return coincidencia ? coincidencia[1] : null;
}

function abrirArchivo(uriArchivo) {
  try { require("electron").shell.openExternal(uriArchivo); } catch (error) { window.open(uriArchivo); }
}

async function marcarLeido(tarea) {
  const archivo = app.vault.getAbstractFileByPath(tarea.path);
  if (!archivo) return;
  const idBloque = tarea.blockId || ((tarea.text || "").match(/\^([\w-]+)\s*$/) || [])[1];
  await app.vault.process(archivo, (texto) => {
    const lineas = texto.split("\n");
    let indiceLinea = (typeof tarea.line === "number" && /^\s*(>\s*)*- \[ \]/.test(lineas[tarea.line] || "") &&
             (!idBloque || lineas[tarea.line].includes("^" + idBloque))) ? tarea.line : -1;
    if (indiceLinea < 0 && idBloque) indiceLinea = lineas.findIndex(linea => /^\s*(>\s*)*- \[ \]/.test(linea) && linea.includes("^" + idBloque));
    if (indiceLinea >= 0) lineas[indiceLinea] = lineas[indiceLinea].replace("- [ ]", "- [x]");
    return lineas.join("\n");
  });
}

function titulo(texto) {
  raiz.createEl("h2", { text: texto, attr: { style: "margin-top:1.6em" } });
}

// ================= Datos =================
const eventos = datos.orden.map(nombreEvento => {
  const evento = datos.eventos[nombreEvento];
  const paginaEvento = dv.page(evento.nota);
  const tareas = tareasDelEvento(evento);
  return { evento, pagina: paginaEvento, tareas, leidos: tareas.filter(tarea => tarea.completed).length, total: evento.numeros.length };
});
const comics = dv.pages(`"${datos.comics}"`).sort(paginaComic => paginaComic.file.name).array().map(paginaComic => {
  const tareas = paginaComic.file.tasks.array ? paginaComic.file.tasks.array() : paginaComic.file.tasks;
  return { pagina: paginaComic, tareas, leidos: tareas.filter(tarea => tarea.completed).length, total: tareas.length };
});

// ================= 1. Continuar leyendo =================
// 1) Toma el cómic donde marcaste algo más recientemente y, dentro de él, el último número marcado.
// 2) Si ese número es parte de uno de tus eventos, sigue el ORDEN DEL EVENTO (siguiente sin marcar).
// 3) Si no es parte de un evento (o el evento ya está completo), sigue el orden del CÓMIC.
const eventosDeNumero = {};   // "nota|bloque" -> eventos donde aparece ese número
for (const registroEvento of eventos) {
  for (const [nota, idBloque] of registroEvento.evento.numeros) (eventosDeNumero[`${nota}|${idBloque}`] ||= []).push(registroEvento);
}
const quitarExtensionMd = (ruta) => ruta.replace(/\.md$/, "");

let siguiente = null;
const tocados = comics.filter(registroComic => registroComic.leidos > 0)
  .sort((primero, segundo) => Number(segundo.pagina.file.mtime) - Number(primero.pagina.file.mtime));
for (const registroComic of tocados) {
  const marcados = registroComic.tareas.filter(tarea => tarea.completed);
  const ultimo = marcados[marcados.length - 1];
  const idBloque = ultimo && (ultimo.blockId || ((ultimo.text || "").match(/\^([\w-]+)\s*$/) || [])[1]);
  const eventosDelNumero = eventosDeNumero[`${quitarExtensionMd(registroComic.pagina.file.path)}|${idBloque}`] || [];
  for (const registroEvento of eventosDelNumero) {
    const tarea = registroEvento.tareas.find(tarea => !tarea.completed);
    if (tarea) { siguiente = { tarea, origen: registroComic.pagina.file.name, rutaOrigen: registroComic.pagina.file.path, portadaOrigen: registroEvento.pagina && registroEvento.pagina.banner }; break; }
  }
  if (siguiente) break;
  const tarea = registroComic.tareas.find(tarea => !tarea.completed);
  if (tarea) { siguiente = { tarea, origen: registroComic.pagina.file.name, rutaOrigen: registroComic.pagina.file.path, portadaOrigen: registroComic.pagina.banner }; break; }
}
// Si todavía no has marcado nada, parte por el primer número de tus eventos
if (!siguiente) {
  for (const registroEvento of eventos) {
    const tarea = registroEvento.tareas.find(tarea => !tarea.completed);
    if (tarea) { siguiente = { tarea, origen: registroEvento.evento.nombre_visible, rutaOrigen: registroEvento.evento.nota, portadaOrigen: registroEvento.pagina && registroEvento.pagina.banner }; break; }
  }
}

if (siguiente) {
  const pagComic = dv.page(siguiente.tarea.path);
  const portada = urlDeImagen(pagComic && pagComic.banner) || urlDeImagen(siguiente.portadaOrigen);
  const tarjetaContinuar = raiz.createDiv({ attr: { style:
    "display:flex;gap:18px;padding:16px;border-radius:12px;background:var(--background-secondary);" +
    "border:1px solid var(--background-modifier-border);align-items:center;margin-bottom:6px" } });
  const contenedorPortada = tarjetaContinuar.createDiv({ attr: { style:
    "width:110px;min-width:110px;aspect-ratio:2/3;border-radius:8px;overflow:hidden;" +
    "background:var(--background-modifier-border);display:flex;align-items:center;justify-content:center;font-size:2.5em" } });
  if (portada) contenedorPortada.createEl("img", { attr: { src: portada, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
  else contenedorPortada.setText("📖");
  contenedorPortada.setAttr("style", contenedorPortada.getAttr("style") + ";cursor:pointer");
  contenedorPortada.onclick = () => app.workspace.openLinkText(pagComic ? pagComic.file.path : siguiente.rutaOrigen, "", false);

  const columnaInfo = tarjetaContinuar.createDiv({ attr: { style: "display:flex;flex-direction:column;gap:6px;flex:1" } });
  columnaInfo.createDiv({ text: "CONTINUAR LEYENDO", attr: { style: "font-size:0.75em;letter-spacing:0.12em;color:var(--text-muted)" } });
  columnaInfo.createDiv({ text: textoNumero(siguiente.tarea), attr: { style: "font-size:1.35em;font-weight:700" } });
  const linea = columnaInfo.createDiv({ attr: { style: "font-size:0.9em;color:var(--text-muted)" } });
  linea.appendText("Cómic: ");
  const pagNum = dv.page(siguiente.tarea.path);
  if (pagNum) crearEnlaceInterno(linea, pagNum.file.path, pagNum.file.name);
  else crearEnlaceInterno(linea, siguiente.rutaOrigen, siguiente.origen);
  const marcas = (siguiente.tarea.text || "").split("· 📌 ").slice(1).join("").replace(/\s*\^[\w-]+\s*$/, "").split(" · ").filter(texto => texto.trim());
  if (marcas.length) {
    const lineaEventos = columnaInfo.createDiv({ attr: { style: "font-size:0.9em;color:var(--text-muted)" } });
    lineaEventos.appendText("📌 Parte de: ");
    marcas.forEach((marca, indiceLinea) => {
      if (indiceLinea) lineaEventos.appendText(" · ");
      const coincidencia = marca.match(/\[\[([^\]|]+)\|?([^\]]*)\]\](.*)/);
      if (coincidencia) { crearEnlaceInterno(lineaEventos, coincidencia[1], coincidencia[2] || coincidencia[1]); lineaEventos.appendText(coincidencia[3]); }
      else lineaEventos.appendText(marca.trim());
    });
  }

  const botones = columnaInfo.createDiv({ attr: { style: "display:flex;gap:8px;margin-top:6px;align-items:center;flex-wrap:wrap" } });
  const uriArchivo = uriDelNumero(siguiente.tarea);
  if (uriArchivo) {
    const botonLeer = botones.createEl("button", { text: "📖 Leer", cls: "mod-cta" });
    botonLeer.onclick = () => abrirArchivo(uriArchivo);
  }
  const marcar = botones.createEl("button", { text: "✔ Marcar como leído" });
  marcar.onclick = async () => {
    marcar.disabled = true;
    marcar.setText("Marcando…");
    await marcarLeido(siguiente.tarea);   // Dataview vuelve a dibujar la página y aparece el siguiente número
  };
  if (!uriArchivo) botones.createSpan({ text: "❌ No tienes este archivo", attr: { style: "font-size:0.85em;color:var(--text-muted)" } });
} else {
  raiz.createDiv({ text: "🎉 No tienes nada pendiente", attr: { style: "padding:16px;border-radius:12px;background:var(--background-secondary)" } });
}

// ================= 2. Resumen =================
const totalLeidos = comics.reduce((suma, registroComic) => suma + registroComic.leidos, 0);
const totalNumeros = comics.reduce((suma, registroComic) => suma + registroComic.total, 0);
const enCurso = comics.filter(registroComic => registroComic.leidos > 0 && registroComic.leidos < registroComic.total).length;
const terminados = comics.filter(registroComic => registroComic.total > 0 && registroComic.leidos === registroComic.total).length;
const resumen = raiz.createDiv({ attr: { style: "display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:18px 0" } });
for (const [valor, etiqueta] of [[`${totalLeidos}/${totalNumeros}`, "números leídos"], [eventos.length, "eventos"],
                                 [enCurso, "cómics en curso"], [terminados, "cómics terminados"]]) {
  const cajaResumen = resumen.createDiv({ attr: { style: "padding:10px;border-radius:10px;background:var(--background-secondary);text-align:center" } });
  cajaResumen.createDiv({ text: String(valor), attr: { style: "font-size:1.4em;font-weight:700" } });
  cajaResumen.createDiv({ text: etiqueta, attr: { style: "font-size:0.75em;color:var(--text-muted)" } });
}

// ================= 3. Biblioteca (buscador, filtro y páginas) =================
const POR_PAGINA = 12;        // tarjetas por página en la biblioteca
const POR_PAGINA_PJ = 16;     // personajes por página

function normalizarTexto(texto) { return (texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); }
function estadoSegunProgreso(leidos, total) { return total > 0 && leidos === total ? "terminado" : (leidos > 0 ? "curso" : "empezar"); }
const ETIQUETA = { evento: "⚡ Evento", curso: "📖 En curso", empezar: "🆕 Por empezar", terminado: "✅ Terminado" };
const ORDEN_ESTADO = { curso: 0, empezar: 1, terminado: 2 };

const biblioteca = [
  ...eventos.map(registroEvento => ({ tipo: "evento", estado: estadoSegunProgreso(registroEvento.leidos, registroEvento.total), ruta: registroEvento.evento.nota, nombre: registroEvento.evento.nombre_visible,
                         portada: registroEvento.pagina && registroEvento.pagina.banner, leidos: registroEvento.leidos, total: registroEvento.total,
                         textoAnios: (registroEvento.evento.anios_evento && registroEvento.evento.anios_evento[0]) ? (registroEvento.evento.anios_evento[0] === registroEvento.evento.anios_evento[1] ? String(registroEvento.evento.anios_evento[0]) : `${registroEvento.evento.anios_evento[0]}–${registroEvento.evento.anios_evento[1]}`) : "" })),
  ...comics.map(registroComic => ({ tipo: "comic", estado: estadoSegunProgreso(registroComic.leidos, registroComic.total), ruta: registroComic.pagina.file.path, nombre: registroComic.pagina.file.name,
                        portada: registroComic.pagina.banner, leidos: registroComic.leidos, total: registroComic.total })),
].sort((primero, segundo) => (primero.tipo === segundo.tipo ? 0 : primero.tipo === "evento" ? -1 : 1)
              || (ORDEN_ESTADO[primero.estado] - ORDEN_ESTADO[segundo.estado]) || primero.nombre.localeCompare(segundo.nombre));

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

function dibujarTarjeta(contenedor, elemento) {
  const recuadroTarjeta = contenedor.createDiv({ attr: { style: "background:var(--background-secondary);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;position:relative" } });
  recuadroTarjeta.createDiv({ text: ETIQUETA[elemento.tipo === "evento" ? "evento" : elemento.estado], attr: { style:
    "position:absolute;top:6px;left:6px;font-size:0.65em;padding:2px 6px;border-radius:6px;background:var(--background-primary);opacity:0.9" } });
  const contenedorPortada = recuadroTarjeta.createDiv({ attr: { style: "aspect-ratio:2/3;background:var(--background-modifier-border);display:flex;align-items:center;justify-content:center;font-size:2em;cursor:pointer" } });
  const imagen = urlDeImagen(elemento.portada);
  if (imagen) contenedorPortada.createEl("img", { attr: { src: imagen, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
  else contenedorPortada.setText(elemento.tipo === "evento" ? "⚡" : "📚");
  contenedorPortada.onclick = () => app.workspace.openLinkText(elemento.ruta, "", false);
  const columnaInfo = recuadroTarjeta.createDiv({ attr: { style: "padding:6px 8px 8px;display:flex;flex-direction:column;gap:4px" } });
  crearEnlaceInterno(columnaInfo, elemento.ruta, elemento.nombre, "font-size:0.8em;font-weight:600;line-height:1.25");
  if (elemento.textoAnios) columnaInfo.createDiv({ text: "📅 " + elemento.textoAnios, attr: { style: "font-size:0.7em;color:var(--text-muted)" } });
  dibujarBarraDeProgreso(columnaInfo, elemento.leidos, elemento.total);
}

titulo("📚 Biblioteca");
const controles = raiz.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px" } });
const buscador = controles.createEl("input", { attr: { type: "search", placeholder: "🔎 Buscar por nombre…", style: "flex:1;min-width:180px" } });
const filtro = controles.createEl("select", { cls: "dropdown" });
for (const [valor, texto] of [["todo", "Todo"], ["evento", "⚡ Eventos"], ["curso", "📖 Cómics en curso"],
                              ["empezar", "🆕 Cómics por empezar"], ["terminado", "✅ Cómics terminados"]]) {
  filtro.createEl("option", { text: texto, attr: { value: valor } });
}
const zona = raiz.createDiv();
let numeroPaginaActual = 0;

function dibujarBiblioteca() {
  zona.empty();
  const consulta = normalizarTexto(buscador.value.trim());
  const filtroElegido = filtro.value || "todo";
  const elementosFiltrados = biblioteca.filter(elemento => (!consulta || normalizarTexto(elemento.nombre).includes(consulta))
    && (filtroElegido === "todo" || (filtroElegido === "evento" ? elemento.tipo === "evento" : (elemento.tipo === "comic" && elemento.estado === filtroElegido))));
  const paginas = Math.max(1, Math.ceil(elementosFiltrados.length / POR_PAGINA));
  numeroPaginaActual = Math.min(numeroPaginaActual, paginas - 1);
  zona.createDiv({ text: elementosFiltrados.length ? `${elementosFiltrados.length} resultado${elementosFiltrados.length === 1 ? "" : "s"}` : "No hay resultados",
                   attr: { style: "font-size:0.8em;color:var(--text-muted);margin-bottom:8px" } });
  const contenedor = zona.createDiv({ attr: { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:14px" } });
  for (const elemento of elementosFiltrados.slice(numeroPaginaActual * POR_PAGINA, (numeroPaginaActual + 1) * POR_PAGINA)) dibujarTarjeta(contenedor, elemento);
  dibujarPaginador(zona, numeroPaginaActual, paginas, (numeroPagina) => { numeroPaginaActual = numeroPagina; dibujarBiblioteca(); });
}
buscador.oninput = () => { numeroPaginaActual = 0; dibujarBiblioteca(); };
filtro.onchange = () => { numeroPaginaActual = 0; dibujarBiblioteca(); };
dibujarBiblioteca();

// ================= 4. Personajes (con buscador y páginas) =================
const personajes = dv.pages().where(paginaPersonaje => paginaPersonaje.tipo === "personaje" || (paginaPersonaje.file.folder || "").endsWith("Personajes"))
  .sort(paginaPersonaje => paginaPersonaje.file.name).array();
if (personajes.length) {
  titulo(`👤 Personajes (${personajes.length})`);
  const buscaPj = raiz.createEl("input", { attr: { type: "search", placeholder: "🔎 Buscar personaje…", style: "width:100%;margin-bottom:10px" } });
  const zonaPj = raiz.createDiv();
  let paginaPj = 0;
  function dibujarPersonajes() {
    zonaPj.empty();
    const consulta = normalizarTexto(buscaPj.value.trim());
    const personajesFiltrados = personajes.filter(paginaPersonaje => !consulta || normalizarTexto(paginaPersonaje.file.name).includes(consulta));
    const paginas = Math.max(1, Math.ceil(personajesFiltrados.length / POR_PAGINA_PJ));
    paginaPj = Math.min(paginaPj, paginas - 1);
    const filaBarra = zonaPj.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:16px" } });
    for (const personaje of personajesFiltrados.slice(paginaPj * POR_PAGINA_PJ, (paginaPj + 1) * POR_PAGINA_PJ)) {
      const recuadroPersonaje = filaBarra.createDiv({ attr: { style: "display:flex;flex-direction:column;align-items:center;gap:4px;width:72px;cursor:pointer" } });
      const avatar = recuadroPersonaje.createDiv({ attr: { style: "width:60px;height:60px;border-radius:50%;overflow:hidden;background:var(--background-secondary);display:flex;align-items:center;justify-content:center;font-size:1.4em;border:2px solid var(--interactive-accent)" } });
      const imagen = urlDeImagen(personaje.imagen);
      if (imagen) avatar.createEl("img", { attr: { src: imagen, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
      else avatar.setText(personaje.file.name.charAt(0));
      recuadroPersonaje.createDiv({ text: personaje.file.name, attr: { style: "font-size:0.75em;text-align:center;line-height:1.2" } });
      recuadroPersonaje.onclick = () => app.workspace.openLinkText(personaje.file.path, "", false);
    }
    if (!personajesFiltrados.length) filaBarra.createDiv({ text: "No hay resultados", attr: { style: "font-size:0.8em;color:var(--text-muted)" } });
    dibujarPaginador(zonaPj, paginaPj, paginas, (numeroPagina) => { paginaPj = numeroPagina; dibujarPersonajes(); });
  }
  buscaPj.oninput = () => { paginaPj = 0; dibujarPersonajes(); };
  dibujarPersonajes();
}
