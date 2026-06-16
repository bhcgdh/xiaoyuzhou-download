const APP_URL = "http://127.0.0.1:8765";
const MAX_SIZE = 500 * 1024 * 1024;
const MAX_FILES = 50;

const filesElement = document.querySelector("#files");
const uploadButton = document.querySelector("#upload");
const statusElement = document.querySelector("#status");

function formatSize(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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
    ? `已选择 ${files.length} 个音频。`
    : "请选择一个或多个音频。";
}

async function loadFiles() {
  try {
    const response = await fetch(`${APP_URL}/api/audio-files`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "本地服务返回错误");

    filesElement.replaceChildren();
    for (const file of data.files) {
      const option = document.createElement("option");
      option.value = file.path;
      option.dataset.name = file.name;
      option.dataset.size = file.size;
      option.disabled = file.size > MAX_SIZE;
      option.textContent =
        `${file.name} (${formatSize(file.size)})${option.disabled ? " - 超过 500 MB" : ""}`;
      filesElement.append(option);
    }
    uploadButton.disabled = true;
    statusElement.textContent = data.files.length
      ? `找到 ${data.files.length} 个音频，按修改时间从新到旧排列。`
      : "download 目录中没有音频文件。";
  } catch (error) {
    statusElement.className = "error";
    statusElement.textContent = `读取失败：${error.message}\n请先运行 start.bat。`;
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
  statusElement.textContent = `正在打开千问并上传 ${files.length} 个音频……`;
  const response = await chrome.runtime.sendMessage({
    type: "START_UPLOAD",
    files
  });
  if (response?.success) {
    statusElement.textContent = "已在千问页面开始上传。";
  } else {
    uploadButton.disabled = false;
    statusElement.className = "error";
    statusElement.textContent = `启动失败：${response?.error || "未知错误"}`;
  }
});

filesElement.addEventListener("change", updateSelectionStatus);
loadFiles();
