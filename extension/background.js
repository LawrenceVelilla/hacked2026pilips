// Open side panel when clicking the extension icon
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

// Open side panel when content script requests it (e.g. "Try on" button)
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg?.type === "FITTED_OPEN_SIDEPANEL" && sender.tab?.id) {
    chrome.sidePanel.open({ tabId: sender.tab.id });
  }
});
