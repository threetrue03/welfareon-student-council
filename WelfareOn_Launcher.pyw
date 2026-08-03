# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

APP_NAME = "복지온"
APP_SUBTITLE = "Welfare Operation System"
SERVER_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
WINDOW_WIDTH = 1040
WINDOW_HEIGHT = 800
CONFIG_FILE = "launcher_config.json"
LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "log.txt"
CONTACT_EMAIL = "threetrue03@gmail.com"
COPYRIGHT_TEXT = "© 2026 조세진. All rights reserved."
LICENSE_TEXT = "본 프로그램의 저작권은 조세진에게 있습니다. 무단 복제, 배포, 수정, 재판매를 금지합니다."

COLORS = {
    "bg": "#f3f6fb",
    "card": "#ffffff",
    "line": "#dbe3ef",
    "line_dark": "#cbd5e1",
    "text": "#111827",
    "muted": "#64748b",
    "primary": "#1f6feb",
    "primary_dark": "#1557c8",
    "primary_light": "#eaf2ff",
    "success": "#16a34a",
    "danger": "#dc2626",
    "warning": "#d97706",
}

FONT_FAMILY = "Malgun Gothic"
TITLE_FONT = (FONT_FAMILY, 22, "bold")
H2_FONT = (FONT_FAMILY, 15, "bold")
TEXT_FONT = (FONT_FAMILY, 10)
TEXT_BOLD = (FONT_FAMILY, 10, "bold")
SMALL_FONT = (FONT_FAMILY, 9)
BUTTON_FONT = (FONT_FAMILY, 10, "bold")

HANGUL_START = ord("가")
HANGUL_END = ord("힣")
JAMO_RANGES = [
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
    (0xA960, 0xA97F),
    (0xD7B0, 0xD7FF),
]

IS_WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
STARTUPINFO = None
if IS_WINDOWS:
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW

SINGLE_INSTANCE_MUTEX_NAME = "WelfareON_Launcher_SingleInstance_Mutex_v1"
ERROR_ALREADY_EXISTS = 183
MB_ICONINFORMATION = 0x00000040
MB_OK = 0x00000000


def resource_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        current = Path(sys.executable).resolve().parent
        # PyInstaller 빌드 결과물을 dist 폴더에서 바로 실행하는 경우,
        # 실제 배포 루트는 dist의 부모 폴더입니다.
        if current.name.lower() == "dist" and (current.parent / "app" / "manage.py").exists():
            return current.parent
        if (current / "app" / "manage.py").exists():
            return current
        if (current.parent / "app" / "manage.py").exists():
            return current.parent
        return current
    return Path(__file__).resolve().parent


BASE_DIR = resource_base_dir()
APP_DIR = BASE_DIR / "app" if (BASE_DIR / "app" / "manage.py").exists() else BASE_DIR
CONFIG_PATH = BASE_DIR / CONFIG_FILE
LOG_DIR = BASE_DIR / LOG_DIR_NAME
LOG_PATH = LOG_DIR / LOG_FILE_NAME
SERVER_PID_PATH = LOG_DIR / "server.pid"
WEBVIEW_PID_PATH = LOG_DIR / "webview.pid"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "launcher_logo.png"
ICON_PATH = ASSETS_DIR / "welfareon.ico"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_log(text: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as target:
        target.write(f"[{now_text()}] {text}\n")


def build_subprocess_env(extra: dict | None = None) -> dict:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("PYTHONLEGACYWINDOWSSTDIO", "0")
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    return env


def run_hidden(cmd, cwd=None, timeout=None, check=True):
    append_log("실행: " + " ".join(str(x) for x in cmd))
    proc = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd or APP_DIR),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=STARTUPINFO,
        creationflags=CREATE_NO_WINDOW,
        env=build_subprocess_env(),
        timeout=timeout,
    )
    if proc.stdout:
        append_log(proc.stdout.rstrip())
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stdout.strip() or f"명령 실패: {cmd}")
    return proc



def run_hidden_stream(cmd, cwd=None, check=True, on_output=None, input_text: str | None = None):
    append_log("실행: " + " ".join(str(x) for x in cmd))
    proc = subprocess.Popen(
        [str(x) for x in cmd],
        cwd=str(cwd or APP_DIR),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        startupinfo=STARTUPINFO,
        creationflags=CREATE_NO_WINDOW,
        env=build_subprocess_env(),
    )
    if input_text is not None and proc.stdin is not None:
        try:
            proc.stdin.write(input_text)
            proc.stdin.close()
        except Exception as exc:
            append_log("표준 입력 전달 실패: " + str(exc))
    lines = []
    assert proc.stdout is not None
    for raw_line in proc.stdout:
        line = raw_line.rstrip()
        if not line:
            continue
        lines.append(line)
        append_log(line)
        if on_output:
            on_output(line)
    return_code = proc.wait()
    if check and return_code != 0:
        tail = "\n".join(lines[-20:]).strip()
        raise RuntimeError(tail or f"명령 실패: {cmd}")
    return return_code, "\n".join(lines)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    data.setdefault("initialized", False)
    data.setdefault("port", DEFAULT_PORT)
    data.setdefault("department_name", "")
    data.setdefault("organization_name", "")
    data.setdefault("spreadsheet_id", "")
    data.setdefault("service_account_path", "")
    return data


def save_config(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_department_name(value: str) -> str:
    value = strip_student_council_suffix(value)
    return f"{value} 학생회" if value else ""


def strip_student_council_suffix(value: str) -> str:
    value = str(value or "").strip()
    return value[:-3].strip() if value.endswith("학생회") else value


def contains_hangul(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if HANGUL_START <= code <= HANGUL_END:
            return True
        for start, end in JAMO_RANGES:
            if start <= code <= end:
                return True
    return False


def sanitize_password(text: str) -> str:
    # 비밀번호 입력칸 안에서만 적용한다. Windows 한/영 상태는 절대 건드리지 않는다.
    return "".join(ch for ch in text if 33 <= ord(ch) <= 126 and not contains_hangul(ch))


def find_python_command():
    candidates = []
    if not getattr(sys, "frozen", False):
        candidates.append([sys.executable])
    candidates.extend([["py", "-3.12"], ["python"], ["python3"], ["py", "-3"]])
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd + ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, startupinfo=STARTUPINFO, creationflags=CREATE_NO_WINDOW, env=build_subprocess_env(), timeout=5
            )
            if proc.returncode != 0:
                continue
            version_text = (proc.stdout or "").strip().splitlines()[-1]
            parts = [int(part) for part in version_text.split(".")[:2]]
            if parts == [3, 12]:
                return cmd
            append_log(f"Python 3.12가 아닌 실행 파일 제외: {' '.join(cmd)} / {version_text}")
        except Exception:
            continue
    return None


def venv_python() -> Path:
    if IS_WINDOWS:
        return APP_DIR / ".venv" / "Scripts" / "python.exe"
    return APP_DIR / ".venv" / "bin" / "python"


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((SERVER_HOST, int(port))) == 0


def welfare_health_ok(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{SERVER_HOST}:{port}/health/", timeout=2) as response:
            body = response.read(2048).decode("utf-8", errors="ignore")
        return "WelfareON" in body and "ok" in body
    except Exception:
        return False


def wait_server(port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if welfare_health_ok(port):
            return True
        time.sleep(0.35)
    return False


def is_welfare_server_running(port: int) -> bool:
    return port_open(port) and welfare_health_ok(port)


def write_server_pid(pid: int) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        SERVER_PID_PATH.write_text(str(pid), encoding="utf-8")
    except Exception as exc:
        append_log("서버 PID 저장 실패: " + str(exc))


def read_server_pid() -> int | None:
    try:
        if SERVER_PID_PATH.exists():
            value = SERVER_PID_PATH.read_text(encoding="utf-8").strip()
            return int(value) if value.isdigit() else None
    except Exception:
        return None
    return None


def is_pid_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        if IS_WINDOWS:
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return exit_code.value == 259
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def write_webview_pid(pid: int) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        WEBVIEW_PID_PATH.write_text(str(pid), encoding="utf-8")
    except Exception as exc:
        append_log("웹뷰 PID 저장 실패: " + str(exc))


def read_webview_pid() -> int | None:
    try:
        if WEBVIEW_PID_PATH.exists():
            value = WEBVIEW_PID_PATH.read_text(encoding="utf-8").strip()
            return int(value) if value.isdigit() else None
    except Exception:
        return None
    return None


def clear_webview_pid(expected_pid: int | None = None) -> None:
    try:
        if WEBVIEW_PID_PATH.exists():
            if expected_pid is not None:
                current = read_webview_pid()
                if current and int(current) != int(expected_pid):
                    return
            WEBVIEW_PID_PATH.unlink()
    except Exception:
        pass


def find_webview_process_ids() -> set[int]:
    """PID 파일이 꼬였을 때도 --webview로 실행된 복지온 내부 창을 찾아낸다."""
    pids: set[int] = set()
    pid = read_webview_pid()
    if pid and is_pid_running(pid):
        pids.add(int(pid))
    if not IS_WINDOWS:
        return pids
    try:
        command = (
            "$self=$PID; "
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.ProcessId -ne $self -and $_.CommandLine -and "
            "$_.CommandLine -like '*--webview*' -and "
            "($_.CommandLine -like '*WelfareOn*' -or $_.CommandLine -like '*복지온*' -or $_.CommandLine -like '*WelfareON*') } | "
            "ForEach-Object { $_.ProcessId }"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            startupinfo=STARTUPINFO,
            creationflags=CREATE_NO_WINDOW,
            env=build_subprocess_env(),
            timeout=5,
        )
        for line in (proc.stdout or "").splitlines():
            value = line.strip()
            if value.isdigit():
                pids.add(int(value))
    except Exception as exc:
        append_log("웹뷰 프로세스 탐색 실패: " + str(exc))
    return {pid for pid in pids if is_pid_running(pid)}


def find_pids_on_port(port: int) -> set[int]:
    pids: set[int] = set()
    if not IS_WINDOWS:
        return pids
    try:
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            startupinfo=STARTUPINFO,
            creationflags=CREATE_NO_WINDOW,
            env=build_subprocess_env(),
            timeout=8,
        )
        target = f":{int(port)}"
        for line in (proc.stdout or "").splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            local_addr = parts[1]
            state = parts[3].upper() if len(parts) >= 5 else ""
            pid_text = parts[-1]
            if local_addr.endswith(target) and state == "LISTENING" and pid_text.isdigit():
                pids.add(int(pid_text))
    except Exception as exc:
        append_log("포트 점유 PID 탐색 실패: " + str(exc))
    return {pid for pid in pids if is_pid_running(pid)}


def is_webview_running() -> bool:
    pids = find_webview_process_ids()
    if pids:
        return True
    clear_webview_pid()
    return False


def stop_webview() -> bool:
    pids = find_webview_process_ids()
    if not pids:
        clear_webview_pid()
        return False
    for pid in sorted(pids):
        if is_pid_running(pid):
            append_log(f"웹뷰 종료 요청: PID {pid}")
            kill_pid(pid)
    time.sleep(0.7)
    for pid in sorted(find_webview_process_ids()):
        if is_pid_running(pid):
            append_log(f"잔여 웹뷰 강제 종료 재시도: PID {pid}")
            kill_pid(pid)
    clear_webview_pid()
    return True


def kill_pid(pid: int) -> None:
    if not pid:
        return
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=STARTUPINFO, creationflags=CREATE_NO_WINDOW)
        else:
            os.kill(pid, 15)
    except Exception as exc:
        append_log("PID 종료 실패: " + str(exc))


def clear_server_pid() -> None:
    try:
        if SERVER_PID_PATH.exists():
            SERVER_PID_PATH.unlink()
    except Exception:
        pass


def maybe_copy_logo_from_upload():
    ASSETS_DIR.mkdir(exist_ok=True)
    if LOGO_PATH.exists():
        return
    # 배포본에 로고가 없을 때를 대비한 단순 placeholder. 사용자는 assets/launcher_logo.png로 교체 가능.
    try:
        import base64
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAARUlEQVR4nO3BAQ0AAADCoPdPbQ43oAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4D8GgAAB+S7jAAAAAElFTkSuQmCC"
        )
        LOGO_PATH.write_bytes(png)
    except Exception:
        pass


def open_webview_process(url: str) -> tuple[bool, str]:
    """내부 WebView 창을 하나만 실행한다."""
    if is_webview_running():
        append_log("웹뷰 중복 실행 차단: 기존 창 사용")
        return True, "이미 프로그램 창이 실행 중입니다."

    clear_webview_pid()
    append_log("웹뷰 실행 준비: " + url)
    try:
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--webview", url]
            cwd = BASE_DIR
        else:
            py = venv_python()
            if not py.exists():
                py_cmd = find_python_command()
                if not py_cmd:
                    raise RuntimeError("Python을 찾을 수 없습니다.")
                cmd = py_cmd + [str(Path(__file__).resolve()), "--webview", url]
                cwd = BASE_DIR
            else:
                ensure_pywebview(py)
                cmd = [str(py), str(Path(__file__).resolve()), "--webview", url]
                cwd = BASE_DIR

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        webview_log_path = LOG_DIR / "webview.log"
        with webview_log_path.open("a", encoding="utf-8") as log_handle:
            log_handle.write(f"[{now_text()}] 웹뷰 프로세스 실행: {' '.join(str(x) for x in cmd)}\n")
            log_handle.flush()
            proc = subprocess.Popen(
                [str(x) for x in cmd],
                cwd=str(cwd),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                startupinfo=STARTUPINFO,
                creationflags=CREATE_NO_WINDOW,
                close_fds=True,
                env=build_subprocess_env(),
            )
        write_webview_pid(proc.pid)

        # exe 환경에서는 WebView 초기화가 늦게 끝날 수 있으므로 즉시 종료 여부를 조금 더 오래 확인합니다.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if proc.poll() is not None:
                clear_webview_pid(proc.pid)
                message = "내부 창 실행 직후 종료되었습니다. WebView 실행 모듈 또는 WebView2 Runtime을 확인해야 합니다."
                append_log(message + f" 종료 코드: {proc.returncode}")
                return False, message
            time.sleep(0.5)

        append_log(f"웹뷰 실행 완료: PID {proc.pid}")
        return True, "프로그램 창을 열었습니다."
    except Exception as exc:
        clear_webview_pid()
        message = "내부 창 실행 실패: " + str(exc)
        append_log(message)
        return False, message

def ensure_pywebview(python_exe: Path):
    test = subprocess.run(
        [str(python_exe), "-c", "import webview"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        startupinfo=STARTUPINFO,
        creationflags=CREATE_NO_WINDOW,
        env=build_subprocess_env(),
    )
    if test.returncode == 0:
        return
    append_log("pywebview 설치 시작")
    run_hidden([python_exe, "-m", "pip", "install", "pywebview>=5.0"], cwd=BASE_DIR, check=True)
    append_log("pywebview 설치 완료")


def run_webview_mode(url: str):
    try:
        import webview
    except Exception as exc:
        if getattr(sys, "frozen", False):
            append_log("웹뷰 로드 실패: exe에 WebView 실행 모듈이 포함되지 않았습니다. " + str(exc))
            raise RuntimeError("exe에 WebView 실행 모듈이 포함되지 않았습니다. build_launcher.bat으로 런처를 다시 빌드해주세요.") from exc
        py = Path(sys.executable)
        try:
            ensure_pywebview(py)
            import webview
        except Exception as inner_exc:
            append_log("웹뷰 로드 실패: " + str(inner_exc))
            raise

    title = APP_NAME
    window = webview.create_window(title, url, width=1280, height=820, resizable=True, text_select=True)

    def lock_internal_navigation():
        script = r'''
        (function(){
          if (window.__welfareWebviewLocked) return;
          window.__welfareWebviewLocked = true;
          window.open = function(){ return null; };
          document.addEventListener('keydown', function(event){
            if (event.shiftKey && event.key === 'Enter') {
              event.preventDefault();
              event.stopPropagation();
            }
          }, true);
          function fixTargets(){
            document.querySelectorAll('a[target], form[target]').forEach(function(el){ el.removeAttribute('target'); });
          }
          document.addEventListener('click', function(event){
            var a = event.target && event.target.closest ? event.target.closest('a') : null;
            if (!a) return;
            var href = a.getAttribute('href') || '';
            if (href.indexOf('http://127.0.0.1') === 0 || href.indexOf('http://localhost') === 0 || href.indexOf('/') === 0 || href.indexOf('#') === 0) return;
            if (/^https?:/i.test(href)) {
              event.preventDefault();
              event.stopPropagation();
            }
          }, true);
          fixTargets();
          new MutationObserver(fixTargets).observe(document.documentElement, {childList:true, subtree:true});
        })();
        '''
        try:
            window.evaluate_js(script)
        except Exception as exc:
            append_log("웹뷰 스크립트 주입 실패: " + str(exc))

    try:
        window.events.loaded += lock_internal_navigation
    except Exception:
        pass
    try:
        webview.start(debug=False)
    finally:
        clear_webview_pid(os.getpid())


def show_already_running_message() -> None:
    message = "이미 복지온 런처가 실행 중입니다.\n기존 창에서 작업을 계속 진행해주세요."
    if IS_WINDOWS:
        try:
            ctypes.windll.user32.MessageBoxW(None, message, "복지온 Launcher", MB_OK | MB_ICONINFORMATION)
            return
        except Exception:
            pass
    try:
        temp = tk.Tk()
        temp.withdraw()
        messagebox.showinfo("복지온 Launcher", message)
        temp.destroy()
    except Exception:
        pass


def acquire_single_instance_lock():
    if not IS_WINDOWS:
        return None, False
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
        if not handle:
            append_log("런처 중복 실행 잠금 생성 실패")
            return None, False
        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            try:
                ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                pass
            append_log("런처 중복 실행 감지: 새 런처를 종료합니다.")
            return None, True
        append_log("런처 중복 실행 잠금 획득")
        return handle, False
    except Exception as exc:
        append_log("런처 중복 실행 잠금 오류: " + str(exc))
        return None, False


def release_single_instance_lock(handle) -> None:
    if not handle or not IS_WINDOWS:
        return
    try:
        ctypes.windll.kernel32.CloseHandle(handle)
        append_log("런처 중복 실행 잠금 해제")
    except Exception:
        pass


class WelfareLauncher:
    def __init__(self):
        append_log("런처 시작")
        self.config = load_config()
        self.server_process = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Launcher")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        # Windows DPI/글꼴 배율에 따라 하단 버튼이 잘리지 않도록 최대 크기 고정을 제거합니다.
        self.root.resizable(True, True)
        self.root.configure(bg=COLORS["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._center_window()
        self._set_icon()
        self._setup_styles()
        self.container = tk.Frame(self.root, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)
        self.after_jobs()
        if self.config.get("initialized"):
            self.show_dashboard()
        else:
            self.show_intro()

    def _center_window(self):
        self.root.update_idletasks()
        x = max((self.root.winfo_screenwidth() - WINDOW_WIDTH) // 2, 0)
        y = max((self.root.winfo_screenheight() - WINDOW_HEIGHT) // 2, 0)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _set_icon(self):
        if ICON_PATH.exists():
            try:
                self.root.iconbitmap(str(ICON_PATH))
            except Exception:
                pass

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Primary.TButton", font=BUTTON_FONT, padding=(16, 8), background=COLORS["primary"], foreground="white")
        style.map(
            "Primary.TButton",
            background=[("disabled", "#cbd5e1"), ("active", COLORS["primary_dark"])],
            foreground=[("disabled", "#64748b")],
        )
        style.configure("Secondary.TButton", font=BUTTON_FONT, padding=(14, 8), background="#eef2f7", foreground=COLORS["text"])
        style.map("Secondary.TButton", background=[("disabled", "#e5e7eb")], foreground=[("disabled", "#94a3b8")])
        style.configure("Danger.TButton", font=BUTTON_FONT, padding=(14, 8), background="#fee2e2", foreground=COLORS["danger"])
        style.map("Danger.TButton", background=[("disabled", "#f1f5f9")], foreground=[("disabled", "#94a3b8")])
        style.configure("TEntry", font=TEXT_FONT, padding=6)
        style.configure("Setup.Horizontal.TProgressbar", troughcolor="#e5e7eb", background=COLORS["primary"], thickness=14)

    def clear(self):
        for child in self.container.winfo_children():
            child.destroy()

    def card(self):
        self.clear()
        outer = tk.Frame(self.container, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True, padx=28, pady=24)
        card = tk.Frame(outer, bg=COLORS["card"], highlightbackground=COLORS["line"], highlightthickness=1)
        card.pack(fill="both", expand=True)
        return card

    def header(self, parent, title, subtitle=""):
        h = tk.Frame(parent, bg=COLORS["card"])
        h.pack(fill="x", padx=28, pady=(22, 12))
        maybe_copy_logo_from_upload()
        if LOGO_PATH.exists():
            try:
                img = tk.PhotoImage(file=str(LOGO_PATH))
                img = img.subsample(max(img.width() // 56, 1), max(img.height() // 56, 1))
                label = tk.Label(h, image=img, bg=COLORS["card"])
                label.image = img
                label.pack(side="left", padx=(0, 14))
            except Exception:
                pass
        text = tk.Frame(h, bg=COLORS["card"])
        text.pack(side="left", fill="x", expand=True)
        tk.Label(text, text=title, bg=COLORS["card"], fg=COLORS["text"], font=TITLE_FONT, anchor="w").pack(fill="x")
        if subtitle:
            tk.Label(text, text=subtitle, bg=COLORS["card"], fg=COLORS["muted"], font=SMALL_FONT, anchor="w").pack(fill="x", pady=(3, 0))

    def footer(self, parent):
        f = tk.Frame(parent, bg=COLORS["card"])
        f.pack(side="bottom", fill="x", padx=28, pady=(4, 18))
        tk.Label(f, text=f"{COPYRIGHT_TEXT}   문의: {CONTACT_EMAIL}", bg=COLORS["card"], fg=COLORS["muted"], font=SMALL_FONT).pack(anchor="w")

    def show_intro(self):
        c = self.card()
        self.header(c, "복지온 Launcher", "학생회 복지 운영 시스템을 시작합니다.")
        body = tk.Frame(c, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=28, pady=(2, 6))
        left = self.info_box(body, "현재 상태", ["초기 설정이 필요합니다.", "학과(부) 명과 관리자 계정을 먼저 등록합니다."])
        left.place(x=0, y=0, width=405, height=220)
        right = self.info_box(body, "진행 단계", ["1. 학과(부) 명 입력", "2. 관리자 계정 생성", "3. 프로그램 환경 설정", "4. 구글 시트 연동 선택", "5. 프로그램 실행"])
        right.place(x=430, y=0, width=430, height=220)
        desc = tk.Label(body, text="처음 한 번만 설정하면 다음 실행부터는 대시보드형 런처만 표시됩니다.", bg=COLORS["card"], fg=COLORS["muted"], font=TEXT_FONT, anchor="w")
        desc.place(x=0, y=245, width=860, height=32)
        btn = ttk.Button(body, text="초기 설정 시작", style="Primary.TButton", command=self.show_initial_form)
        btn.place(x=686, y=310, width=174, height=42)
        self.footer(c)

    def info_box(self, parent, title, lines):
        box = tk.Frame(parent, bg="#f8fafc", highlightbackground=COLORS["line"], highlightthickness=1)
        tk.Label(box, text=title, bg="#f8fafc", fg=COLORS["text"], font=H2_FONT, anchor="w").pack(fill="x", padx=18, pady=(16, 8))
        for line in lines:
            tk.Label(box, text=line, bg="#f8fafc", fg=COLORS["muted"], font=TEXT_FONT, anchor="w").pack(fill="x", padx=18, pady=2)
        return box

    def show_initial_form(self):
        c = self.card()
        self.header(c, "초기 설정", "학과(부) 명과 최초 관리자 계정을 입력해주세요.")
        body = tk.Frame(c, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 0))
        self.org_var = tk.StringVar(value=strip_student_council_suffix(self.config.get("department_name") or self.config.get("organization_name") or ""))
        self.name_var = tk.StringVar()
        self.student_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.password_confirm_var = tk.StringVar()
        self.form_error = tk.StringVar(value="비밀번호는 영문, 숫자, 특수문자만 입력할 수 있습니다.")
        self._password_guard(self.password_var)
        self._password_guard(self.password_confirm_var)
        self._digits_guard(self.student_var)

        labels = ["학과(부) 명", "관리자 이름", "관리자 학번", "관리자 비밀번호", "비밀번호 확인"]
        vars_ = [self.org_var, self.name_var, self.student_var, self.password_var, self.password_confirm_var]
        shows = [None, None, None, "*", "*"]
        y = 8
        for label, var, show in zip(labels, vars_, shows):
            tk.Label(body, text=label, bg=COLORS["card"], fg=COLORS["text"], font=TEXT_BOLD, anchor="w").place(x=36, y=y, width=180, height=26)
            ent = ttk.Entry(body, textvariable=var, show=show or "")
            ent.place(x=220, y=y, width=520, height=34)
            y += 48
        tk.Label(body, textvariable=self.form_error, bg=COLORS["card"], fg=COLORS["muted"], font=SMALL_FONT, anchor="w").place(x=220, y=y-8, width=560, height=24)
        ttk.Button(body, text="이전", style="Secondary.TButton", command=self.show_intro).place(x=565, y=300, width=85, height=40)
        ttk.Button(body, text="다음", style="Primary.TButton", command=self.start_environment_setup).place(x=660, y=300, width=110, height=40)
        self.footer(c)

    def _password_guard(self, var: tk.StringVar):
        busy = {"value": False}
        def on_change(*_):
            if busy["value"]:
                return
            text = var.get()
            cleaned = sanitize_password(text)
            if text != cleaned:
                busy["value"] = True
                var.set(cleaned)
                busy["value"] = False
                if hasattr(self, "form_error"):
                    self.form_error.set("한글은 입력할 수 없습니다. 영문, 숫자, 특수문자만 입력해주세요.")
        var.trace_add("write", on_change)

    def _digits_guard(self, var: tk.StringVar):
        busy = {"value": False}
        def on_change(*_):
            if busy["value"]:
                return
            text = var.get()
            cleaned = "".join(ch for ch in text if ch.isdigit())
            if text != cleaned:
                busy["value"] = True
                var.set(cleaned)
                busy["value"] = False
                if hasattr(self, "form_error"):
                    self.form_error.set("관리자 학번은 숫자만 입력할 수 있습니다.")
        var.trace_add("write", on_change)

    def validate_initial_form(self):
        org = self.org_var.get().strip()
        name = self.name_var.get().strip()
        sid = self.student_var.get().strip()
        pw = sanitize_password(self.password_var.get())
        pw2 = sanitize_password(self.password_confirm_var.get())
        self.password_var.set(pw)
        self.password_confirm_var.set(pw2)
        if not org:
            return "학과(부) 명을 입력해주세요."
        if not name:
            return "관리자 이름을 입력해주세요."
        if not sid:
            return "관리자 학번을 입력해주세요."
        if not sid.isdigit():
            return "관리자 학번은 숫자만 입력할 수 있습니다."
        if not pw:
            return "관리자 비밀번호를 입력해주세요."
        if pw != pw2:
            return "비밀번호 확인이 일치하지 않습니다."
        return ""

    def start_environment_setup(self):
        err = self.validate_initial_form()
        if err:
            self.form_error.set(err)
            return
        department_name = strip_student_council_suffix(self.org_var.get().strip())
        organization_name = normalize_department_name(department_name)
        self.admin_info = {
            "department_name": department_name,
            "organization_name": organization_name,
            "name": self.name_var.get().strip(),
            "student_id": self.student_var.get().strip(),
            "password": sanitize_password(self.password_var.get()),
        }
        self.show_progress("프로그램 환경 설정")
        threading.Thread(target=self.environment_worker, daemon=True).start()

    def show_progress(self, title):
        c = self.card()
        self.header(c, title, "자동 설정을 진행합니다. 현재 세부 작업과 출력 로그를 확인할 수 있습니다.")

        self.progress_step_var = tk.StringVar(value="대기 중")
        self.progress_detail_var = tk.StringVar(value="설정을 시작할 준비를 하고 있습니다.")
        self.progress_percent_var = tk.StringVar(value="진행률 0%")

        body = tk.Frame(c, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 10))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(7, weight=1)

        tk.Label(body, text="현재 작업", bg=COLORS["card"], fg=COLORS["text"], font=TEXT_BOLD, anchor="w").grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(body, textvariable=self.progress_step_var, bg=COLORS["primary_light"], fg=COLORS["primary_dark"], font=TEXT_BOLD, anchor="w", padx=12).grid(row=1, column=0, sticky="ew", ipady=9)

        tk.Label(body, text="세부 작업", bg=COLORS["card"], fg=COLORS["text"], font=TEXT_BOLD, anchor="w").grid(row=2, column=0, sticky="ew", pady=(14, 6))
        self.progress_detail_label = tk.Label(
            body,
            textvariable=self.progress_detail_var,
            bg="#f8fafc",
            fg=COLORS["muted"],
            font=SMALL_FONT,
            anchor="w",
            justify="left",
            padx=12,
            wraplength=900,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
        )
        self.progress_detail_label.grid(row=3, column=0, sticky="ew", ipady=9)

        progress_header = tk.Frame(body, bg=COLORS["card"])
        progress_header.grid(row=4, column=0, sticky="ew", pady=(14, 6))
        progress_header.columnconfigure(0, weight=1)
        tk.Label(progress_header, text="진행률", bg=COLORS["card"], fg=COLORS["text"], font=TEXT_BOLD, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(progress_header, textvariable=self.progress_percent_var, bg=COLORS["card"], fg=COLORS["primary_dark"], font=TEXT_BOLD, anchor="e").grid(row=0, column=1, sticky="e")
        self.progress_bar = ttk.Progressbar(body, style="Setup.Horizontal.TProgressbar", mode="determinate", maximum=100, value=0)
        self.progress_bar.grid(row=5, column=0, sticky="ew")

        tk.Label(body, text="작업 출력", bg=COLORS["card"], fg=COLORS["text"], font=TEXT_BOLD, anchor="w").grid(row=6, column=0, sticky="ew", pady=(16, 6))
        output_frame = tk.Frame(body, bg="#f8fafc", highlightbackground=COLORS["line"], highlightthickness=1)
        output_frame.grid(row=7, column=0, sticky="nsew")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.progress_text = tk.Text(
            output_frame,
            height=10,
            wrap="word",
            bg="#f8fafc",
            fg=COLORS["text"],
            font=SMALL_FONT,
            relief="flat",
            padx=12,
            pady=10,
        )
        self.progress_scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.progress_text.yview)
        self.progress_text.configure(state="disabled", yscrollcommand=self.progress_scrollbar.set)
        self.progress_text.grid(row=0, column=0, sticky="nsew")
        self.progress_scrollbar.grid(row=0, column=1, sticky="ns")

        action_bar = tk.Frame(c, bg=COLORS["card"])
        action_bar.pack(fill="x", padx=28, pady=(0, 12))
        action_bar.columnconfigure(1, weight=1)
        ttk.Button(action_bar, text="로그 파일 보기", style="Secondary.TButton", command=self.open_log).grid(row=0, column=0, sticky="w", ipadx=10, ipady=3)
        self.progress_next_btn = ttk.Button(action_bar, text="구글 시트 연동으로 이동", style="Primary.TButton", command=self.show_google_sheet_setup, state="disabled")
        self.progress_next_btn.grid(row=0, column=2, sticky="e", ipadx=10, ipady=3)

        self.footer(c)

    def queue_log(self, text):
        append_log(text)
        self.log_queue.put(text)

    def queue_user_log(self, text):
        self.queue_log(text)

    def set_progress(self, percent: int, step: str, detail: str) -> None:
        self.log_queue.put(f"PROGRESS::{percent}::{step}::{detail}")
        self.queue_log(f"[{percent}%] {step} - {detail}")

    def environment_worker(self):
        try:
            self.set_progress(3, "환경 설정 시작", "초기 설정 정보를 확인하고 작업 로그를 준비하고 있습니다.")
            self.set_progress(8, "프로그램 폴더 확인", "manage.py와 실행 폴더 구조를 확인하고 있습니다.")
            if not (APP_DIR / "manage.py").exists():
                raise RuntimeError(f"manage.py를 찾을 수 없습니다: {APP_DIR}")
            APP_DIR.joinpath("auth").mkdir(exist_ok=True)
            APP_DIR.joinpath("credentials").mkdir(exist_ok=True)
            self.queue_log("프로그램 폴더 확인 완료")

            self.set_progress(16, "Python 환경 확인", "사용 가능한 Python 3.12 실행 파일을 찾고 있습니다.")
            py_cmd = find_python_command()
            if not py_cmd:
                raise RuntimeError("Python 3.12.x를 찾을 수 없습니다. Python 3.12를 설치한 뒤 다시 실행해주세요.")
            self.queue_log("Python 실행 파일: " + " ".join(str(x) for x in py_cmd))

            self.set_progress(28, "가상환경 준비", "app/.venv 가상환경을 생성하거나 기존 환경을 확인하고 있습니다.")
            py = venv_python()
            if not py.exists():
                self.queue_log("가상환경 생성 시작")
                run_hidden_stream(py_cmd + ["-m", "venv", str(APP_DIR / ".venv")], cwd=APP_DIR, on_output=self.log_queue.put)
                self.queue_log("가상환경 생성 완료")
            else:
                self.queue_log("기존 가상환경 확인 완료")

            self.set_progress(45, "필수 패키지 설치", "requirements.txt 기준으로 Django와 필수 패키지를 설치하고 있습니다. 처음 설치 시 1~5분 정도 걸릴 수 있습니다.")
            req = APP_DIR / "requirements.txt"
            if req.exists():
                self.queue_user_log("필수 패키지 설치를 시작했습니다. 잠시만 기다려주세요.")
                run_hidden_stream([py, "-m", "pip", "install", "-r", req], cwd=APP_DIR)
                self.queue_user_log("필수 패키지 설치 완료")
            else:
                self.queue_log("requirements.txt가 없어 필수 패키지 설치를 건너뜁니다.")

            self.set_progress(62, "추가 실행 패키지 확인", "내부 창 실행에 필요한 pywebview 패키지를 확인하고 있습니다.")
            self.queue_user_log("내부 창 실행 패키지를 확인하고 있습니다.")
            run_hidden_stream([py, "-m", "pip", "install", "pywebview>=5.0"], cwd=APP_DIR, check=False)
            self.queue_user_log("내부 창 실행 패키지 확인 완료")

            self.set_progress(76, "데이터베이스 준비", "기존 테스트 DB를 정리하고 새 데이터베이스를 초기화하고 있습니다.")
            db_path = APP_DIR / "db.sqlite3"
            if db_path.exists():
                try:
                    db_path.unlink()
                    self.queue_log("기존 테스트 DB 삭제 완료")
                except Exception as exc:
                    raise RuntimeError("기존 DB 파일을 삭제할 수 없습니다. 프로그램을 모두 종료한 뒤 다시 실행해주세요. " + str(exc))
            site_config = APP_DIR / "config" / "welfare_site.json"
            if site_config.exists():
                try:
                    site_config.unlink()
                    self.queue_log("기존 사이트 설정 파일 정리 완료")
                except Exception:
                    pass
            self.queue_user_log("데이터베이스 구조를 준비하고 있습니다.")
            run_hidden_stream([py, "manage.py", "migrate", "--noinput"], cwd=APP_DIR)
            self.queue_user_log("학생 정보 테이블 확인 완료")
            self.queue_user_log("물품 관리 테이블 확인 완료")
            self.queue_user_log("대여 기록 테이블 확인 완료")

            self.set_progress(92, "관리자 계정 생성", "입력한 관리자 정보로 최초 관리자 계정과 관리자 CSV를 생성하고 있습니다.")
            info = self.admin_info
            cmd = [py, "manage.py", "bootstrap_welfare", "--organization-name", info["department_name"], "--name", info["name"], "--student-id", info["student_id"], "--password-stdin", "--contact-email", CONTACT_EMAIL]
            run_hidden_stream(cmd, cwd=APP_DIR, input_text=info["password"] + "\n")
            self.queue_user_log("관리자 계정 생성 완료")
            self.queue_user_log("학과(부) 명 저장 완료")
            self.config.update({
                "initialized": True,
                "department_name": info["department_name"],
                "organization_name": info["organization_name"],
                "contact_email": CONTACT_EMAIL,
                "spreadsheet_id": "",
                "service_account_path": "",
            })
            self.set_progress(98, "설정 저장 및 정리", "구글 시트 테스트 값과 임시 설정을 정리하고 최종 설정을 저장하고 있습니다.")
            self.clear_google_sheet_files()
            save_config(self.config)
            self.log_queue.put("DONE::환경 설정 완료")
        except Exception as exc:
            self.log_queue.put("ERROR::" + str(exc))
            append_log("환경 설정 실패: " + str(exc))

    def clear_google_sheet_files(self):
        # 구글 시트 연동을 건너뛰거나 초기화할 때 남은 테스트 값/파일을 제거한다.
        for rel in ["auth/google_sheets.json", "auth/google_service_account.json", "credentials/service-account.json"]:
            try:
                target = APP_DIR / rel
                if target.exists():
                    target.unlink()
            except Exception as exc:
                append_log(f"구글 시트 파일 정리 실패: {rel} / {exc}")

    def save_app_google_sheet_config(self, spreadsheet_id: str, service_account_path: str = ""):
        # 런처 설정과 웹사이트 설정 파일을 함께 저장한다. 웹사이트는 app/auth/google_sheets.json을 읽는다.
        target = APP_DIR / "auth" / "google_sheets.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        saved = {
            "spreadsheet_id": "",
            "service_account_path": "",
            "last_synced_at": "",
            "last_synced_date": "",
            "last_error": "",
        }
        if target.exists():
            try:
                current = json.loads(target.read_text(encoding="utf-8"))
                if isinstance(current, dict):
                    saved.update({key: str(value) for key, value in current.items() if value is not None})
            except Exception as exc:
                append_log("기존 구글 시트 설정 읽기 실패: " + str(exc))
        saved["spreadsheet_id"] = str(spreadsheet_id or "").strip()
        saved["service_account_path"] = str(service_account_path or "").strip()
        saved["last_error"] = ""
        target.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
        append_log("웹사이트 구글 시트 설정 저장 완료")

    def sync_google_sheet_config_to_app(self):
        spreadsheet_id = str(self.config.get("spreadsheet_id") or "").strip()
        service_account_path = str(self.config.get("service_account_path") or "").strip()
        if not spreadsheet_id and not service_account_path:
            return
        relative_path = "credentials/service-account.json" if (APP_DIR / "credentials" / "service-account.json").exists() else service_account_path
        self.save_app_google_sheet_config(spreadsheet_id, relative_path)

    def show_setup_done(self):
        c = self.card()
        self.header(c, "프로그램 환경 설정 완료", "다음 버튼을 누르면 구글 시트 연동 단계로 이동합니다.")
        body = tk.Frame(c, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 0))
        box = self.info_box(body, "완료된 작업", ["가상환경 준비 완료", "필수 패키지 설치 완료", "데이터베이스 준비 완료", "관리자 계정 생성 완료"])
        box.place(x=0, y=0, width=860, height=210)
        ttk.Button(body, text="로그 파일 보기", style="Secondary.TButton", command=self.open_log).place(x=540, y=300, width=130, height=40)
        ttk.Button(body, text="다음", style="Primary.TButton", command=self.show_google_sheet_setup).place(x=680, y=300, width=120, height=40)
        self.footer(c)

    def show_google_sheet_setup(self):
        c = self.card()
        self.header(c, "구글 시트 연동", "선택 사항입니다. 나중에 프로그램 안에서 다시 설정할 수 있습니다.")
        body = tk.Frame(c, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 0))
        self.sheet_var = tk.StringVar(value="")
        self.json_var = tk.StringVar(value="")
        tk.Label(body, text="스프레드시트 ID", bg=COLORS["card"], fg=COLORS["text"], font=TEXT_BOLD, anchor="w").place(x=40, y=30, width=160, height=30)
        ttk.Entry(body, textvariable=self.sheet_var).place(x=205, y=30, width=550, height=34)
        tk.Label(body, text="서비스 계정 JSON", bg=COLORS["card"], fg=COLORS["text"], font=TEXT_BOLD, anchor="w").place(x=40, y=90, width=160, height=30)
        ttk.Entry(body, textvariable=self.json_var).place(x=205, y=90, width=430, height=34)
        ttk.Button(body, text="파일 선택", style="Secondary.TButton", command=self.select_json).place(x=645, y=88, width=110, height=38)
        tk.Label(body, text="구글 시트 연동을 건너뛰어도 프로그램은 정상 실행됩니다.", bg=COLORS["card"], fg=COLORS["muted"], font=SMALL_FONT, anchor="w").place(x=205, y=145, width=550, height=28)
        ttk.Button(body, text="건너뛰기", style="Secondary.TButton", command=self.finish_setup).place(x=560, y=300, width=100, height=40)
        ttk.Button(body, text="저장하고 다음", style="Primary.TButton", command=self.save_sheet_and_finish).place(x=670, y=300, width=130, height=40)
        self.footer(c)

    def select_json(self):
        path = filedialog.askopenfilename(title="서비스 계정 JSON 선택", filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if path:
            self.json_var.set(path)

    def save_sheet_and_finish(self):
        spreadsheet_id = self.sheet_var.get().strip()
        src = self.json_var.get().strip()
        service_account_relative_path = ""
        self.config["spreadsheet_id"] = spreadsheet_id
        self.config["service_account_path"] = ""
        if src:
            try:
                target = APP_DIR / "credentials" / "service-account.json"
                target.parent.mkdir(exist_ok=True)
                if Path(src).resolve() != target.resolve():
                    shutil.copyfile(src, target)
                service_account_relative_path = "credentials/service-account.json"
                self.config["service_account_path"] = str(target)
            except Exception as exc:
                messagebox.showerror("구글 시트 설정", f"JSON 파일을 저장하지 못했습니다.\n{exc}")
                return
        elif (APP_DIR / "credentials" / "service-account.json").exists():
            service_account_relative_path = "credentials/service-account.json"
            self.config["service_account_path"] = str(APP_DIR / "credentials" / "service-account.json")

        if not spreadsheet_id and not service_account_relative_path:
            self.clear_google_sheet_files()
        else:
            self.save_app_google_sheet_config(spreadsheet_id, service_account_relative_path)
        save_config(self.config)
        self.show_dashboard()

    def finish_setup(self):
        self.config["spreadsheet_id"] = ""
        self.config["service_account_path"] = ""
        self.clear_google_sheet_files()
        save_config(self.config)
        self.show_dashboard()

    def show_dashboard(self):
        c = self.card()
        self.sync_google_sheet_config_to_app()
        org = self.config.get("organization_name") or normalize_department_name(self.config.get("department_name", "")) or "학과(부)명 학생회"
        self.header(c, "복지온 Launcher", f"{org} 복지 운영 시스템")
        body = tk.Frame(c, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 0))
        port = int(self.config.get("port", DEFAULT_PORT))
        initial_status = "프로그램 실행 중" if is_webview_running() else ("서버 실행 중" if is_welfare_server_running(port) else "프로그램이 꺼져 있습니다.")
        self.status_var = tk.StringVar(value=initial_status)
        left = tk.Frame(body, bg="#f8fafc", highlightbackground=COLORS["line"], highlightthickness=1)
        left.place(x=0, y=0, width=410, height=260)
        tk.Label(left, text="프로그램 상태", bg="#f8fafc", fg=COLORS["text"], font=H2_FONT, anchor="w").pack(fill="x", padx=18, pady=(18, 8))
        tk.Label(left, textvariable=self.status_var, bg="#f8fafc", fg=COLORS["muted"], font=TEXT_FONT, anchor="w").pack(fill="x", padx=18, pady=2)
        button_area = tk.Frame(left, bg="#f8fafc")
        button_area.pack(fill="x", padx=18, pady=(28, 0))
        self.start_button = ttk.Button(button_area, text="프로그램 시작", style="Primary.TButton", command=self.start_program)
        self.start_button.pack(anchor="w", fill="x", pady=(0, 10), ipady=2)
        self.stop_button = ttk.Button(button_area, text="프로그램 종료", style="Danger.TButton", command=self.stop_program)
        self.stop_button.pack(anchor="w", fill="x", pady=(0, 0), ipady=2)
        right = tk.Frame(body, bg="#f8fafc", highlightbackground=COLORS["line"], highlightthickness=1)
        right.place(x=435, y=0, width=425, height=260)
        tk.Label(right, text="설정 상태", bg="#f8fafc", fg=COLORS["text"], font=H2_FONT, anchor="w").pack(fill="x", padx=18, pady=(18, 8))
        lines = [
            f"학과(부) 명: {strip_student_council_suffix(org)}",
            "관리자 설정: 완료",
            "데이터베이스: 완료",
            "구글 시트 연동: " + ("설정됨" if self.config.get("spreadsheet_id") else "미설정"),
        ]
        for line in lines:
            tk.Label(right, text=line, bg="#f8fafc", fg=COLORS["muted"], font=TEXT_FONT, anchor="w").pack(fill="x", padx=18, pady=3)
        ttk.Button(right, text="로그 보기", style="Secondary.TButton", command=self.open_log).pack(anchor="w", padx=18, pady=(18, 4), ipadx=12)
        info = tk.Frame(body, bg=COLORS["card"])
        info.place(x=0, y=286, width=860, height=78)
        tk.Label(info, text=LICENSE_TEXT, bg=COLORS["card"], fg=COLORS["muted"], font=SMALL_FONT, anchor="w").pack(fill="x")
        tk.Label(info, text=f"문의: {CONTACT_EMAIL}  ·  Instagram: 추후 공개 예정", bg=COLORS["card"], fg=COLORS["muted"], font=SMALL_FONT, anchor="w").pack(fill="x", pady=(6, 0))
        self.footer(c)

    def set_starting_ui(self, is_starting: bool, text: str | None = None):
        if hasattr(self, "start_button"):
            self.start_button.configure(state="disabled" if is_starting else "normal")
            self.start_button.configure(text="시작 중..." if is_starting else "프로그램 시작")
        if hasattr(self, "stop_button"):
            self.stop_button.configure(state="disabled" if is_starting else "normal")
        if text and hasattr(self, "status_var"):
            self.status_var.set(text)


    def handle_webview_result(self, ok: bool, message: str, url: str):
        if ok:
            self.status_var.set(message if message.startswith("이미") else "프로그램 실행 중")
            return
        self.status_var.set("내부 창 실행 실패")
        messagebox.showerror(
            "내부 창 실행 실패",
            message + "\n\nlogs/webview.log 또는 logs/log.txt를 확인해주세요."
        )

    def open_webview_with_feedback(self, url: str):
        self.root.after(0, self.status_var.set, "내부 창을 여는 중입니다...")
        append_log("내부 창 실행 단계 시작")
        ok, msg = open_webview_process(url)
        self.root.after(0, self.handle_webview_result, ok, msg, url)

    def start_program(self):
        if hasattr(self, "start_button") and str(self.start_button.cget("state")) == "disabled":
            return
        self.set_starting_ui(True, "서버 상태를 확인하는 중입니다...")
        threading.Thread(target=self.start_program_worker, daemon=True).start()

    def start_program_worker(self):
        port = int(self.config.get("port", DEFAULT_PORT))
        url = f"http://{SERVER_HOST}:{port}/"
        try:
            self.root.after(0, self.status_var.set, "서버 상태를 확인하는 중입니다...")
            if is_welfare_server_running(port):
                append_log("기존 서버 감지: 새 서버를 실행하지 않고 WebView만 엽니다.")
                self.root.after(0, self.status_var.set, "이미 실행 중인 프로그램에 연결합니다.")
                self.root.after(0, self.status_var.set, "내부 창을 여는 중입니다...")
                ok, msg = open_webview_process(url)
                self.root.after(0, self.handle_webview_result, ok, msg, url)
                return
            if port_open(port):
                self.root.after(0, self.status_var.set, "포트 충돌로 시작할 수 없습니다.")
                self.root.after(0, messagebox.showerror, "프로그램 시작 실패", f"{port}번 포트가 다른 프로그램에서 사용 중입니다. 해당 프로그램을 종료한 뒤 다시 실행해주세요.")
                return

            py = venv_python()
            if not py.exists():
                self.root.after(0, messagebox.showerror, "프로그램 시작", "가상환경이 없습니다. 초기 설정을 다시 진행해주세요.")
                self.root.after(0, self.status_var.set, "프로그램 시작 실패")
                return

            self.root.after(0, self.status_var.set, "데이터베이스 업데이트를 확인하는 중입니다...")
            append_log("Django 데이터베이스 마이그레이션 확인")
            _migration_code, migration_output = run_hidden_stream(
                [str(py), "manage.py", "migrate", "--noinput"],
                cwd=APP_DIR,
                on_output=lambda line: append_log("[migrate] " + line),
            )
            migration_applied = any(
                line.strip().startswith("Applying ")
                for line in migration_output.splitlines()
            )
            if migration_applied:
                append_log("프로그램 데이터베이스 업데이트 적용 완료")
                self.root.after(
                    0,
                    messagebox.showinfo,
                    "복지온 업데이트 완료",
                    "새로운 프로그램 업데이트가 적용되었습니다.\n데이터베이스 준비가 완료되었습니다.",
                )
            else:
                append_log("적용할 데이터베이스 업데이트 없음")

            self.root.after(0, self.status_var.set, "서버를 시작하는 중입니다...")
            append_log("Django 서버 실행")
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_handle = open(LOG_PATH, "a", encoding="utf-8")
            try:
                self.server_process = subprocess.Popen(
                    [str(py), "manage.py", "runserver", f"{SERVER_HOST}:{port}", "--noreload"],
                    cwd=str(APP_DIR),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    startupinfo=STARTUPINFO,
                    creationflags=CREATE_NO_WINDOW,
                    env=build_subprocess_env(),
                )
            finally:
                try:
                    log_handle.close()
                except Exception:
                    pass
            write_server_pid(self.server_process.pid)

            self.root.after(0, self.status_var.set, "서버 응답을 확인하는 중입니다...")
            if not wait_server(port, 45):
                self.root.after(0, self.status_var.set, "프로그램 시작 실패")
                try:
                    if self.server_process and self.server_process.poll() is None:
                        self.server_process.terminate()
                        try:
                            self.server_process.wait(timeout=5)
                        except Exception:
                            self.server_process.kill()
                finally:
                    clear_server_pid()
                self.root.after(0, messagebox.showerror, "프로그램 시작 실패", "서버가 정상 응답하지 않습니다. 로그를 확인해주세요.")
                return

            self.root.after(0, self.status_var.set, "서버 실행 완료. 내부 창을 여는 중입니다...")
            ok, msg = open_webview_process(url)
            self.root.after(0, self.handle_webview_result, ok, msg, url)
        except Exception as exc:
            append_log("프로그램 시작 중 오류: " + str(exc))
            self.root.after(0, self.status_var.set, "프로그램 시작 실패")
            self.root.after(0, messagebox.showerror, "프로그램 시작 실패", str(exc))
        finally:
            self.root.after(0, self.set_starting_ui, False, None)

    def stop_program(self):
        if hasattr(self, "stop_button"):
            self.stop_button.configure(state="disabled")
        if hasattr(self, "start_button"):
            self.start_button.configure(state="disabled")
        self.status_var.set("프로그램을 종료하는 중입니다...")
        self.root.update_idletasks()
        try:
            stopped_webview = stop_webview()
            if self.server_process and self.server_process.poll() is None:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                except Exception:
                    self.server_process.kill()
            else:
                pid = read_server_pid()
                if pid and is_pid_running(pid):
                    kill_pid(pid)
                for port_pid in find_pids_on_port(int(self.config.get("port", DEFAULT_PORT))):
                    if port_pid != os.getpid():
                        append_log(f"포트 점유 서버 종료 요청: PID {port_pid}")
                        kill_pid(port_pid)
            clear_server_pid()
            clear_webview_pid()
            self.status_var.set("프로그램이 꺼져 있습니다.")
            append_log("프로그램 종료" + (" - 웹뷰 종료 포함" if stopped_webview else ""))
        finally:
            if hasattr(self, "stop_button"):
                self.stop_button.configure(state="normal")
            if hasattr(self, "start_button"):
                self.start_button.configure(state="normal")

    def open_log(self):
        LOG_DIR.mkdir(exist_ok=True)
        if not LOG_PATH.exists():
            LOG_PATH.write_text("", encoding="utf-8")
        try:
            os.startfile(str(LOG_PATH))
        except Exception:
            messagebox.showinfo("로그 위치", str(LOG_PATH))

    def after_jobs(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item.startswith("PROGRESS::"):
                    _, percent, step, detail = item.split("::", 3)
                    if hasattr(self, "progress_step_var"):
                        self.progress_step_var.set(step)
                    if hasattr(self, "progress_detail_var"):
                        self.progress_detail_var.set(detail)
                    if hasattr(self, "progress_percent_var"):
                        self.progress_percent_var.set(f"진행률 {percent}%")
                    if hasattr(self, "progress_bar"):
                        try:
                            self.progress_bar.configure(value=int(percent), maximum=100)
                        except Exception:
                            pass
                elif item.startswith("STEP::"):
                    if hasattr(self, "progress_step_var"):
                        self.progress_step_var.set(item.replace("STEP::", ""))
                elif item.startswith("DONE::"):
                    if hasattr(self, "progress_step_var"):
                        self.progress_step_var.set("환경 설정 완료")
                    if hasattr(self, "progress_detail_var"):
                        self.progress_detail_var.set("환경 설정이 완료되었습니다. 다음 버튼을 눌러 구글 시트 연동 단계로 이동하세요.")
                    if hasattr(self, "progress_percent_var"):
                        self.progress_percent_var.set("진행률 100%")
                    if hasattr(self, "progress_bar"):
                        try:
                            self.progress_bar.configure(mode="determinate", value=100, maximum=100)
                        except Exception:
                            pass
                    if hasattr(self, "progress_next_btn"):
                        self.progress_next_btn.configure(state="normal")
                    if hasattr(self, "progress_text"):
                        self.progress_text.configure(state="normal")
                        self.progress_text.insert("end", "환경 설정이 완료되었습니다. 다음 버튼을 눌러 구글 시트 연동 단계로 이동하세요.\n")
                        self.progress_text.see("end")
                        self.progress_text.configure(state="disabled")
                elif item.startswith("ERROR::"):
                    msg = item.replace("ERROR::", "")
                    if hasattr(self, "progress_step_var"):
                        self.progress_step_var.set("오류 발생")
                    if hasattr(self, "progress_detail_var"):
                        self.progress_detail_var.set("오류가 발생해 환경 설정을 중단합니다. 로그 파일을 확인해주세요.")
                    if hasattr(self, "progress_percent_var"):
                        self.progress_percent_var.set("중단")
                    if hasattr(self, "progress_bar"):
                        try:
                            self.progress_bar.configure(mode="determinate")
                        except Exception:
                            pass
                    self.config["initialized"] = False
                    self.config["spreadsheet_id"] = ""
                    self.config["service_account_path"] = ""
                    self.clear_google_sheet_files()
                    try:
                        db_path = APP_DIR / "db.sqlite3"
                        if db_path.exists():
                            db_path.unlink()
                    except Exception as cleanup_exc:
                        append_log("불완전한 DB 정리 실패: " + str(cleanup_exc))
                    save_config(self.config)
                    messagebox.showerror("설정 오류", msg + "\n\n환경 설정을 중단합니다. logs/log.txt를 확인해주세요.")
                    self.root.destroy()
                else:
                    if hasattr(self, "progress_text"):
                        self.progress_text.configure(state="normal")
                        self.progress_text.insert("end", item + "\n")
                        self.progress_text.see("end")
                        self.progress_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(200, self.after_jobs)

    def on_close(self):
        choice = messagebox.askyesnocancel(
            "복지온 종료",
            "런처를 종료하시겠습니까?"
        )
        if choice is None:
            return
        if choice is True:
            try:
                self.stop_program()
            except Exception as exc:
                append_log("종료 중 오류: " + str(exc))
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    single_instance_handle = None
    try:
        if "--webview" in sys.argv:
            index = sys.argv.index("--webview")
            target_url = sys.argv[index + 1] if len(sys.argv) > index + 1 else f"http://{SERVER_HOST}:{DEFAULT_PORT}/"
            run_webview_mode(target_url)
        else:
            single_instance_handle, already_running = acquire_single_instance_lock()
            if already_running:
                show_already_running_message()
                raise SystemExit(0)
            WelfareLauncher().run()
    except SystemExit:
        raise
    except Exception as exc:
        append_log("런처 치명적 오류: " + str(exc))
        try:
            messagebox.showerror("복지온 런처 오류", str(exc))
        except Exception:
            pass
    finally:
        release_single_instance_lock(single_instance_handle)
