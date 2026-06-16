import os
import shutil
from pathlib import Path

# ====== 配置区域 ======
SOURCE_DIR = r"F:\xyz-dl\download"
TARGET_DIR = r"F:\xyz-dl\download\all_音频"
MOVE_FILES = False  # True = 移动；False = 复制
# ======================

def collect_m4a():
    source_path = Path(SOURCE_DIR)
    target_path = Path(TARGET_DIR)

    target_path.mkdir(parents=True, exist_ok=True)

    count = 0

    for file in source_path.rglob("*.m4a"):

        dest_file = target_path / file.name

        if MOVE_FILES:
            # move 默认就是覆盖
            if dest_file.exists():
                dest_file.unlink()
            shutil.move(file, dest_file)
        else:
            # copy2 保留修改时间
            try:
                shutil.copy2(file, dest_file)
                set_windows_file_times(dest_file, file)
            except:
                pass
        print(f"已处理: {file}")
        count += 1

    print(f"\n完成，共处理 {count} 个 m4a 文件")

if __name__ == "__main__":
    collect_m4a()