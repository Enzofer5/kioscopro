/* Cierre de caja: diferencia en vivo entre lo contado y lo esperado. */
(function () {
  "use strict";
  const f = document.getElementById("form-cierre");
  if (!f) return;
  const esperado = parseFloat(f.dataset.esperado) || 0;
  const input = document.getElementById("monto_declarado");
  const out = document.getElementById("diferencia");
  const calc = () => {
    const v = KP.parseNum(input.value);
    if (!Number.isFinite(v)) { out.textContent = "—"; out.className = "num"; return; }
    const d = KP.round2(v - esperado);
    out.textContent = (d > 0 ? "Sobrante " : d < 0 ? "Faltante " : "") + KP.money(Math.abs(d));
    out.className = "num " + (d < 0 ? "text-danger" : d > 0 ? "text-warning" : "text-success");
  };
  input.addEventListener("input", calc);
  calc();
})();
