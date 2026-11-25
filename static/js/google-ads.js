/* TravelPipa — Google tag for Google Ads, plus a conversion each time a visitor
   clicks a WhatsApp link (header, floating button, tour pages, contact page...).
   Only loaded when settings.GOOGLE_ADS_ENABLED is on. Kept out of inline <script>
   so the Content-Security-Policy can stay strict. */
(function () {
  "use strict";
  var me = document.currentScript;
  if (!me || !me.dataset.id) return;

  window.dataLayer = window.dataLayer || [];
  if (!window.gtag) {
    window.gtag = function () { window.dataLayer.push(arguments); };
  }
  window.gtag("js", new Date());
  window.gtag("config", me.dataset.id);

  var sendTo = me.dataset.whatsapp;
  if (!sendTo) return;

  var WHATSAPP = /^https:\/\/(wa\.me|api\.whatsapp\.com|chat\.whatsapp\.com)\//i;
  var counted = false;  // one conversion per page view is enough for a lead

  function onClick(event) {
    var link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
    if (!link || counted || !WHATSAPP.test(link.href)) return;
    counted = true;
    // WhatsApp opens in a new tab (target="_blank"), so the page stays and the hit is sent.
    window.gtag("event", "conversion", { send_to: sendTo, transport_type: "beacon" });
  }

  document.addEventListener("click", onClick, true);
  document.addEventListener("auxclick", onClick, true);  // middle click / open in new tab
})();
