const APP_URL = "http://127.0.0.1:8765";

function waitFor(getValue, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = setInterval(() => {
      const value = getValue();
      if (value) {
        clearInterval(timer);
        resolve(value);
      } else if (Date.now() - started > timeoutMs) {
        clearInterval(timer);
        reject(new Error("Timed out waiting for Qianwen upload controls."));
      }
    }, 300);
  });
}

async function readAudio(pendingUpload) {
  const response = await fetch(
    `${APP_URL}/api/audio-file?path=${encodeURIComponent(pendingUpload.path)}`
  );
  if (!response.ok) throw new Error(`Unable to read audio: ${pendingUpload.name}`);

  const blob = await response.blob();
  return new File([blob], pendingUpload.name, {
    type: blob.type || "audio/mp4",
    lastModified: Date.now()
  });
}

async function uploadPendingFiles() {
  const { pendingUploads } = await chrome.storage.local.get("pendingUploads");
  if (!Array.isArray(pendingUploads) || pendingUploads.length === 0) return;
  await chrome.storage.local.remove("pendingUploads");

  try {
    const input = await waitFor(() => document.querySelector('input[type="file"]'));
    const transfer = new DataTransfer();
    for (const pendingUpload of pendingUploads) {
      transfer.items.add(await readAudio(pendingUpload));
    }

    input.files = transfer.files;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));

    const confirmButton = await waitFor(() =>
      [...document.querySelectorAll("button")].find((button) =>
        button.textContent.replace(/\s+/g, "") === "确认" && !button.disabled
      ), 180000);
    confirmButton.click();
  } catch (error) {
    console.error("Qianwen audio upload failed:", error);
    alert(`Qianwen audio upload failed: ${error.message}`);
  }
}

uploadPendingFiles();
