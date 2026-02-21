(() => {
if (window.__fittedContentLoaded) {
  const existingPanel = document.getElementById("fitted-panel");
  if (existingPanel) {
    existingPanel.classList.remove("hidden");
    existingPanel.classList.add("expanded");
  }
  return;
}
window.__fittedContentLoaded = true;

const PANEL_ID = "fitted-panel";
const STORAGE_KEY = "fitted_garments";

function createHoverButton(container, imgUrl) {
  if (container.querySelector(".fitted-tryon-btn")) return;
  const rect = container.getBoundingClientRect();
  if (rect.width < 120 || rect.height < 120) return;
  container.classList.add("fitted-hover-wrap");
  const computed = window.getComputedStyle(container);
  if (computed.position === "static") container.style.position = "relative";

  const btn = document.createElement("button");
  btn.className = "fitted-tryon-btn";
  btn.textContent = "Try on";
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    e.preventDefault();
    addGarment(imgUrl);
    openPanel();
  });

  container.appendChild(btn);
}

function addGarment(url) {
  chrome.storage.local.get([STORAGE_KEY], (res) => {
    const current = Array.isArray(res[STORAGE_KEY]) ? res[STORAGE_KEY] : [];
    if (!current.includes(url)) current.unshift(url);
    chrome.storage.local.set({ [STORAGE_KEY]: current.slice(0, 12) });
  });
}

function observePins() {
  const process = () => {
    const imgs = document.querySelectorAll("img[src]");
    imgs.forEach((img) => {
      const link = img.closest('a[href*="/pin/"]');
      if (!link) return;
      const container = img.closest("div");
      if (!container) return;
      createHoverButton(container, img.currentSrc || img.src);
    });
  };

  process();
  const observer = new MutationObserver(process);
  observer.observe(document.body, { childList: true, subtree: true });
}

function addPinPageButton() {
  const insertButton = () => {
    const categoryBtn = Array.from(document.querySelectorAll("button, div[role='button']"))
      .find((el) => el.textContent?.trim().toLowerCase() === "clothing");
    const actionBar =
      categoryBtn?.parentElement ||
      document.querySelector('button[aria-label="Save"]')?.parentElement;
    if (!actionBar || actionBar.querySelector(".fitted-pin-action-btn")) return;

    const btn = document.createElement("button");
    btn.className = "fitted-pin-action-btn";
    btn.textContent = "Try on";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const img = document.querySelector('img[src][alt]');
      if (img) addGarment(img.currentSrc || img.src);
      openPanel();
    });

    if (categoryBtn && categoryBtn.parentElement) {
      categoryBtn.parentElement.insertBefore(btn, categoryBtn);
    } else {
      actionBar.appendChild(btn);
    }
  };

  insertButton();
  const observer = new MutationObserver(insertButton);
  observer.observe(document.body, { childList: true, subtree: true });
}

function ensurePanel() {
  if (document.getElementById(PANEL_ID)) return;

  const panel = document.createElement("div");
  panel.id = PANEL_ID;
  panel.className = "fitted-panel hidden";
  panel.innerHTML = `
    <div class="fitted-panel-header fitted-drag-handle">
      <div class="title">FITTED</div>
      <div class="actions">
        <button class="fitted-btn" id="fitted-reset">Reset</button>
        <button class="fitted-btn secondary" id="fitted-close">Close</button>
      </div>
    </div>
    <div class="fitted-panel-body">
      <div class="fitted-image-stage">
        <img id="fitted-stage-img" alt="Try on" />
        <div class="fitted-upload-overlay" id="fitted-upload-overlay">
          <button class="fitted-upload-btn" id="fitted-upload-btn">Upload Photo</button>
          <div class="fitted-upload-hint">Full-body or upper-body photo</div>
          <input type="file" id="fitted-upload-input" accept="image/*" hidden />
        </div>
      </div>
      <div class="fitted-garments" id="fitted-garments"></div>
      <div class="fitted-input-row">
        <input id="fitted-prompt" placeholder="How would a black jacket look?" />
        <button class="fitted-btn" id="fitted-try">Try</button>
      </div>
    </div>
    <div class="fitted-resize-handle" id="fitted-resize"></div>
  `;

  document.body.appendChild(panel);
  attachPanelLogic(panel);
}

function openPanel(expanded = false) {
  ensurePanel();
  const panel = document.getElementById(PANEL_ID);
  panel.classList.remove("hidden");
  panel.classList.toggle("expanded", expanded);

  const rect = panel.getBoundingClientRect();
  const unsetPosition = rect.width === 0 || rect.height === 0 || !panel.style.top;
  if (unsetPosition) {
    panel.style.top = expanded ? "60px" : "80px";
    panel.style.right = "40px";
    panel.style.left = "auto";
  }

  refreshGarments();
  loadUserPhoto();
}

function closePanel() {
  const panel = document.getElementById(PANEL_ID);
  if (panel) panel.classList.add("hidden");
}

function refreshGarments() {
  const list = document.getElementById("fitted-garments");
  if (!list) return;
  chrome.storage.local.get([STORAGE_KEY], (res) => {
    const items = Array.isArray(res[STORAGE_KEY]) ? res[STORAGE_KEY] : [];
    list.innerHTML = "";
    items.forEach((url) => {
      const item = document.createElement("div");
      item.className = "fitted-garment";
      const img = document.createElement("img");
      img.src = url;
      item.appendChild(img);
      item.addEventListener("click", () => {
        setActiveGarment(url);
      });
      list.appendChild(item);
    });
    if (items[0]) setActiveGarment(items[0], true);
  });
}

let activeGarment = null;
function setActiveGarment(url, updateStage = true) {
  activeGarment = url;
  if (updateStage) {
    const stage = document.getElementById("fitted-stage-img");
    if (stage) stage.src = url;
  }
}

function attachPanelLogic(panel) {
  const closeBtn = panel.querySelector("#fitted-close");
  const resetBtn = panel.querySelector("#fitted-reset");
  const tryBtn = panel.querySelector("#fitted-try");
  const uploadBtn = panel.querySelector("#fitted-upload-btn");
  const uploadInput = panel.querySelector("#fitted-upload-input");

  closeBtn.addEventListener("click", closePanel);
  resetBtn.addEventListener("click", () => {
    loadUserPhoto(true);
  });

  tryBtn.addEventListener("click", async () => {
    if (!activeGarment) return;
    const stage = document.getElementById("fitted-stage-img");
    stage.src = "";
    const baseUrl = await getBaseUrl();
    try {
      const resp = await fetch(`${baseUrl}/try-on`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ garment_image_url: activeGarment })
      });
      const data = await resp.json();
      if (data.tryon_image_url) stage.src = data.tryon_image_url;
    } catch (err) {
      console.warn("Try-on failed", err);
    }
  });

  makeDraggable(panel, panel.querySelector(".fitted-drag-handle"));
  makeResizable(panel, panel.querySelector("#fitted-resize"));

  uploadBtn.addEventListener("click", () => uploadInput.click());
  uploadInput.addEventListener("change", async () => {
    const file = uploadInput.files?.[0];
    if (!file) return;
    const stage = document.getElementById("fitted-stage-img");
    const overlayEl = document.getElementById("fitted-upload-overlay");
    stage.src = URL.createObjectURL(file);
    overlayEl.classList.remove("visible");

    const baseUrl = await getBaseUrl();
    const body = new FormData();
    body.append("file", file);
    const url = `${baseUrl}/upload-photo?photo_type=upper_body`;
    try {
      const resp = await fetch(url, { method: "POST", body });
      const data = await resp.json();
      if (data.photo_url) {
        chrome.storage.local.set({ fitted_user_photo: data.photo_url });
        stage.src = data.photo_url;
      }
    } catch (err) {
      console.warn("Upload failed", err);
    }
  });
}

async function loadUserPhoto(forceShowUpload = false) {
  const stage = document.getElementById("fitted-stage-img");
  const overlayEl = document.getElementById("fitted-upload-overlay");
  if (!stage) return;
  if (forceShowUpload) {
    stage.src = "";
    overlayEl.classList.add("visible");
    return;
  }

  chrome.storage.local.get(["fitted_user_photo"], (res) => {
    if (res.fitted_user_photo) {
      stage.src = res.fitted_user_photo;
      overlayEl.classList.remove("visible");
      return;
    }
  });

  const baseUrl = await getBaseUrl();
  try {
    const resp = await fetch(`${baseUrl}/user-photos`);
    const data = await resp.json();
    const photoUrl = data.upper_body || data.full_body || "";
    if (photoUrl) {
      chrome.storage.local.set({ fitted_user_photo: photoUrl });
      stage.src = photoUrl;
      overlayEl.classList.remove("visible");
    } else {
      overlayEl.classList.add("visible");
    }
  } catch (err) {
    console.warn("Failed to load user photo", err);
    overlayEl.classList.add("visible");
  }
}

function getBaseUrl() {
  return Promise.resolve("http://localhost:8000");
}

function makeDraggable(panel, handle) {
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;

  const onMouseMove = (e) => {
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    panel.style.left = `${startLeft + dx}px`;
    panel.style.top = `${startTop + dy}px`;
    panel.style.right = "auto";
  };

  const onMouseUp = () => {
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  handle.addEventListener("mousedown", (e) => {
    startX = e.clientX;
    startY = e.clientY;
    const rect = panel.getBoundingClientRect();
    startLeft = rect.left;
    startTop = rect.top;
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  });
}

function makeResizable(panel, handle) {
  let startX = 0;
  let startY = 0;
  let startW = 0;
  let startH = 0;

  const onMouseMove = (e) => {
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    panel.style.width = `${Math.max(280, startW + dx)}px`;
    panel.style.height = `${Math.max(360, startH + dy)}px`;
  };

  const onMouseUp = () => {
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  handle.addEventListener("mousedown", (e) => {
    startX = e.clientX;
    startY = e.clientY;
    const rect = panel.getBoundingClientRect();
    startW = rect.width;
    startH = rect.height;
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  });
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "FITTED_OPEN") openPanel(false);
  if (msg?.type === "FITTED_OPEN_EXPANDED") openPanel(true);
});

observePins();
addPinPageButton();
})();
