# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYW = ROOT / "WelfareOn_Launcher.pyw"
ICON = ROOT / "assets" / "welfareon.ico"
LOGO = ROOT / "assets" / "launcher_logo.png"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "WelfareOn_Launcher.spec"
LOG_DIR = ROOT / "logs"
LOG_PATH = LOG_DIR / "build_launcher.log"


def build_env() -> dict:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def log(message: str = "") -> None:
    LOG_DIR.mkdir(exist_ok=True)
    print(message, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def run_and_log(cmd: list[str], cwd: Path | None = None) -> int:
    log("[build] 실행: " + " ".join(map(str, cmd)))
    proc = subprocess.Popen(
        [str(x) for x in cmd],
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=build_env(),
    )
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip()
        if line:
            log(line)
    return proc.wait()


def remove_if_exists(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def clean_cache() -> None:
    for target in ROOT.rglob("__pycache__"):
        shutil.rmtree(target, ignore_errors=True)
    for pattern in ("*.pyc", "*.pyo"):
        for target in ROOT.rglob(pattern):
            try:
                target.unlink()
            except Exception:
                pass


def main() -> int:
    LOG_DIR.mkdir(exist_ok=True)
    LOG_PATH.write_text("[build] started\n", encoding="utf-8")
    if sys.version_info[:2] != (3, 12):
        log(f"ERROR: Python 3.12.x로 빌드해야 합니다. 현재 버전: {sys.version.split()[0]}")
        return 1
    log("[build] 1/4 빌드 환경 확인")
    if not PYW.exists():
        log("ERROR: WelfareOn_Launcher.pyw 파일을 찾을 수 없습니다.")
        return 1

    log("[build] 2/4 PyInstaller 및 실행 패키지 확인")
    rc = run_and_log([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller", "pywebview", "pillow", "pythonnet", "clr_loader"], cwd=ROOT)
    if rc != 0:
        log("ERROR: PyInstaller 설치 또는 업데이트에 실패했습니다.")
        return rc

    log("[build] 3/4 이전 빌드 산출물 정리")
    remove_if_exists(DIST)
    remove_if_exists(BUILD)
    remove_if_exists(SPEC)
    clean_cache()

    sep = ";" if sys.platform.startswith("win") else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "WelfareOn_Launcher",
        "--hidden-import",
        "webview",
        "--hidden-import",
        "webview.platforms.edgechromium",
        "--hidden-import",
        "webview.platforms.winforms",
        "--hidden-import",
        "clr",
        "--hidden-import",
        "pythonnet",
        "--hidden-import",
        "clr_loader",
        "--collect-all",
        "webview",
        "--collect-all",
        "pythonnet",
        "--collect-all",
        "clr_loader",
    ]
    if ICON.exists():
        cmd.append(f"--icon={ICON}")
        cmd.extend(["--add-data", f"{ICON}{sep}assets"])
    if LOGO.exists():
        cmd.extend(["--add-data", f"{LOGO}{sep}assets"])
    cmd.append(str(PYW))

    log("[build] 4/4 런처 exe 생성")
    rc = run_and_log(cmd, cwd=ROOT)
    if rc != 0:
        log("ERROR: PyInstaller 빌드에 실패했습니다.")
        return rc

    exe = DIST / "WelfareOn_Launcher.exe"
    kor = DIST / "복지온_Launcher.exe"
    if not exe.exists():
        log("ERROR: EXE 파일이 생성되지 않았습니다.")
        return 1
    shutil.copy2(exe, kor)
    log(f"[build] 생성 완료: {exe}")
    log(f"[build] 생성 완료: {kor}")
    log("[build] 빌드 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
