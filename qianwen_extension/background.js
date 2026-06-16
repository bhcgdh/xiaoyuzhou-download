const QIANWEN_URL = "https://www.qianwen.com/discover/audioread";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "START_UPLOAD") return;

  startUpload(message.files)
    .then(() => sendResponse({ success: true }))
    .catch((error) => sendResponse({ success: false, error: error.message }));
  return true;
});

async function startUpload(files) {
  if (!Array.isArray(files) || files.length === 0 || files.length > 50) {
    throw new Error("请选择 1 到 50 个音频。");
  }

  await chrome.storage.local.set({ pendingUploads: files });
  const tabs = await chrome.tabs.query({ url: `${QIANWEN_URL}*` });
  if (tabs.length) {
    const tab = tabs[0];
    await chrome.tabs.update(tab.id, { active: true });
    await chrome.windows.update(tab.windowId, { focused: true });
    await chrome.tabs.reload(tab.id);
    return;
  }
  await chrome.tabs.create({ url: QIANWEN_URL });
}
