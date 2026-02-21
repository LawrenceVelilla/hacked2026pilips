const BACKEND_URL = "http://localhost:8000";
const STORAGE_USER_PHOTO = "fitted_user_photo";
const STORAGE_GARMENTS = "fitted_garments";
const STORAGE_CHAT = "fitted_chat_history";

const stageImg = document.getElementById("stage-img");
const uploadOverlay = document.getElementById("upload-overlay");
const uploadBtn = document.getElementById("upload-btn");
const uploadInput = document.getElementById("upload-input");
const resetBtn = document.getElementById("reset-btn");
const backBtn = document.getElementById("back-btn");
const addBtn = document.getElementById("add-btn");
const promptInput = document.getElementById("prompt-input");
const statusEl = document.getElementById("status");

let basePhotoUrl = "";
let localObjectUrl = "";

function setStatus(text) {
  statusEl.textContent = text;
}

function showUploadOverlay(show) {
  uploadOverlay.classList.toggle("visible", show);
}

function setStageImage(src) {
  if (!src) return;
  stageImg.src = src;
  showUploadOverlay(false);
}

function revokeLocalUrl() {
  if (!localObjectUrl) return;
  URL.revokeObjectURL(localObjectUrl);
  localObjectUrl = "";
}

function storageGet(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}

function storageSet(items) {
  return new Promise((resolve) => chrome.storage.local.set(items, resolve));
}

function storageRemove(keys) {
  return new Promise((resolve) => chrome.storage.local.remove(keys, resolve));
}

async function loadPhotoFromBackend() {
  try {
    const resp = await fetch(`${BACKEND_URL}/user-photos`);
    if (!resp.ok) return "";
    const data = await resp.json();
    return data.upper_body || data.full_body || "";
  } catch {
    return "";
  }
}

async function initialize() {
  const state = await storageGet([STORAGE_USER_PHOTO]);
  if (state[STORAGE_USER_PHOTO]) {
    basePhotoUrl = state[STORAGE_USER_PHOTO];
    setStageImage(basePhotoUrl);
    setStatus("");
    return;
  }

  const backendPhoto = await loadPhotoFromBackend();
  if (backendPhoto) {
    basePhotoUrl = backendPhoto;
    await storageSet({ [STORAGE_USER_PHOTO]: backendPhoto });
    setStageImage(backendPhoto);
    setStatus("");
    return;
  }

  stageImg.removeAttribute("src");
  showUploadOverlay(true);
  setStatus("Upload your photo to start.");
}

async function uploadUserPhoto(file) {
  revokeLocalUrl();
  localObjectUrl = URL.createObjectURL(file);
  setStageImage(localObjectUrl);
  setStatus("Uploading...");

  try {
    const body = new FormData();
    body.append("file", file);
    const resp = await fetch(`${BACKEND_URL}/upload-photo?photo_type=upper_body`, {
      method: "POST",
      body,
    });

    const data = await resp.json();
    if (!resp.ok || !data.photo_url) {
      throw new Error(data.error || "Upload failed");
    }

    basePhotoUrl = data.photo_url;
    await storageSet({ [STORAGE_USER_PHOTO]: data.photo_url });
    revokeLocalUrl();
    setStageImage(data.photo_url);
    setStatus("Photo uploaded.");
  } catch (err) {
    setStatus(err instanceof Error ? err.message : "Upload failed.");
  }
}

async function tryOnLatestGarment() {
  if (!basePhotoUrl) {
    setStatus("Upload your photo first.");
    return;
  }

  const state = await storageGet([STORAGE_GARMENTS]);
  const garments = Array.isArray(state[STORAGE_GARMENTS]) ? state[STORAGE_GARMENTS] : [];
  if (!garments.length) {
    setStatus("Hover a Pinterest image and tap Try on first.");
    return;
  }

  setStatus("Generating try-on...");
  try {
    const prompt = promptInput.value.trim();
    const chatState = await storageGet([STORAGE_CHAT]);
    const history = Array.isArray(chatState[STORAGE_CHAT]) ? chatState[STORAGE_CHAT] : [];
    history.push({ prompt, garment: garments[0], created_at: Date.now() });
    await storageSet({ [STORAGE_CHAT]: history.slice(-30) });

    const resp = await fetch(`${BACKEND_URL}/try-on`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ garment_image_url: garments[0] }),
    });
    const data = await resp.json();
    if (!resp.ok || !data.tryon_image_url) {
      throw new Error(data.error || "Try-on failed");
    }
    setStageImage(data.tryon_image_url);
    setStatus("Done.");
  } catch (err) {
    setStatus(err instanceof Error ? err.message : "Try-on failed.");
  }
}

uploadBtn.addEventListener("click", () => uploadInput.click());
uploadInput.addEventListener("change", () => {
  const file = uploadInput.files?.[0];
  if (!file) return;
  uploadUserPhoto(file);
});

resetBtn.addEventListener("click", async () => {
  await storageRemove([STORAGE_CHAT]);
  promptInput.value = "";
  if (basePhotoUrl) {
    setStageImage(basePhotoUrl);
    setStatus("Cleared chat and restored original photo.");
    return;
  }

  revokeLocalUrl();
  stageImg.removeAttribute("src");
  showUploadOverlay(true);
  setStatus("Cleared chat. Upload your photo to continue.");
});

backBtn.addEventListener("click", () => {
  if (basePhotoUrl) {
    setStageImage(basePhotoUrl);
    setStatus("");
    return;
  }
  stageImg.removeAttribute("src");
  showUploadOverlay(true);
  setStatus("Upload your photo to start.");
});

addBtn.addEventListener("click", tryOnLatestGarment);

initialize();
