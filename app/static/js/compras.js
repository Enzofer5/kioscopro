/* Carga de compras a proveedores. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const root = $("#compra");
  if (!root) return;
  let items = [];

  const pintar = () => {
    const tb = $("#items");
    tb.innerHTML = "";
    let total = 0;
    items.forEach((it, i) => {
      const sub = KP.round2(it.cantidad * it.precio);
      total += sub;
      const tr = document.createElement("tr");
      tr.innerHTML = `<td><b></b><div class="xsmall muted mono"></div></td><td class="num muted"></td>
        <td class="num"><input type="text" inputmode="decimal" data-f="cantidad" data-i="${i}" style="width:90px;text-align:right" aria-label="Cantidad"></td>
        <td class="num"><input type="text" inputmode="decimal" data-f="precio" data-i="${i}" style="width:120px;text-align:right" aria-label="Precio"></td>
        <td class="num"><b></b></td>
        <td class="actions"><button type="button" class="btn btn-ghost btn-icon btn-sm" data-quitar="${i}" aria-label="Quitar">${KP.icon("trash-2", "sm")}</button></td>`;
      tr.querySelector("td b").textContent = it.nombre;
      tr.querySelector("td .mono").textContent = it.codigo || "";
      tr.children[1].textContent = it.costo != null ? KP.money(it.costo) : "—";
      tr.querySelector('[data-f="cantidad"]').value = KP.qty(it.cantidad);
      tr.querySelector('[data-f="precio"]').value = String(it.precio).replace(".", ",");
      tr.children[4].querySelector("b").textContent = KP.money(sub);
      tb.appendChild(tr);
    });
    $("#total").textContent = KP.money(total);
    $("#vacio").classList.toggle("hidden", items.length > 0);
    $("#confirmar").disabled = !items.length;
  };

  $("#items").addEventListener("change", (e) => {
    const el = e.target, it = items[+el.dataset.i];
    if (!it) return;
    const n = KP.parseNum(el.value);
    if (el.dataset.f === "cantidad") it.cantidad = Number.isFinite(n) && n > 0 ? n : 1;
    if (el.dataset.f === "precio") it.precio = Number.isFinite(n) && n >= 0 ? KP.round2(n) : 0;
    pintar();
  });
  $("#items").addEventListener("click", (e) => {
    const b = e.target.closest("[data-quitar]");
    if (b) { items.splice(+b.dataset.quitar, 1); pintar(); }
  });

  const buscar = $("#buscar");
  KP.autocomplete(buscar, {
    fetch: async (q) => (await KP.api(`${root.dataset.apiProductos}?q=${encodeURIComponent(q)}`)).productos,
    render: (p) => `<div class="grow"><b>${KP.esc(p.nombre)}</b><span>${KP.esc(p.codigo || "Sin código")} · Stock ${KP.esc(KP.qty(p.stock))}</span></div><span class="price">${KP.esc(KP.money(p.costo ?? 0))}</span>`,
    onSelect: (p) => {
      const ex = items.find((x) => x.id === p.id);
      if (ex) ex.cantidad += 1;
      else items.push({ id: p.id, nombre: p.nombre, codigo: p.codigo, costo: p.costo ?? null, cantidad: 1, precio: p.costo ?? 0 });
      buscar.value = "";
      pintar();
      const inputs = document.querySelectorAll(`[data-f="cantidad"]`);
      inputs[ex ? items.indexOf(ex) : items.length - 1]?.select();
    },
  });

  $("#confirmar").addEventListener("click", async () => {
    if (!$("#proveedor").value) { KP.toast("Elegí el proveedor.", "danger"); $("#proveedor").focus(); return; }
    const total = items.reduce((a, it) => a + KP.round2(it.cantidad * it.precio), 0);
    if (!(await KP.confirm(`¿Confirmar la compra por ${KP.money(total)}? Se sumará el stock de ${items.length} producto(s).`))) return;
    const btn = $("#confirmar");
    btn.disabled = true;
    try {
      const r = await KP.api(root.dataset.apiConfirmar, {
        proveedor_id: $("#proveedor").value,
        fecha: $("#fecha").value,
        numero_comprobante: $("#comprobante").value,
        observaciones: $("#obs").value,
        actualizar_costos: $("#actualizar-costos").checked,
        items: items.map((it) => ({ producto_id: it.id, cantidad: it.cantidad, precio: it.precio })),
      });
      location.href = r.url;
    } catch (err) {
      KP.toast(err.message, "danger");
      btn.disabled = false;
    }
  });
  pintar();
})();
