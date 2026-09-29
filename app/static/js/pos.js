/* Punto de venta. El servidor recalcula todo: aquí solo se muestra una vista previa. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const root = $("#pos");
  if (!root) return;

  const API = { productos: root.dataset.apiProductos, clientes: root.dataset.apiClientes, confirmar: root.dataset.apiConfirmar };
  const bloqueado = root.dataset.bloqueado === "1";
  const CLAVE = "kp_pos_carrito";
  const r2 = KP.round2;

  let carrito = [];
  let cliente = null;
  let enviando = false;

  // ------------------------------------------------------------ persistencia (por si se recarga la página)
  const guardar = () => {
    try { sessionStorage.setItem(CLAVE, JSON.stringify({ carrito, cliente })); } catch (e) { /* sin storage */ }
  };
  try {
    const prev = JSON.parse(sessionStorage.getItem(CLAVE) || "null");
    if (prev && Array.isArray(prev.carrito)) { carrito = prev.carrito; cliente = prev.cliente || null; }
  } catch (e) { /* ignorar */ }

  // ------------------------------------------------------------ cálculo
  const metodoSel = () => document.querySelector('input[name="metodo"]:checked');
  const calcular = () => {
    let bruto = 0, descItems = 0;
    carrito.forEach((it) => {
      const b = r2(it.cantidad * it.precio);
      const d = r2((b * (it.desc || 0)) / 100);
      it._sub = b - d;
      bruto += b; descItems += d;
    });
    const neto = r2(bruto - descItems);
    const tipo = $("#desc-tipo").value;
    let v = KP.parseNum($("#desc-valor").value);
    if (!Number.isFinite(v) || v < 0) v = 0;
    let dg = tipo === "porcentaje" ? r2((neto * Math.min(v, 100)) / 100) : Math.min(r2(v), neto);
    const total = r2(neto - dg);
    return { bruto: r2(bruto), descuento: r2(descItems + dg), total };
  };

  // ------------------------------------------------------------ render
  const tbody = $("#carrito");
  const pintar = () => {
    tbody.innerHTML = "";
    carrito.forEach((it, i) => {
      const tr = document.createElement("tr");
      const sinStock = it.cantidad > it.stock;
      tr.innerHTML = `
        <td><b></b><div class="xsmall muted"></div>${sinStock ? '<span class="badge badge-danger mt-1">Stock: ' + KP.esc(KP.qty(it.stock)) + "</span>" : ""}</td>
        <td class="num"></td>
        <td class="center"><div class="qty">
          <button type="button" data-op="menos" data-i="${i}" aria-label="Restar">${KP.icon("minus", "sm")}</button>
          <input type="text" inputmode="decimal" data-op="cant" data-i="${i}" aria-label="Cantidad">
          <button type="button" data-op="mas" data-i="${i}" aria-label="Sumar">${KP.icon("plus", "sm")}</button></div></td>
        <td class="num hide-sm"><input type="text" class="desc" inputmode="decimal" data-op="desc" data-i="${i}" aria-label="Descuento %"></td>
        <td class="num"><b></b></td>
        <td class="actions"><button type="button" class="btn btn-ghost btn-icon btn-sm" data-op="quitar" data-i="${i}" aria-label="Quitar">${KP.icon("trash-2", "sm")}</button></td>`;
      tr.querySelector("td b").textContent = it.nombre;
      tr.querySelector("td .xsmall").textContent = [it.codigo, it.marca].filter(Boolean).join(" · ");
      tr.children[1].textContent = KP.money(it.precio);
      tr.querySelector('[data-op="cant"]').value = KP.qty(it.cantidad);
      tr.querySelector('[data-op="desc"]').value = it.desc ? String(it.desc).replace(".", ",") : "";
      tbody.appendChild(tr);
    });
    const t = calcular();
    carrito.forEach((it, i) => { tbody.children[i].children[4].querySelector("b").textContent = KP.money(it._sub); });
    $("#carrito-vacio").classList.toggle("hidden", carrito.length > 0);
    $("#cant-items").textContent = carrito.length;
    $("#t-subtotal").textContent = KP.money(t.bruto);
    $("#t-descuento").textContent = "− " + KP.money(t.descuento);
    $("#t-total").textContent = KP.money(t.total);
    $("#m-total").textContent = KP.money(t.total);
    $("#cobrar").disabled = bloqueado || !carrito.length || t.total <= 0;
    actualizarEfectivo(t.total);
    pintarCliente();
    guardar();
  };

  const actualizarEfectivo = (total) => {
    const m = metodoSel();
    const esEf = m && m.dataset.efectivo === "1";
    $("#bloque-efectivo").classList.toggle("hidden", !esEf);
    const rec = KP.parseNum($("#recibido").value);
    const v = $("#vuelto");
    if (Number.isFinite(rec) && rec > 0) {
      const vuelto = r2(rec - total);
      v.textContent = vuelto >= 0 ? KP.money(vuelto) : "Falta " + KP.money(-vuelto);
      v.style.color = vuelto >= 0 ? "" : "var(--danger)";
    } else { v.textContent = "—"; v.style.color = ""; }
    // Billetes sugeridos
    const box = $("#billetes");
    box.innerHTML = "";
    if (total > 0) {
      const opciones = new Set([total]);
      [1000, 2000, 10000, 20000].forEach((b) => opciones.add(Math.ceil(total / b) * b));
      [...opciones].sort((a, b) => a - b).slice(0, 4).forEach((val) => {
        const c = document.createElement("button");
        c.type = "button"; c.className = "chip"; c.dataset.monto = val;
        c.textContent = val === total ? "Justo" : KP.money(val).replace(",00", "");
        box.appendChild(c);
      });
    }
  };

  // ------------------------------------------------------------ carrito
  const agregar = (p, cantidad = 1) => {
    const ex = carrito.find((x) => x.id === p.id);
    if (ex) ex.cantidad = r2(ex.cantidad + cantidad);
    else carrito.unshift({ id: p.id, nombre: p.nombre, codigo: p.codigo, marca: p.marca, precio: p.precio, stock: p.stock, decimales: p.decimales, cantidad, desc: 0 });
    const item = ex || carrito[0];
    if (item.cantidad > p.stock) KP.toast(`Atención: stock disponible de «${p.nombre}»: ${KP.qty(p.stock)}`, "warning");
    item.stock = p.stock;
    item.precio = p.precio;
    pintar();
  };

  tbody.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-op]");
    if (!b) return;
    const it = carrito[+b.dataset.i];
    const paso = it.decimales ? 0.1 : 1;
    if (b.dataset.op === "mas") it.cantidad = r2(it.cantidad + paso);
    if (b.dataset.op === "menos") it.cantidad = Math.max(paso, r2(it.cantidad - paso));
    if (b.dataset.op === "quitar") carrito.splice(+b.dataset.i, 1);
    pintar();
  });
  tbody.addEventListener("change", (e) => {
    const el = e.target;
    const it = carrito[+el.dataset.i];
    if (!it) return;
    if (el.dataset.op === "cant") {
      let n = KP.parseNum(el.value);
      if (!Number.isFinite(n) || n <= 0) n = 1;
      if (!it.decimales) n = Math.max(1, Math.round(n));
      it.cantidad = Math.round(n * 1000) / 1000;
    }
    if (el.dataset.op === "desc") {
      let n = KP.parseNum(el.value);
      it.desc = Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : 0;
    }
    pintar();
  });
  tbody.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.matches("input")) { e.target.blur(); $("#buscar").focus(); }
  });

  $("#vaciar").addEventListener("click", async () => {
    if (!carrito.length) return;
    if (await KP.confirm("¿Vaciar el carrito?", { ok: "Vaciar", peligro: true })) { carrito = []; pintar(); $("#buscar").focus(); }
  });

  // ------------------------------------------------------------ búsqueda de productos
  const buscar = $("#buscar");
  const leerMultiplicador = (texto) => {
    const m = texto.match(/^(\d+(?:[.,]\d+)?)\s*\*\s*(.+)$/);
    return m ? { cant: KP.parseNum(m[1]), q: m[2].trim() } : { cant: 1, q: texto.trim() };
  };
  const pedir = async (q) => (await KP.api(`${API.productos}?q=${encodeURIComponent(q)}`)).productos;

  const acProd = KP.autocomplete(buscar, {
    enterPropio: true,
    fetch: (texto) => pedir(leerMultiplicador(texto).q),
    vacio: "No se encontraron productos",
    render: (p) => `<div class="grow"><b>${KP.esc(p.nombre)}</b><span>${KP.esc([p.codigo, p.marca].filter(Boolean).join(" · "))} · Stock ${KP.esc(KP.qty(p.stock))}</span></div>
                    <span class="price">${KP.esc(KP.money(p.precio))}</span>`,
    onSelect: (p) => {
      agregar(p, leerMultiplicador(buscar.value).cant || 1);
      buscar.value = "";
      buscar.focus();
    },
  });

  buscar.addEventListener("keydown", async (e) => {
    if (e.key === "Escape") { buscar.value = ""; acProd.cerrar(); return; }
    if (e.key !== "Enter") return;
    e.preventDefault();
    const texto = buscar.value.trim();
    if (!texto) { if (carrito.length) cobrar(); return; }
    const { cant, q } = leerMultiplicador(texto);
    if (acProd.abierta() && acProd.seleccionado()) { acProd.elegirActual(); return; }
    try {
      const res = await pedir(q);
      if (res.length === 1) { agregar(res[0], cant || 1); buscar.value = ""; acProd.cerrar(); }
      else if (!res.length) { KP.toast(`No se encontró «${q}»`, "danger"); buscar.select(); }
      else buscar.dispatchEvent(new Event("input"));
    } catch (err) { KP.toast(err.message, "danger"); }
  });

  // ------------------------------------------------------------ clientes
  const pintarCliente = () => {
    $("#cliente-elegido").classList.toggle("hidden", !cliente);
    $("#cliente-buscar").classList.toggle("hidden", !!cliente);
    $("#cliente-nombre").textContent = cliente ? cliente.nombre + (cliente.dni ? ` · DNI ${cliente.dni}` : "") : "";
  };
  const inputCli = $("#buscar-cliente");
  KP.autocomplete(inputCli, {
    min: 2,
    fetch: async (q) => (await KP.api(`${API.clientes}?q=${encodeURIComponent(q)}`)).clientes,
    vacio: "Sin coincidencias",
    render: (c) => `<div class="grow"><b>${KP.esc(c.nombre)}</b><span>${c.dni ? "DNI " + KP.esc(c.dni) : ""}</span></div>`,
    onSelect: (c) => { cliente = c; inputCli.value = ""; pintar(); buscar.focus(); },
  });
  $("#quitar-cliente").addEventListener("click", () => { cliente = null; pintar(); });

  const formCli = $("#form-cliente");
  if (formCli) {
    formCli.addEventListener("submit", async (e) => {
      e.preventDefault();
      const datos = Object.fromEntries(new FormData(formCli).entries());
      try {
        const r = await KP.api(API.clientes, datos);
        cliente = r.cliente;
        formCli.reset();
        formCli.closest("dialog").close();
        KP.toast("Cliente creado", "success");
        pintar();
      } catch (err) { KP.toast(err.message, "danger"); }
    });
  }

  // ------------------------------------------------------------ pago
  document.querySelectorAll('input[name="metodo"]').forEach((r) => r.addEventListener("change", pintar));
  $("#desc-valor").addEventListener("input", pintar);
  $("#desc-tipo").addEventListener("change", pintar);
  $("#recibido").addEventListener("input", () => actualizarEfectivo(calcular().total));
  $("#recibido").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); cobrar(); } });
  $("#billetes").addEventListener("click", (e) => {
    const c = e.target.closest("[data-monto]");
    if (!c) return;
    $("#recibido").value = String(c.dataset.monto).replace(".", ",");
    actualizarEfectivo(calcular().total);
  });

  const cobrar = async () => {
    if (enviando || bloqueado) return;
    if (!carrito.length) { KP.toast("El carrito está vacío.", "warning"); return; }
    const t = calcular();
    const m = metodoSel();
    const esEf = m.dataset.efectivo === "1";
    const rec = KP.parseNum($("#recibido").value);
    if (esEf && Number.isFinite(rec) && rec > 0 && rec < t.total) { KP.toast("El monto recibido es menor al total.", "danger"); $("#recibido").focus(); return; }
    enviando = true;
    $("#cobrar").disabled = true;
    try {
      const r = await KP.api(API.confirmar, {
        items: carrito.map((it) => ({ producto_id: it.id, cantidad: it.cantidad, descuento_pct: it.desc || 0 })),
        cliente_id: cliente ? cliente.id : null,
        metodo_pago: m.value,
        descuento_tipo: $("#desc-tipo").value,
        descuento_valor: KP.parseNum($("#desc-valor").value) || 0,
        monto_recibido: esEf && Number.isFinite(rec) && rec > 0 ? rec : null,
      });
      $("#exito-titulo").textContent = `Venta #${r.venta_id} registrada`;
      $("#exito-total").textContent = r.total_fmt;
      const v = $("#exito-vuelto");
      v.classList.toggle("hidden", !r.vuelto_fmt);
      v.textContent = r.vuelto_fmt ? "Vuelto: " + r.vuelto_fmt : "";
      $("#exito-imprimir").href = r.comprobante + "?imprimir=1";
      carrito = []; cliente = null;
      $("#desc-valor").value = ""; $("#recibido").value = "";
      document.querySelector('input[name="metodo"]').checked = true;
      pintar();
      $("#modal-exito").showModal();
      $("#exito-nueva").focus();
    } catch (err) {
      KP.toast(err.message, "danger");
    } finally {
      enviando = false;
      $("#cobrar").disabled = bloqueado || !carrito.length;
    }
  };
  $("#cobrar").addEventListener("click", cobrar);

  const nuevaVenta = () => { $("#modal-exito").close(); buscar.focus(); };
  $("#exito-nueva").addEventListener("click", nuevaVenta);
  $("#modal-exito").addEventListener("close", () => buscar.focus());

  // ------------------------------------------------------------ atajos
  document.addEventListener("keydown", (e) => {
    if (document.querySelector("dialog[open]") && e.key !== "F2") return;
    if (e.key === "F2") { e.preventDefault(); document.querySelector("dialog[open]")?.close(); buscar.focus(); buscar.select(); }
    if (e.key === "F4") { e.preventDefault(); cobrar(); }
  });

  pintar();
  if (bloqueado) buscar.placeholder = "Caja cerrada: abrí la caja para vender";
})();
