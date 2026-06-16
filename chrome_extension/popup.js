const APP_URL = "http://127.0.0.1:8765/";
const statusElement = document.querySelector("#status");

function isEpisodeUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.hostname === "www.xiaoyuzhoufm.com"
      && /^\/episode\/[0-9a-fA-F]{24}(?:\/|$)/.test(parsed.pathname);
  } catch {
    return false;
  }
}

async function focusOrOpenApp() {
  const appTabs = await chrome.tabs.query({ url: `${APP_URL}*` });
  if (appTabs.length) {
    await chrome.tabs.update(appTabs[0].id, { active: true });
    await chrome.windows.update(appTabs[0].windowId, { focused: true });
    await chrome.tabs.reload(appTabs[0].id);
    return;
  }
  await chrome.tabs.create({ url: APP_URL });
}

async function sendUrls() {
  try {
    const tabs = await chrome.tabs.query({});
    const urls = [...new Set(tabs.map((tab) => tab.url).filter(isEpisodeUrl))];

    const response = await fetch(`${APP_URL}api/import-urls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "本地服务返回错误");

    statusElement.className = "ok";
    statusElement.textContent = data.count
      ? `已发送 ${data.count} 个单集网址。`
      : "没有找到已打开的小宇宙单集页面。";
    await focusOrOpenApp();
  } catch (error) {
    statusElement.className = "error";
    statusElement.textContent = `发送失败：${error.message}。请先运行 start.bat。`;
  }
}

sendUrls();
