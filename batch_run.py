import subprocess
import sys
import shlex

ID_FILE = "ids.txt"
MAIN_SCRIPT = "main.py"
BASE_URL = "https://www.xiaoyuzhoufm.com/episode/"

def run_batch():
    with open(ID_FILE, "r", encoding="utf-8") as f:
        ids = [line.strip() for line in f if line.strip()]

    print(f"共 {len(ids)} 条任务")

    for i, eid in enumerate(ids, 1):

        full_url = BASE_URL + eid
        cmd = [sys.executable, MAIN_SCRIPT, full_url]

        # 用于打印安全命令
        cmd_str = " ".join(shlex.quote(x) for x in cmd)

        print(f"\n[{i}/{len(ids)}] 执行: {full_url}")

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print("❌ 失败")
            print(cmd_str)
        else:
            print("✅ 完成")


if __name__ == "__main__":
    run_batch()