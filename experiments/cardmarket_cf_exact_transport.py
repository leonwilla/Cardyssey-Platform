#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import datetime
import hashlib
import html as htmllib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import websockets
    import wreq
    from wreq.blocking import Client
    from wreq.dns import DnsOptions, LookupIpStrategy
    from wreq.redirect import Policy
except ImportError as exc:
    sys.exit(f'missing dependency "{exc.name}": pip install "wreq==0.13.0" "websockets>=12"')

TARGET_URL = "https://www.cardmarket.com/de/Pokemon"
COOKIE_SITE = "cardmarket.com"
SESSION_FILE = Path(__file__).resolve().with_name("cardmarket_cf_test_session.json")

ACCEPT_DOCUMENT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,"
    "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
)
ACCEPT_ENCODING = "gzip, deflate, br, zstd"

LOW_ENTROPY_HINTS = ("sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform")
HIGH_ENTROPY_HINTS = (
    "sec-ch-ua-full-version",
    "sec-ch-ua-arch",
    "sec-ch-ua-platform-version",
    "sec-ch-ua-model",
    "sec-ch-ua-bitness",
    "sec-ch-ua-full-version-list",
)

ORDER_TYPED_NAV = (
    "upgrade-insecure-requests", "user-agent", "accept",
    "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
    "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user", "sec-fetch-dest",
    "accept-encoding", "accept-language", "cookie", "priority",
)
ORDER_RESTART_NAV = (
    "upgrade-insecure-requests", "user-agent", "accept",
    "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user", "sec-fetch-dest",
    "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", *HIGH_ENTROPY_HINTS,
    "accept-encoding", "accept-language", "cookie", "priority",
)
ORDER_TYPED_NAV_HINTS = (
    "upgrade-insecure-requests", "user-agent", "accept",
    "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", *HIGH_ENTROPY_HINTS,
    "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user", "sec-fetch-dest",
    "accept-encoding", "accept-language", "cookie", "priority",
)

CHALLENGE_MARKERS = ("cdn-cgi/challenge-platform", "_cf_chl_opt", "__cf_chl_")

log = logging.getLogger("pc.main")
log_session = logging.getLogger("pc.session")
log_proxy = logging.getLogger("pc.proxy")
log_chrome = logging.getLogger("pc.chrome")
log_http = logging.getLogger("pc.http")


class CliError(Exception):
    pass


# --- logging ---------------------------------------------------------------------------


class LogFormatter(logging.Formatter):
    COLORS = {logging.DEBUG: "\033[2m", logging.WARNING: "\033[33m", logging.ERROR: "\033[31m"}

    def __init__(self, color: bool):
        super().__init__()
        self.color = color

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(record.created))
        component = record.name.rpartition(".")[2]
        line = f"{ts} {record.levelname:<7} {component:<7} {record.getMessage()}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        color = self.COLORS.get(record.levelno) if self.color else None
        return f"{color}{line}\033[0m" if color else line


def setup_logging(verbose: bool, quiet: bool) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(LogFormatter(sys.stderr.isatty() and "NO_COLOR" not in os.environ))
    root = logging.getLogger("pc")
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO)
    root.propagate = False


# --- identity + session ----------------------------------------------------------------


def _brand_list(entries: list[dict]) -> str:
    return ", ".join(f'"{e["brand"]}";v="{e["version"]}"' for e in entries)


def chrome_accept_language(languages: list[str]) -> str:
    parts, q10 = [], 10
    for lang in languages:
        parts.append(lang if q10 == 10 else f"{lang};q=0.{q10}")
        if q10 > 1:
            q10 -= 1
    return ",".join(parts)


@dataclass
class Identity:
    user_agent: str
    brands: list
    full_version_list: list
    full_version: str
    platform: str
    platform_version: str
    architecture: str
    bitness: str
    model: str
    mobile: bool
    accept_language: str

    @property
    def major(self) -> int:
        m = re.search(r"Chrome/(\d+)", self.user_agent)
        return int(m.group(1)) if m else 0

    def hint_values(self) -> dict[str, str]:
        return {
            "sec-ch-ua": _brand_list(self.brands),
            "sec-ch-ua-mobile": "?1" if self.mobile else "?0",
            "sec-ch-ua-platform": f'"{self.platform}"',
            "sec-ch-ua-full-version": f'"{self.full_version}"',
            "sec-ch-ua-arch": f'"{self.architecture}"',
            "sec-ch-ua-platform-version": f'"{self.platform_version}"',
            "sec-ch-ua-model": f'"{self.model}"',
            "sec-ch-ua-bitness": f'"{self.bitness}"',
            "sec-ch-ua-full-version-list": _brand_list(self.full_version_list),
        }


@dataclass
class CfSession:
    identity: Identity
    cookies: list = field(default_factory=list)
    stored_hints: list = field(default_factory=list)
    proxy_key: str = "direct"
    exit_ip: str = ""
    saved_at: str = ""

    def set_cookie(self, name: str, value: str) -> None:
        for pair in self.cookies:
            if pair[0] == name:
                pair[1] = value
                return
        self.cookies.append([name, value])

    def drop_cookie(self, name: str) -> None:
        self.cookies = [p for p in self.cookies if p[0] != name]

    def has_clearance(self) -> bool:
        return any(n == "cf_clearance" for n, _ in self.cookies)


def proxy_key(proxy: ProxySpec | None) -> str:
    if proxy is None:
        return "direct"
    return hashlib.sha256(proxy.url_with_auth.encode()).hexdigest()[:16]


def load_session(key: str) -> CfSession | None:
    try:
        raw = json.loads(SESSION_FILE.read_text())
        sess = CfSession(identity=Identity(**raw["identity"]), cookies=raw["cookies"],
                         stored_hints=raw.get("stored_hints", []), proxy_key=raw["proxy_key"],
                         exit_ip=raw.get("exit_ip", ""), saved_at=raw.get("saved_at", ""))
    except FileNotFoundError:
        log_session.debug("no cached session at %s", SESSION_FILE)
        return None
    except Exception as exc:
        log_session.warning("ignoring unreadable session file: %s", exc)
        return None
    if sess.proxy_key != key:
        log_session.info("cached session belongs to a different proxy, discarding it")
        return None
    if not sess.has_clearance():
        log_session.info("cached session has no cf_clearance, discarding it")
        return None
    return sess


def save_session(sess: CfSession) -> None:
    sess.saved_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    tmp = SESSION_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(sess), indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(SESSION_FILE)
    log_session.debug("saved %d cookie(s) to %s", len(sess.cookies), SESSION_FILE)


# --- proxy -----------------------------------------------------------------------------


@dataclass
class ProxySpec:
    host: str
    port: int
    username: str | None = None
    password: str | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def url_with_auth(self) -> str:
        if self.username is None:
            return self.url
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"


def parse_proxy(raw: str) -> ProxySpec:
    raw = raw.strip()
    if "://" in raw:
        u = urllib.parse.urlsplit(raw)
        if u.scheme not in ("http", ""):
            raise CliError(f"only http:// proxies are supported, got {u.scheme}://")
        return ProxySpec(u.hostname or "", u.port or 80,
                         urllib.parse.unquote(u.username) if u.username else None,
                         urllib.parse.unquote(u.password) if u.password else None)
    parts = raw.split(":")
    if len(parts) == 2:
        return ProxySpec(parts[0], int(parts[1]))
    if len(parts) >= 4:
        return ProxySpec(parts[0], int(parts[1]), parts[2], ":".join(parts[3:]))
    raise CliError("proxy format: http://user:pass@host:port or host:port[:user:pass]")


class ProxyAuthBridge:
    def __init__(self, upstream: ProxySpec):
        self.upstream = upstream
        self.auth = b"Basic " + base64.b64encode(f"{upstream.username}:{upstream.password}".encode())
        self.loop = asyncio.new_event_loop()
        self.port = 0
        self._ready = threading.Event()
        self._server = None
        threading.Thread(target=self._run, daemon=True).start()
        if not self._ready.wait(5):
            raise RuntimeError("proxy auth bridge did not start")
        log_proxy.debug("auth bridge 127.0.0.1:%d -> %s:%d", self.port, upstream.host, upstream.port)

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self._server = self.loop.run_until_complete(
            asyncio.start_server(self._handle, "127.0.0.1", 0))
        self.port = self._server.sockets[0].getsockname()[1]
        self._ready.set()
        self.loop.run_forever()

    async def _handle(self, reader, writer) -> None:
        up_writer = None
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            line = head.split(b"\r\n", 1)[0].split()
            if len(line) < 2 or line[0] != b"CONNECT":
                writer.write(b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
                return
            target = line[1]
            up_reader, up_writer = await asyncio.open_connection(self.upstream.host, self.upstream.port)
            up_writer.write(b"CONNECT " + target + b" HTTP/1.1\r\nHost: " + target
                            + b"\r\nProxy-Authorization: " + self.auth + b"\r\n\r\n")
            await up_writer.drain()
            resp = await up_reader.readuntil(b"\r\n\r\n")
            status = resp.split(b"\r\n", 1)[0]
            if b" 200" not in status:
                log_proxy.warning("upstream proxy refused CONNECT %s: %s",
                                  target.decode(errors="replace"), status.decode(errors="replace"))
                writer.write(status + b"\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
                return
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()

            async def pipe(src, dst):
                try:
                    while chunk := await src.read(65536):
                        dst.write(chunk)
                        await dst.drain()
                finally:
                    dst.close()

            await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer),
                                 return_exceptions=True)
        except Exception as exc:
            log_proxy.debug("tunnel closed: %s", exc or type(exc).__name__)
        finally:
            writer.close()
            if up_writer is not None:
                up_writer.close()

    def close(self) -> None:
        if self._server is not None:
            self.loop.call_soon_threadsafe(self._server.close)
        self.loop.call_soon_threadsafe(self.loop.stop)


# --- solver: real Chrome over CDP ------------------------------------------------------


def find_chrome() -> str:
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    system = platform.system()
    candidates: list[str] = []
    if system == "Darwin":
        candidates = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                      str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    elif system == "Windows":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"),
                     os.environ.get("LOCALAPPDATA")):
            if base:
                candidates.append(str(Path(base) / "Google/Chrome/Application/chrome.exe"))
    else:
        candidates = [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable",
                                                      "chromium", "chromium-browser")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise CliError("Google Chrome not found, install it or set CHROME_PATH")


_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http_json(port: int, path: str):
    with _LOCAL.open(f"http://127.0.0.1:{port}{path}", timeout=3) as r:
        return json.loads(r.read())


async def _cdp_call(ws_url: str, method: str, params: dict | None = None, timeout: float = 8) -> dict:
    kwargs = {"max_size": None, "open_timeout": timeout}
    try:
        conn = websockets.connect(ws_url, proxy=None, **kwargs)
    except TypeError:
        conn = websockets.connect(ws_url, **kwargs)
    async with conn as ws:
        await ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout))
            if msg.get("id") == 1:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method}: {msg['error'].get('message')}")
                return msg.get("result", {})


class ChromeProcess:
    def __init__(self, url: str, proxy_server: str | None, headless: bool, show: bool):
        chrome = find_chrome()
        self.profile = tempfile.mkdtemp(prefix="pc-cf-chrome-")
        args = [
            chrome,
            f"--user-data-dir={self.profile}",
            "--remote-debugging-port=0",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1200,900",
        ]
        if not show:
            args.append("--window-position=-32000,-32000")
        if proxy_server:
            args += [f"--proxy-server={proxy_server}",
                     "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]
        if headless:
            args.append("--headless=new")
        args.append(f"--app={url}")
        log_chrome.debug("launching %s", chrome)
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.port: int | None = None

    def wait_port(self, timeout: float = 20) -> int:
        marker = Path(self.profile) / "DevToolsActivePort"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                port = int(marker.read_text().split("\n")[0].strip())
                _http_json(port, "/json/version")
                self.port = port
                log_chrome.debug("DevTools on port %d", port)
                return port
            except (FileNotFoundError, ValueError, OSError):
                pass
            time.sleep(0.2)
        raise RuntimeError("Chrome did not open its DevTools port")

    def alive(self) -> bool:
        try:
            return bool(_http_json(self.port, "/json/version").get("webSocketDebuggerUrl"))
        except Exception:
            return False

    def browser_ws(self) -> str:
        return _http_json(self.port, "/json/version")["webSocketDebuggerUrl"]

    def page(self) -> dict | None:
        pages = [t for t in _http_json(self.port, "/json/list")
                 if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        return next((t for t in pages if COOKIE_SITE in t.get("url", "")), pages[0] if pages else None)

    async def move_offscreen(self) -> None:
        try:
            page = None
            for _ in range(15):
                page = self.page()
                if page:
                    break
                await asyncio.sleep(0.2)
            if not page:
                log_chrome.warning("no page target yet, window stays where Chrome put it")
                return
            bws = self.browser_ws()
            win = await _cdp_call(bws, "Browser.getWindowForTarget", {"targetId": page["id"]})
            width = win.get("bounds", {}).get("width", 1200)
            await _cdp_call(bws, "Browser.setWindowBounds",
                            {"windowId": win["windowId"], "bounds": {"left": -(width - 1), "top": 0}})
            log_chrome.debug("window moved off-screen")
        except Exception as exc:
            log_chrome.warning("could not move the window off-screen: %s", exc)

    async def close(self) -> None:
        if self.port is not None:
            try:
                await _cdp_call(self.browser_ws(), "Browser.close", timeout=3)
            except Exception:
                pass
        if self.proc.poll() is None:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/pid", str(self.proc.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        for _ in range(10):
            shutil.rmtree(self.profile, ignore_errors=True)
            if not Path(self.profile).exists():
                break
            await asyncio.sleep(0.3)
        log_chrome.debug("Chrome closed, temp profile removed")


IDENTITY_JS = """
(async () => {
  const d = navigator.userAgentData;
  const he = d ? await d.getHighEntropyValues(
      ["architecture", "bitness", "model", "platformVersion", "fullVersionList", "uaFullVersion"]) : {};
  return JSON.stringify({
    user_agent: navigator.userAgent,
    webdriver: navigator.webdriver,
    languages: navigator.languages,
    brands: d ? d.brands : [],
    mobile: d ? d.mobile : false,
    platform: d ? d.platform : "",
    he: he,
  });
})()
"""


def _site_cookie(c: dict) -> bool:
    dom = c.get("domain", "").lstrip(".")
    return dom == COOKIE_SITE or dom.endswith("." + COOKIE_SITE)


async def _browser_cookies(chrome: ChromeProcess) -> list[dict]:
    return (await _cdp_call(chrome.browser_ws(), "Storage.getCookies"))["cookies"]


async def _evaluate(chrome: ChromeProcess, expression: str, await_promise: bool = False):
    page = chrome.page()
    if not page:
        return None
    res = await _cdp_call(page["webSocketDebuggerUrl"], "Runtime.evaluate",
                          {"expression": expression, "returnByValue": True, "awaitPromise": await_promise})
    if res.get("exceptionDetails"):
        raise RuntimeError(res["exceptionDetails"].get("text", "page exception"))
    return res.get("result", {}).get("value")


async def _solve(url: str, proxy_server: str | None, headless: bool, show: bool,
                 timeout: float) -> CfSession:
    mode = "headless" if headless else "visible" if show else "off-screen"
    log_chrome.info("solving the challenge in Chrome (%s)", mode)
    chrome = ChromeProcess(url, proxy_server, headless, show)
    try:
        chrome.wait_port()
        if not show and not headless:
            await chrome.move_offscreen()

        t0 = time.monotonic()
        next_note = t0 + 15
        while True:
            elapsed = time.monotonic() - t0
            if elapsed > timeout:
                raise TimeoutError(f"no cf_clearance after {timeout:.0f}s, "
                                   "rerun with --show and solve the Turnstile by hand")
            if not chrome.alive():
                raise RuntimeError("Chrome exited before the challenge cleared")
            try:
                cookies = await _browser_cookies(chrome)
            except Exception:
                cookies = []
            if any(c["name"] == "cf_clearance" and _site_cookie(c) for c in cookies):
                break
            if time.monotonic() >= next_note:
                log_chrome.info("waiting for cf_clearance (%.0fs)", elapsed)
                next_note += 15
            await asyncio.sleep(1)
        log_chrome.info("cf_clearance issued after %.1fs", time.monotonic() - t0)

        deadline = time.monotonic() + 20
        html = ""
        while time.monotonic() < deadline:
            try:
                html = await _evaluate(
                    chrome, "document.documentElement ? document.documentElement.outerHTML : ''") or ""
            except Exception:
                html = ""
            if html and not any(m in html for m in CHALLENGE_MARKERS):
                break
            await asyncio.sleep(0.5)
        else:
            raise TimeoutError("cf_clearance was issued but the real page never loaded")
        title = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        log_chrome.info("page loaded: %s", htmllib.unescape(title.group(1).strip()) if title else "-")
        await asyncio.sleep(1.5)

        raw = json.loads(await _evaluate(chrome, IDENTITY_JS, await_promise=True))
        if raw.get("webdriver"):
            log_chrome.warning("navigator.webdriver is true in the solver Chrome")
        he = raw["he"]
        ident = Identity(
            user_agent=raw["user_agent"],
            brands=raw["brands"],
            full_version_list=he.get("fullVersionList", []),
            full_version=he.get("uaFullVersion", ""),
            platform=raw["platform"],
            platform_version=he.get("platformVersion", ""),
            architecture=he.get("architecture", ""),
            bitness=he.get("bitness", ""),
            model=he.get("model", ""),
            mobile=bool(raw["mobile"]),
            accept_language=chrome_accept_language(raw["languages"]),
        )
        site = [c for c in await _browser_cookies(chrome) if _site_cookie(c)]
        site.sort(key=lambda c: 0 if c["name"] == "cf_clearance" else 1)
        sess = CfSession(identity=ident, cookies=[[c["name"], c["value"]] for c in site])
        log_chrome.debug("%d site cookie(s): %s", len(site), ", ".join(c["name"] for c in site))

        try:
            trace = await _evaluate(chrome, "fetch('/cdn-cgi/trace', {cache: 'no-store'}).then(r => r.text())",
                                    await_promise=True) or ""
            m = re.search(r"^ip=(\S+)$", trace, re.M)
            sess.exit_ip = m.group(1) if m else ""
        except Exception as exc:
            log_chrome.warning("could not read the exit IP: %s", exc)
        if not sess.exit_ip:
            log_chrome.warning("exit IP unknown, the request client will not pin the IP family")
        sess.stored_hints = list(HIGH_ENTROPY_HINTS)
        return sess
    finally:
        await chrome.close()


def solve_with_chrome(url: str, proxy: ProxySpec | None, headless: bool, show: bool,
                      timeout: float) -> CfSession:
    bridge = None
    proxy_server = None
    if proxy is not None:
        log_proxy.info("Chrome goes through %s:%d", proxy.host, proxy.port)
        if proxy.username is not None:
            bridge = ProxyAuthBridge(proxy)
            proxy_server = f"http://127.0.0.1:{bridge.port}"
        else:
            proxy_server = proxy.url
    try:
        return asyncio.run(_solve(url, proxy_server, headless, show, timeout))
    finally:
        if bridge is not None:
            bridge.close()


# --- request client --------------------------------------------------------------------


def pick_profile(major: int) -> str:
    available = sorted((int(n[6:]), n) for n in dir(wreq.Profile) if re.fullmatch(r"Chrome\d+", n))
    eligible = [n for v, n in available if v <= major] or [available[-1][1]]
    return eligible[-1]


def pick_platform(name: str):
    return {"macos": wreq.Platform.MacOS, "windows": wreq.Platform.Windows,
            "linux": wreq.Platform.Linux}.get(name.lower(), wreq.Platform.MacOS)


def build_client(ident: Identity, proxy: ProxySpec | None, insecure: bool, exit_ip: str = "") -> Client:
    profile = pick_profile(ident.major)
    log_http.debug("wreq emulation %s on %s", profile, ident.platform or "macOS")
    kwargs: dict = dict(
        emulation=wreq.Emulation(profile=getattr(wreq.Profile, profile),
                                 platform=pick_platform(ident.platform), headers=False),
        redirect=Policy.none(),
        cookie_store=False,
        timeout=datetime.timedelta(seconds=30),
    )
    if proxy is not None:
        auth = {}
        if proxy.username is not None:
            auth = {"username": proxy.username, "password": proxy.password or ""}
        kwargs["proxies"] = [wreq.Proxy.all(proxy.url, **auth)]
        log_http.debug("request client goes through %s:%d", proxy.host, proxy.port)
    else:
        kwargs["no_proxy"] = True
        if exit_ip:
            v6 = ":" in exit_ip
            kwargs["dns_options"] = DnsOptions(lookup_ip_strategy=LookupIpStrategy.IPV6_THEN_IPV4 if v6
                                               else LookupIpStrategy.IPV4_THEN_IPV6)
            log_http.debug("preferring %s to match the clearance IP", "IPv6" if v6 else "IPv4")
    if insecure:
        kwargs["tls_verify"] = False
    return Client(**kwargs)


def navigation_headers(sess: CfSession, restart: bool) -> list[tuple[str, str]]:
    ident = sess.identity
    hints = ident.hint_values()
    stored = [h for h in HIGH_ENTROPY_HINTS if h in sess.stored_hints]
    values: dict[str, str] = {
        "upgrade-insecure-requests": "1",
        "user-agent": ident.user_agent,
        "accept": ACCEPT_DOCUMENT,
        "sec-fetch-site": "none",
        "sec-fetch-mode": "navigate",
        "sec-fetch-user": "?1",
        "sec-fetch-dest": "document",
        "accept-encoding": ACCEPT_ENCODING,
        "accept-language": ident.accept_language,
        "priority": "u=0, i",
    }
    for h in (*LOW_ENTROPY_HINTS, *stored):
        values[h] = hints[h]
    order = ORDER_RESTART_NAV if restart else (ORDER_TYPED_NAV_HINTS if stored else ORDER_TYPED_NAV)
    out: list[tuple[str, str]] = []
    for name in order:
        if name == "cookie":
            out.extend(("cookie", f"{n}={v}") for n, v in sess.cookies)
        elif name in values:
            out.append((name, values[name]))
    return out


def _header(resp, name: str) -> str:
    v = resp.headers.get(name)
    return bytes(v).decode("latin-1") if v is not None else ""


def _absorb_cookies(sess: CfSession, resp) -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    names = []
    for c in resp.cookies:
        expired = (c.max_age is not None and c.max_age.total_seconds() <= 0) or \
                  (c.expires is not None and c.expires.replace(tzinfo=c.expires.tzinfo or datetime.timezone.utc) <= now)
        if expired or c.value == "":
            sess.drop_cookie(c.name)
            names.append(f"-{c.name}")
        else:
            sess.set_cookie(c.name, c.value)
            names.append(c.name)
    if names:
        log_http.debug("response cookies: %s", ", ".join(names))


def _parse_ch(value: str) -> set[str]:
    return {p.strip().lower() for p in value.split(",") if p.strip()}


def navigate(client: Client, sess: CfSession, url: str):
    restart = False
    for _ in range(2):
        headers = navigation_headers(sess, restart)
        log_http.debug("GET %s%s with %d cookie(s)", url, " (Critical-CH restart)" if restart else "",
                       len(sess.cookies))
        log_http.debug("header order: %s", ", ".join(dict.fromkeys(k for k, _ in headers)))
        hm = wreq.HeaderMap()
        for k, v in headers:
            hm.append(k, v)
        resp = client.get(url, headers=hm, orig_headers=[k for k, _ in headers], default_headers=False)
        body = bytes(resp.bytes())
        _absorb_cookies(sess, resp)

        accept_ch = _parse_ch(_header(resp, "accept-ch"))
        if accept_ch:
            sess.stored_hints = [h for h in HIGH_ENTROPY_HINTS if h in accept_ch]
        critical = _parse_ch(_header(resp, "critical-ch"))
        sent = {k for k, _ in headers}
        missing = [h for h in HIGH_ENTROPY_HINTS if h in critical and h in accept_ch and h not in sent]
        if missing and not restart:
            log_http.info("Critical-CH asks for %d hint(s), resending with them", len(missing))
            restart = True
            continue
        return resp, body
    return resp, body


def classify(resp, body: bytes) -> str:
    status = resp.status.as_int()
    if _header(resp, "cf-mitigated").lower() == "challenge":
        return "challenge"
    if status in (403, 429, 503):
        if b"/cdn-cgi/challenge-platform/" in body or b"<title>Just a moment" in body:
            return "challenge"
        if b"Sorry, you have been blocked" in body or b"cf-error-details" in body:
            return "blocked"
    return "ok" if 200 <= status < 300 else f"http-{status}"


# --- cli -------------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Cardmarket isolated test using original PriceCharting transport.")
    ap.add_argument("--url", default=TARGET_URL, help="page to fetch (default: %(default)s)")
    ap.add_argument("--proxy", help="sticky proxy: http://user:pass@host:port or host:port[:user:pass]")
    ap.add_argument("--out", help="write the page HTML to this file")
    ap.add_argument("--fresh", action="store_true", help="ignore the cached session")
    ap.add_argument("--show", action="store_true", help="keep the solver Chrome window visible")
    ap.add_argument("--headless", action="store_true", help="run the solver Chrome headless")
    ap.add_argument("--solve-timeout", type=float, default=120, metavar="SEC",
                    help="max wait for cf_clearance (default: %(default)s)")
    ap.add_argument("--powhttp", type=int, metavar="PORT", help="route all traffic through powhttp")
    verbosity = ap.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true", help="debug output")
    verbosity.add_argument("-q", "--quiet", action="store_true", help="warnings and errors only")
    return ap.parse_args()


def run(args: argparse.Namespace) -> int:
    insecure = False
    proxy = parse_proxy(args.proxy) if args.proxy else None
    if args.powhttp:
        if proxy is not None:
            raise CliError("--powhttp and --proxy cannot be combined")
        proxy = ProxySpec("127.0.0.1", args.powhttp)
        insecure = True
        log.info("routing all traffic through powhttp on 127.0.0.1:%d", args.powhttp)
    key = proxy_key(proxy)

    sess = None if args.fresh else load_session(key)
    if sess is not None:
        log.info("using cached session from %s (clearance IP %s)", sess.saved_at, sess.exit_ip or "unknown")

    for attempt in range(2):
        if sess is None:
            sess = solve_with_chrome(args.url, proxy, args.headless, args.show, args.solve_timeout)
            sess.proxy_key = key
            save_session(sess)
            ident = sess.identity
            log.info("identity: Chrome %s on %s %s %s, clearance IP %s",
                     ident.full_version or ident.major, ident.platform, ident.platform_version,
                     ident.architecture, sess.exit_ip or "unknown")
            log.debug("user agent: %s", ident.user_agent)
            log.debug("accept-language: %s", ident.accept_language)

        client = build_client(sess.identity, proxy, insecure, sess.exit_ip)
        resp, body = navigate(client, sess, args.url)
        save_session(sess)
        status = resp.status.as_int()
        verdict = classify(resp, body)
        log_http.info("GET %s -> %d %s, %d bytes, cf-ray %s",
                      args.url, status, verdict, len(body), _header(resp, "cf-ray") or "-")

        if verdict == "ok":
            title = re.search(rb"<title>(.*?)</title>", body, re.S | re.I)
            log.info("title: %s", htmllib.unescape(title.group(1).decode("utf-8", "replace").strip()) if title else "-")
            if args.out:
                Path(args.out).write_bytes(body)
                log.info("saved HTML to %s", args.out)
            return 0
        if verdict == "blocked":
            log.error("hard block (WAF rule or IP), a solve cannot fix this; use another exit IP")
            return 3
        if verdict != "challenge":
            log.error("unexpected HTTP %d", status)
            return 4
        if attempt == 0:
            log.warning("challenged, solving again in Chrome")
            sess = None
    log.error("still challenged after a fresh solve: the exit IP changed between Chrome and the "
              "request client (rotating proxy?) or the request fingerprint is off")
    return 2


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose, args.quiet)
    try:
        return run(args)
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130
    except (CliError, TimeoutError, RuntimeError) as exc:
        log.error("%s", exc)
        log.debug("traceback", exc_info=True)
        return 1
    except Exception as exc:
        log.error("%s: %s", type(exc).__name__, exc)
        log.debug("traceback", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
