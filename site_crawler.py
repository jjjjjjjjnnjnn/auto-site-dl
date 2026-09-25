# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 jjjjjjjjnnjnn
"""通用站点媒体下载器 v1.2.0: 填网址 -> 检测人机验证 -> 需验证弹窗等人工 -> 自动全站下载.

用法 (python -u -X utf8 site_crawler.py ...):
  check <url>              只检测: 该站是否需要人机验证 (不下载, 不存页面内容)
  wait <url>               弹窗打开网站, 人工验证后保存会话 (自动识别 + 回车确认双保险)
  dl <url> [batch]         用已验证会话下载 (默认每轮60页, 支持断点续传;
                              视频优先时自动进详情/观看页深挖真流)
  auto <url> [batch]       全流程: 检测 -> 需验证则弹窗等人工 -> 自动下载
  diag <url>               诊断媒体分布: 只统计URL主机/后缀 (不保存文本/图片)
  watch <url> [batch]      深层: 点视频->点观看->等加载->下真流 (见 watchflow.py)
  nav <url>                栏目测绘: 导航区清单 columns.txt + 分页器试探
  purge <url>              清扫: 补/纠正扩展名, 隔离非媒体到 rejected/(纯本地, 不联网)
  envcheck [url]           环境自检: 依赖/浏览器/引擎 (纯本地, 不碰目标站)

选项 (加在末尾):
  --allow-cdn              媒体允许本站外CDN域名 (默认只收本站; 开启后仍只收字节并验文件头)
  --allow-http             允许http (默认只https)
  --proxy URL              路由中转: 浏览器/requests/三引擎全走代理 (http/socks5);
                              不设时自动读系统代理(与人工浏览器同路)
  --insecure               忽略证书校验(仅可信内网/MITM代理下用, 默认开校验)
  --browser CH             浏览器通道 camoufox(推荐, C++层指纹)/chrome/edge/默认chromium
  --clone-profile PATH     克隆真实浏览器profile(Torch思路, 只读源, 隔离副本)
  --column SUB             只爬URL含该子串的栏目
  --video-first            视频优先(默认开, 只下视频/m3u8跳过图片; --no-video-first 关)
  --dl-jobs N              watch下载并发(默认3, 收获串行+下载并行)

退出码: 0 成功/无验证 | 1 等待验证超时 | 2 环境缺失·代理已死·导航失败 |
        3 会话未验证 | 4 中途重现验证 | 10 需人机验证

安全约束 (写死, 不可绕过):
  - 只GET; 跳过 login/logout/register/pay/order/submit/upload/delete/admin 类链接
  - 只收白名单后缀; Content-Type + 文件头魔数双重校验; <512B 追踪像素丢弃
  - SSRF防护: 下载目标必须解析为公网IP; 跳转终点复检 scheme+主机白名单+SSRF
  - TLS默认强制校验; 外部引擎禁自动更新; robots.txt Disallow 默认遵守(取失败放行)
  - 日志脱敏: URL只记到path, query/fragment不落盘; Cookie/代理认证信息永不打印
  - 不保存 HTML/文本/截图; 只存媒体文件 + inventory.csv 记账
  - 不填任何表单, 不登录, 不调用外部打码

反追踪设计 (防画像/防回溯):
  - 请求伪装: 每次运行随机 UA+视口(会话内统一); Sec-CH-UA 等头部与 UA 身份一致;
    下载层优先 curl_cffi(chrome TLS指纹, 可选依赖, 自检失败自动回落requests);
    浏览器注入 stealth(去 webdriver/补插件语言平台); 拟人点击 human_click
    (分段移动+落点抖动+思考停顿), 限速带随机抖动
  - 路由中转: --proxy 后浏览器/requests/robots/三引擎全走代理; trust_env=False
    防环境变量旁路; 不设时代理自动读 Windows 系统代理(与人工浏览器同路)
  - 浏览器三通道: bundled chromium / 本机 chrome·edge / camoufox(C++层指纹,
    block_webrtc+humanize+geoip); 真profile克隆只读源、隔离副本
"""

import argparse
import csv
import hashlib
import ipaddress
import json
import os
import random
import re
import shutil
import socket
import sys
import time
from collections import defaultdict
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib import robotparser

import requests

__version__ = "1.2.0"

# ---------------------------------------------------------------- 身份池
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
    "Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
]
VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
]

VERIFY_SELECTORS = [
    ".sliderCaptcha_thumb", ".slider-captcha", ".slidercaptcha",
    ".geetest_holder", ".geetest_widget", ".nc-container", ".nc_scale",
    "#captcha-box", "#captchaBox", ".captcha-box",
    "iframe[src*='captcha']", "iframe[src*='recaptcha']",
    ".cf-challenge", ".cf-turnstile",
]
SKIP_LINK_PAT = re.compile(
    r"login|logout|register|signup|signin|sign-in|sign-up|pay|order|checkout"
    r"|submit|upload|delete|admin|user|member|password|登.?录|注.?册|支.?付"
    r"|订.?单|投.?稿|管.?理|退.?出|会.?员|充.?值",
    re.I,
)

IMG_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VID_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}
STREAM_SUFFIXES = {".m3u8"}
MEDIA_SUFFIXES = IMG_SUFFIXES | VID_SUFFIXES | STREAM_SUFFIXES

AD_KEYWORDS = ["advert", "preroll", "doubleclick", "googlesyndication",
               "popads", "adserver", "tracking"]

NAV_HINTS = [
    ("ERR_CERT_AUTHORITY_INVALID",
     "证书链不可信(公司网/抓包代理常见). 可信环境加 --insecure, 否则给系统装代理CA."),
    ("ERR_CERT_", "证书问题. 可信内网/MITM 时可用 --insecure, 公网请勿忽略."),
    ("ERR_PROXY_CONNECTION_FAILED",
     "连不上代理. 检查代理进程是否启动、端口是否正确, 先跑 envcheck."),
    ("ERR_TUNNEL_CONNECTION_FAILED",
     "代理隧道失败. 代理不支持 CONNECT 或目标被代理拦截, 换代理或直连."),
    ("ERR_NETWORK_ACCESS_DENIED",
     "本机网络被拦截. 程序走系统代理试试 --proxy, 或与人工浏览器同通道 --browser chrome."),
    ("ERR_CONNECTION_REFUSED", "目标拒连(端口关/被墙). 检查URL与网络出口."),
    ("TIMED_OUT", "连接超时. 网络慢或目标限流, 降 batch 或换网络."),
    ("ERR_NAME_NOT_RESOLVED", "DNS 解析失败. 检查域名拼写与 DNS."),
    ("ERR_INTERNET_DISCONNECTED", "本机断网."),
    ("407", "代理要求认证. --proxy 填 user:pass@host:port 格式."),
    ("ERR_SSL_", "TLS 握手失败. 目标协议过旧或被中间设备干扰."),
]

STEALTH_JS = """() => {
  try {
    Object.defineProperty(navigator, 'webdriver', {get: () => false});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
    if (!navigator.userAgentData) {
      Object.defineProperty(navigator, 'userAgentData', {get: () => ({
        brands: [{brand: 'Chromium', version: '131'},
                 {brand: 'Google Chrome', version: '131'}],
        mobile: false, platform: 'Windows'})});
    }
    const s = {width: window.innerWidth, height: window.innerHeight,
               availWidth: window.innerWidth, availHeight: window.innerHeight};
    for (const k of Object.keys(s)) {
      try { Object.defineProperty(window.screen, k, {get: () => s[k]}); } catch (e) {}
    }
    try {
      const origQ = window.navigator.permissions.query.bind(window.navigator.permissions);
      window.navigator.permissions.query = (p) => (p && p.name === 'notifications')
        ? Promise.resolve({state: 'denied'}) : origQ(p);
    } catch (e) {}
    try {
      const getP = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function (p) {
        if (p === 37445) return 'Google Inc. (ANGLE)';
        if (p === 37446) return 'ANGLE (Google, Vulkan 1.3.0)';
        return getP.call(this, p);
      };
    } catch (e) {}
  } catch (e) {}
}"""

JS_HARVEST = """() => ({
  img: Array.from(document.images).map(e => e.currentSrc || e.src || ''),
  vid: Array.from(document.querySelectorAll('video')).map(e => e.currentSrc || e.src || ''),
  src: Array.from(document.querySelectorAll('source')).map(e => e.src || ''),
  a: Array.from(document.querySelectorAll('a[href]')).map(e => e.href || '')
})"""
JS_COUNT = "() => document.querySelectorAll('img,video,source,a[href]').length"

_TLS_WARNED = False

# ================================================================ URL/网络安全
def norm_url(url: str) -> str:
    """规范化: 反斜杠转正(防 https:\\\\evil 绕过), userinfo 强制剥离, 主机小写."""
    url = (url or "").strip().replace("\\", "/")
    try:
        p = urlsplit(url)
    except Exception:
        return ""
    host = (p.hostname or "").lower()
    if not host:
        return ""
    try:
        port = p.port
    except ValueError:
        return ""  # 非法端口(:99999): 拒绝而非抛错, 防远端页面一句即崩整轮
    if port == 0:
        return ""
    netloc = host + ((":%d" % port) if port else "")
    return urlunsplit((p.scheme.lower(), netloc, p.path or "/", "", ""))


def _safe_host(host: str) -> str:
    """主机名文件系统安全: 只允许 alnum/点/连字符/冒号(IPv6), 拒绝..穿越与畸形."""
    h = (host or "").strip().lower()
    if not h or h in (".", ".."):
        return ""
    if re.search(r"[^a-z0-9.\-:]", h):
        return ""
    if h.startswith((".", "-", ":")) or h.endswith((".", "-", ":")):
        return ""
    if any(seg in ("", ".", "..") for seg in h.split(".")):
        return ""
    return h


def _cfg_str(v) -> str:
    """配置字符串取值: 非 str 一律回 '', 防 config.json 手写类型混乱崩溃."""
    return v.strip() if isinstance(v, str) else ""


def _cfg_list(v):
    """配置列表取值: str 按 |,;换行拆; list/tuple 逐项转 str; 其他回 []."""
    if isinstance(v, str):
        return [x for x in re.split(r"[|,;\n]+", v) if x.strip()]
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return []


def url_for_log(url: str) -> str:
    """日志脱敏: 只到 path, query/fragment 永不落盘."""
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower()
        return "%s://%s%s" % (p.scheme.lower(), host, p.path or "/")
    except Exception:
        return "(bad-url)"


def _resolve_ips(host: str):
    try:
        return sorted({r[4][0] for r in socket.getaddrinfo(host, None)})
    except Exception:
        return []


def is_public_host(host: str) -> bool:
    """SSRF: 全部解析结果必须为公网单播. 私网/回环/链路本地/组播/保留/未指定全拦."""
    host = (host or "").strip().lower().rstrip(".")
    if not host:
        return False
    if host in ("localhost",):
        return False
    ips = _resolve_ips(host)
    if not ips:
        return False
    for ip in ips:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            return False
        cands = [a]
        try:  # IPv4-mapped/6to4/teredo: 拆出内嵌 IPv4 双检, 防 ::ffff:127.0.0.1 类穿透
            m = getattr(a, "ipv4_mapped", None)
            if m is not None:
                cands.append(m)
            s64 = getattr(a, "sixtofour", None)
            if s64 is not None:
                cands.append(s64)
            ter = getattr(a, "teredo", None)
            if ter is not None:
                cands.append(ter[0])
        except Exception:
            pass
        for c in cands:
            try:
                bad = (c.is_private or c.is_loopback or c.is_link_local
                       or c.is_multicast or c.is_reserved or c.is_unspecified)
            except ValueError:
                bad = True
            if bad:
                return False
    return True


def check_proxy(s: str) -> str:
    """代理校验: 拒收空白/控制字符(防日志注入), 必须 scheme://[auth@]host:port.

    保留 userinfo(认证代理 407 链路需要) 与 IPv6 方括号, 显示层由 mask_proxy 脱敏.
    """
    s = (s or "").strip()
    if not s:
        return ""
    if re.search(r"\s|[\x00-\x1f\x7f]", s):
        return ""
    try:
        p = urlsplit(s if "://" in s else "http://" + s)
    except Exception:
        return ""
    if (p.scheme or "").lower() not in ("http", "https", "socks5", "socks5h"):
        return ""
    host = p.hostname or ""
    try:
        port = p.port
    except ValueError:
        return ""
    if not host or not port:
        return ""
    auth = ""
    if p.username:
        auth = p.username + ((":" + (p.password or "")) if p.password else "") + "@"
    if ":" in host and not host.startswith("["):
        host = "[%s]" % host
    return "%s://%s%s:%d" % (p.scheme.lower(), auth, host.lower(), port)


def mask_proxy(p: str) -> str:
    """代理脱敏(单行): 只露首尾, 凭证永不打印."""
    if not p:
        return ""
    try:
        u = urlsplit(p)
        h = u.hostname or ""
        shown = (h[0] + "***" + h[-1]) if len(h) > 2 else "***"
        return "%s://%s:%s" % (u.scheme, shown, u.port or "")
    except Exception:
        return "***"


def polite_sleep(site, base=None) -> None:
    """限速 + 随机抖动."""
    try:
        t = float(base if base is not None else site.cfg.get("delay", 1.2))
    except Exception:
        t = 1.2
    time.sleep(max(0.2, t) + random.random() * 0.8)


def think(page, ms: int = 600) -> None:
    try:
        page.wait_for_timeout(max(100, int(ms)))
    except Exception:
        pass


# ================================================================ 诊断/代理
def diagnose_nav_error(err: str) -> str:
    """导航错误 -> 处置建议. 兜底指向 envcheck."""
    e = str(err or "")
    for sub, hint in NAV_HINTS:
        if sub in e:
            return hint
    return "未知导航错误. 先跑 envcheck 看环境, 再看完整报错."


def proxy_alive(proxy: str, timeout: float = 5) -> bool:
    """代理存活预检: 只 TCP 连代理自身, 不碰目标站."""
    p = check_proxy(proxy)
    if not p:
        return False
    try:
        u = urlsplit(p)
        with socket.create_connection((u.hostname, u.port), timeout=timeout):
            return True
    except Exception:
        return False


def detect_system_proxy() -> str:
    """读 Windows 系统代理(WinINET), 非 Windows 读环境变量. 返回校验后的串或''."""
    sp = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as k:
            try:
                enabled, _ = winreg.QueryValueEx(k, "ProxyEnable")
            except OSError:
                enabled = 0
            if enabled:
                try:
                    raw, _ = winreg.QueryValueEx(k, "ProxyServer")
                except OSError:
                    raw = ""
                parts = re.split(r"[;]", raw or "")
                for part in parts:
                    cand = part.split("=", 1)[-1].strip()
                    if check_proxy(cand):
                        sp = check_proxy(cand)
                        break
    except Exception:
        pass
    if not sp:
        for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
            if check_proxy(os.environ.get(key, "")):
                sp = check_proxy(os.environ[key])
                break
    return sp


def preflight(site) -> int:
    """开工预检: 代理已死直接拦下(返回2), 不带病空跑."""
    p, origin = eff_proxy(site)
    if p and not proxy_alive(p):
        site.log("PROXY-DEAD 代理不可用(%s %s), 停止. 检查代理进程与端口."
                 % (origin, mask_proxy(p)))
        return 2
    if p:
        site.log("代理: %s(%s)" % (origin, mask_proxy(p)))
    return 0


# ================================================================ 站点对象
class Site:
    def __init__(self, url: str, args):
        self.args = args
        self.url = url
        p = urlsplit(url)
        self.host = _safe_host(p.hostname or "")
        if not self.host:
            raise ValueError("bad host: %r" % (p.hostname or ""))
        self.root = os.path.join("sites", self.host)
        self.dl = os.path.join(self.root, "downloads")
        self.prof = os.path.join(self.root, "profile")
        self.ckf = os.path.join(self.root, "cookies.txt")
        self.logf = os.path.join(self.root, "crawl.log")
        self.invf = os.path.join(self.root, "inventory.csv")
        self.colf = os.path.join(self.root, "columns.txt")
        for d in (self.root, self.dl, self.prof):
            os.makedirs(d, exist_ok=True)
        self.cfg = {}
        try:
            cf = os.path.join(self.root, "config.json")
            if os.path.isfile(cf):
                with open(cf, encoding="utf-8") as f:
                    self.cfg = json.load(f) or {}
        except Exception:
            self.cfg = {}
        if not isinstance(self.cfg, dict):
            self.cfg = {}
        self.proxy = getattr(args, "proxy", "") or ""
        self.counters = defaultdict(int)
        self.fails = []
        self._proxy_idx = 0
        self._cloned_done = False
        self._camoufox_cm = None
        self._robots = None
        self.pick_identity()

    # -- 身份 --
    def pick_identity(self) -> None:
        self.UA = random.choice(UA_POOL)
        self.viewport = dict(random.choice(VIEWPORTS))

    def tls_verify(self) -> bool:
        if getattr(self.args, "insecure", False):
            return False
        return not bool(self.cfg.get("insecure", False))

    # -- 代理 --
    def _proxy_list(self):
        raw = _cfg_list(self.cfg.get("proxies"))
        return [c for c in (check_proxy(x) for x in raw) if c]

    def rotate_proxy(self) -> str:
        """代理轮换: proxies>=2 条时按序取用完回卷; 否则返回''."""
        lst = self._proxy_list()
        if len(lst) < 2:
            return ""
        p = lst[self._proxy_idx % len(lst)]
        self._proxy_idx += 1
        return p

    def want_clone(self) -> bool:
        """是否启用真实浏览器 profile 克隆: 有 --clone-profile 路径即开."""
        return bool(_cfg_str(getattr(self.args, "clone_profile", ""))
                    or _cfg_str(self.cfg.get("clone_profile")))

    # -- 过滤 --
    def _video_first(self) -> bool:
        v = getattr(self.args, "video_first", None)
        if v is not None:
            return bool(v)
        return bool(self.cfg.get("video_first", True))

    def column_ok(self, url: str) -> bool:
        sub = _cfg_str(getattr(self.args, "column", "")) or \
            _cfg_str(self.cfg.get("column", ""))
        if not sub:
            return True
        return sub in url

    def media_ok(self, url: str) -> bool:
        """主机白名单: 本站恒收; 站外仅 allow_cdn 时收. scheme 默认只 https."""
        try:
            p = urlsplit(url)
        except Exception:
            return False
        if (p.scheme or "").lower() == "http":
            if not (getattr(self.args, "allow_http", False) or self.cfg.get("allow_http")):
                return False
        elif (p.scheme or "").lower() != "https":
            return False
        host = (p.hostname or "").lower()
        if not host:
            return False
        if host == self.host or host.endswith("." + self.host):
            return True
        allow_cdn = getattr(self.args, "allow_cdn", False) or self.cfg.get("allow_cdn")
        return bool(allow_cdn)

    # -- robots --
    def ensure_robots(self, sess) -> None:
        if self._robots is not None:
            return
        rp = robotparser.RobotFileParser()
        try:
            r = sess.get("https://%s/robots.txt" % self.host, timeout=10)
            if r.status_code == 200 and "disallow" in r.text.lower():
                rp.parse(r.text.splitlines())
            else:
                rp.parse(["User-agent: *", "Disallow:"])
        except Exception:
            self.log("robots获取失败(放行)")
            rp.parse(["User-agent: *", "Disallow:"])
        self._robots = rp
        try:  # Crawl-delay: 对方要慢, 我们就更慢(礼貌下限)
            cd = rp.crawl_delay(self.UA)
            if cd:
                cur = float(self.cfg.get("delay", 1.2) or 1.2)
                self.cfg["delay"] = max(cur, float(cd))
        except Exception:
            pass

    def robot_denied(self, url: str) -> bool:
        try:
            return not self._robots.can_fetch(self.UA, url)
        except Exception:
            return False

    # -- 记账 --
    def log(self, *a) -> None:
        line = " ".join(str(x) for x in a)
        line = line.replace("\r", "").replace("\n", "\\n")  # 注行攻击: 日志恒单行
        print(line, flush=True)
        try:
            with open(self.logf, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def bump(self, k: str, n: int = 1) -> None:
        self.counters[k] += n

    def note_fail(self, url: str, why: str) -> None:
        if len(self.fails) < 3:
            self.fails.append("%s | %s" % (url_for_log(url), str(why)[:120]))
        self.bump("fetch_fail")

    def summary(self) -> None:
        parts = ["%s=%s" % (k, v) for k, v in sorted(self.counters.items())]
        self.log("SUMMARY " + (" ".join(parts) if parts else "(空)"))
        for f in self.fails:
            self.log("  fail样本: " + f)


def eff_proxy(site):
    """代理生效顺序: 站点proxies轮换(>=2条) > 站点单条 > 命令行手动 > 站点proxy > 系统代理."""
    lst = site._proxy_list()
    if len(lst) >= 2:
        return site.rotate_proxy(), "rotated"
    if len(lst) == 1:
        return lst[0], "site"
    m = check_proxy(site.proxy)
    if m:
        return m, "manual"
    c = check_proxy(site.cfg.get("proxy", ""))
    if c:
        return c, "site"
    s = detect_system_proxy()
    if s:
        return s, "system"
    return "", ""


# ================================================================ 请求层
def _sec_ch_ua(ua: str) -> str:
    m = re.search(r"Chrome/(\d+)", ua or "")
    v = m.group(1) if m else "131"
    return '"Chromium";v="%s", "Google Chrome";v="%s", "Not-A.Brand";v="99"' % (v, v)


_IMPERSONATE_OK = ("chrome136", "chrome131", "chrome124", "chrome120",
                    "chrome116", "chrome")


def _pick_impersonate(ua: str) -> str:
    """指纹与 UA 同代绑定: 取 UA 的 Chrome 大版本, 就近选 curl_cffi 支持的 preset.

    老指纹配新 UA 是教科书级脚本信号; preset 不存在则抛错由上层回落 requests.
    """
    m = re.search(r"Chrome/(\d+)", ua or "")
    major = int(m.group(1)) if m else 0
    for name in _IMPERSONATE_OK:
        if name == "chrome":
            return "chrome"
        if major >= int(name[6:]):
            return name
    return "chrome"


def make_session(site):
    """下载会话: curl_cffi(chrome指纹)优先, 自检失败回落requests(每进程只警告一次)."""
    global _TLS_WARNED
    headers = {
        "User-Agent": site.UA,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,*/*;q=0.8",
        "Sec-CH-UA": _sec_ch_ua(site.UA),
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    p, _ = eff_proxy(site)
    proxies = {"http": p, "https": p} if p else {}
    kind = "requests"
    try:
        from curl_cffi import requests as cr
        imp = _pick_impersonate(site.UA)
        s = cr.Session(impersonate=imp)
        kind = "curl_cffi:" + imp
    except Exception as e:
        if not _TLS_WARNED:
            site.log("WARNING TLS伪装不可用(回落requests): %s" % str(e)[:100])
            _TLS_WARNED = True
        s = requests.Session()
    try:
        s.headers.update(headers)
    except Exception:
        pass
    try:
        s.proxies.update(proxies)
        s.verify = site.tls_verify()
        s.trust_env = False
        s.timeout = 30
    except Exception:
        pass
    return s, kind


# ================================================================ 浏览器层
def clone_profile_dir(site) -> str:
    """真profile克隆(Torch思路): 只读源, 只复制身份文件到站点隔离副本."""
    src = _cfg_str(getattr(site.args, "clone_profile", "")) or \
        _cfg_str(site.cfg.get("clone_profile"))
    if not src or not os.path.isdir(src):
        return site.prof
    dst = os.path.join(site.root, "profile_cloned")
    if site._cloned_done and os.path.isdir(dst):
        return dst
    top_files = ["Local State", "Preferences"]
    sub_files = [os.path.join("Default", x) for x in
                 ("Network", "Local Storage", "Session Storage", "IndexedDB",
                  "Preferences", "Secure Preferences")]
    n = 0
    for rel in top_files + sub_files:
        s, d = os.path.join(src, rel), os.path.join(dst, rel)
        if not os.path.exists(s):
            continue
        try:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
                n += sum(len(fs) for _, _, fs in os.walk(d))
            else:
                shutil.copy2(s, d)
                n += 1
        except Exception:
            pass
    site._cloned_done = True
    site.log("clone-profile: 已克隆%d项身份文件 -> profile_cloned(只读源)" % n)
    return dst


def _open_ctx_camoufox(site, headless: bool, proxy: str):
    """Camoufox后端: C++层指纹 + WebRTC硬关 + 拟人 + 地理对齐."""
    from camoufox.sync_api import Camoufox
    prof = clone_profile_dir(site) if site.want_clone() else site.prof
    kw = dict(persistent_context=True, user_data_dir=prof, headless=headless,
              os="windows", locale="zh-CN", block_webrtc=True, humanize=True,
              geoip=bool(proxy))
    if proxy:
        kw["proxy"] = {"server": proxy}
    cm = Camoufox(**kw)
    ctx = cm.__enter__()
    ctx._camoufox_cm = cm
    site._camoufox_cm = cm
    return None, None, ctx, ctx.new_page()


def open_ctx(site, headless: bool = True, proxy: str = ""):
    """打开浏览器上下文. 返回 (pw, browser, ctx, page); camoufox 通道 pw/browser 为 None."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    ch = (getattr(site.args, "browser", "") or site.cfg.get("browser", "") or "").lower()
    if ch == "camoufox":
        return _open_ctx_camoufox(site, headless, proxy)
    launch_kw = {"headless": headless,
                 "args": ["--disable-blink-features=AutomationControlled"]}
    if proxy:
        launch_kw["proxy"] = {"server": proxy}
    if ch in ("chrome", "edge"):
        launch_kw["channel"] = ch
    insecure = not site.tls_verify()
    if site.want_clone():
        prof = clone_profile_dir(site)
        ctx = pw.chromium.launch_persistent_context(
            prof, headless=headless, channel=launch_kw.get("channel"),
            user_agent=site.UA, viewport=site.viewport, locale="zh-CN",
            timezone_id="Asia/Shanghai", ignore_https_errors=insecure,
            proxy=launch_kw.get("proxy"))
        ctx.add_init_script(STEALTH_JS)
        return pw, None, ctx, ctx.new_page()
    browser = pw.chromium.launch(**launch_kw)
    ctx = browser.new_context(
        user_agent=site.UA, viewport=site.viewport, locale="zh-CN",
        timezone_id="Asia/Shanghai", ignore_https_errors=insecure)
    ctx.add_init_script(STEALTH_JS)
    return pw, browser, ctx, ctx.new_page()


def close_ctx(pw, browser, ctx) -> None:
    cm = getattr(ctx, "_camoufox_cm", None) if ctx is not None else None
    try:
        if ctx is not None:
            ctx.close()
    except Exception:
        pass
    try:
        if browser is not None:
            browser.close()
    except Exception:
        pass
    try:
        if cm is not None:
            cm.__exit__(None, None, None)
    except Exception:
        pass
    try:
        if pw is not None:
            pw.stop()
    except Exception:
        pass


def human_click(page, locator, timeout: int = 8000) -> bool:
    """拟人点击: 等可见 -> 分段移动 -> 落点抖动 -> 思考停顿 -> 点."""
    try:
        locator.wait_for(state="visible", timeout=timeout)
        try:
            box = locator.bounding_box()
        except Exception:
            box = None
        if box:
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            try:
                page.mouse.move(x + random.uniform(-30, 30), y + random.uniform(-20, 20),
                                steps=7)
                page.mouse.move(x + random.uniform(-3, 3), y + random.uniform(-3, 3),
                                steps=3)
            except Exception:
                pass
            think(page, random.uniform(300, 900))
        locator.click(timeout=timeout)
        return True
    except Exception:
        return False


def settle_lazy_load(page, site, max_rounds: int = 3) -> int:
    """懒加载沉降: 滚到底触发挂载再回顶. 只滚动+计数, 不点任何东西."""
    try:
        before = page.evaluate(JS_COUNT) or 0
    except Exception:
        return 0
    try:
        rounds = int(site.cfg.get("lazy_rounds", max_rounds) or max_rounds)
    except Exception:
        rounds = max_rounds
    for _ in range(max(1, min(rounds, 8))):
        try:
            page.mouse.wheel(0, 1600)
            page.wait_for_timeout(600)
        except Exception:
            break
    try:
        page.evaluate("() => window.scrollTo(0, 0)")
    except Exception:
        pass
    try:
        after = page.evaluate(JS_COUNT) or 0
    except Exception:
        after = before
    return max(0, after - before)


# ================================================================ 页面分析
def detect_verify(page, site=None):
    """验证检测: 命中选择器即需人工. 返回 (needed, selector)."""
    sels = list(VERIFY_SELECTORS)
    try:
        if site is not None:
            sels += _cfg_list(site.cfg.get("extra_verify_selectors"))
    except Exception:
        pass
    for sel in sels:
        try:
            if page.query_selector(sel):
                return True, sel
        except Exception:
            pass
    return False, ""


def norm_link(site, base: str, href: str) -> str:
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return ""
    try:
        u = urljoin(base, href.strip())
    except Exception:
        return ""
    u = norm_url(u.split("#")[0])
    if not u:
        return ""
    if SKIP_LINK_PAT.search(u):
        return ""
    try:
        if urlsplit(u).hostname != site.host:
            return ""
    except Exception:
        return ""
    return u


def norm_media(site, base: str, src: str) -> str:
    """媒体URL归一化: 不做站外限制(由 media_ok 判定), 但必须合法后缀或流."""
    if not src or src.startswith(("data:", "blob:", "javascript:")):
        return ""
    try:
        u = urljoin(base, src.strip())
    except Exception:
        return ""
    u = norm_url(u.split("#")[0])
    if not u or not is_media_url(u):
        return ""
    return u


def _clean_nav_text(t: str) -> str:
    """导航文本清洗: 去换行/制表/分隔符后截断, 防 columns.txt 与日志注行."""
    return re.sub(r"[\r\n\t|]", " ", str(t or "")).strip()[:24]


def discover_nav(page, site):
    """栏目发现: 导航区链接, 跳过登录/付费/管理类. 返回 [(text, url)]."""
    out, seen = [], set()
    try:
        links = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'header a[href], nav a[href], .nav a[href], .menu a[href]'))"
            ".map(e => [e.innerText.trim().slice(0,24), e.href])")
    except Exception:
        return []
    for text, href in links or []:
        u = norm_link(site, page.url, href or "")
        if not u or u in seen or not site.column_ok(u):
            continue
        seen.add(u)
        out.append((_clean_nav_text(text) or "(无标题)", u))
    return out


def find_next(page, url: str) -> str:
    """分页器试探: rel=next 或 下一页文字."""
    try:
        el = page.query_selector("a[rel='next']")
        if el:
            u = norm_link_from(page, url, el.get_attribute("href") or "")
            if u:
                return u
        cands = page.query_selector_all("a")
        for el in cands[-30:]:
            try:
                t = (el.inner_text() or "").strip()
            except Exception:
                continue
            if t in ("下一页", "下一頁", "Next", "next", ">", "›", "»", "下页"):
                u = norm_link_from(page, url, el.get_attribute("href") or "")
                if u:
                    return u
    except Exception:
        pass
    return ""


def norm_link_from(page, base: str, href: str) -> str:
    try:
        site = page._site_ref  # 仅测试注入用
        return norm_link(site, base, href)
    except Exception:
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            return ""
        try:
            return norm_url(urljoin(base, href.strip()).split("#")[0])
        except Exception:
            return ""


# ================================================================ 文件类型
def sniff_ext(head: bytes):
    """文件头嗅探真实类型. 魔数是地面真相, URL/Content-Type 声称什么都不算数."""
    if not head:
        return None
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12] == b"WEBP":
        return ".webp"
    if head.startswith(b"BM") and len(head) >= 14:
        return ".bmp"
    if len(head) >= 12 and head[4:8] == b"ftyp" and \
            re.match(rb"^[A-Za-z0-9]{4}$", head[8:12]):
        return ".mp4"
    if head.startswith(b"\x1aE\xdf\xa3"):
        return ".webm"
    h = head
    if h.startswith(b"\xef\xbb\xbf"):
        h = h[3:]  # 仅容忍 UTF-8 BOM, 前导空格即拒(防 polyglot 冒充)
    if h.startswith(b"#EXTM3U") and b"\n" in h:
        return ".m3u8"
    return None


def check_magic(path: str):
    try:
        with open(path, "rb") as f:
            return sniff_ext(f.read(64))
    except Exception:
        return None


def media_rank(url: str, ctype: str = "") -> int:
    """视频优先排序: m3u8 < mp4系 < 图片."""
    u = (url or "").lower()
    c = (ctype or "").lower()
    if u.endswith(".m3u8") or "mpegurl" in c:
        return 0
    if u.endswith(tuple(VID_SUFFIXES)) or c.startswith("video/"):
        return 1
    return 2


def is_media_url(url: str) -> bool:
    try:
        path = urlsplit(url).path.lower()
    except Exception:
        return False
    return any(path.endswith(s) for s in MEDIA_SUFFIXES)


# ================================================================ 下载引擎
def hash_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def find_exe(names):
    """外部引擎查找: tools/ -> PATH. 禁自动下载/更新."""
    if isinstance(names, str):
        names = [names]
    for n in names:
        p = os.path.join("tools", n)
        if os.path.isfile(p):
            return p
    for n in names:
        w = shutil.which(n)
        if w:
            return w
    return ""


def _csv_safe(v) -> str:
    """CSV注入防护全集: 去前导空白/BOM/方向符后, 公式符=+-@| 与全角变体一律加'前缀."""
    s = str(v)
    t = s.lstrip(" \t\r\n\uFEFF\u200b\u200c\u200e\u200f")
    if t[:1] in ("=", "+", "-", "@", "|", "\t", "\r", "\n"):
        return "'" + s
    if t[:1] in ("＝", "＋", "－", "＠"):
        return "'" + s
    return s


def record(site, url: str, path: str, source: str = "list") -> None:
    size = os.path.getsize(path) if os.path.isfile(path) else 0
    new = not os.path.isfile(site.invf)
    try:
        with open(site.invf, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["url", "file", "bytes", "sha256", "source"])
            w.writerow([_csv_safe(url_for_log(url)), _csv_safe(os.path.basename(path)),
                        size, hash_file(path), _csv_safe(source)])
    except Exception:
        pass
    site.bump("downloaded")


def _next_idx(site) -> int:
    n = 0
    try:
        with open(site.invf, encoding="utf-8-sig") as f:
            n = max(0, sum(1 for _ in f) - 1)
    except Exception:
        pass
    try:
        files = [x for x in os.listdir(site.dl)
                 if os.path.isfile(os.path.join(site.dl, x))]
        n = max(n, len(files))
    except Exception:
        pass
    return n + 1


def _peer_is_public(resp) -> bool:
    """连接后对端复检: 取底层 socket 对端 IP, 闭合 DNS TOCTOU 重绑定窗口.

    无法判定(代理/未知传输)时返回 True, 交由主机名守卫承担.
    """
    try:
        sock = getattr(getattr(resp, "raw", None), "_connection", None)
        sock = getattr(sock, "sock", None)
        if sock is None:
            return True
        peer = sock.getpeername()[0]
        a = ipaddress.ip_address(peer)
        return not (a.is_private or a.is_loopback or a.is_link_local
                    or a.is_multicast or a.is_reserved or a.is_unspecified)
    except Exception:
        return True


def _proxied(sess) -> bool:
    try:
        pr = getattr(sess, "proxies", {}) or {}
        return bool(pr.get("https") or pr.get("http"))
    except Exception:
        return True


def _fetch_guarded(sess, url: str, referer: str, accept: str, max_hops: int = 5):
    """守卫式 GET: 纯手动跟跳转, 每跳主机名 SSRF 守卫, 落定后对端复检(直连时).

    返回 (resp, final_url, status). resp 为 None 表示被拦/失败, status 供重试判决.
    """
    cur = url
    status = 0
    for _ in range(max_hops + 1):
        try:
            host = urlsplit(cur).hostname or ""
        except Exception:
            return None, cur, status
        if not is_public_host(host):
            return None, cur, -1
        try:
            r = sess.get(cur, headers={"Referer": referer, "Accept": accept},
                         timeout=30, stream=True, allow_redirects=False)
        except Exception:
            return None, cur, -2
        try:
            status = int(getattr(r, "status_code", 0) or 0)
        except Exception:
            status = 0
        if status in (301, 302, 303, 307, 308):
            try:
                loc = (r.headers or {}).get("Location", "")
            except Exception:
                loc = ""
            try:
                r.close()
            except Exception:
                pass
            if not loc:
                return None, cur, status
            cur = urljoin(cur, loc)
            continue
        if status != 200:
            try:
                r.close()
            except Exception:
                pass
            return None, cur, status
        if not _proxied(sess) and not _peer_is_public(r):
            try:
                r.close()
            except Exception:
                pass
            return None, cur, -3
        try:
            final = getattr(r, "url", None) or cur
        except Exception:
            final = cur
        return r, final, status
    return None, cur, status


def _fetch_with_retry(site, sess, url: str, referer: str, accept: str):
    """429/5xx 重试: 指数退避+抖动, 优先服从 Retry-After(封顶60s), 最多3次."""
    delays = [2.0, 4.0, 8.0]
    last = (None, url, 0)
    for i in range(4):
        r, final, status = _fetch_guarded(sess, url, referer, accept)
        if r is not None:
            return r, final, status
        if status not in (429, 500, 502, 503, 504):
            return None, final, status
        if i >= 3:
            return None, final, status
        wait = delays[i] + random.random()
        site.bump("retry_%d" % status)
        time.sleep(min(wait, 60.0))
        last = (None, final, status)
    return last


def _safe_url_for_cmd(url: str) -> str:
    """subprocess 传参前最后一道: 必须 http(s):// 开头且无空白/控制符, 防 URL 即选项."""
    u = (url or "").strip()
    if not re.match(r"^https?://", u):
        return ""
    if re.search(r"\s|[\x00-\x1f\x7f]", u):
        return ""
    return u


def _playlist_guard_ok(site, sess, url: str, referer: str) -> bool:
    """m3u8 播放列表守卫: 自取文本, 绝对地址的 KEY/分片逐条过 SSRF 守卫再交引擎.

    相对分片继承播放列表主机(已守卫). 引擎只负责下载, 不替我们做安全决策.
    """
    r, _, status = _fetch_guarded(sess, url, referer, "*/*")
    if r is None:
        return False
    try:
        text = r.text or ""
    except Exception:
        text = ""
    try:
        r.close()
    except Exception:
        pass
    if "#EXTM3U" not in text[:256].replace("\xef\xbb\xbf", ""):
        return False
    bad = 0
    for m in re.findall(r'URI="([^"]+)"', text):
        u = urljoin(url, m.strip())
        if re.match(r"^https?://", u):
            try:
                h = urlsplit(u).hostname or ""
            except Exception:
                h = ""
            if not h or not is_public_host(h):
                bad += 1
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^https?://", line):
            try:
                h = urlsplit(line).hostname or ""
            except Exception:
                h = ""
            if not h or not is_public_host(h):
                bad += 1
                if bad > 5:
                    break
    if bad:
        site.bump("skip_playlist_guard")
        return False
    return True


def _attach_capture(page, site, bucket, cap: int = 500) -> None:
    """网络层响应捕获: 导航期间路过的 .m3u8/视频直链全部收下(只收不下).

    补 DOM 抓取盲区(播放器 JS 动态拉流). handler 只做 append, 异常自吞.
    """
    try:
        def _on_resp(resp):
            try:
                if len(bucket) >= cap:
                    return
                u = getattr(resp, "url", "") or ""
                low = u.lower()
                if low.endswith((".m3u8", ".mp4", ".webm", ".mov", ".mkv")):
                    nu = norm_media(site, u, u)
                    if nu and site.media_ok(nu) and nu not in bucket:
                        bucket.append(nu)
            except Exception:
                pass
        page.on("response", _on_resp)
    except Exception:
        pass


def fetch_one(site, sess, url: str, idx: int, referer: str, source: str = "list"):
    """直链下载: SSRF -> GET -> Content-Type/魔数双检 -> 落盘定型."""
    if not site.media_ok(url):
        site.bump("skip_host")
        return ""
    try:
        host = urlsplit(url).hostname or ""
    except Exception:
        return ""
    if not is_public_host(host):
        site.bump("skip_ssrf")
        return ""
    low = url.lower()
    if site._video_first() and low.endswith(tuple(IMG_SUFFIXES)):
        site.bump("skip_img_vfirst")
        return ""
    if site.robot_denied(url):
        site.bump("skip_robots")
        return ""
    try:
        acc = ("video/*" if low.endswith(tuple(VID_SUFFIXES | STREAM_SUFFIXES))
               else "image/*,*/*;q=0.8")
        r, final, status = _fetch_with_retry(site, sess, url, referer, acc)
        if r is None:
            if status in (-1, -3):
                site.bump("skip_ssrf")
            elif status > 0:
                site.note_fail(url, "http-%s" % status)
            else:
                site.note_fail(url, "conn-fail")
            return ""
        if not site.media_ok(final):  # 跳转终点复检: 落定主机仍须在白名单
            try:
                r.close()
            except Exception:
                pass
            site.bump("skip_host")
            return ""
        buf = b""
        for chunk in r.iter_content(1 << 16):
            buf += chunk
            if len(buf) > 200 * (1 << 20):
                break
        try:
            r.close()
        except Exception:
            pass
        if len(buf) < 512:
            site.bump("skip_tiny")
            return ""
        ext = sniff_ext(buf[:64])
        if not ext or ext == ".m3u8":
            site.note_fail(url, "nomagic")
            site.bump("skip_nomagic")
            return ""
        stem = re.sub(r"[^\w\-]+", "_", urlsplit(url).path.rsplit("/", 1)[-1]
                      .rsplit(".", 1)[0])[:80].strip("_") or "f"
        final = os.path.join(site.dl, "%05d_%s%s" % (idx, stem, ext))
        tmp = final + ".part"
        with open(tmp, "wb") as f:
            f.write(buf)
        os.replace(tmp, final)
        record(site, url, final, source)
        return final
    except Exception as e:
        site.note_fail(url, str(e)[:80])
        return ""


def _write_netscape(site, path: str) -> bool:
    """cookies.txt(name=value;...) -> netscape 格式(供 yt-dlp). 用完即删."""
    try:
        with open(site.ckf, encoding="utf-8") as f:
            raw = f.read().strip()
    except Exception:
        return False
    if not raw:
        return False
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for kv in raw.split(";"):
                kv = kv.strip()
                if "=" not in kv:
                    continue
                k, v = kv.split("=", 1)
                k = re.sub(r"[\r\n\t]", "", k).strip()  # 换行注入防御
                v = re.sub(r"[\r\n\t]", "", v).strip()
                if not k or k.startswith("#") or ";" in k or ";" in v:
                    continue
                f.write("%s\tTRUE\t/\tTRUE\t0\t%s\t%s\n"
                        % (site.host, k, v))
        try:
            os.chmod(path, 0o600)  # posix 下仅属主可读; Windows 下尽力
        except Exception:
            pass
        return True
    except Exception:
        return False


def fetch_m3u8(site, url: str, idx: int, referer: str, sess=None):
    """m3u8 三引擎链: N_m3u8DL-RE -> yt-dlp -> ffmpeg. 广告分片按关键字过滤."""
    import subprocess
    url = _safe_url_for_cmd(url)  # URL即选项防御: 非 http(s):// 直接拒
    if not url or not site.media_ok(url):
        site.bump("skip_host")
        return ""
    try:
        host = urlsplit(url).hostname or ""
    except Exception:
        return ""
    if not is_public_host(host):
        site.bump("skip_ssrf")
        return ""
    final = os.path.join(site.dl, "%05d.mp4" % idx)
    if os.path.isfile(final):
        return final
    if sess is None:
        sess, _ = make_session(site)
    if not _playlist_guard_ok(site, sess, url, referer):
        site.note_fail(url, "playlist-guard")
        return ""
    ads = list(AD_KEYWORDS) + _cfg_list(site.cfg.get("ad_keywords"))
    p, _ = eff_proxy(site)
    insecure = not site.tls_verify()
    ck = os.path.join(site.root, ".cookies_%d.netscape" % idx)
    have_ck = _write_netscape(site, ck)
    try:
        exe = find_exe(["N_m3u8DL-RE.exe", "N_m3u8DL-RE"])
        if exe:
            cmd = [exe, url, "--save-dir", site.dl, "--save-name", "%05d" % idx,
                   "--auto-select"]
            for a in ads:
                cmd += ["--ad-keyword", a]
            if p:
                cmd += ["--proxy", p]
            if insecure:
                cmd += ["--no-check-certificate"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode == 0 and check_magic(final) == ".mp4":
                record(site, url, final, "m3u8:n_m3u8dl")
                return final
        exe = find_exe(["yt-dlp.exe", "yt-dlp"])
        if exe:
            cmd = [exe, "--no-playlist", "-o", final, "--socket-timeout", "30"]
            if have_ck:
                cmd += ["--cookies", ck]
            if p:
                cmd += ["--proxy", p]
            if insecure:
                cmd += ["--no-check-certificate"]
            cmd += [url]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode == 0 and check_magic(final) == ".mp4":
                record(site, url, final, "m3u8:ytdlp")
                return final
            err = (r.stderr or "").strip().splitlines()
            site.note_fail(url, "ytdlp:" + (err[-1][:100] if err else "rc=%s" % r.returncode))
            return ""
        exe = find_exe(["ffmpeg.exe", "ffmpeg"])
        if exe:
            cmd = [exe, "-y", "-i", url, "-c", "copy", final]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode == 0 and check_magic(final) == ".mp4":
                record(site, url, final, "m3u8:ffmpeg")
                return final
        site.note_fail(url, "no-engine")
        return ""
    except subprocess.TimeoutExpired:
        site.note_fail(url, "timeout")
        return ""
    except Exception as e:
        site.note_fail(url, str(e)[:80])
        return ""
    finally:
        try:
            if os.path.isfile(ck):
                os.remove(ck)
        except Exception:
            pass


# ================================================================ 页面收获
def harvest(page, site, base: str):
    """抓取页内媒体: 图片/video/source/a, 归一化+过滤+视频优先排序."""
    try:
        data = page.evaluate(JS_HARVEST)
    except Exception:
        return [], []
    media, anchors = [], []
    for key in ("img", "vid", "src"):
        for s in (data or {}).get(key, []) or []:
            u = norm_media(site, base, s)
            if u and site.media_ok(u):
                media.append(u)
    for h in (data or {}).get("a", []) or []:
        u = norm_media(site, base, h)
        if u and site.media_ok(u):
            media.append(u)
        u2 = norm_link(site, base, h)
        if u2 and site.column_ok(u2):
            anchors.append(u2)
    media = sorted(set(media), key=lambda u: media_rank(u))
    return media, sorted(set(anchors))


def deep_dive(page, site, sess, anchors, idx: int, budget: int):
    """详情/观看页深挖: 每页至多2个, 全局预算封顶. 拿 video/source/m3u8 真流."""
    got = []
    n = 0
    for a in anchors:
        if n >= 2 or budget[0] <= 0:
            break
        if not re.search(r"detail|play|/vod/|/video/|watch|/p/", a):
            continue
        budget[0] -= 1
        n += 1
        try:
            page.goto(a, wait_until="domcontentloaded", timeout=30000)
            think(page, 800)
        except Exception:
            continue
        nv, _ = detect_verify(page, site)
        if nv:
            return got, True
        try:
            html = page.content()
        except Exception:
            html = ""
        for m in re.findall(r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*", html):
            u = norm_url(m)
            if u and site.media_ok(u):
                f = fetch_m3u8(site, u, idx[0], a)
                if f:
                    got.append(f)
                    idx[0] += 1
        try:
            data = page.evaluate(JS_HARVEST)
        except Exception:
            data = {}
        for key in ("vid", "src"):
            for s in (data or {}).get(key, []) or []:
                u = norm_media(site, base=a, src=s)
                if not u or not site.media_ok(u):
                    continue
                if u.lower().endswith(".m3u8"):
                    f = fetch_m3u8(site, u, idx[0], a)
                else:
                    f = fetch_one(site, sess, u, idx[0], a, "deep")
                if f:
                    got.append(f)
                    idx[0] += 1
        polite_sleep(site)
    return got, False


# ================================================================ 模式
def _goto(page, site, url: str):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return ""
    except Exception as e:
        hint = diagnose_nav_error(str(e))
        site.log("NAV-FAIL %s 诊断: %s" % (url_for_log(url), hint))
        return hint


def cmd_check(site) -> int:
    site.log("TARGET=%s MODE=check v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    p, _ = eff_proxy(site)
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
        if _goto(page, site, site.url):
            return 2
        nv, why = detect_verify(page, site)
        if nv:
            site.log("CHECK %s -> VERIFY-NEEDED 需人工验证 (selector:%s)"
                     % (site.url, why))
            return 10
        site.log("CHECK %s -> OPEN 无验证, 可直接dl" % site.url)
        return 0
    except Exception as e:
        site.log("CHECK-FAIL 诊断: " + diagnose_nav_error(str(e)))
        return 2
    finally:
        close_ctx(pw, browser, ctx)


def cmd_wait(site, timeout: int = 300) -> int:
    site.log("TARGET=%s MODE=wait v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    p, _ = eff_proxy(site)
    pw, browser, ctx, page = open_ctx(site, False, p)
    try:
        if _goto(page, site, site.url):
            try:
                input("页面未加载, 人工处理后回车继续(直接回车退出): ")
            except EOFError:
                return 2
        t0 = time.time()
        ok, why = False, ""
        while time.time() - t0 < timeout:
            nv, why = detect_verify(page, site)
            if not nv:
                ok = True
                break
            if int(time.time() - t0) % 60 < 5:
                site.log("等待验证中…(%ds)" % int(time.time() - t0))
            think(page, 4000)
        if not ok:
            try:
                input("自动识别超时. 若已人工验证完, 回车确认保存会话(直接Ctrl+C退出): ")
                ok = True
            except (EOFError, KeyboardInterrupt):
                return 1
        if ok:
            try:
                with open(site.ckf, "w", encoding="utf-8") as f:
                    f.write("; ".join('%s=%s' % (c["name"], c["value"])
                                      for c in ctx.cookies()))
            except Exception as e:
                site.log("会话保存失败: %s" % str(e)[:100])
                return 1
            site.log("VERIFIED (%s) 会话已保存. 可运行 dl." % (why or "人工确认"))
            return 0
        site.log("TIMEOUT 未检测到验证.")
        return 1
    finally:
        close_ctx(pw, browser, ctx)


def cmd_dl(site, batch: int = 60) -> int:
    site.log("TARGET=%s MODE=dl v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    if os.path.isfile(site.ckf):
        try:
            if os.path.getsize(site.ckf) < 8:
                site.log("会话为空, 先跑 wait.")
                return 3
        except Exception:
            pass
    sess, kind = make_session(site)
    site.log("下载层: " + kind)
    try:
        site.ensure_robots(sess)
    except Exception:
        pass
    p, _ = eff_proxy(site)
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
    except Exception as e:
        site.log("浏览器启动失败 诊断: " + diagnose_nav_error(str(e)))
        return 2
    idx = [_next_idx(site)]
    budget = [20]
    seen_page = set()
    net_cap = []  # 网络层响应捕获: 导航期间路过的流地址
    url = site.url
    stop_verify = False
    try:
        _attach_capture(page, site, net_cap)
        for _ in range(max(1, batch)):
            if not url or url in seen_page:
                break
            if site.robot_denied(url):
                site.bump("skip_robots")
                break
            seen_page.add(url)
            if _goto(page, site, url):
                break
            settle_lazy_load(page, site)
            nv, _ = detect_verify(page, site)
            if nv:
                site.log("REVERIFY 又出现验证, 停止. 请重跑 wait.")
                stop_verify = True
                break
            media, anchors = harvest(page, site, url)
            for u in net_cap:  # 网络层捕获优先(播放器 JS 动态拉流 DOM 看不见)
                if u not in media:
                    media.append(u)
            net_cap.clear()
            media = sorted(set(media), key=lambda u: media_rank(u))
            for u in media:
                if u.lower().endswith(".m3u8"):
                    f = fetch_m3u8(site, u, idx[0], url)
                else:
                    f = fetch_one(site, sess, u, idx[0], url, "list")
                if f:
                    idx[0] += 1
                polite_sleep(site, 0.4)
            if site._video_first():
                _, reverify = deep_dive(page, site, sess, anchors, idx, budget)
                if reverify:
                    site.log("REVERIFY 又出现验证, 停止. 请重跑 wait.")
                    stop_verify = True
                    break
            nxt = find_next(page, url)
            url = nxt if (nxt and nxt not in seen_page) else ""
            polite_sleep(site)
    finally:
        close_ctx(pw, browser, ctx)
    site.summary()
    return 4 if stop_verify else 0


def cmd_auto(site, batch: int = 60) -> int:
    rc = cmd_check(site)
    if rc == 10:
        rc = cmd_wait(site)
        if rc != 0:
            return rc
    elif rc != 0:
        return rc
    return cmd_dl(site, batch)


def cmd_diag(site) -> int:
    site.log("TARGET=%s MODE=diag v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    p, _ = eff_proxy(site)
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
        if _goto(page, site, site.url):
            return 2
        media, anchors = harvest(page, site, site.url)
        hosts, sufs = defaultdict(int), defaultdict(int)
        for u in media:
            try:
                hosts[urlsplit(u).hostname or "?"] += 1
                sufs[os.path.splitext(urlsplit(u).path)[1].lower() or "?"] += 1
            except Exception:
                pass
        site.log("DIAG 媒体%d 锚点%d" % (len(media), len(anchors)))
        for h, n in sorted(hosts.items(), key=lambda x: -x[1])[:10]:
            site.log("  host %s x%d" % (h, n))
        for s, n in sorted(sufs.items(), key=lambda x: -x[1])[:10]:
            site.log("  suf %s x%d" % (s, n))
        return 0
    except Exception as e:
        site.log("DIAG-FAIL 诊断: " + diagnose_nav_error(str(e)))
        return 2
    finally:
        close_ctx(pw, browser, ctx)


def cmd_nav(site) -> int:
    site.log("TARGET=%s MODE=nav v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    p, _ = eff_proxy(site)
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
        if _goto(page, site, site.url):
            return 2
        cols = discover_nav(page, site)
        lines = []
        for text, u in cols:
            has_next = ""
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=20000)
                think(page, 800)
                has_next = "有" if find_next(page, u) else "无"
            except Exception:
                has_next = "?"
            line = "%s|%s|分页:%s" % (text, u, has_next)
            lines.append(line)
            site.log("NAV 栏目: %s" % line)
        with open(site.colf, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return 0
    except Exception as e:
        site.log("NAV-FAIL 诊断: " + diagnose_nav_error(str(e)))
        return 2
    finally:
        close_ctx(pw, browser, ctx)


def cmd_purge(site) -> int:
    """清扫(纯本地不联网): 补/纠正扩展名, 隔离非媒体到 rejected/, 重写记账保留原列."""
    site.log("TARGET=%s MODE=purge(本地)" % site.url)
    rej = os.path.join(site.root, "rejected")
    os.makedirs(rej, exist_ok=True)
    old_rows, header = [], None
    try:
        with open(site.invf, encoding="utf-8-sig") as f:
            r = csv.DictReader(f)
            header = r.fieldnames
            old_rows = list(r)
    except Exception:
        pass
    by_file = {r.get("file", ""): r for r in old_rows}
    fixed, isolated = 0, 0
    try:
        names = sorted(os.listdir(site.dl))
    except Exception:
        names = []
    for name in names:
        path = os.path.join(site.dl, name)
        if not os.path.isfile(path):
            continue
        real = check_magic(path)
        if real is None:
            try:
                os.replace(path, os.path.join(rej, name))
                isolated += 1
            except Exception:
                pass
            continue
        cur = os.path.splitext(name)[1].lower()
        if cur != real:
            stem = os.path.splitext(name)[0]
            try:
                os.replace(path, os.path.join(site.dl, stem + real))
                fixed += 1
            except Exception:
                pass
    rows = []
    try:
        for name in sorted(os.listdir(site.dl)):
            path = os.path.join(site.dl, name)
            if not os.path.isfile(path):
                continue
            old = by_file.get(name, {})
            rows.append({
                "url": _csv_safe(old.get("url", "")),
                "file": _csv_safe(name),
                "bytes": os.path.getsize(path),
                "sha256": hash_file(path),
                "source": _csv_safe(old.get("source", "purge")),
            })
    except Exception:
        pass
    try:
        with open(site.invf, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header or
                               ["url", "file", "bytes", "sha256", "source"])
            w.writeheader()
            w.writerows(rows)
    except Exception:
        pass
    site.log("PURGE 纠正扩展名%d 隔离非媒体%d 记账%d行" % (fixed, isolated, len(rows)))
    return 0


def cmd_envcheck(site=None) -> int:
    print("site_crawler v%s" % __version__)
    bad = []

    def rep(name, ok, note=""):
        print("[%s] %s%s" % ("OK" if ok else "MISS", name,
                             (" " + note) if note else ""))
        if not ok and name in ("python", "requests", "playwright-py", "chromium"):
            bad.append(name)

    rep("python", True, sys.version.split()[0])
    try:
        import requests as _r
        rep("requests", True, _r.__version__)
    except ImportError:
        rep("requests", False, "pip install requests")
    try:
        import playwright  # noqa: F401
        rep("playwright-py", True, "")
    except ImportError:
        rep("playwright-py", False, "pip install playwright")
    chrom = ""
    import glob as _glob
    pats = [os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win\chrome.exe"),
            os.path.join(os.path.expanduser("~"), ".cache", "ms-playwright",
                         "chromium-*", "chrome-linux", "chrome")]
    for pat in pats:
        try:
            hit = _glob.glob(pat)
        except Exception:
            hit = []
        if hit:
            chrom = hit[0]
            break
    rep("chromium", bool(chrom), chrom or "(未安装: playwright install chromium)")
    rep("ffmpeg.exe", bool(find_exe(["ffmpeg.exe", "ffmpeg"])),
        find_exe(["ffmpeg.exe", "ffmpeg"]))
    rep("yt-dlp.exe", bool(find_exe(["yt-dlp.exe", "yt-dlp"])),
        find_exe(["yt-dlp.exe", "yt-dlp"]))
    rep("N_m3u8DL-RE.exe", bool(find_exe(["N_m3u8DL-RE.exe", "N_m3u8DL-RE"])),
        "(未安装, 对应引擎自动跳过)")
    try:
        import curl_cffi  # noqa: F401
        rep("curl_cffi(TLS伪装)", True, "下载层走chrome指纹")
    except ImportError:
        rep("curl_cffi(TLS伪装)", False, "pip install curl-cffi (缺则回落requests)")
    try:
        import camoufox  # noqa: F401
        rep("camoufox(C++指纹)", True, "可选后端 --browser camoufox")
    except Exception:
        rep("camoufox(C++指纹)", False, "pip install camoufox && python -m camoufox fetch")
    if bad:
        print("envcheck: FAIL(缺核心项: %s)" % ",".join(bad))
        return 1
    print("envcheck: OK(缺项功能降级, 见上)")
    return 0


# ================================================================ 入口
def build_parser():
    ap = argparse.ArgumentParser(
        prog="site_crawler.py",
        description="通用站点媒体下载器 v%s: 填网址->检测验证->人工验证->自动下载" % __version__)
    ap.add_argument("mode", nargs="?", default="envcheck",
                    choices=["check", "wait", "dl", "auto", "diag", "watch",
                             "nav", "purge", "envcheck"])
    ap.add_argument("url", nargs="?", default="")
    ap.add_argument("batch", nargs="?", type=int, default=60)
    ap.add_argument("--allow-cdn", action="store_true")
    ap.add_argument("--allow-http", action="store_true")
    ap.add_argument("--proxy", default="")
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--browser", default="",
                    choices=["", "chromium", "chrome", "edge", "camoufox"],
                    help="浏览器通道: camoufox=C++层指纹(最强); chrome/edge=本机真实浏览器")
    ap.add_argument("--clone-profile", default="",
                    help="克隆真实浏览器profile路径(Torch思路, 只读源, 隔离副本)")
    ap.add_argument("--column", default="")
    ap.add_argument("--video-first", dest="video_first", action="store_const",
                    const=True, default=None)
    ap.add_argument("--no-video-first", dest="video_first", action="store_const",
                    const=False)
    ap.add_argument("--dl-jobs", type=int, default=3)
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.mode == "envcheck":
        return cmd_envcheck()
    if not a.url:
        ap.error("需要目标URL")
    if not re.match(r"^https?://", a.url.strip()):
        print("URL 必须以 http(s):// 开头")
        return 2
    try:
        site = Site(a.url.strip(), a)
    except ValueError as e:
        print("非法目标主机: %s" % e)
        return 2
    if a.mode == "check":
        return cmd_check(site)
    if a.mode == "wait":
        return cmd_wait(site)
    if a.mode == "dl":
        return cmd_dl(site, a.batch)
    if a.mode == "auto":
        return cmd_auto(site, a.batch)
    if a.mode == "diag":
        return cmd_diag(site)
    if a.mode == "nav":
        return cmd_nav(site)
    if a.mode == "purge":
        return cmd_purge(site)
    if a.mode == "watch":
        from watchflow import cmd_watch
        jobs = max(1, min(8, int(a.dl_jobs or 3)))
        return cmd_watch(site, a.batch, jobs)
    return 2


if __name__ == "__main__":
    sys.exit(main())
