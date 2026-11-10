"""Web arayüzü: aynı Wi-Fi'daki telefonun tarayıcısından Jarvis'e ulaşmayı sağlar.

GÜVENLİK: Sayfa ve API gizli bir anahtarla (token) korunur. Anahtarı bilmeyen
hiç kimse ev bilgisayarınıza komut gönderemez. Konuşma tanıma ve seslendirme
telefonun kendi tarayıcısında çalışır; ses sunucuya gitmez.
"""

from __future__ import annotations

import hmac
import json
import secrets
import socket
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PAGE = """<!doctype html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Jarvis</title>
<style>
  :root { color-scheme: dark; --bg:#0b0f17; --card:#131a26; --line:#223049; --me:#1f6feb; --jx:#1d2a3a; --accent:#49b6ff; --text:#e6edf3; --dim:#8aa0b5; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  body { margin:0; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; background:var(--bg); color:var(--text); height:100dvh; display:flex; flex-direction:column; }
  header { padding:14px 16px; background:var(--card); border-bottom:1px solid var(--line); display:flex; align-items:center; gap:10px; }
  header .dot { width:10px; height:10px; border-radius:50%; background:var(--accent); box-shadow:0 0 10px var(--accent); }
  header b { font-size:18px; letter-spacing:.5px; } header span { color:var(--dim); font-size:12px; margin-left:auto; }
  #log { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:10px; }
  .msg { max-width:86%; padding:10px 14px; border-radius:16px; line-height:1.4; white-space:pre-wrap; word-wrap:break-word; }
  .me { align-self:flex-end; background:var(--me); border-bottom-right-radius:4px; }
  .jx { align-self:flex-start; background:var(--jx); border:1px solid var(--line); border-bottom-left-radius:4px; }
  .sys { align-self:center; color:var(--dim); font-size:13px; }
  .err { align-self:flex-start; background:#3a1d1d; border:1px solid #5a2a2a; border-radius:16px; padding:10px 14px; }
  form { display:flex; gap:8px; padding:12px; background:var(--card); border-top:1px solid var(--line); align-items:flex-end; }
  textarea { flex:1; resize:none; background:#0d1420; color:var(--text); border:1px solid var(--line); border-radius:12px; padding:11px 13px; font-size:16px; max-height:120px; }
  button { border:0; border-radius:12px; padding:0 16px; height:44px; font-size:15px; font-weight:600; color:#fff; background:var(--me); cursor:pointer; }
  button.ghost { background:#24324a; } button:active { transform:scale(.96); }
  button:disabled { opacity:.5; } #mic.on { background:#d9433f; }
  .row { display:flex; gap:8px; }
</style></head>
<body>
<header><span class="dot"></span><b>JARVIS</b><span id="st">bağlanıyor…</span></header>
<div id="log"></div>
<form id="f">
  <button type="button" id="mic" class="ghost" title="Konuş">🎤</button>
  <textarea id="t" rows="1" placeholder="Jarvis'e yazın…" autocomplete="off"></textarea>
  <button type="submit" id="send">Gönder</button>
</form>
<script>
const token = new URLSearchParams(location.search).get("t") || "";
const log = document.getElementById("log"), st = document.getElementById("st");
const ta = document.getElementById("t"), mic = document.getElementById("mic");
let speak = true, lastEvent = 0;

function add(text, cls){ const d=document.createElement("div"); d.className="msg "+cls; d.textContent=text; log.appendChild(d); log.scrollTop=log.scrollHeight; return d; }
function say(text){ if(!speak||!window.speechSynthesis) return; try{ const u=new SpeechSynthesisUtterance(text); u.lang="tr-TR"; speechSynthesis.cancel(); speechSynthesis.speak(u);}catch(e){} }

async function api(path, body){
  const r = await fetch(path, {method: body?"POST":"GET", headers:{"X-Jarvis-Token":token,"Content-Type":"application/json"}, body: body?JSON.stringify(body):undefined});
  if(r.status===401){ st.textContent="anahtar geçersiz"; throw new Error("401"); }
  return r.json();
}

async function send(text){
  text=text.trim(); if(!text) return;
  add(text,"me"); ta.value=""; ta.style.height="auto";
  const sending=add("…","jx");
  try{ const res=await api("/api/ask",{text}); sending.textContent=res.reply; sending.className="msg "+(res.ok?"jx":"err"); if(res.ok) say(res.reply); }
  catch(e){ sending.textContent="Bağlanamadım."; sending.className="msg err"; }
}

document.getElementById("f").addEventListener("submit", e=>{ e.preventDefault(); send(ta.value); });
ta.addEventListener("input", ()=>{ ta.style.height="auto"; ta.style.height=Math.min(ta.scrollHeight,120)+"px"; });
ta.addEventListener("keydown", e=>{ if(e.key==="Enter"&&!e.shiftKey){ e.preventDefault(); send(ta.value); } });

// Telefonun kendi konuşma tanıması (tarayıcıda çalışır, ses sunucuya gitmez)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if(SR){
  const rec=new SR(); rec.lang="tr-TR"; rec.interimResults=false;
  let on=false;
  mic.onclick=()=>{ if(on){rec.stop();return;} try{rec.start();}catch(e){} };
  rec.onstart=()=>{on=true; mic.classList.add("on");};
  rec.onend=()=>{on=false; mic.classList.remove("on");};
  rec.onresult=e=>{ send(e.results[0][0].transcript); };
} else { mic.style.display="none"; }

// Hatırlatıcılar için yoklama
async function poll(){
  try{ const res=await api("/api/events?after="+lastEvent);
    st.textContent="bağlı"; (res.reminders||[]).forEach(r=>{ lastEvent=Math.max(lastEvent,r.id); add("⏰ "+r.text,"sys"); say(r.text); });
  }catch(e){}
  setTimeout(poll, 4000);
}
if(!token){ st.textContent="anahtar yok"; add("Bu sayfaya anahtarsız girdiniz. Jarvis'in verdiği tam adresi kullanın.","err"); }
else { add("Bağlandım. Ev bilgisayarınızdaki Jarvis'e yazabilir ya da 🎤 ile konuşabilirsiniz.","sys"); poll(); }
</script></body></html>
"""


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # paket göndermez, yerel IP'yi öğrenir
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # erişim loglarını sustur
        pass

    @property
    def srv(self):
        return self.server  # type: ignore[return-value]

    def _ok(self, token: str | None) -> bool:
        return token is not None and hmac.compare_digest(token, self.srv.token)

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _token_from_request(self) -> str | None:
        header = self.headers.get("X-Jarvis-Token")
        if header:
            return header
        qs = parse_qs(urlparse(self.path).query)
        return qs.get("t", [None])[0]

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            body = self.srv.page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/events":
            if not self._ok(self._token_from_request()):
                self._json(401, {"error": "yetkisiz"})
                return
            after = 0
            try:
                after = int(parse_qs(urlparse(self.path).query).get("after", ["0"])[0])
            except ValueError:
                pass
            self._json(200, {"reminders": self.srv.events_since(after)})
            return
        self._json(404, {"error": "bulunamadı"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not self._ok(self._token_from_request()):
            self._json(401, {"error": "yetkisiz"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 100_000:
            self._json(413, {"error": "çok büyük"})
            return
        try:
            data = json.loads(self.rfile.read(length) or "{}")
        except (json.JSONDecodeError, ValueError):
            self._json(400, {"error": "geçersiz istek"})
            return
        if path == "/api/ask":
            text = (data.get("text") or "").strip()
            if not text:
                self._json(400, {"error": "boş"})
                return
            reply = self.srv.service.ask("web", text, mode="phone")
            self._json(200, {"ok": reply.ok, "reply": reply.text})
            return
        if path == "/api/reset":
            self.srv.service.reset_channel("web")
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "bulunamadı"})


class WebInterface:
    def __init__(self, service, config):
        self.service = service
        self.config = config
        self.token = config.web_token or self._load_or_create_token(config)
        self.host = config.web_host or "0.0.0.0"
        self.port = config.web_port or 8765
        self._events: deque[dict] = deque(maxlen=50)
        self._event_lock = threading.Lock()
        self._next_id = 1
        self._server: ThreadingHTTPServer | None = None

    @staticmethod
    def _load_or_create_token(config) -> str:
        """Anahtar .env'de yoksa veri klasöründe saklanır; adres her açılışta aynı kalır."""
        path = config.data_dir / "web_token.txt"
        try:
            token = path.read_text(encoding="utf-8").strip()
            if token:
                return token
        except OSError:
            pass
        token = secrets.token_urlsafe(12)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(token, encoding="utf-8")
        except OSError:
            pass
        return token

    def add_event(self, text: str) -> None:
        with self._event_lock:
            self._events.append({"id": self._next_id, "text": text})
            self._next_id += 1

    def events_since(self, after: int) -> list[dict]:
        with self._event_lock:
            return [e for e in self._events if e["id"] > after]

    @property
    def url(self) -> str:
        return f"http://{_lan_ip()}:{self.port}/?t={self.token}"

    def start(self) -> threading.Thread:
        server = ThreadingHTTPServer((self.host, self.port), _Handler)
        server.daemon_threads = True
        # Handler'ın erişebilmesi için servis bilgilerini sunucuya iliştir.
        server.service = self.service          # type: ignore[attr-defined]
        server.token = self.token              # type: ignore[attr-defined]
        server.page = PAGE                     # type: ignore[attr-defined]
        server.events_since = self.events_since  # type: ignore[attr-defined]
        self._server = server
        thread = threading.Thread(target=server.serve_forever, name="web", daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
