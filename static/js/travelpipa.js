/* TravelPipa — small progressive enhancements. The site works without JavaScript. */
(function () {
  "use strict";
  document.documentElement.classList.remove("no-js");

  // Header style after scrolling
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Discreet reveal on scroll
  var items = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && items.length) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    items.forEach(function (el) { observer.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add("is-visible"); });
  }

  // Gallery lightbox (uses a Bootstrap modal)
  var modalEl = document.getElementById("galleryModal");
  if (modalEl && window.bootstrap) {
    var modal = new bootstrap.Modal(modalEl);
    var img = modalEl.querySelector("img");
    var caption = modalEl.querySelector(".gallery-caption");
    var links = Array.prototype.slice.call(document.querySelectorAll("[data-gallery]"));
    var index = 0;
    var show = function (i) {
      index = (i + links.length) % links.length;
      var link = links[index];
      img.src = link.getAttribute("href");
      img.alt = link.dataset.alt || "";
      if (caption) caption.textContent = (index + 1) + " / " + links.length;
    };
    links.forEach(function (link, i) {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        show(i);
        modal.show();
      });
    });
    modalEl.querySelectorAll("[data-gallery-nav]").forEach(function (btn) {
      btn.addEventListener("click", function () { show(index + parseInt(btn.dataset.galleryNav, 10)); });
    });
    modalEl.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") show(index + 1);
      if (e.key === "ArrowLeft") show(index - 1);
    });
  }

  // Booking form: one-way / round-trip choice only for transfers
  var tripBox = document.querySelector("[data-trip-options]");
  if (tripBox) {
    var select = document.getElementById("id_experience");
    var returnBox = tripBox.querySelector("[data-return-date]");
    var returnInput = returnBox ? returnBox.querySelector("input") : null;
    var radios = tripBox.querySelectorAll("input[type=radio]");
    var syncTrip = function () {
      var option = select && select.options[select.selectedIndex];
      var isTransfer = !!(option && option.getAttribute("data-transfer"));
      tripBox.hidden = !isTransfer;
      var round = false;
      radios.forEach(function (r) { if (r.checked && r.value === "round_trip") round = true; });
      var showReturn = isTransfer && round;
      if (returnBox) returnBox.hidden = !showReturn;
      if (returnInput) returnInput.required = showReturn;
    };
    if (select) select.addEventListener("change", syncTrip);
    radios.forEach(function (r) { r.addEventListener("change", syncTrip); });
    syncTrip();
  }

  // Prevent double submission of forms
  document.querySelectorAll("form[data-once]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var btn = form.querySelector("[type=submit]");
      if (btn && form.checkValidity()) {
        setTimeout(function () { btn.disabled = true; btn.classList.add("disabled"); }, 0);
      }
    });
  });

  // Load small HTML fragments (weather/tide widgets) without delaying the page
  document.querySelectorAll("[data-fragment]").forEach(function (box) {
    if (!window.fetch) return;
    fetch(box.getAttribute("data-fragment"), { headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) { if (html && html.trim()) { box.innerHTML = html; } })
      .catch(function () { /* keep the fallback link */ });
  });

  // Focus the first invalid field after a failed submission
  var invalid = document.querySelector(".is-invalid");
  if (invalid) { invalid.focus({ preventScroll: false }); }
})();
