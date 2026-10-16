/* Selector de producto del formulario de movimientos de stock. */
(function () {
  "use strict";
  const input = document.getElementById("buscar-prod");
  if (!input) return;
  const hidden = document.getElementById("producto_id");
  const box = document.getElementById("prod-elegido");
  const nombre = document.getElementById("prod-nombre");
  KP.autocomplete(input, {
    fetch: async (q) => (await KP.api(`${input.dataset.api}?q=${encodeURIComponent(q)}`)).productos,
    render: (p) => `<div class="grow"><b>${KP.esc(p.nombre)}</b><span>${KP.esc(p.codigo || "Sin código")}</span></div><span class="price">Stock ${KP.esc(KP.qty(p.stock))} ${KP.esc(p.unidad)}</span>`,
    onSelect: (p) => {
      hidden.value = p.id;
      nombre.textContent = `${p.nombre} — stock actual: ${KP.qty(p.stock)} ${p.unidad}`;
      box.classList.remove("hidden");
      input.value = "";
      document.getElementById("cantidad").focus();
    },
  });
  document.getElementById("form-mov").addEventListener("submit", (e) => {
    if (!hidden.value) { e.preventDefault(); e.stopImmediatePropagation(); KP.toast("Elegí un producto.", "danger"); input.focus(); }
  }, true);
})();
