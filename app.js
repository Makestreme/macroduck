const DOWNLOAD_URL = "https://github.com/YOUR_USER/YOUR_REPO/releases/latest/download/macro-duck-windows.zip";

const btn = document.getElementById("downloadBtn");
const note = document.getElementById("downloadNote");

if (btn) {
  btn.href = DOWNLOAD_URL;
  btn.addEventListener("click", function (e) {
    if (DOWNLOAD_URL.indexOf("YOUR_USER") !== -1) {
      e.preventDefault();
      alert("Download link not configured yet. Set DOWNLOAD_URL in docs/app.js.");
    }
  });
}

if (note) {
  note.textContent = "";
}

function styleInstallButtons() {
  document.querySelectorAll("esp-web-install-button").forEach(function (el) {
    var root = el.shadowRoot;
    if (!root) return;
    var style = document.createElement("style");
    style.textContent =
      "button { font-family: inherit; font-size: 13px; font-weight: 600; " +
      "padding: 8px 16px; border-radius: 7px; border: none; " +
      "background: #0a6c4d; color: #ffffff; cursor: pointer; transition: background .12s; }" +
      "button::before { display: none; }" +
      "button:hover { background: #0b7d59; }";
    root.appendChild(style);
    var b = root.querySelector("button");
    if (b) b.textContent = "install";
  });
}

if (window.customElements && customElements.whenDefined) {
  customElements.whenDefined("esp-web-install-button").then(styleInstallButtons);
} else if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", styleInstallButtons);
} else {
  styleInstallButtons();
}
