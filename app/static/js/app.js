/* KioscoPro — utilidades comunes (sin dependencias).
   Nunca se inserta HTML con datos del usuario sin escapar: se usa textContent o KP.esc(). */
(function () {
  "use strict";

  const KP = (window.KP = {});
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || "";
  const ICONS = document.querySelector('link[rel="stylesheet"]')?.href.replace(/css\/app\.css.*$/, "img/icons.svg") || "/static/img/icons.svg";

  KP.esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  KP.icon = (name, cls = "") => `<svg class="i ${cls}" aria-hidden="true"><use href="${ICONS}#i-${name}"></use></svg>`;

  const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  KP.money = (n) => "$ " + fmt.format(Number(n) || 0);
  KP.qty = (n) => new Intl.NumberFormat("es-AR", { maximumFractionDigits: 3 }).format(Number(n) || 0);
  /** Convierte "1.234,56" / "1234.56" a número. */
  KP.parseNum = (v) => {
    if (typeof v === "number") return v;
    let s = String(v ?? "").trim().replace(/\$|\s/g, "");
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : NaN;
  };
  KP.round2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100;

  /** fetch JSON con token CSRF. Devuelve {ok, ...} o lanza Error con el mensaje del servidor. */
  KP.api = async (url, data, method) => {
    const opts = { method: method || (data ? "POST" : "GET"), headers: { Accept: "application/json" }, credentials: "same-origin" };
    if (data) {
      opts.headers["Content-Type"] = "application/json";
      opts.headers["X-CSRFToken"] = csrf();
      opts.body = JSON.stringify(data);
    }
    let resp;
    try {
      resp = await fetch(url, opts);
    } catch (e) {
      throw new Error("No hay conexión con el servidor.");
    }
    if (resp.redirected && resp.url.includes("/auth/login")) throw new Error("Tu sesión expiró. Volvé a iniciar sesión.");
    let json = null;
    try { json = await resp.json(); } catch (e) { /* respuesta no JSON */ }
    if (!resp.ok || !json || json.ok === false) throw new Error((json && json.error) || `Error ${resp.status}`);
    return json;
  };

  KP.debounce = (fn, ms = 200) => {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  };

  /* ---------------------------------------------------------- Toast */
  KP.toast = (msg, tipo = "info") => {
    let box = document.getElementById("kp-toasts");
    if (!box) {
      box = document.createElement("div");
      box.id = "kp-toasts";
      box.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:100;display:flex;flex-direction:column;gap:8px;max-width:min(380px,calc(100vw - 32px))";
      document.body.appendChild(box);
    }
    const el = document.createElement("div");
    el.className = `alert alert-${tipo}`;
    el.style.boxShadow = "var(--shadow-lg)";
    el.innerHTML = KP.icon(tipo === "success" ? "circle-check" : tipo === "danger" ? "circle-x" : "info");
    const span = document.createElement("span");
    span.textContent = msg;
    el.appendChild(span);
    box.appendChild(el);
    setTimeout(() => el.remove(), tipo === "danger" ? 6000 : 3200);
  };

  /* ---------------------------------------------------------- Confirmación */
  KP.confirm = (texto, { ok = "Confirmar", peligro = false } = {}) =>
    new Promise((resolve) => {
      const dlg = document.createElement("dialog");
      dlg.className = "modal";
      dlg.innerHTML = `<div class="modal-head"><h2>Confirmar</h2></div>
        <div class="modal-body"><p class="mb-0"></p></div>
        <div class="modal-foot"><button type="button" class="btn" data-r="0">Cancelar</button>
        <button type="button" class="btn ${peligro ? "btn-danger" : "btn-primary"}" data-r="1"></button></div>`;
      dlg.querySelector("p").textContent = texto;
      dlg.querySelector('[data-r="1"]').textContent = ok;
      document.body.appendChild(dlg);
      const fin = (v) => { dlg.close(); dlg.remove(); resolve(v); };
      dlg.addEventListener("click", (e) => {
        const b = e.target.closest("[data-r]");
        if (b) fin(b.dataset.r === "1");
        else if (e.target === dlg) fin(false);
      });
      dlg.addEventListener("cancel", (e) => { e.preventDefault(); fin(false); });
      dlg.showModal();
      dlg.querySelector('[data-r="1"]').focus();
    });

  /* ---------------------------------------------------------- Autocompletar genérico
     KP.autocomplete(input, { fetch: async (q) => items[], render: (item) => html, onSelect: (item) => {} }) */
  KP.autocomplete = (input, cfg) => {
    const wrap = input.closest(".ac") || input.parentElement;
    const list = document.createElement("div");
    list.className = "ac-list";
    list.setAttribute("role", "listbox");
    wrap.appendChild(list);
    let items = [], sel = -1, ultimo = "";

    const cerrar = () => { list.classList.remove("open"); sel = -1; };
    const pintar = () => {
      if (!items.length) {
        list.innerHTML = `<div class="ac-empty">${KP.esc(cfg.vacio || "Sin resultados")}</div>`;
      } else {
        list.innerHTML = items.map((it, i) => `<div class="ac-item ${i === sel ? "sel" : ""}" data-i="${i}" role="option">${cfg.render(it)}</div>`).join("");
      }
      list.classList.add("open");
    };
    const elegir = (i) => {
      const it = items[i];
      if (!it) return;
      cerrar();
      cfg.onSelect(it);
    };
    const buscar = KP.debounce(async () => {
      const q = input.value.trim();
      if (q.length < (cfg.min ?? 1)) { cerrar(); return; }
      ultimo = q;
      try {
        const res = await cfg.fetch(q);
        if (q !== ultimo) return;
        items = res; sel = res.length ? 0 : -1; pintar();
      } catch (e) { KP.toast(e.message, "danger"); }
    }, cfg.delay ?? 180);

    input.addEventListener("input", buscar);
    input.addEventListener("keydown", (e) => {
      if (!list.classList.contains("open")) return;
      if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(items.length - 1, sel + 1); pintar(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); pintar(); }
      else if (e.key === "Enter" && sel >= 0 && !cfg.enterPropio) { e.preventDefault(); elegir(sel); }
      else if (e.key === "Escape") { cerrar(); }
    });
    list.addEventListener("mousedown", (e) => {
      const it = e.target.closest(".ac-item");
      if (it) { e.preventDefault(); elegir(+it.dataset.i); }
    });
    input.addEventListener("blur", () => setTimeout(cerrar, 150));
    return {
      cerrar,
      abierta: () => list.classList.contains("open"),
      seleccionado: () => (sel >= 0 ? items[sel] : null),
      elegirActual: () => elegir(sel),
    };
  };

  /* ---------------------------------------------------------- Comportamiento global */
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-action]");
    if (t) {
      const a = t.dataset.action;
      if (a === "toggle-nav") document.body.classList.toggle("nav-open");
      if (a === "close-nav") document.body.classList.remove("nav-open");
      if (a === "dismiss") t.closest(".alert")?.remove();
      if (a === "toggle-dropdown") {
        const dd = t.nextElementSibling;
        const abierto = dd.classList.toggle("open");
        t.setAttribute("aria-expanded", abierto);
        e.stopPropagation();
        return;
      }
      if (a === "open-modal") document.getElementById(t.dataset.target)?.showModal();
      if (a === "close-modal") t.closest("dialog")?.close();
      if (a === "print") window.print();
      if (a === "back") history.back();
    }
    document.querySelectorAll(".dropdown.open").forEach((d) => {
      if (!d.contains(e.target)) d.classList.remove("open");
    });
  });

  // Formularios que piden confirmación: <form data-confirm="texto">
  document.addEventListener("submit", async (e) => {
    const f = e.target;
    if (f.dataset.confirm && !f.dataset.confirmado) {
      e.preventDefault();
      const peligro = /anul|elimin|desactiv|borr|baja/i.test(f.dataset.confirm);
      if (await KP.confirm(f.dataset.confirm, { peligro })) {
        f.dataset.confirmado = "1";
        f.requestSubmit ? f.requestSubmit(e.submitter) : f.submit();
      }
      return;
    }
    // Evita doble envío
    const btn = e.submitter || f.querySelector('[type="submit"]');
    if (btn && !f.dataset.multi) setTimeout(() => (btn.disabled = true), 0);
  });

  // Filtros: no enviar parámetros vacíos (URLs limpias)
  document.querySelectorAll("form[data-clean]").forEach((f) =>
    f.addEventListener("submit", () => f.querySelectorAll("input,select").forEach((el) => { if (!el.value) el.disabled = true; }))
  );

  // Atajo global: F9 = nueva venta
  document.addEventListener("keydown", (e) => {
    if (e.key === "F9") {
      const link = document.querySelector(".pos-link");
      if (link && !location.pathname.endsWith("/ventas/pos")) { e.preventDefault(); location.href = link.href; }
    }
  });

  // Mostrar/ocultar bloques según un select/radio: data-show-when="nombre=valor"
  const toggles = () =>
    document.querySelectorAll("[data-show-when]").forEach((el) => {
      const [name, val] = el.dataset.showWhen.split("=");
      const ctrl = document.querySelector(`[name="${name}"]:checked, select[name="${name}"]`);
      const ok = ctrl && val.split("|").includes(ctrl.value);
      el.classList.toggle("hidden", !ok);
    });
  document.addEventListener("change", toggles);
  toggles();

  // Cierra alertas de éxito automáticamente
  setTimeout(() => document.querySelectorAll(".flashes .alert-success").forEach((a) => a.remove()), 6000);
})();
