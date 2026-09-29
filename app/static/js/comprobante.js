/* Comprobante: imprime automáticamente si se abrió con ?imprimir=1 */
(function () {
  "use strict";
  if (new URLSearchParams(location.search).get("imprimir") === "1") {
    window.addEventListener("load", () => setTimeout(() => window.print(), 250));
  }
  document.getElementById("cerrar-ventana")?.addEventListener("click", () => {
    if (window.opener) window.close(); else history.back();
  });
})();
