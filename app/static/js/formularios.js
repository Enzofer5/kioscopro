/* Formulario de producto: cálculo de margen en vivo. */
(function () {
  "use strict";
  const c = document.getElementById("precio_compra");
  const v = document.getElementById("precio_venta");
  const m = document.getElementById("margen");
  if (!c || !v || !m) return;
  const calc = () => {
    const pc = KP.parseNum(c.value), pv = KP.parseNum(v.value);
    if (!(pc > 0) || !Number.isFinite(pv)) { m.value = "—"; return; }
    const pct = ((pv - pc) / pc) * 100;
    m.value = `${pct.toFixed(1).replace(".", ",")} %  (${KP.money(pv - pc)} por unidad)`;
    m.style.color = pct < 0 ? "var(--danger)" : "";
  };
  c.addEventListener("input", calc);
  v.addEventListener("input", calc);
  calc();
})();
