const QIANWEN_URL = "https://www.qianwen.com/discover/audioread";
const APP_URL = "http://127.0.0.1:8765";
const EXPORT_EXTENSIONS = /\.(docx?|pdf|txt|md|srt|vtt)$/i;

const processedDownloads = new Set();
let watchStartedAt = 0;
let watchEndsAt = 0;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const action = message.type === "START_UPLOAD"
    ? startUpload(message.files)
    : message.type === "START_EXPORT_WATCH"
      ? startExportWatch()
      : null;
  if (!action) return;

  action
    .then((result) => sendResponse({ success: true, ...result }))
    .catch((error) => sendResponse({ success: false, error: error.message }));
  return true;
});

chrome.downloads.onChanged.addListener(async (delta) => {
  if (delta.state?.current !== "complete") return;
  if (!isWatchingExports()) return;

  const [item] = await chrome.downloads.search({ id: delta.id });
  if (item) await trySaveDownload(item);
});

function isWatchingExports() {
  return watchStartedAt > 0 && Date.now() <= watchEndsAt;
}

async function startUpload(files) {
  if (!Array.isArray(files) || files.length === 0 || files.length > 50) {
    throw new Error("Select 1 to 50 audio files.");
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

async function startExportWatch() {
  watchStartedAt = Date.now();
  watchEndsAt = watchStartedAt + 10 * 60 * 1000;
  processedDownloads.clear();
  await chrome.storage.local.set({
    lastExportStatus: {
      success: true,
      text: "watching; export transcript files manually in Qianwen",
      time: Date.now()
    }
  });
  await chrome.action.setBadgeBackgroundColor({ color: "#4f7fc8" });
  await chrome.action.setBadgeText({ text: "ON" });
  scanCompletedDownloads();
  return {};
}

async function scanCompletedDownloads() {
  while (isWatchingExports()) {
    const items = await chrome.downloads.search({
      startedAfter: new Date(watchStartedAt - 2000).toISOString(),
      state: "complete"
    });
    for (const item of items) {
      await trySaveDownload(item);
    }
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  await chrome.action.setBadgeText({ text: "" });
}

async function trySaveDownload(item) {
  if (!item?.filename || processedDownloads.has(item.id)) return;
  if (!EXPORT_EXTENSIONS.test(item.filename)) return;
  processedDownloads.add(item.id);

  const response = await fetch(`${APP_URL}/api/qianwen-export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: item.filename })
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    await chrome.storage.local.set({
      lastExportStatus: {
        success: false,
        text: data.error || `failed to save ${item.filename}`,
        time: Date.now()
      }
    });
    await chrome.action.setBadgeBackgroundColor({ color: "#c0392b" });
    await chrome.action.setBadgeText({ text: "ERR" });
    return;
  }

  const data = await response.json();
  await chrome.storage.local.set({
    lastExportStatus: {
      success: true,
      text: `saved ${data.path}`,
      time: Date.now()
    }
  });
  await chrome.action.setBadgeBackgroundColor({ color: "#2e9b68" });
  await chrome.action.setBadgeText({ text: "OK" });
}
