import json
import mimetypes
import re
import shutil
import subprocess
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse


HOST = "127.0.0.1"
PORT = 8765
APP_DIR = Path(__file__).resolve().parent
DOWNLOADER_DIR = APP_DIR
CONDA_EXE = Path(r"D:\anaconda3\Scripts\conda.exe")
EPISODE_ID_RE = re.compile(r"^[0-9a-fA-F]{24}$")
IMPORTED_URLS = []
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".wma", ".aac", ".ogg", ".amr", ".flac", ".aiff"}
DOWNLOAD_DIR = APP_DIR / "download"
QIANWEN_EXPORT_DIR = DOWNLOAD_DIR / "千问导出"
USER_DOWNLOAD_DIR = Path.home() / "Downloads"
QIANWEN_EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def extract_episode_id(value: str) -> str:
    value = value.strip()
    if EPISODE_ID_RE.fullmatch(value):
        return value.lower()

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"不是有效的网址或单集 ID：{value}")

    match = re.search(r"/episode/([0-9a-fA-F]{24})(?:/|$)", parsed.path)
    if not match:
        raise ValueError(f"网址中没有找到 24 位单集 ID：{value}")
    return match.group(1).lower()


def parse_episode_ids(raw_urls: str) -> list[str]:
    values = [item.strip() for item in re.split(r"[,，\r\n]+", raw_urls)]
    values = [item for item in values if item]
    if not values:
        raise ValueError("请至少输入一个网址。")

    result = []
    seen = set()
    for value in values:
        episode_id = extract_episode_id(value)
        if episode_id not in seen:
            seen.add(episode_id)
            result.append(episode_id)
    return result


def filter_xiaoyuzhou_urls(tabs: list[dict]) -> list[str]:
    urls = []
    seen_ids = set()
    for tab in tabs:
        url = str(tab.get("url", "")).strip()
        if urlparse(url).hostname != "www.xiaoyuzhoufm.com":
            continue
        try:
            episode_id = extract_episode_id(url)
        except ValueError:
            continue
        if episode_id not in seen_ids:
            seen_ids.add(episode_id)
            urls.append(url)
    return urls


def list_audio_files() -> list[dict]:
    files = []
    if not DOWNLOAD_DIR.is_dir():
        return files
    for path in DOWNLOAD_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        stat = path.stat()
        files.append(
            {
                "path": path.relative_to(DOWNLOAD_DIR).as_posix(),
                "name": path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        )
    return sorted(files, key=lambda item: item["modified"], reverse=True)


def resolve_audio_file(relative_path: str) -> Path:
    path = (DOWNLOAD_DIR / relative_path).resolve()
    download_root = DOWNLOAD_DIR.resolve()
    if path == download_root or download_root not in path.parents:
        raise ValueError("无效的音频文件路径。")
    if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("音频文件不存在或格式不受支持。")
    return path


def move_qianwen_export(source_value: str) -> Path:
    source = Path(source_value).resolve()
    downloads_root = USER_DOWNLOAD_DIR.resolve()
    if source == downloads_root or downloads_root not in source.parents:
        raise ValueError("只能接收 Windows 下载目录中的导出文件。")
    if not source.is_file():
        raise ValueError("导出文件不存在。")

    QIANWEN_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    destination = QIANWEN_EXPORT_DIR / source.name
    if destination.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = destination.with_name(
            f"{destination.stem}-{stamp}{destination.suffix}"
        )
    try:
        return Path(shutil.move(str(source), str(destination)))
    except PermissionError:
        shutil.copy2(source, destination)
        return destination


def conda_command(*args: str) -> list[str]:
    return [
        str(CONDA_EXE),
        "run",
        "-n",
        "py313",
        "--no-capture-output",
        "python",
        *args,
    ]


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=DOWNLOADER_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    return completed.returncode, output


def save_credentials(refresh_token: str, device_id: str) -> tuple[int, str]:
    code = (
        "import sys\n"
        "from auth import XiaoyuzhouAuth\n"
        "auth = XiaoyuzhouAuth()\n"
        "result = auth.login_with_refresh_token(sys.argv[1], sys.argv[2])\n"
        "if not result.get('success'):\n"
        "    raise SystemExit(result.get('error', '登录失败'))\n"
        "if not auth.save_credentials():\n"
        "    raise SystemExit('认证信息保存失败')\n"
        "print('认证信息已更新')\n"
    )
    return run_command(conda_command("-c", code, refresh_token, device_id))


def download_episode(episode_id: str) -> dict:
    url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"
    return_code, output = run_command(conda_command("main.py", url))
    return {
        "episode_id": episode_id,
        "url": url,
        "success": return_code == 0,
        "return_code": return_code,
        "output": output,
    }


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/import-urls":
            self.send_json(200, {"success": True, "urls": IMPORTED_URLS})
            return
        if self.path == "/api/audio-files":
            self.send_json(200, {"success": True, "files": list_audio_files()})
            return
        if self.path.startswith("/api/audio-file?"):
            self.handle_audio_file()
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/import-urls":
            self.handle_import_urls()
            return
        if self.path == "/api/qianwen-export":
            self.handle_qianwen_export()
            return
        if self.path == "/api/download":
            self.handle_download()
            return
        self.send_error(404)

    def handle_import_urls(self):
        global IMPORTED_URLS
        try:
            payload = self.read_json()
            tabs = [{"url": url} for url in payload.get("urls", [])]
            IMPORTED_URLS = filter_xiaoyuzhou_urls(tabs)
            self.send_json(
                200,
                {"success": True, "count": len(IMPORTED_URLS), "urls": IMPORTED_URLS},
            )
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"success": False, "error": str(error)})

    def handle_download(self):
        try:
            payload = self.read_json()
            episode_ids = parse_episode_ids(str(payload.get("urls", "")))
            refresh_token = str(payload.get("token", "")).strip()
            device_id = str(payload.get("device_id", "")).strip()

            if bool(refresh_token) != bool(device_id):
                raise ValueError("token 和 device id 必须同时填写，或同时留空。")
            if not DOWNLOADER_DIR.is_dir():
                raise RuntimeError(f"下载程序目录不存在：{DOWNLOADER_DIR}")
            if not CONDA_EXE.is_file():
                raise RuntimeError(f"找不到 Conda：{CONDA_EXE}")

            auth_output = ""
            if refresh_token:
                return_code, auth_output = save_credentials(refresh_token, device_id)
                if return_code != 0:
                    self.send_json(
                        400,
                        {"success": False, "error": "认证失败", "output": auth_output},
                    )
                    return

            results = []
            for index, episode_id in enumerate(episode_ids):
                if index:
                    time.sleep(0.5)
                results.append(download_episode(episode_id))

            self.send_json(
                200,
                {
                    "success": all(item["success"] for item in results),
                    "auth_output": auth_output,
                    "results": results,
                },
            )
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"success": False, "error": str(error)})
        except Exception as error:
            self.send_json(500, {"success": False, "error": str(error)})

    def handle_qianwen_export(self):
        try:
            payload = self.read_json()
            destination = move_qianwen_export(str(payload.get("path", "")))
            self.send_json(
                200,
                {
                    "success": True,
                    "path": str(destination.relative_to(APP_DIR)),
                },
            )
        except (ValueError, OSError) as error:
            self.send_json(400, {"success": False, "error": str(error)})

    def read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(content_length) or b"{}")

    def handle_audio_file(self):
        try:
            query = parse_qs(urlparse(self.path).query)
            relative_path = query.get("path", [""])[0]
            audio_path = resolve_audio_file(relative_path)
            content_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(audio_path.stat().st_size))
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{quote(audio_path.name)}",
            )
            self.send_cors_headers()
            self.end_headers()
            with audio_path.open("rb") as audio_file:
                shutil.copyfileobj(audio_file, self.wfile)
        except (ValueError, OSError) as error:
            self.send_json(404, {"success": False, "error": str(error)})

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"小宇宙下载界面：http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止服务")
    HTTPServer((HOST, PORT), AppHandler).serve_forever()
