/* Gráficos con Chart.js. Los datos llegan en <script type="application/json" id="datos-graficos">
   y cada <canvas data-chart="nombre"> indica qué gráfico dibujar. */
(function () {
  "use strict";
  const nodo = document.getElementById("datos-graficos");
  if (!nodo || !window.Chart) return;
  const D = JSON.parse(nodo.textContent);

  const C = {
    brand: "#0d7a5c", brandSoft: "rgba(13,122,92,.14)", accent: "#f0a012", accentSoft: "rgba(240,160,18,.18)",
    red: "#c23a2f", blue: "#2860a8", grid: "#eceee9", text: "#56625c",
  };
  const PALETA = ["#0d7a5c", "#f0a012", "#2860a8", "#c23a2f", "#7a5bc2", "#3aa6a0", "#8a8f3a", "#d06b9c"];
  const money = (v) => "$ " + new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 }).format(v);
  const moneyTip = (ctx) => ` ${ctx.dataset.label || ctx.label}: ${window.KP ? KP.money(ctx.parsed.y ?? ctx.parsed) : ctx.formattedValue}`;

  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.font.size = 12;
  Chart.defaults.color = C.text;
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.boxHeight = 12;
  Chart.defaults.maintainAspectRatio = false;

  const ejes = (dinero = true) => ({
    x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
    y: { beginAtZero: true, grid: { color: C.grid }, border: { display: false }, ticks: { callback: (v) => (dinero ? money(v) : v) } },
  });

  const builders = {
    ultimos7: (d) => ({
      type: "bar",
      data: {
        labels: d.labels,
        datasets: [
          { label: "Ventas", data: d.ventas, backgroundColor: C.brand, borderRadius: 6, maxBarThickness: 38 },
          { label: "Ganancia bruta", data: d.ganancia, backgroundColor: C.accent, borderRadius: 6, maxBarThickness: 38 },
        ],
      },
      options: { scales: ejes(), plugins: { tooltip: { callbacks: { label: moneyTip } } } },
    }),
    metodos: (d) => ({
      type: "doughnut",
      data: { labels: d.labels, datasets: [{ data: d.valores, backgroundColor: PALETA, borderWidth: 2, borderColor: "#fff" }] },
      options: {
        cutout: "62%",
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${KP.money(ctx.parsed)}` } },
        },
      },
    }),
    top: (d) => ({
      type: "bar",
      data: { labels: d.labels, datasets: [{ label: "Unidades", data: d.valores, backgroundColor: C.brand, borderRadius: 5, maxBarThickness: 22 }] },
      options: {
        indexAxis: "y",
        scales: { x: { beginAtZero: true, grid: { color: C.grid } }, y: { grid: { display: false }, ticks: { callback: function (v) { const l = this.getLabelForValue(v); return l.length > 24 ? l.slice(0, 23) + "…" : l; } } } },
        plugins: { legend: { display: false } },
      },
    }),
    ganancias: (d) => ({
      type: "bar",
      data: {
        labels: d.labels,
        datasets: [
          { type: "line", label: "Ganancia neta", data: d.neta, borderColor: C.blue, backgroundColor: C.blue, tension: 0.3, pointRadius: 3, order: 0 },
          { label: "Ganancia bruta", data: d.bruta, backgroundColor: C.brand, borderRadius: 5, maxBarThickness: 34, order: 1 },
          { label: "Gastos", data: d.gastos, backgroundColor: "rgba(194,58,47,.75)", borderRadius: 5, maxBarThickness: 34, order: 1 },
        ],
      },
      options: { scales: ejes(), plugins: { tooltip: { callbacks: { label: moneyTip } } } },
    }),
    ventasDiarias: (d) => ({
      type: "line",
      data: {
        labels: d.labels,
        datasets: [{ label: "Facturación", data: d.ventas, borderColor: C.brand, backgroundColor: C.brandSoft, fill: true, tension: 0.3, pointRadius: d.labels.length > 31 ? 0 : 3 }],
      },
      options: { scales: ejes(), plugins: { legend: { display: false }, tooltip: { callbacks: { label: moneyTip } } } },
    }),
    pagos: (d) => ({
      type: "bar",
      data: { labels: d.labels, datasets: [{ label: "Total", data: d.valores, backgroundColor: PALETA, borderRadius: 6, maxBarThickness: 48 }] },
      options: { scales: ejes(), plugins: { legend: { display: false }, tooltip: { callbacks: { label: moneyTip } } } },
    }),
  };

  document.querySelectorAll("canvas[data-chart]").forEach((cv) => {
    const nombre = cv.dataset.chart;
    const fuente = cv.dataset.source || nombre;
    if (!builders[nombre] || !D[fuente]) return;
    const vacio = (D[fuente].labels || []).length === 0;
    if (vacio) {
      cv.parentElement.innerHTML = '<div class="empty"><p class="small mb-0">Sin datos para el período.</p></div>';
      return;
    }
    new Chart(cv, builders[nombre](D[fuente]));
  });
})();
