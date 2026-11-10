"""Bilgisayar kontrolü: uygulama/site açma, dosya bulma, ekran görüntüsü,
sistem durumu, kilitleme/kapatma."""

from __future__ import annotations

import base64
import difflib
import io
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from . import ToolError

SYSTEM = platform.system()
CREATE_NO_WINDOW = 0x08000000 if SYSTEM == "Windows" else 0

# Kabuğa (cmd) gönderilen isimlerde izin verilmeyen karakterler.
_UNSAFE_CHARS = re.compile(r'[&|<>^"%\r\n`$;]')

# Doğrudan açılmasına izin verilmeyen (program çalıştıran) dosya türleri.
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".msp", ".ps1", ".psm1", ".vbs", ".vbe", ".js", ".jse",
    ".wsf", ".wsh", ".scr", ".pif", ".reg", ".lnk", ".url", ".hta", ".cpl", ".jar", ".py", ".pyw",
    ".sh", ".bash", ".zsh", ".command", ".app", ".desktop", ".appimage", ".run", ".deb", ".rpm", ".pkg",
}

# Kapatılmasına izin verilmeyen kritik sistem süreçleri.
PROTECTED_PROCESSES = {
    "system", "idle", "csrss", "wininit", "winlogon", "services", "lsass", "smss", "svchost", "dwm",
    "explorer", "fontdrvhost", "sihost", "ctfmon", "conhost", "runtimebroker", "searchhost", "startmenuexperiencehost",
    "systemd", "init", "launchd", "kernel_task", "windowserver", "loginwindow", "finder", "dock",
    "xorg", "xwayland", "gnome-shell", "plasmashell", "kwin_x11", "kwin_wayland", "pulseaudio", "pipewire",
    "python", "python3", "pythonw", "py",
}

SKIP_DIRS = {"appdata", "node_modules", "library", "__pycache__", "venv", ".venv", "site-packages", "$recycle.bin", "windows", "program files", "program files (x86)"}

WINDOWS_ALIASES = {
    "not defteri": "notepad", "notepad": "notepad",
    "hesap makinesi": "calc", "calculator": "calc",
    "paint": "mspaint",
    "dosya gezgini": "explorer", "dosyalar": "explorer", "explorer": "explorer", "bu bilgisayar": "explorer",
    "görev yöneticisi": "taskmgr",
    "denetim masası": "control",
    "ayarlar": "ms-settings:",
    "komut istemi": "cmd", "cmd": "cmd", "powershell": "powershell",
    "chrome": "chrome", "google chrome": "chrome", "edge": "msedge", "microsoft edge": "msedge", "firefox": "firefox",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt", "outlook": "outlook",
    "spotify": "spotify:", "steam": "steam://open/main",
    "kamera": "microsoft.windows.camera:", "takvim": "outlookcal:", "saat": "ms-clock:", "alarmlar": "ms-clock:",
    "mağaza": "ms-windows-store:", "microsoft store": "ms-windows-store:",
    "ekran alıntısı": "ms-screenclip:",
    "vs code": "code", "vscode": "code", "visual studio code": "code",
}

MAC_ALIASES = {
    "hesap makinesi": "Calculator", "notlar": "Notes", "not defteri": "TextEdit", "takvim": "Calendar",
    "müzik": "Music", "fotoğraflar": "Photos", "ayarlar": "System Settings", "sistem ayarları": "System Settings",
    "terminal": "Terminal", "finder": "Finder", "dosyalar": "Finder", "safari": "Safari",
    "chrome": "Google Chrome", "google chrome": "Google Chrome", "mesajlar": "Messages", "posta": "Mail",
    "mail": "Mail", "haritalar": "Maps", "harita": "Maps", "facetime": "FaceTime", "kamera": "Photo Booth",
    "vs code": "Visual Studio Code", "vscode": "Visual Studio Code", "word": "Microsoft Word",
    "excel": "Microsoft Excel", "powerpoint": "Microsoft PowerPoint", "saat": "Clock",
    "hatırlatıcılar": "Reminders", "app store": "App Store", "mağaza": "App Store",
}

LINUX_ALIASES = {
    "hesap makinesi": "gnome-calculator", "terminal": "x-terminal-emulator", "dosyalar": "nautilus",
    "dosya gezgini": "nautilus", "not defteri": "gedit", "ayarlar": "gnome-control-center",
    "chrome": "google-chrome", "firefox": "firefox", "vs code": "code", "vscode": "code",
}

CLOSE_ALIASES = {
    "word": "winword", "edge": "msedge", "microsoft edge": "msedge", "not defteri": "notepad",
    "hesap makinesi": "calculator", "powerpoint": "powerpnt", "vs code": "code", "vscode": "code",
    "visual studio code": "code", "google chrome": "chrome", "paint": "mspaint",
}


def fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").casefold().strip()


def _check_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > 100:
        raise ToolError("Uygulama adı boş ya da çok uzun.")
    if _UNSAFE_CHARS.search(name):
        raise ToolError("Uygulama adında izin verilmeyen karakterler var.")
    return name


def _popen(args: list[str], **kwargs) -> subprocess.Popen:
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
        **kwargs,
    )


def _run(args: list[str], timeout: float = 15) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=CREATE_NO_WINDOW)


def _best_match(query: str, candidates: dict[str, str]) -> str | None:
    """candidates: {görünen ad: değer}. En iyi eşleşmenin değerini döndürür."""
    q = fold(query)
    if not q:
        return None
    folded = {fold(k): v for k, v in candidates.items()}
    if q in folded:
        return folded[q]
    starts = sorted((k for k in folded if k.startswith(q)), key=len)
    if starts:
        return folded[starts[0]]
    contains = sorted((k for k in folded if q in k), key=len)
    if contains:
        return folded[contains[0]]
    close = difflib.get_close_matches(q, list(folded), n=1, cutoff=0.8)
    return folded[close[0]] if close else None


def open_with_default_app(path: str) -> None:
    if SYSTEM == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif SYSTEM == "Darwin":
        _popen(["open", path])
    else:
        _popen(["xdg-open", path])


# ----------------------------------------------------------------- Windows
def _windows_shortcuts() -> dict[str, str]:
    roots = [
        Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "Desktop",
        Path.home() / "OneDrive" / "Desktop",
        Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
    ]
    found: dict[str, str] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for ext in ("*.lnk", "*.url"):
            for p in root.rglob(ext):
                stem = p.stem
                low = fold(stem)
                if "uninstall" in low or "kaldır" in low:
                    continue
                found.setdefault(stem, str(p))
    return found


_start_apps_cache: dict[str, str] | None = None


def _windows_start_apps() -> dict[str, str]:
    """Mağaza uygulamaları dahil, Başlat menüsündeki tüm uygulamalar (ad -> AppID)."""
    global _start_apps_cache
    if _start_apps_cache is None:
        _start_apps_cache = {}
        try:
            out = _run(
                ["powershell", "-NoProfile", "-Command",
                 "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-StartApps | ConvertTo-Json -Compress"],
                timeout=20,
            ).stdout
            data = json.loads(out) if out.strip() else []
            if isinstance(data, dict):
                data = [data]
            for item in data:
                if item.get("Name") and item.get("AppID"):
                    _start_apps_cache[item["Name"]] = item["AppID"]
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            pass
    return _start_apps_cache


def _open_app_windows(name: str) -> str:
    alias = WINDOWS_ALIASES.get(fold(name))
    if alias and (alias.endswith(":") or "://" in alias or alias in {"notepad", "calc", "mspaint", "explorer", "taskmgr", "control", "cmd", "powershell"}):
        _popen(["cmd", "/c", "start", "", alias])
        return f"{name} açıldı."
    shortcut = _best_match(name, _windows_shortcuts())
    if shortcut:
        os.startfile(shortcut)  # type: ignore[attr-defined]
        return f"{Path(shortcut).stem} açıldı."
    app_id = _best_match(name, _windows_start_apps())
    if app_id:
        _popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
        return f"{name} açıldı."
    target = alias or name
    exe = shutil.which(target) or _windows_app_path(target)
    if exe:
        _popen([exe])
        return f"{name} açıldı."
    raise ToolError(f"'{name}' adında bir uygulama bulunamadı.")


def _windows_app_path(name: str) -> str | None:
    """Kayıt defterindeki 'App Paths' listesinden programın yolunu bulur (örn. chrome, winword)."""
    try:
        import winreg
    except ImportError:
        return None
    exe = name if fold(name).endswith(".exe") else name + ".exe"
    key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "")
                if value:
                    return value.strip('"')
        except OSError:
            continue
    return None


# --------------------------------------------------------------------- Mac
def _mac_apps() -> dict[str, str]:
    found: dict[str, str] = {}
    for root in (Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications", Path("/System/Applications/Utilities")):
        if root.is_dir():
            for p in root.glob("*.app"):
                found.setdefault(p.stem, str(p))
    return found


def _open_app_mac(name: str) -> str:
    target = MAC_ALIASES.get(fold(name), name)
    if _run(["open", "-a", target]).returncode == 0:
        return f"{target} açıldı."
    path = _best_match(name, _mac_apps())
    if path and _run(["open", path]).returncode == 0:
        return f"{Path(path).stem} açıldı."
    raise ToolError(f"'{name}' adında bir uygulama bulunamadı.")


# ------------------------------------------------------------------- Linux
def _linux_desktop_entries() -> dict[str, str]:
    roots = [
        Path("/usr/share/applications"), Path("/usr/local/share/applications"),
        Path.home() / ".local/share/applications", Path("/var/lib/flatpak/exports/share/applications"),
        Path("/var/lib/snapd/desktop/applications"),
    ]
    found: dict[str, str] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.glob("*.desktop"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "NoDisplay=true" in text:
                continue
            for line in text.splitlines():
                if line.startswith(("Name=", "Name[tr]=")):
                    found.setdefault(line.split("=", 1)[1].strip(), str(p))
            found.setdefault(p.stem, str(p))
    return found


def _open_app_linux(name: str) -> str:
    desktop = _best_match(name, _linux_desktop_entries())
    if desktop:
        if shutil.which("gtk-launch"):
            _popen(["gtk-launch", Path(desktop).stem])
            return f"{name} açıldı."
        for line in Path(desktop).read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("Exec="):
                parts = [a for a in shlex.split(line[5:]) if not a.startswith("%")]
                if parts:
                    _popen(parts)
                    return f"{name} açıldı."
    exe = shutil.which(LINUX_ALIASES.get(fold(name), name))
    if exe:
        _popen([exe])
        return f"{name} açıldı."
    raise ToolError(f"'{name}' adında bir uygulama bulunamadı.")


def open_app(name: str) -> str:
    name = _check_name(name)
    if SYSTEM == "Windows":
        return _open_app_windows(name)
    if SYSTEM == "Darwin":
        return _open_app_mac(name)
    return _open_app_linux(name)


def close_app(name: str) -> str:
    import psutil

    name = _check_name(name)
    key = fold(CLOSE_ALIASES.get(fold(name), name)).replace(" ", "")
    if len(key) < 3:
        raise ToolError("Kapatılacak uygulamanın adını biraz daha açık söyleyin.")
    own_pid = os.getpid()
    targets = []
    for proc in psutil.process_iter(["pid", "name"]):
        pname = fold(proc.info.get("name") or "")
        base = pname[:-4] if pname.endswith(".exe") else pname
        if not base or proc.info["pid"] == own_pid or base in PROTECTED_PROCESSES:
            continue
        if key in base.replace(" ", ""):
            targets.append(proc)
    if not targets:
        raise ToolError(f"Çalışan '{name}' uygulaması bulunamadı.")
    for proc in targets:
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    psutil.wait_procs(targets, timeout=3)
    names = sorted({p.info["name"] for p in targets})
    return f"Kapatıldı: {', '.join(names)}"


def open_website(target: str) -> str:
    target = target.strip()
    if not target:
        raise ToolError("Açılacak site veya aranacak şey boş.")
    looks_like_url = " " not in target and ("." in target or target.startswith(("http://", "https://")))
    if looks_like_url:
        url = target if "://" in target else "https://" + target
        if urlparse(url).scheme not in ("http", "https"):
            raise ToolError("Sadece http/https adresleri açılabilir.")
        webbrowser.open(url)
        return f"{url} açıldı."
    webbrowser.open("https://www.google.com/search?q=" + quote_plus(target))
    return f"Google'da '{target}' araması açıldı."


def search_files(query: str, max_results: int = 15) -> str:
    q = fold(query)
    if len(q) < 2:
        raise ToolError("Aranacak dosya adı en az 2 harf olmalı.")
    home = Path.home()
    preferred = [home / d for d in ("Desktop", "Masaüstü", "Documents", "Belgeler", "Downloads", "İndirilenler",
                                    "Pictures", "Resimler", "Music", "Müzik", "Videos", "Videolar", "OneDrive")]
    roots = [p for p in preferred if p.is_dir()] + [home]
    deadline = time.monotonic() + 6
    seen: set[str] = set()
    results: list[tuple[float, str]] = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and fold(d) not in SKIP_DIRS]
            if dirpath in seen:
                dirnames[:] = []
                continue
            seen.add(dirpath)
            for fn in filenames + dirnames:
                if q in fold(fn):
                    full = os.path.join(dirpath, fn)
                    try:
                        results.append((os.path.getmtime(full), full))
                    except OSError:
                        pass
            if time.monotonic() > deadline or len(results) > 200:
                break
        if time.monotonic() > deadline:
            break
    if not results:
        return f"'{query}' adını içeren dosya bulunamadı."
    results.sort(reverse=True)
    lines = [f"{datetime.fromtimestamp(m):%d.%m.%Y} - {p}" for m, p in results[:max_results]]
    return "Bulunanlar (en yeni önce):\n" + "\n".join(lines)


def open_path(path: str) -> str:
    p = Path(os.path.expandvars(os.path.expanduser(path.strip())))
    if not p.exists():
        raise ToolError(f"Bu yol bulunamadı: {p}")
    if p.is_file() and p.suffix.lower() in BLOCKED_EXTENSIONS:
        raise ToolError("Güvenlik nedeniyle program/komut dosyaları bu araçla açılmaz. Uygulamalar için open_app kullanın.")
    open_with_default_app(str(p))
    return f"Açıldı: {p}"


def take_screenshot(ctx, look: bool = True):
    from PIL import Image

    out_dir = ctx.config.data_dir / "ekran_goruntuleri"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"ekran_{datetime.now():%Y%m%d_%H%M%S}.png"
    image = None
    try:
        from PIL import ImageGrab

        image = ImageGrab.grab(all_screens=True) if SYSTEM == "Windows" else ImageGrab.grab()
        image.save(path)
    except Exception:
        for cmd in (["grim", str(path)], ["gnome-screenshot", "-f", str(path)], ["scrot", str(path)]):
            if shutil.which(cmd[0]) and _run(cmd).returncode == 0 and path.exists():
                image = Image.open(path)
                break
    if image is None:
        raise ToolError("Ekran görüntüsü alınamadı.")
    note = f"Ekran görüntüsü kaydedildi: {path}"
    if not look:
        return note
    img = image.convert("RGB")
    img.thumbnail((1568, 1568))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    data = base64.standard_b64encode(buf.getvalue()).decode("ascii")
    return [
        {"type": "text", "text": note + " Ekranın görüntüsü ekte."},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
    ]


def system_status() -> str:
    import psutil

    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home().anchor or "/"))
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    lines = [
        f"İşletim sistemi: {platform.system()} {platform.release()}",
        f"İşlemci kullanımı: %{cpu:.0f} ({psutil.cpu_count()} çekirdek)",
        f"Bellek (RAM): %{mem.percent:.0f} dolu ({mem.used / 2**30:.1f} / {mem.total / 2**30:.1f} GB)",
        f"Disk: %{disk.percent:.0f} dolu ({disk.free / 2**30:.0f} GB boş)",
        f"Açık kalma süresi: {hours} saat {rem // 60} dakika",
    ]
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is not None:
        state = "şarj oluyor" if battery.power_plugged else "pilde"
        lines.append(f"Pil: %{battery.percent:.0f} ({state})")
    procs = []
    for proc in psutil.process_iter(["name", "memory_info"]):
        mi = proc.info.get("memory_info")
        if mi:
            procs.append((mi.rss, proc.info.get("name") or "?"))
    procs.sort(reverse=True)
    top = ", ".join(f"{n} ({r / 2**20:.0f} MB)" for r, n in procs[:5])
    lines.append(f"En çok bellek kullananlar: {top}")
    return "\n".join(lines)


class PowerController:
    """Kilitleme, uyku, kapatma ve yeniden başlatma. Kapatma her zaman gecikmeli yapılır
    ki kullanıcı 'iptal et' diyebilsin."""

    def __init__(self) -> None:
        self._timer: threading.Timer | None = None

    def _schedule(self, delay: int, args: list[str]) -> None:
        self.cancel_timer()
        self._timer = threading.Timer(delay, lambda: _popen(args))
        self._timer.daemon = True
        self._timer.start()

    def cancel_timer(self) -> bool:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
            return True
        return False

    def __call__(self, action: str, delay_seconds: int = 60) -> str:
        delay = max(10, min(int(delay_seconds), 3600))
        if action == "lock":
            if SYSTEM == "Windows":
                _popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            elif SYSTEM == "Darwin":
                _popen(["pmset", "displaysleepnow"])
            else:
                _popen(["loginctl", "lock-session"])
            return "Bilgisayar kilitlendi."
        if action == "sleep":
            if SYSTEM == "Windows":
                _popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            elif SYSTEM == "Darwin":
                _popen(["pmset", "sleepnow"])
            else:
                _popen(["systemctl", "suspend"])
            return "Bilgisayar uyku moduna alınıyor."
        if action in ("shutdown", "restart"):
            word = "kapatılacak" if action == "shutdown" else "yeniden başlatılacak"
            if SYSTEM == "Windows":
                flag = "/s" if action == "shutdown" else "/r"
                _run(["shutdown", flag, "/t", str(delay)])
            elif SYSTEM == "Darwin":
                verb = "shut down" if action == "shutdown" else "restart"
                self._schedule(delay, ["osascript", "-e", f'tell application "System Events" to {verb}'])
            else:
                self._schedule(delay, ["systemctl", "poweroff" if action == "shutdown" else "reboot"])
            return f"Bilgisayar {delay} saniye sonra {word}. Vazgeçmek için 'iptal et' demeniz yeterli."
        if action == "cancel":
            cancelled = self.cancel_timer()
            if SYSTEM == "Windows":
                cancelled = _run(["shutdown", "/a"]).returncode == 0 or cancelled
            return "Kapatma/yeniden başlatma iptal edildi." if cancelled else "İptal edilecek bekleyen bir kapatma yok."
        raise ToolError("Bilinmeyen işlem.")


def register(registry, ctx) -> None:
    registry.add(
        "open_app",
        "Bilgisayarda bir uygulamayı açar (Chrome, Spotify, Discord, Steam, Word, hesap makinesi, oyunlar vb.). "
        "Kullanıcı bir programı açmanı istediğinde çağır. Web sitesi için open_website kullan.",
        open_app,
        {"name": {"type": "string", "description": "Uygulamanın adı, kullanıcının söylediği gibi. Örn: 'spotify', 'hesap makinesi'."}},
        ["name"],
        status="🖥️ Uygulama açıyor",
    )
    registry.add(
        "close_app",
        "Çalışan bir uygulamayı kapatır. Kullanıcı açıkça kapatmanı istediğinde çağır.",
        close_app,
        {"name": {"type": "string", "description": "Kapatılacak uygulamanın adı. Örn: 'chrome'."}},
        ["name"],
        status="🖥️ Uygulama kapatıyor",
    )
    registry.add(
        "open_website",
        "Tarayıcıda bir web sitesi açar ya da Google'da arama sayfası açar. Kullanıcı bir siteyi açmanı veya "
        "tarayıcıda bir şey aramanı istediğinde çağır. Sadece bilgi gerekiyorsa web_search kullan.",
        open_website,
        {"target": {"type": "string", "description": "Adres (örn. 'youtube.com') veya aranacak metin."}},
        ["target"],
        status="🌐 Site açıyor",
    )
    registry.add(
        "search_files",
        "Kullanıcının bilgisayarındaki (Masaüstü, Belgeler, İndirilenler vb.) dosya ve klasörleri adına göre arar.",
        search_files,
        {
            "query": {"type": "string", "description": "Dosya adında geçen kelime. Örn: 'fatura', 'cv'."},
            "max_results": {"type": "integer", "description": "En fazla kaç sonuç (varsayılan 15).", "minimum": 1, "maximum": 50},
        },
        ["query"],
        status="🔎 Dosya arıyor",
    )
    registry.add(
        "open_path",
        "Bir dosyayı veya klasörü varsayılan programıyla açar (PDF, resim, belge, klasör). Yolu bilmiyorsan önce search_files kullan.",
        open_path,
        {"path": {"type": "string", "description": "Dosyanın veya klasörün tam yolu."}},
        ["path"],
        status="📂 Dosya açıyor",
    )
    registry.add(
        "take_screenshot",
        "Ekran görüntüsü alır ve kaydeder. look=true ise görüntüyü sen de görürsün; kullanıcı 'ekranımda ne var', "
        "'şuna bak', 'bu hata ne' dediğinde look=true ile çağır.",
        lambda look=True: take_screenshot(ctx, look),
        {"look": {"type": "boolean", "description": "Görüntüyü incelemen gerekiyorsa true (varsayılan true)."}},
        status="📸 Ekran görüntüsü alıyor",
    )
    registry.add(
        "system_status",
        "Bilgisayarın durumunu verir: işlemci, bellek, disk, pil, açık kalma süresi ve en çok bellek kullanan programlar. "
        "'Bilgisayar neden yavaş', 'şarj ne durumda' gibi sorularda çağır.",
        system_status,
        status="💻 Sistemi kontrol ediyor",
    )
    registry.add(
        "power_action",
        "Bilgisayarı kilitler, uyutur, kapatır veya yeniden başlatır; ya da bekleyen kapatmayı iptal eder. "
        "Kapatma ve yeniden başlatmadan ÖNCE kullanıcı açıkça istemediyse onay iste. Kapatma her zaman gecikmeli yapılır.",
        PowerController(),
        {
            "action": {"type": "string", "enum": ["lock", "sleep", "shutdown", "restart", "cancel"],
                       "description": "lock=kilitle, sleep=uyku, shutdown=kapat, restart=yeniden başlat, cancel=bekleyen kapatmayı iptal et."},
            "delay_seconds": {"type": "integer", "description": "Kapatma/yeniden başlatma gecikmesi saniye (varsayılan 60, en az 10).",
                              "minimum": 10, "maximum": 3600},
        },
        ["action"],
        status="⚡ Güç işlemi",
    )
