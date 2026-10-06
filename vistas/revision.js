
// Revisar mi biblioteca: qué cómics tienes y cuáles faltan. Los datos los calcula el programa al actualizar las notas.
const raiz = dv.container;
const ESTILO_CAJA = "background:var(--background-secondary);border:1px solid var(--background-modifier-border);border-radius:12px";
const ESTADO_ENTRE_REFRESCOS = (window.__vistaRevision ||= { tab: "faltantes", consulta: "", completos: false });

function crearEnlaceInterno(padre, ruta, texto, estilo) {
  const ancla = padre.createEl("a", { text: texto, cls: "internal-link", href: ruta });
  ancla.setAttr("data-href", ruta);
  if (estilo) ancla.setAttr("style", estilo);
  ancla.onclick = (clic) => { clic.preventDefault(); app.workspace.openLinkText(ruta, "", false); };
  return ancla;
}
function dibujarBarraDeProgreso(padre, hechos, total, alto) {
  const fondo = padre.createDiv({ attr: { style: `height:${alto}px;border-radius:${alto / 2}px;background:var(--background-modifier-border);overflow:hidden` } });
  fondo.createDiv({ attr: { style: `height:100%;width:${total ? Math.round(100 * hechos / total) : 0}%;background:var(--interactive-accent)` } });
}
function normalizarTexto(texto) { return (texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); }
function dibujarListaDeTexto(padre, filas, maximo) {
  const listaHtml = padre.createEl("ul", { attr: { style: "margin:6px 0 0 0;padding-left:20px" } });
  for (const linea of filas.slice(0, maximo)) listaHtml.createEl("li", { text: linea, attr: { style: "font-size:0.85em" } });
  if (filas.length > maximo) padre.createDiv({ text: `… y ${filas.length - maximo} más`, attr: { style: "font-size:0.8em;color:var(--text-muted)" } });
}

let revision = null;
try { revision = JSON.parse(await dv.io.load("__REVISION__")); } catch (error) { revision = null; }

if (!revision) {
  raiz.createDiv({ text: "⚠️ Todavía no hay datos. Elige «Actualizar notas» (opción 1) en el programa y vuelve a abrir esta página.", attr: { style: ESTILO_CAJA + ";padding:12px" } });
} else {
  const resumen = revision.resumen;
  const zonaCab = raiz.createDiv();
  const tabs = raiz.createDiv({ attr: { style: "display:flex;gap:8px;margin:18px 0 8px;flex-wrap:wrap" } });
  const zonaCtrl = raiz.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px" } });
  const zonaContenido = raiz.createDiv();

  // ---- tarjeta principal
  const tarjetaPrincipal = zonaCab.createDiv({ attr: { style: ESTILO_CAJA + ";padding:16px;display:flex;flex-direction:column;gap:8px" } });
  tarjetaPrincipal.createDiv({ text: "REVISAR MI BIBLIOTECA", attr: { style: "font-size:0.75em;letter-spacing:0.12em;color:var(--text-muted)" } });
  if (!revision.tiene_carpeta) {
    tarjetaPrincipal.createDiv({ text: "Aún no indicas la carpeta donde guardas tus cómics. Configúrala en el programa, en «Configuración → Carpetas de cómics de este PC», y aquí verás qué te falta." });
  } else {
    const porcentaje = resumen.numeros ? Math.round(100 * resumen.con_archivo / resumen.numeros) : 0;
    const filaPorcentaje = tarjetaPrincipal.createDiv({ attr: { style: "display:flex;align-items:baseline;gap:10px" } });
    filaPorcentaje.createDiv({ text: `${porcentaje}%`, attr: { style: "font-size:1.8em;font-weight:700" } });
    filaPorcentaje.createDiv({ text: `de tus números tienen archivo (${resumen.con_archivo} de ${resumen.numeros})`, attr: { style: "color:var(--text-muted)" } });
    dibujarBarraDeProgreso(tarjetaPrincipal, resumen.con_archivo, resumen.numeros, 10);
    const chips = tarjetaPrincipal.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:6px" } });
    for (const texto of [`✅ ${resumen.con_archivo} con archivo`, `❌ ${resumen.numeros - resumen.con_archivo} faltan`, resumen.sin_emparejar ? `❓ ${resumen.sin_emparejar} sin emparejar` : null,
                      resumen.aproximados ? `≈ ${resumen.aproximados} por aproximación` : null, revision.avisos.length ? `⚠️ ${revision.avisos.length} aviso(s)` : null].filter(Boolean)) {
      chips.createSpan({ text: texto, attr: { style: "font-size:0.75em;padding:2px 8px;border-radius:10px;background:var(--background-modifier-border)" } });
    }
  }
  tarjetaPrincipal.createDiv({ text: `Revisado el ${revision.generado}. Se actualiza al elegir «Actualizar notas» (opción 1) en el programa.`, attr: { style: "font-size:0.75em;color:var(--text-muted)" } });

  // ---- pestañas
  const TABS = [["faltantes", "❌ Faltantes"], ["sin", `❓ Sin emparejar (${revision.sin_emparejar.length})`],
                ["aprox", `≈ Por aproximación (${revision.aproximados.length})`], ["avisos", `⚠️ Avisos (${revision.avisos.length})`]];
  const botones = {};
  for (const [idPestana, texto] of TABS) {
    botones[idPestana] = tabs.createEl("button", { text: texto });
    botones[idPestana].onclick = () => { ESTADO_ENTRE_REFRESCOS.tab = idPestana; dibujarPagina(); };
  }

  function dibujarTarjetaDeRevision(contenedor, elemento) {
    const tarjetaElemento = contenedor.createDiv({ attr: { style: ESTILO_CAJA + ";padding:10px;display:flex;flex-direction:column;gap:6px" } });
    const cab = tarjetaElemento.createDiv({ attr: { style: "display:flex;justify-content:space-between;gap:8px;align-items:baseline" } });
    crearEnlaceInterno(cab, elemento.nota, elemento.nombre_visible || elemento.nombre, "font-weight:600");
    cab.createSpan({ text: `${elemento.con_archivo}/${elemento.total}`, attr: { style: "font-size:0.8em;color:var(--text-muted)" } });
    dibujarBarraDeProgreso(tarjetaElemento, elemento.con_archivo, elemento.total, 6);
    if (elemento.faltan.length) {
      const detalles = tarjetaElemento.createEl("details");
      detalles.createEl("summary", { text: `Ver lo que falta (${elemento.total - elemento.con_archivo} número${elemento.total - elemento.con_archivo === 1 ? "" : "s"})`, attr: { style: "cursor:pointer;font-size:0.85em" } });
      dibujarListaDeTexto(detalles, elemento.faltan, 200);
    } else {
      tarjetaElemento.createDiv({ text: "✅ Lo tienes todo", attr: { style: "font-size:0.8em;color:var(--text-muted)" } });
    }
  }

  function dibujarPagina() {
    for (const [idPestana] of TABS) { if (idPestana === ESTADO_ENTRE_REFRESCOS.tab) botones[idPestana].addClass("mod-cta"); else botones[idPestana].removeClass("mod-cta"); }
    zonaCtrl.empty();
    zonaContenido.empty();
    if (ESTADO_ENTRE_REFRESCOS.tab === "faltantes") {
      const buscador = zonaCtrl.createEl("input", { attr: { type: "search", placeholder: "🔎 Buscar evento o cómic…", style: "flex:1;min-width:160px" } });
      buscador.value = ESTADO_ENTRE_REFRESCOS.consulta;
      const etiqueta = zonaCtrl.createEl("label", { attr: { style: "font-size:0.85em;display:flex;gap:6px;align-items:center" } });
      const casillaCompletos = etiqueta.createEl("input", { attr: { type: "checkbox" } });
      casillaCompletos.checked = ESTADO_ENTRE_REFRESCOS.completos;
      etiqueta.appendText("Mostrar también los completos");
      const pintar = () => {
        zonaContenido.empty();
        const consulta = normalizarTexto(ESTADO_ENTRE_REFRESCOS.consulta);
        for (const [titulo, items] of [["⚡ Eventos", revision.eventos], ["📖 Cómics", revision.comics]]) {
          const filtrados = items.filter(elemento => (ESTADO_ENTRE_REFRESCOS.completos || elemento.faltan.length) && (!consulta || normalizarTexto(elemento.nombre_visible || elemento.nombre).includes(consulta)));
          if (!filtrados.length) continue;
          zonaContenido.createEl("h2", { text: `${titulo} (${filtrados.length})`, attr: { style: "margin-top:1em" } });
          const contenedor = zonaContenido.createDiv({ attr: { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px" } });
          for (const elemento of filtrados) dibujarTarjetaDeRevision(contenedor, elemento);
        }
        if (!zonaContenido.children || !zonaContenido.children.length) zonaContenido.createDiv({ text: ESTADO_ENTRE_REFRESCOS.completos || ESTADO_ENTRE_REFRESCOS.consulta ? "No hay resultados." : "🎉 No te falta ningún número.", attr: { style: "padding:10px" } });
      };
      buscador.oninput = () => { ESTADO_ENTRE_REFRESCOS.consulta = buscador.value; pintar(); };
      casillaCompletos.onchange = () => { ESTADO_ENTRE_REFRESCOS.completos = casillaCompletos.checked; pintar(); };
      pintar();
    } else if (ESTADO_ENTRE_REFRESCOS.tab === "sin") {
      zonaContenido.createDiv({ text: "Archivos de tu carpeta que el programa no pudo asociar a ningún número de tus eventos o cómics. Para decirle cuál es cada uno sin renombrarlo, usa «Configuración → Emparejar a mano» en el programa.",
                       attr: { style: "font-size:0.85em;color:var(--text-muted);margin-bottom:8px" } });
      if (revision.sin_emparejar.length) dibujarListaDeTexto(zonaContenido, revision.sin_emparejar, 300); else zonaContenido.createDiv({ text: "🎉 Todos tus archivos están emparejados." });
    } else if (ESTADO_ENTRE_REFRESCOS.tab === "aprox") {
      zonaContenido.createDiv({ text: "Archivos que el programa asoció por parecido de nombre. Revisa que estén bien; si alguno está mal, corrígelo con «Emparejar a mano».",
                       attr: { style: "font-size:0.85em;color:var(--text-muted);margin-bottom:8px" } });
      if (revision.aproximados.length) dibujarListaDeTexto(zonaContenido, revision.aproximados.map(aproximado => `${aproximado.archivo}  →  ${aproximado.destino}`), 300); else zonaContenido.createDiv({ text: "Ninguno." });
    } else {
      if (revision.avisos.length) dibujarListaDeTexto(zonaContenido, revision.avisos, 100); else zonaContenido.createDiv({ text: "🎉 Sin avisos." });
    }
  }
  dibujarPagina();
}
