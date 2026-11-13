/* TravelPipa management panel — small enhancements. Everything also works without JavaScript. */
(function () {
  "use strict";

  function csrf() {
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    var input = document.querySelector("input[name=csrfmiddlewaretoken]");
    return m ? decodeURIComponent(m[1]) : (input ? input.value : "");
  }

  var toastEl = document.getElementById("panelToast");
  function toast(text) {
    if (!toastEl || !window.bootstrap) return;
    toastEl.querySelector(".toast-body").textContent = text;
    bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 2500 }).show();
  }

  // Filters that apply as soon as an option is picked (no inline handlers: CSP)
  document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
    select.addEventListener("change", function () { select.form.submit(); });
  });

  // On/off switches: save immediately without reloading the page
  document.querySelectorAll("form[data-toggle]").forEach(function (form) {
    var input = form.querySelector("input[type=checkbox]");
    var noscriptBtn = form.querySelector("button[type=submit]");
    if (noscriptBtn) noscriptBtn.hidden = true;
    if (!input) return;
    input.addEventListener("change", function () {
      var body = new FormData(form);
      body.set("value", input.checked ? "1" : "0");
      input.disabled = true;
      fetch(form.action, { method: "POST", body: body, headers: { "X-Requested-With": "fetch", "X-CSRFToken": csrf() } })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (data) {
          input.checked = !!data.value;
          var row = form.closest("[data-row]");
          if (row && form.dataset.toggle === "active") row.classList.toggle("off", !data.value);
          toast(data.message);
        })
        .catch(function () { input.checked = !input.checked; toast("Não foi possível salvar. Tente de novo."); })
        .finally(function () { input.disabled = false; });
    });
  });

  // Confirm destructive buttons
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) { if (!window.confirm(el.dataset.confirm)) e.preventDefault(); });
  });

  // Drag and drop to reorder photos
  var grid = document.querySelector("[data-photo-grid]");
  if (grid) {
    var dragged = null;
    grid.querySelectorAll(".photo").forEach(function (card) {
      card.setAttribute("draggable", "true");
      card.addEventListener("dragstart", function (e) { dragged = card; card.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
      card.addEventListener("dragend", function () { card.classList.remove("dragging"); grid.querySelectorAll(".drop-target").forEach(function (c) { c.classList.remove("drop-target"); }); });
      card.addEventListener("dragover", function (e) { e.preventDefault(); if (card !== dragged) card.classList.add("drop-target"); });
      card.addEventListener("dragleave", function () { card.classList.remove("drop-target"); });
      card.addEventListener("drop", function (e) {
        e.preventDefault(); card.classList.remove("drop-target");
        if (!dragged || dragged === card) return;
        var cards = Array.prototype.slice.call(grid.children);
        if (cards.indexOf(dragged) < cards.indexOf(card)) card.after(dragged); else card.before(dragged);
        var order = Array.prototype.map.call(grid.querySelectorAll(".photo"), function (c) { return parseInt(c.dataset.id, 10); });
        grid.querySelectorAll(".photo .num").forEach(function (n, i) { n.textContent = i + 1; });
        fetch(grid.dataset.reorderUrl, {
          method: "POST", headers: { "Content-Type": "application/json", "X-Requested-With": "fetch", "X-CSRFToken": csrf() },
          body: JSON.stringify({ order: order })
        }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
          .then(function (d) { toast(d.message); })
          .catch(function () { toast("Não foi possível salvar a ordem. Recarregue a página."); });
      });
    });
  }

  // Show the names of the photos chosen for upload
  document.querySelectorAll("input[type=file][multiple]").forEach(function (input) {
    var out = document.querySelector("[data-files-for='" + input.id + "']");
    if (!out) return;
    input.addEventListener("change", function () {
      out.textContent = input.files.length ? input.files.length + " foto(s) selecionada(s)" : "";
    });
  });

  // Keep the language tab open after saving (remember last tab)
  document.querySelectorAll("[data-bs-toggle=tab]").forEach(function (tab) {
    tab.addEventListener("shown.bs.tab", function () { try { sessionStorage.setItem("panelTab", tab.getAttribute("data-bs-target")); } catch (e) {} });
  });
  try {
    var last = sessionStorage.getItem("panelTab");
    var btn = last && document.querySelector("[data-bs-target='" + last + "']");
    if (btn && window.bootstrap) bootstrap.Tab.getOrCreateInstance(btn).show();
  } catch (e) {}

  // Open the tab that contains the first error
  var firstError = document.querySelector(".is-invalid");
  if (firstError && window.bootstrap) {
    var pane = firstError.closest(".tab-pane");
    if (pane) {
      var trigger = document.querySelector("[data-bs-target='#" + pane.id + "']");
      if (trigger) bootstrap.Tab.getOrCreateInstance(trigger).show();
    }
    var collapse = firstError.closest(".collapse");
    if (collapse) bootstrap.Collapse.getOrCreateInstance(collapse, { toggle: false }).show();
    setTimeout(function () { firstError.focus(); }, 150);
  }
})();
