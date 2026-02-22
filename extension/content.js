(() => {
if (window.__fittedContentLoaded) return;
window.__fittedContentLoaded = true;

const STORAGE_KEY = "fitted_garments";

function isContextValid() {
  try {
    return !!chrome.runtime?.id;
  } catch {
    return false;
  }
}

function addGarment(url) {
  if (!isContextValid()) {
    alert("Fitted extension was updated. Please refresh this page.");
    return;
  }
  chrome.storage.local.get([STORAGE_KEY], (res) => {
    if (chrome.runtime.lastError) return;
    const current = Array.isArray(res[STORAGE_KEY]) ? res[STORAGE_KEY] : [];
    if (!current.includes(url)) current.unshift(url);
    chrome.storage.local.set({ [STORAGE_KEY]: current.slice(0, 12) });
  });
  chrome.runtime.sendMessage({ type: "FITTED_OPEN_SIDEPANEL" });
}

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
  });

  container.appendChild(btn);
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
      // Grab the main pin image — it's the largest image on the page
      const imgs = Array.from(document.querySelectorAll('img[src][alt]'));
      const mainImg = imgs
        .filter((i) => i.naturalWidth > 200 && i.naturalHeight > 200)
        .sort((a, b) => (b.naturalWidth * b.naturalHeight) - (a.naturalWidth * a.naturalHeight))[0];
      if (mainImg) addGarment(mainImg.currentSrc || mainImg.src);
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

observePins();
addPinPageButton();
})();
