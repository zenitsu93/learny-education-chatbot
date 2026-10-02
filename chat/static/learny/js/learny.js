/* Learny · comportements de l'interface (sans dépendance hormis htmx). */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var reduit = function () {
    return document.documentElement.hasAttribute("data-reduce") ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  };

  function annoncer(texte) {
    var a = $("#annonce");
    if (!a) return;
    a.textContent = "";
    window.setTimeout(function () { a.textContent = texte; }, 50);
  }

  function toast(texte, ok) {
    var zone = $("#toasts");
    if (!zone) return;
    var t = document.createElement("div");
    t.className = "toast" + (ok ? " ok" : "");
    var s = document.createElement("span");
    s.textContent = texte;
    t.appendChild(document.createElement("span"));
    t.appendChild(s);
    zone.appendChild(t);
    fermerToastPlusTard(t);
  }

  function fermerToast(t) {
    if (!t || t.classList.contains("sortie")) return;
    t.classList.add("sortie");
    window.setTimeout(function () { t.remove(); }, reduit() ? 0 : 200);
  }

  function fermerToastPlusTard(t) {
    var minuteur = window.setTimeout(function () { fermerToast(t); }, 6000);
    // On ne ferme pas un message pendant qu'on le lit.
    t.addEventListener("mouseenter", function () { window.clearTimeout(minuteur); });
    t.addEventListener("focusin", function () { window.clearTimeout(minuteur); });
  }

  /* --- Notifications ------------------------------------------------------ */
  $$(".toast").forEach(fermerToastPlusTard);
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".toast-close");
    if (b) fermerToast(b.closest(".toast"));
  });

  /* --- Hors connexion ----------------------------------------------------- */
  var barre = $("#offline-bar");
  function majReseau() { if (barre) barre.hidden = navigator.onLine; }
  window.addEventListener("online", function () { majReseau(); toast("Connexion revenue.", true); });
  window.addEventListener("offline", majReseau);
  majReseau();

  /* --- Service worker ----------------------------------------------------- */
  var sw = document.body.getAttribute("data-sw");
  if (sw && "serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register(sw, { scope: "/" }).catch(function () {});
    });
  }

  // Téléphone partagé : à la déconnexion, on vide les pages gardées hors ligne.
  document.addEventListener("submit", function (e) {
    if (!/deconnexion/.test(e.target.getAttribute("action") || "")) return;
    if (window.caches && caches.keys) {
      caches.keys().then(function (cles) { cles.forEach(function (c) { caches.delete(c); }); });
    }
  });

  /* --- Dialogues ---------------------------------------------------------- */
  var declencheur = null;
  function fermerDialogue(d) {
    if (!d.open) return;
    if (reduit()) { d.close(); return; }
    d.classList.add("fermeture");
    window.setTimeout(function () { d.classList.remove("fermeture"); d.close(); }, 180);
  }
  document.addEventListener("click", function (e) {
    var ouvrir = e.target.closest("[data-dialog-open]");
    if (ouvrir) {
      var d = document.getElementById(ouvrir.getAttribute("data-dialog-open"));
      if (d && d.showModal) { declencheur = ouvrir; d.showModal(); }
      return;
    }
    var fermer = e.target.closest("[data-dialog-close]");
    if (fermer) { e.preventDefault(); fermerDialogue(fermer.closest("dialog")); return; }
    // Un clic sur le fond ferme le dialogue.
    if (e.target.tagName === "DIALOG" && e.target.classList.contains("dlg")) fermerDialogue(e.target);
  });
  $$("dialog.dlg").forEach(function (d) {
    d.addEventListener("cancel", function (e) { e.preventDefault(); fermerDialogue(d); });
    d.addEventListener("close", function () { if (declencheur) { declencheur.focus(); declencheur = null; } });
  });

  /* --- Inscription : règles du mot de passe ------------------------------- */
  $$("[data-rules-for]").forEach(function (liste) {
    var champ = document.getElementById(liste.getAttribute("data-rules-for"));
    if (!champ) return;
    var tests = { len: function (v) { return v.length >= 8; }, num: function (v) { return v.length > 0 && !/^\d+$/.test(v); } };
    champ.addEventListener("input", function () {
      $$("[data-r]", liste).forEach(function (li) {
        var t = tests[li.getAttribute("data-r")];
        li.classList.toggle("ok", !!(t && t(champ.value)));
      });
    });
  });

  /* --- Réglages : aperçu immédiat ----------------------------------------- */
  var taille = $("[data-apercu-taille]");
  var apercu = $("#apercu");
  if (taille && apercu) {
    var appliquer = function () { apercu.style.fontSize = (17 * Number(taille.value) / 100) + "px"; };
    taille.addEventListener("change", appliquer);
    appliquer();
  }

  /* --- Discussion --------------------------------------------------------- */
  var form = $("#composer");
  if (!form) return;
  var zone = $("#q", form);
  var envoyer = $(".send", form);
  var fil = $("#thread");
  var micro = $(".mic", form);
  var ecoute = $(".listening", form);

  function enBas() {
    fil.scrollTo({ top: fil.scrollHeight, behavior: reduit() ? "auto" : "smooth" });
  }
  function ajuster() {
    zone.style.height = "auto";
    zone.style.height = Math.min(zone.scrollHeight, 160) + "px";
    envoyer.disabled = !zone.value.trim();
  }
  zone.addEventListener("input", ajuster);
  zone.addEventListener("keydown", function (e) {
    // Entrée envoie, Maj + Entrée passe à la ligne. Pas d'envoi pendant une saisie IME.
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      if (zone.value.trim() && !envoyer.disabled) form.requestSubmit(envoyer);
    }
  });
  ajuster();
  enBas();

  $$("[data-suggest]").forEach(function (b) {
    b.addEventListener("click", function () {
      zone.value = b.textContent.trim();
      ajuster();
      zone.focus();
    });
  });

  // Bulle de l'élève et « Learny écrit… » affichées tout de suite, remplacées par la réponse.
  var attente = [];
  function bulleEleve(texte) {
    var m = document.createElement("div");
    m.className = "msg user";
    var b = document.createElement("div");
    b.className = "bubble";
    b.textContent = texte;
    m.appendChild(b);
    return m;
  }
  function bulleEcrit() {
    var m = document.createElement("div");
    m.className = "msg bot";
    m.innerHTML = '<span class="bot-av" aria-hidden="true"></span><div class="typing"><i></i><i></i><i></i><span>Learny écrit…</span></div>';
    return m;
  }
  function viderAttente() { attente.forEach(function (n) { n.remove(); }); attente = []; }

  document.body.addEventListener("htmx:beforeRequest", function (e) {
    var source = e.detail.elt;
    if (source !== form && !source.hasAttribute("data-retry")) return;
    var texte = source === form ? zone.value.trim() : ($("input[name=question]", source) || {}).value;
    if (!texte) return;
    var vide = $("#vide");
    if (vide) vide.remove();
    if (source.hasAttribute("data-retry")) {
      // On retire l'erreur et la question restée en suspens avant de renvoyer.
      var bloc = source.closest(".msg");
      var avant = bloc && bloc.previousElementSibling;
      if (avant && avant.classList.contains("user")) avant.remove();
      if (bloc) bloc.remove();
    }
    attente = [bulleEleve(texte), bulleEcrit()];
    attente.forEach(function (n) { fil.appendChild(n); });
    annoncer("Question envoyée. Learny prépare sa réponse.");
    if (source === form) { zone.value = ""; ajuster(); }
    enBas();
  });
  document.body.addEventListener("htmx:beforeSwap", function (e) {
    if (e.detail.target === fil) viderAttente();
  });
  document.body.addEventListener("htmx:afterSwap", function (e) {
    if (e.detail.target === fil) { enBas(); envoyer.disabled = !zone.value.trim(); }
  });
  // Réseau coupé ou serveur en panne : la question est remise dans la zone de saisie.
  function echec(e) {
    var source = e.detail.elt;
    if (source !== form && !source.hasAttribute("data-retry")) return;
    var texte = attente.length ? attente[0].textContent : "";
    viderAttente();
    if (texte && !zone.value) { zone.value = texte; ajuster(); }
    toast("La question n'est pas partie. Vérifie ta connexion puis renvoie-la.");
    annoncer("La question n'est pas partie.");
  }
  document.body.addEventListener("htmx:sendError", echec);
  document.body.addEventListener("htmx:responseError", echec);

  /* Outils sous chaque réponse : écouter, copier. */
  var parle = null;
  fil.addEventListener("click", function (e) {
    var copier = e.target.closest("[data-copier]");
    if (copier) {
      var texte = copier.closest(".msg").querySelector(".bubble").innerText;
      var fait = function () { toast("Réponse copiée.", true); };
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(texte).then(fait, function () {});
      else {
        var t = document.createElement("textarea");
        t.value = texte; document.body.appendChild(t); t.select();
        try { document.execCommand("copy"); fait(); } catch (err) { /* rien */ }
        t.remove();
      }
      return;
    }
    var ecouter = e.target.closest("[data-ecouter]");
    if (ecouter) {
      if (!("speechSynthesis" in window)) { toast("La lecture à voix haute ne marche pas sur ce navigateur."); return; }
      var etait = ecouter.getAttribute("aria-pressed") === "true";
      speechSynthesis.cancel();
      $$("[data-ecouter][aria-pressed=true]").forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
      if (etait) return;
      var u = new SpeechSynthesisUtterance(ecouter.closest(".msg").querySelector(".bubble").innerText);
      u.lang = "fr-FR";
      u.onend = u.onerror = function () { ecouter.setAttribute("aria-pressed", "false"); };
      ecouter.setAttribute("aria-pressed", "true");
      parle = u;
      speechSynthesis.speak(parle);
    }
  });

  /* Dictée de la question. */
  var Reco = window.SpeechRecognition || window.webkitSpeechRecognition;
  var reco = null;
  function arreterMicro() {
    if (reco) { try { reco.stop(); } catch (err) { /* déjà arrêté */ } }
    micro.setAttribute("aria-pressed", "false");
    ecoute.hidden = true;
  }
  if (micro) {
    micro.addEventListener("click", function () {
      if (!Reco) { toast("La dictée ne marche pas sur ce navigateur. Écris ta question."); return; }
      if (micro.getAttribute("aria-pressed") === "true") { arreterMicro(); return; }
      reco = new Reco();
      reco.lang = "fr-FR";
      reco.interimResults = true;
      var base = zone.value ? zone.value.replace(/\s*$/, " ") : "";
      reco.onresult = function (ev) {
        var t = "";
        for (var i = 0; i < ev.results.length; i++) t += ev.results[i][0].transcript;
        zone.value = base + t;
        ajuster();
      };
      reco.onerror = function (ev) {
        arreterMicro();
        if (ev.error === "not-allowed" || ev.error === "service-not-allowed") toast("Autorise le micro dans ton navigateur pour dicter.");
        else if (ev.error !== "aborted" && ev.error !== "no-speech") toast("La dictée s'est arrêtée. Réessaie ou écris ta question.");
      };
      reco.onend = function () { arreterMicro(); zone.focus(); };
      micro.setAttribute("aria-pressed", "true");
      ecoute.hidden = false;
      reco.start();
    });
  }
})();
