const APP_URL = "http://127.0.0.1:8765";
const MAX_SIZE = 500 * 1024 * 1024;
const MAX_FILES = 50;

const filesElement = document.querySelector("#files");
const uploadButton = document.querySelector("#upload");
const watchExportButton = document.querySelector("#watch-export");
const statusElement = document.querySelector("#status");

function formatSize(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function showLastExportStatus() {
  const { lastExportStatus } = await chrome.storage.local.get("lastExportStatus");
  if (!lastExportStatus) return;
  statusElement.className = lastExportStatus.success ? "" : "error";
  statusElement.textContent = `Export watcher: ${lastExportStatus.text}`;
}

function selectedFiles() {
  return [...filesElement.selectedOptions]
    .filter((option) => !option.disabled)
    .map((option) => ({
      path: option.value,
      name: option.dataset.name,
      size: Number(option.dataset.size)
    }));
}

function updateSelectionStatus() {
  const files = selectedFiles();
  uploadButton.disabled = files.length === 0 || files.length > MAX_FILES;
  statusElement.className = files.length > MAX_FILES ? "warning" : "";
  statusElement.textContent = files.length
    ? `Selected ${files.length} audio file(s).`
    : "Select one or more audio files.";
}

async function loadFiles() {
  try {
    const response = await fetch(`${APP_URL}/api/audio-files`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Local service error");

    filesElement.replaceChildren();
    for (const file of data.files) {
      const option = document.createElement("option");
      option.value = file.path;
      option.dataset.name = file.name;
      option.dataset.size = file.size;
      option.disabled = file.size > MAX_SIZE;
      option.textContent =
        `${file.name} (${formatSize(file.size)})${option.disabled ? " - over 500 MB" : ""}`;
      filesElement.append(option);
    }
    uploadButton.disabled = true;
    statusElement.textContent = data.files.length
      ? `Found ${data.files.length} audio file(s), newest first.`
      : "No audio files found under download.";
  } catch (error) {
    statusElement.className = "error";
    statusElement.textContent = `Load failed: ${error.message}\nRun start.bat first.`;
  }
}

uploadButton.addEventListener("click", async () => {
  const files = selectedFiles();
  if (!files.length || files.length > MAX_FILES) {
    updateSelectionStatus();
    return;
  }

  uploadButton.disabled = true;
  statusElement.className = "";
  statusElement.textContent = `Opening Qianwen and uploading ${files.length} audio file(s)...`;
  const response = await chrome.runtime.sendMessage({
    type: "START_UPLOAD",
    files
  });
  if (!response?.success) {
    uploadButton.disabled = false;
    statusElement.className = "error";
    statusElement.textContent = `Start failed: ${response?.error || "Unknown error"}`;
  }
});

watchExportButton.addEventListener("click", async () => {
  watchExportButton.disabled = true;
  statusElement.className = "";
  statusElement.textContent = "Starting export watcher...";

  const response = await chrome.runtime.sendMessage({ type: "START_EXPORT_WATCH" });
  if (response?.success) {
    statusElement.textContent = "Watching for 10 minutes. Export files manually in Qianwen now.";
  } else {
    statusElement.className = "error";
    statusElement.textContent = `Watch failed: ${response?.error || "Unknown error"}`;
  }
  watchExportButton.disabled = false;
});

filesElement.addEventListener("change", updateSelectionStatus);
loadFiles().then(showLastExportStatus);
