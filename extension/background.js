// Open side panel when clicking the extension icon
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

// Allow content script "Try on" clicks to open the side panel
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg?.type === "FITTED_OPEN_SIDEPANEL" && sender.tab?.id) {
    try {
      chrome.sidePanel.open({ tabId: sender.tab.id });
    } catch {
      // User gesture context lost — panel can still be opened via extension icon
    }
  }
});
