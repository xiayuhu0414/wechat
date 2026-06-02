from __future__ import annotations

import os
import threading
import time
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core import db
from app.core.config import settings


DEFAULT_UIA_CONFIG: dict[str, Any] = {
    "enabled": False,
    "interval_seconds": 8.0,
    "max_nodes": 800,
    "save_screenshot_on_probe": True,
    "use_dotnet_watcher": True,
}

WECHAT_PROCESS_NAMES = {"Weixin.exe", "WeChat.exe"}
COMPAT_RENDER_ENV = {
    "QT_ACCESSIBILITY": "1",
    "QT_ANGLE_PLATFORM": "software",
    "QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1",
    "QT_OPENGL": "software",
    "QT_QUICK_BACKEND": "software",
    "QSG_RHI_PREFER_SOFTWARE_RENDERER": "1",
    "QSG_RHI_BACKEND": "software",
    "QTWEBENGINE_DISABLE_SANDBOX": "1",
    "QTWEBENGINE_CHROMIUM_FLAGS": "--force-renderer-accessibility --disable-gpu --disable-gpu-compositing --disable-zero-copy",
}


@dataclass
class UiaWindow:
    title: str
    class_name: str
    handle: int
    process_id: int | None
    is_target: bool
    role: str
    is_main_window: bool
    is_login_window: bool


def _safe_call(func: Any, default: Any = None) -> Any:
    try:
        return func()
    except Exception:
        return default


def _settings_key(key: str) -> str:
    return f"uia.{key}"


def _normalize_config(values: dict[str, Any]) -> dict[str, Any]:
    config = {**DEFAULT_UIA_CONFIG, **values}
    config["enabled"] = bool(config.get("enabled"))
    config["interval_seconds"] = max(float(config.get("interval_seconds") or 8.0), 2.0)
    config["max_nodes"] = max(int(config.get("max_nodes") or 800), 50)
    config["save_screenshot_on_probe"] = bool(config.get("save_screenshot_on_probe"))
    config["use_dotnet_watcher"] = bool(config.get("use_dotnet_watcher", True))
    return config


def get_uia_config() -> dict[str, Any]:
    stored = {
        key[4:]: value
        for key, value in db.get_app_settings("uia.").items()
    }
    return _normalize_config(stored)


def update_uia_config(values: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_config(values)
    for key, value in normalized.items():
        if key in values:
            db.set_app_setting(_settings_key(key), value)
    return get_uia_config()


def _wechat_processes() -> list[Any]:
    try:
        import psutil
    except Exception:
        return []
    processes = []
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = process.info.get("name") or ""
            if name in WECHAT_PROCESS_NAMES:
                processes.append(process)
        except Exception:
            continue
    return processes


def find_wechat_executable(explicit_path: str | None = None) -> Path | None:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists():
            return path
    for process in _wechat_processes():
        exe = process.info.get("exe")
        if exe and Path(exe).exists():
            return Path(exe)
    try:
        import winreg
        keys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Tencent\Weixin"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Tencent\Weixin"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Tencent\Weixin"),
        ]
        value_names = ("InstallPath", "InstallDir", "Path")
        for root, key_name in keys:
            try:
                with winreg.OpenKey(root, key_name) as key:
                    for value_name in value_names:
                        try:
                            value, _ = winreg.QueryValueEx(key, value_name)
                        except OSError:
                            continue
                        base = Path(str(value)).expanduser()
                        candidates = [base, base / "Weixin.exe", base / "WeChat.exe"]
                        for candidate in candidates:
                            if candidate.exists() and candidate.is_file():
                                return candidate
            except OSError:
                continue
    except Exception:
        pass
    fallback = Path(r"D:\ProgramData\Weixin\Weixin.exe")
    return fallback if fallback.exists() else None


def launch_wechat_compat(
    *,
    restart: bool = False,
    exe_path: str | None = None,
    wait_seconds: float = 3.0,
    probe_timeout_seconds: float = 0,
    probe_interval_seconds: float = 2.0,
    prewarm_uia: bool = True,
) -> dict[str, Any]:
    path = find_wechat_executable(exe_path)
    if path is None:
        return {
            "ok": False,
            "error": "未找到微信可执行文件，请在系统配置中确认微信安装路径后再重试。",
            "env": COMPAT_RENDER_ENV,
        }

    existing = _wechat_processes()
    if existing and not restart:
        return {
            "ok": False,
            "error": "微信已经在运行，运行中的进程无法补充渲染环境变量。请使用兼容模式重启。",
            "exe_path": str(path),
            "running_pids": [process.pid for process in existing],
            "env": COMPAT_RENDER_ENV,
        }

    prewarm_status = None
    if prewarm_uia:
        try:
            prewarm_status = uia_enhancer.start(interval_seconds=1)
        except Exception as exc:
            prewarm_status = {"ok": False, "error": str(exc)}

    stopped_pids: list[int] = []
    if restart:
        for process in existing:
            try:
                stopped_pids.append(process.pid)
                process.terminate()
            except Exception:
                continue
        deadline = time.time() + 8
        for process in existing:
            try:
                timeout = max(deadline - time.time(), 0.1)
                process.wait(timeout=timeout)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    env = os.environ.copy()
    env.update(COMPAT_RENDER_ENV)
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    process = subprocess.Popen(
        [str(path)],
        cwd=str(path.parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    time.sleep(max(wait_seconds, 0))
    result = {
        "ok": True,
        "exe_path": str(path),
        "pid": process.pid,
        "stopped_pids": stopped_pids,
        "env": COMPAT_RENDER_ENV,
        "prewarm_uia": prewarm_status,
        "message": "微信已使用兼容渲染环境启动，请等待登录完成后再探测 UI 树。",
    }
    if probe_timeout_seconds > 0:
        result["probe"] = wait_for_wechat_ui(
            timeout_seconds=probe_timeout_seconds,
            interval_seconds=probe_interval_seconds,
        )
    return result


def wait_for_wechat_ui(
    *,
    timeout_seconds: float = 30,
    interval_seconds: float = 2,
    max_nodes: int = 800,
) -> dict[str, Any]:
    deadline = time.time() + max(timeout_seconds, 0)
    attempts: list[dict[str, Any]] = []
    best_probe: dict[str, Any] | None = None
    best_main_probe: dict[str, Any] | None = None
    while True:
        probe = probe_wechat_ui(save_screenshot=False, max_nodes=max_nodes)
        window = probe.get("window") or {}
        compact_probe = {
            "ok": probe.get("ok"),
            "tree_state": probe.get("tree_state"),
            "node_count": probe.get("node_count", 0),
            "window": window,
            "window_role": window.get("role"),
            "is_main_window": window.get("is_main_window", False),
            "is_login_window": window.get("is_login_window", False),
            "error": probe.get("error"),
            "duration_seconds": probe.get("duration_seconds"),
        }
        attempts.append(compact_probe)
        if best_probe is None or int(probe.get("node_count") or 0) > int(best_probe.get("node_count") or 0):
            best_probe = probe
        if window.get("is_main_window") and (
            best_main_probe is None
            or int(probe.get("node_count") or 0) > int(best_main_probe.get("node_count") or 0)
        ):
            best_main_probe = probe
        if window.get("is_main_window") and probe.get("tree_state") == "available":
            return {
                "ok": True,
                "ready": True,
                "tree_state": probe.get("tree_state"),
                "node_count": probe.get("node_count", 0),
                "attempts": attempts,
                "best_probe": probe,
            }
        if time.time() >= deadline:
            final_probe = best_main_probe or best_probe
            return {
                "ok": bool(final_probe and final_probe.get("ok")),
                "ready": False,
                "tree_state": final_probe.get("tree_state") if final_probe else "unknown",
                "node_count": final_probe.get("node_count", 0) if final_probe else 0,
                "attempts": attempts,
                "best_main_probe": best_main_probe,
                "best_probe": best_probe,
                "recommendation": "兼容模式启动后仍未探测到微信主界面的完整 UI 树；登录窗口少量节点不代表主界面可自动化。若仍失败，需要改用图像/OCR 坐标兜底。",
            }
        time.sleep(max(interval_seconds, 0.5))


class UiaEnhancer:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._last_probe: dict[str, Any] | None = None
        self._last_error: str | None = None
        self._running = False
        self._watcher_process: subprocess.Popen[Any] | None = None
        self._watcher_state_path: Path | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running and self._thread is not None and self._thread.is_alive(),
                "last_probe": self._last_probe,
                "last_error": self._last_error,
                "config": get_uia_config(),
                "watcher_process_id": self._watcher_process.pid if self._watcher_process and self._watcher_process.poll() is None else None,
                "watcher_state": self._read_watcher_state(),
            }

    def start(self, interval_seconds: float | None = None) -> dict[str, Any]:
        if self._thread is not None and self._thread.is_alive():
            return self.status()
        config = get_uia_config()
        interval = float(interval_seconds or config["interval_seconds"])
        if config["use_dotnet_watcher"]:
            self._start_dotnet_watcher(interval, int(config["max_nodes"]))
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(interval,), name="uia-enhancer", daemon=True)
        self._running = True
        self._thread.start()
        return self.status()

    def stop(self) -> dict[str, Any]:
        self._stop_event.set()
        self._stop_dotnet_watcher()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._running = False
        return self.status()

    def _read_watcher_state(self) -> dict[str, Any] | None:
        if not self._watcher_state_path or not self._watcher_state_path.exists():
            return None
        try:
            return db.decode_json(self._watcher_state_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None

    def _start_dotnet_watcher(self, interval_seconds: float, max_nodes: int) -> None:
        if self._watcher_process is not None and self._watcher_process.poll() is None:
            return
        settings.ensure_dirs()
        script_path = settings.diagnostics_dir / "uia_watcher.ps1"
        state_path = settings.diagnostics_dir / "uia_watcher_state.json"
        script_path.write_text(_POWERSHELL_WATCHER, encoding="utf-8-sig")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._watcher_process = subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-StatePath",
                str(state_path),
                "-IntervalSeconds",
                str(interval_seconds),
                "-MaxNodes",
                str(max_nodes),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        self._watcher_state_path = state_path

    def _stop_dotnet_watcher(self) -> None:
        if self._watcher_process is None:
            return
        if self._watcher_process.poll() is None:
            self._watcher_process.terminate()
            try:
                self._watcher_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._watcher_process.kill()
        self._watcher_process = None

    def configure_from_settings(self) -> dict[str, Any]:
        config = get_uia_config()
        if config["enabled"]:
            return self.start(config["interval_seconds"])
        return self.stop()

    def probe(self, *, save_screenshot: bool | None = None, max_nodes: int | None = None) -> dict[str, Any]:
        config = get_uia_config()
        result = probe_wechat_ui(
            save_screenshot=config["save_screenshot_on_probe"] if save_screenshot is None else save_screenshot,
            max_nodes=int(max_nodes or config["max_nodes"]),
        )
        watcher_state = self._read_watcher_state()
        if watcher_state:
            result["watcher_state"] = watcher_state
            watcher_count = int(watcher_state.get("node_count") or watcher_state.get("raw_node_count") or 0)
            if watcher_count > int(result.get("node_count") or 0):
                effective_state, effective_recommendation = _tree_state(watcher_count)
                result["effective_tree_state"] = effective_state
                result["effective_recommendation"] = effective_recommendation
                result["effective_node_count"] = watcher_count
        with self._lock:
            self._last_probe = result
            self._last_error = None if result["ok"] else result.get("error")
        return result

    def _run(self, interval_seconds: float) -> None:
        while not self._stop_event.is_set():
            try:
                self.probe(save_screenshot=False)
            except Exception as exc:
                with self._lock:
                    self._last_error = str(exc)
            self._stop_event.wait(interval_seconds)
        self._running = False


def _window_to_dict(window: Any) -> UiaWindow:
    info = window.element_info
    title = _safe_call(window.window_text, "") or getattr(info, "name", "") or ""
    class_name = getattr(info, "class_name", "") or ""
    handle = int(getattr(info, "handle", 0) or 0)
    process_id = getattr(info, "process_id", None)
    role = _wechat_window_role(title, class_name)
    is_target = role != "other"
    return UiaWindow(
        title=title,
        class_name=class_name,
        handle=handle,
        process_id=process_id,
        is_target=is_target,
        role=role,
        is_main_window=role == "main",
        is_login_window=role == "login",
    )


def _wechat_window_role(title: str, class_name: str) -> str:
    is_wechat_title = title in {"微信", "Weixin", "WeChat"}
    if class_name == "mmui::LoginWindow":
        return "login"
    if class_name == "mmui::MainWindow":
        return "main"
    if class_name == "Qt51514QWindowIcon" and is_wechat_title:
        return "main"
    if class_name.startswith("mmui::") or is_wechat_title:
        return "wechat"
    return "other"


def _collect_nodes(window: Any, max_nodes: int) -> tuple[int, list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    descendants = window.descendants()
    count = len(descendants)
    for item in descendants[:max_nodes]:
        info = item.element_info
        nodes.append(
            {
                "name": getattr(info, "name", "") or _safe_call(item.window_text, ""),
                "control_type": getattr(info, "control_type", ""),
                "class_name": getattr(info, "class_name", ""),
                "automation_id": getattr(info, "automation_id", ""),
                "handle": int(getattr(info, "handle", 0) or 0),
            }
        )
    return count, nodes


def _tree_state(node_count: int) -> tuple[str, str]:
    if node_count <= 3:
        return "hidden", "微信 UI 树几乎未暴露，建议启动 UIA 增强后保持微信窗口前台再重试。"
    if node_count < 30:
        return "sparse", "微信 UI 树只暴露了少量节点，自动化任务可能不稳定。"
    return "available", "微信 UI 树已暴露，可继续执行自动化任务。"


def probe_wechat_ui(*, save_screenshot: bool = False, max_nodes: int = 800) -> dict[str, Any]:
    started = time.time()
    try:
        from pywinauto import Desktop
    except Exception as exc:
        return {
            "ok": False,
            "error": f"pywinauto 不可用: {exc}",
            "windows": [],
            "node_count": 0,
            "duration_seconds": round(time.time() - started, 3),
        }

    try:
        desktop = Desktop(backend="uia")
        all_windows = desktop.windows()
        windows = [_window_to_dict(window) for window in all_windows]
        pairs = [(window, _window_to_dict(window)) for window in all_windows]
        main_candidates = [window for window, info in pairs if info.is_main_window]
        target_candidates = [window for window, info in pairs if info.is_target]
        target = main_candidates[0] if main_candidates else (target_candidates[0] if target_candidates else None)
        if target is None:
            return {
                "ok": False,
                "error": "未找到微信主窗口，请先启动微信",
                "windows": [window.__dict__ for window in windows],
                "node_count": 0,
                "duration_seconds": round(time.time() - started, 3),
            }

        target_info = _window_to_dict(target)
        target.set_focus()
        time.sleep(0.2)
        node_count, nodes = _collect_nodes(target, max_nodes=max_nodes)
        tree_state, recommendation = _tree_state(node_count)
        screenshot_path = None
        if save_screenshot:
            settings.ensure_dirs()
            screenshot_path = settings.diagnostics_dir / f"uia_probe_{int(time.time())}.png"
            target.capture_as_image().save(screenshot_path)

        return {
            "ok": True,
            "tree_state": tree_state,
            "recommendation": recommendation,
            "window": target_info.__dict__,
            "windows": [window.__dict__ for window in windows],
            "node_count": node_count,
            "sample_nodes": nodes,
            "screenshot_path": str(screenshot_path) if screenshot_path else None,
            "duration_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "windows": [],
            "node_count": 0,
            "duration_seconds": round(time.time() - started, 3),
        }


def probe_wechat_alternative_ui(*, max_nodes: int = 2000, sample_limit: int = 25) -> dict[str, Any]:
    started = time.time()
    try:
        import psutil
        import uiautomation as auto
        import win32gui
        import win32process
    except Exception as exc:
        return {
            "ok": False,
            "error": f"替代 UIA 探测依赖不可用: {exc}",
            "items": [],
            "duration_seconds": round(time.time() - started, 3),
        }

    wechat_pids = {
        process.pid
        for process in psutil.process_iter(["name"])
        if process.info.get("name") in WECHAT_PROCESS_NAMES
    }
    items: list[dict[str, Any]] = []

    def walk(control: Any) -> tuple[int, list[dict[str, Any]]]:
        try:
            queue = list(control.GetChildren())
        except Exception as exc:
            return 0, [{"error": repr(exc)}]
        count = 0
        samples: list[dict[str, Any]] = []
        while queue and count < max_nodes:
            item = queue.pop(0)
            count += 1
            if len(samples) < sample_limit:
                samples.append(
                    {
                        "name": getattr(item, "Name", ""),
                        "control_type": getattr(item, "ControlTypeName", ""),
                        "class_name": getattr(item, "ClassName", ""),
                        "automation_id": getattr(item, "AutomationId", ""),
                        "handle": int(getattr(item, "NativeWindowHandle", 0) or 0),
                    }
                )
            try:
                queue[0:0] = list(item.GetChildren())
            except Exception:
                pass
        return count, samples

    def enum_window(hwnd: int, _extra: Any) -> None:
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            return
        if pid not in wechat_pids:
            return
        title = _safe_call(lambda: win32gui.GetWindowText(hwnd), "") or ""
        class_name = _safe_call(lambda: win32gui.GetClassName(hwnd), "") or ""
        if not title and not class_name:
            return
        try:
            control = auto.ControlFromHandle(hwnd)
            node_count, samples = walk(control)
            role = _wechat_window_role(title or getattr(control, "Name", ""), class_name or getattr(control, "ClassName", ""))
            items.append(
                {
                    "title": title,
                    "class_name": class_name,
                    "handle": hwnd,
                    "process_id": pid,
                    "visible": bool(_safe_call(lambda: win32gui.IsWindowVisible(hwnd), False)),
                    "rect": _safe_call(lambda: list(win32gui.GetWindowRect(hwnd)), []),
                    "role": role,
                    "uia_name": getattr(control, "Name", ""),
                    "uia_control_type": getattr(control, "ControlTypeName", ""),
                    "node_count": node_count,
                    "sample_nodes": samples,
                }
            )
        except Exception as exc:
            items.append(
                {
                    "title": title,
                    "class_name": class_name,
                    "handle": hwnd,
                    "process_id": pid,
                    "error": repr(exc),
                }
            )

    try:
        win32gui.EnumWindows(enum_window, None)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "wechat_pids": sorted(wechat_pids),
            "items": items,
            "duration_seconds": round(time.time() - started, 3),
        }

    main_items = [item for item in items if item.get("role") == "main"]
    best_item = max(items, key=lambda item: int(item.get("node_count") or 0), default=None)
    best_main_item = max(main_items, key=lambda item: int(item.get("node_count") or 0), default=None)
    return {
        "ok": True,
        "backend": "uiautomation-com",
        "wechat_pids": sorted(wechat_pids),
        "items": items,
        "best_item": best_item,
        "best_main_item": best_main_item,
        "main_tree_available": bool(best_main_item and int(best_main_item.get("node_count") or 0) >= 30),
        "duration_seconds": round(time.time() - started, 3),
    }


uia_enhancer = UiaEnhancer()


_POWERSHELL_WATCHER = r'''
param(
  [Parameter(Mandatory=$true)][string]$StatePath,
  [double]$IntervalSeconds = 8,
  [int]$MaxNodes = 800
)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$script:EventCount = 0
$script:LastEvent = $null
$script:SubscribedHandle = $null

function Write-State($state) {
  $state.updated_at = (Get-Date).ToUniversalTime().ToString("o")
  $json = $state | ConvertTo-Json -Compress -Depth 8
  Set-Content -LiteralPath $StatePath -Value $json -Encoding UTF8
}

function Get-TargetWindow {
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $children = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
  foreach ($child in $children) {
    $name = $child.Current.Name
    $className = $child.Current.ClassName
    if ($className -like "mmui::*" -or $name -eq "微信" -or $name -eq "Weixin" -or $name -eq "WeChat") {
      return $child
    }
  }
  return $null
}

function Get-Node-Info($node) {
  if ($null -eq $node) { return $null }
  return @{
    name = $node.Current.Name
    control_type = $node.Current.ControlType.ProgrammaticName
    class_name = $node.Current.ClassName
    automation_id = $node.Current.AutomationId
    handle = $node.Current.NativeWindowHandle
  }
}

function Count-Nodes($target, $walker, [int]$limit, [int]$sampleLimit) {
  $stack = New-Object System.Collections.Stack
  $first = $walker.GetFirstChild($target)
  if ($null -ne $first) { $stack.Push($first) }
  $count = 0
  $samples = New-Object System.Collections.ArrayList
  while ($stack.Count -gt 0 -and $count -lt $limit) {
    $node = $stack.Pop()
    $count += 1
    if ($samples.Count -lt $sampleLimit) {
      [void]$samples.Add((Get-Node-Info $node))
    }
    $sibling = $walker.GetNextSibling($node)
    if ($null -ne $sibling) { $stack.Push($sibling) }
    $child = $walker.GetFirstChild($node)
    if ($null -ne $child) { $stack.Push($child) }
  }
  return @{
    count = $count
    samples = @($samples)
  }
}

$handler = [System.Windows.Automation.StructureChangedEventHandler]{
  param($sender, $eventArgs)
  $script:EventCount += 1
  $script:LastEvent = (Get-Date).ToUniversalTime().ToString("o")
}

$focusHandler = [System.Windows.Automation.AutomationFocusChangedEventHandler]{
  param($sender, $eventArgs)
  $script:EventCount += 1
  $script:LastEvent = (Get-Date).ToUniversalTime().ToString("o")
}

try {
  [System.Windows.Automation.Automation]::AddAutomationFocusChangedEventHandler($focusHandler)
} catch {}

while ($true) {
  try {
    $target = Get-TargetWindow
    if ($null -eq $target) {
      Write-State @{ ok = $false; error = "WeChat window not found"; node_count = 0; event_count = $script:EventCount; last_event = $script:LastEvent }
    } else {
      $handle = $target.Current.NativeWindowHandle
      if ($script:SubscribedHandle -ne $handle) {
        [System.Windows.Automation.Automation]::AddStructureChangedEventHandler($target, [System.Windows.Automation.TreeScope]::Subtree, $handler)
        $script:SubscribedHandle = $handle
      }
      try { [void]$target.SetFocus() } catch {}
      $raw = Count-Nodes $target ([System.Windows.Automation.TreeWalker]::RawViewWalker) $MaxNodes 30
      $control = Count-Nodes $target ([System.Windows.Automation.TreeWalker]::ControlViewWalker) $MaxNodes 30
      $content = Count-Nodes $target ([System.Windows.Automation.TreeWalker]::ContentViewWalker) $MaxNodes 30
      $count = [Math]::Max([int]$control.count, [int]$raw.count)
      $state = "available"
      if ($count -le 3) {
        $state = "hidden"
      } elseif ($count -lt 30) {
        $state = "sparse"
      }
      Write-State @{
        ok = $true
        backend = "dotnet-uia"
        title = $target.Current.Name
        class_name = $target.Current.ClassName
        handle = $handle
        process_id = $target.Current.ProcessId
        node_count = $count
        raw_node_count = [int]$raw.count
        control_node_count = [int]$control.count
        content_node_count = [int]$content.count
        tree_state = $state
        raw_samples = @($raw.samples)
        control_samples = @($control.samples)
        content_samples = @($content.samples)
        event_count = $script:EventCount
        last_event = $script:LastEvent
      }
    }
  } catch {
    Write-State @{ ok = $false; error = $_.Exception.Message; node_count = 0; event_count = $script:EventCount; last_event = $script:LastEvent }
  }
  Start-Sleep -Seconds $IntervalSeconds
}
'''
