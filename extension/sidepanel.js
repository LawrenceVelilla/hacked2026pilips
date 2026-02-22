const BACKEND_URL = "http://localhost:8000";
const STORAGE_USER_PHOTO = "fitted_user_photo";
const STORAGE_GARMENTS = "fitted_garments";

const stageImg = document.getElementById("stage-img");
const uploadOverlay = document.getElementById("upload-overlay");
const uploadBtn = document.getElementById("upload-btn");
const uploadInput = document.getElementById("upload-input");
const resetBtn = document.getElementById("reset-btn");
const sendBtn = document.getElementById("send-btn");
const promptInput = document.getElementById("prompt-input");
const statusEl = document.getElementById("status");
const spinnerEl = document.getElementById("spinner");
const spinnerText = document.getElementById("spinner-text");
const garmentsRow = document.getElementById("garments-row");

let basePhotoUrl = "";
let sessionId = null;
let lastTriedUrl = null;

// --- Helpers ---

function setStatus(text) {
  statusEl.textContent = text;
}

function showSpinner(show, text = "Generating try-on...") {
  spinnerEl.classList.toggle("active", show);
  spinnerText.textContent = text;
}

function showUploadOverlay(show) {
  uploadOverlay.classList.toggle("visible", show);
}

function setStageImage(src) {
  if (!src) return;
  stageImg.src = src;
  showUploadOverlay(false);
}

// --- Initialize ---

async function initialize() {
  const state = await chrome.storage.local.get([STORAGE_USER_PHOTO]);
  if (state[STORAGE_USER_PHOTO]) {
    basePhotoUrl = state[STORAGE_USER_PHOTO];
    setStageImage(basePhotoUrl);
    setStatus("");
  } else {
    try {
      const resp = await fetch(`${BACKEND_URL}/user-photos`);
      if (resp.ok) {
        const data = await resp.json();
        const url = data.full_body || data.upper_body || "";
        if (url) {
          basePhotoUrl = url;
          await chrome.storage.local.set({ [STORAGE_USER_PHOTO]: url });
          setStageImage(url);
          setStatus("");
        } else {
          showUploadOverlay(true);
          setStatus("Upload your photo to start.");
        }
      }
    } catch {
      showUploadOverlay(true);
      setStatus("Upload your photo to start.");
    }
  }

  refreshGarments();
}

// --- Garment thumbnails ---

function refreshGarments() {
  chrome.storage.local.get([STORAGE_GARMENTS], (res) => {
    const items = Array.isArray(res[STORAGE_GARMENTS]) ? res[STORAGE_GARMENTS] : [];
    garmentsRow.innerHTML = "";

    items.forEach((url) => {
      const btn = document.createElement("button");
      btn.className = "garment-thumb";
      const img = document.createElement("img");
      img.src = url;
      btn.appendChild(img);
      btn.addEventListener("click", () => tryOnGarment(url));
      garmentsRow.appendChild(btn);
    });
  });
}

// Listen for storage changes so new garments appear immediately
chrome.storage.onChanged.addListener((changes) => {
  if (changes[STORAGE_GARMENTS]) {
    refreshGarments();
  }
});

// --- Upload Photo ---

async function uploadUserPhoto(file) {
  const localUrl = URL.createObjectURL(file);
  setStageImage(localUrl);
  setStatus("Uploading...");

  try {
    const body = new FormData();
    body.append("file", file);
    const resp = await fetch(`${BACKEND_URL}/upload-photo?photo_type=full_body`, {
      method: "POST",
      body,
    });
    const data = await resp.json();
    if (!resp.ok || !data.photo_url) {
      throw new Error(data.error || "Upload failed");
    }

    URL.revokeObjectURL(localUrl);
    basePhotoUrl = data.photo_url;
    await chrome.storage.local.set({ [STORAGE_USER_PHOTO]: data.photo_url });
    setStageImage(data.photo_url);
    setStatus("Photo uploaded. Now click a garment below to try it on.");
  } catch (err) {
    setStatus(err instanceof Error ? err.message : "Upload failed.");
  }
}

// --- Try On ---

async function tryOnGarment(url) {
  if (!basePhotoUrl) {
    setStatus("Upload your photo first.");
    return;
  }

  // Duplicate prevention
  if (url === lastTriedUrl && sessionId) {
    setStatus("Already tried this on. Pick a different outfit.");
    return;
  }

  // Highlight active garment
  garmentsRow.querySelectorAll(".garment-thumb").forEach((el) => {
    el.classList.toggle("active", el.querySelector("img")?.src === url);
  });

  showSpinner(true, "Generating try-on (~12 sec)...");
  setStatus("");

  try {
    const resp = await fetch(`${BACKEND_URL}/try-on`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_url: url }),
    });
    const data = await resp.json();

    if (data.status === "success" && data.tryon_image_url) {
      setStageImage(data.tryon_image_url);
      sessionId = data.session_id;
      lastTriedUrl = url;
      setStatus(data.description || "Done. Type a message to modify.");
    } else {
      throw new Error(data.error || "Try-on failed");
    }
  } catch (err) {
    setStatus(err instanceof Error ? err.message : "Try-on failed.");
  } finally {
    showSpinner(false);
  }
}

// --- Chat ---

async function sendChat() {
  if (!sessionId) {
    setStatus("Click a garment to try on first.");
    return;
  }

  const msg = promptInput.value.trim();
  if (!msg) {
    setStatus("Type a message first.");
    return;
  }

  showSpinner(true, "Modifying outfit...");
  setStatus("");

  try {
    const resp = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: msg }),
    });
    const data = await resp.json();

    if (data.status === "success" && data.tryon_image_url) {
      setStageImage(data.tryon_image_url);
      promptInput.value = "";
      setStatus(data.description || "Done.");
    } else {
      throw new Error(data.error || "Modification failed");
    }
  } catch (err) {
    setStatus(err instanceof Error ? err.message : "Modification failed.");
  } finally {
    showSpinner(false);
  }
}

// --- Event Listeners ---

uploadBtn.addEventListener("click", () => uploadInput.click());

uploadInput.addEventListener("change", () => {
  const file = uploadInput.files?.[0];
  if (!file) return;
  uploadUserPhoto(file);
});

sendBtn.addEventListener("click", sendChat);

promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});

resetBtn.addEventListener("click", () => {
  sessionId = null;
  lastTriedUrl = null;
  promptInput.value = "";

  if (basePhotoUrl) {
    setStageImage(basePhotoUrl);
    setStatus("Reset. Click a garment to try on.");
    return;
  }

  stageImg.removeAttribute("src");
  showUploadOverlay(true);
  setStatus("Upload your photo to start.");
});

initialize();
