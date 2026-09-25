# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 jjjjjjjjnnjnn
"""通用站点媒体下载器 v1.9.12: 填网址 -> 检测人机验证 -> 需验证弹窗等人工 -> 自动全站下载.

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
  verify <url>             自证: 按 inventory.csv 重算 sha256(纯本地, 不联网)
  replay <url>             重放自测: cookie 换身份只读重放(仅自有/授权站, 只 GET)
  updatecheck              检查 GitHub 新版本(只通知, 永不自动下载/执行)
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
  --lock-session           会话独占锁(防他进程并发写cookies.txt)
  --hijack-check           劫持检测: TOFU 证书钉扎(默认关, 变更只告警不阻断)
  --repin                  证书重钉(人工确认换证合法后, 与 --hijack-check 同用)
  --lang LANG              语言 auto/zh/en(默认auto=系统语言, 取不到回英语;
                             引擎日志暂中文, TUI 已双语)
  --no-learn               关闭自我学习(不读写本站 learn.json)
  --spoof MODE             请求伪装: googlebot/bingbot/mobile(默认off);
                             bot类强制requests+告警, mobile同步移动视口与头
  --spoof-referer URL      伪装Referer(只收http(s), 非法值丢弃)
  --snapshot MODE          缓存快照探测: wayback/archive/auto(默认off);
                             check遇验证时报快照情报, 正文只内存判定不落盘
  --softwall MODE          客户端干预: strip(删遮罩+解滚动锁)/reader(只计数);
                             默认off, 只操作已加载DOM不发额外请求
  --text-proxy PREFIX      一站式文本代理前缀(通用, 不内置第三方);
                             check遇验证时报代理情报, 正文只内存判定不落盘
  --hls-key URI[,IV]       HLS密钥透传(默认空=不用; 非法整体丢弃;
                             N_m3u8DL-RE/yt-dlp生效, ffmpeg跳过)
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
from urllib.parse import urljoin, urlsplit, urlunsplit, quote
from urllib import robotparser

import requests

__version__ = "1.9.12"

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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
]
VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
]
MOBILE_VIEWPORTS = [
    {"width": 412, "height": 915},
    {"width": 390, "height": 844},
    {"width": 360, "height": 740},
]

# 路径一: 请求伪装预设. 默认 off(桌面池不变); bot 类无对应 TLS preset,
# 用时强制回落 requests 并告警(防"新 UA + 旧指纹"脚本信号).
SPOOF_PRESETS = {
    "googlebot": {
        "ua": "Mozilla/5.0 (compatible; Googlebot/2.1; "
              "+http://www.google.com/bot.html)",
        "mobile": False, "platform": '"Windows"', "bot": True,
    },
    "bingbot": {
        "ua": "Mozilla/5.0 (compatible; bingbot/2.0; "
              "+http://www.bing.com/bingbot.htm)",
        "mobile": False, "platform": '"Windows"', "bot": True,
    },
    "mobile": {
        "ua": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "mobile": True, "platform": '"Android"', "bot": False,
    },
}

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
_TOKEN_Q_RE = re.compile(r"[?&](token|expires?|sign|auth|sig|deadline)=", re.I)


def _chmod_0600(path: str) -> None:
    """敏感文件 0600：posix 生效；Windows os.chmod 尽力 + try 包裹永不抛."""
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass

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
_BOT_WARNED = False
_HLS_FFMPEG_WARNED = False

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
    """主机名文件系统安全: 允许中段 _/- (内网常见), 仍拒 ..穿越/首尾特殊/空标签.

    注: IPv6 字面量(含 :) 一律拒绝 —— Windows 目录名不允许冒号, 此类目标请走域名.
    """
    h = (host or "").strip().lower()
    if not h or h in (".", ".."):
        return ""
    if re.search(r"[^a-z0-9.\-_]", h):
        return ""
    if h[0] in (".", "-", "_") or h[-1] in (".", "-", "_"):
        return ""
    for seg in h.split("."):
        if seg in ("", ".", ".."):
            return ""
        if seg[0] in ("-", "_") or seg[-1] in ("-", "_"):
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


RULES_VERSION = 1
_RULE_SEL_RE = re.compile("^[a-zA-Z0-9_.#\\[\\]=\\\"':\\-\\s>]+$")


def _sanitize_rule_selectors(v):
    """rules 选择器白名单: 仅 CSS 子集, 长度<=200, 非法逐条丢弃."""
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, (list, tuple)):
        return []
    out = []
    for x in v:
        try:
            s = str(x).strip()
        except Exception:
            continue
        if not s or len(s) > 200:
            continue
        if not _RULE_SEL_RE.match(s):
            continue
        out.append(s)
    return out[:20]


def site_rules(site):
    """声明式站点规则(安全子集): cfg['rules'] 必须是 dict 且 version==1.

    键: detail_link_selector / next_page_selector / watch_button_selector.
    值: CSS 选择器字符串白名单. version 错配则整节丢弃并 WARNING.
    """
    try:
        raw = site.cfg.get("rules")
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    try:
        ver = raw.get("version")
    except Exception:
        return {}
    if ver != RULES_VERSION:
        try:
            site.log("WARNING rules 版本错配(要1得%s): 整节丢弃" % (ver,))
        except Exception:
            pass
        return {}
    out = {}
    try:
        for k in ("detail_link_selector", "next_page_selector",
                  "watch_button_selector"):
            out[k] = _sanitize_rule_selectors(raw.get(k, []))
    except Exception:
        return {}
    return out


KNOWN_CFG_KEYS = frozenset([
    "delay", "batch", "browser", "clone_profile", "column", "video_first",
    "allow_cdn", "allow_http", "insecure", "proxy", "proxies",
    "proxy_sticky", "proxy_sticky_ttl", "proxy_trusted",
    "locale", "timezone_id", "lazy_rounds", "extra_verify_selectors",
    "extra_headers", "ad_keywords", "session_ttl_h", "hls_key",
    "snapshot", "softwall", "text_proxy", "spoof", "spoof_referer",
    "tls_spoof", "rules", "learn", "lang",
])


def _validate_config_dict(raw):
    """轻量校验: 未知键->warnings; 类型错->warnings+安全回落. 不执行任何签名脚本."""
    warnings = []
    if not isinstance(raw, dict):
        return {}, ["config 非 dict 已清空"]
    for k in sorted(raw.keys()):
        if k not in KNOWN_CFG_KEYS:
            warnings.append("未知配置键忽略: %s" % k)
    for k in ("proxies", "proxy_trusted", "extra_verify_selectors", "ad_keywords"):
        if k in raw and raw[k] is not None and not isinstance(raw[k], (list, tuple, str)):
            warnings.append("类型错误 %s 须 list/str, 已忽略" % k)
            raw[k] = []
    for k in ("extra_headers", "rules"):
        if k in raw and raw[k] is not None and not isinstance(raw[k], dict):
            warnings.append("类型错误 %s 须 dict, 已忽略" % k)
            raw[k] = {}
    return raw, warnings


def url_for_log(url: str) -> str:
    """日志脱敏: 只到 path, query/fragment 永不落盘."""
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower()
        return "%s://%s%s" % (p.scheme.lower(), host, p.path or "/")
    except Exception:
        return "(bad-url)"


def _resolve_ips(host: str):
    """DNS 进程内缓存 TTL 60s: 只缓存成功公网结果, 失败/私网不留存(防投毒)."""
    try:
        _hk = (host or "").strip().lower().rstrip(".")
    except Exception:
        return []
    if _hk:
        try:
            _ts, _ips = _DNS_CACHE.get(_hk, (0.0, []))
            if _ips and time.time() - _ts < _DNS_TTL:
                return list(_ips)
        except Exception:
            pass
    try:
        ips = sorted({r[4][0] for r in socket.getaddrinfo(host, None)})
    except Exception:
        return []
    if not ips:
        return []
    try:
        _all_pub = True
        for _ip in ips:
            try:
                _a = ipaddress.ip_address(_ip)
            except ValueError:
                _all_pub = False
                break
            if (_a.is_private or _a.is_loopback or _a.is_link_local
                    or _a.is_multicast or _a.is_reserved or _a.is_unspecified):
                _all_pub = False
                break
        if _all_pub and _hk:
            _DNS_CACHE[_hk] = (time.time(), list(ips))
    except Exception:
        pass
    return ips


_DNS_CACHE = {}
_DNS_TTL = 60.0


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
    """限速 + 随机抖动, 叠加自适应乘子(拥塞时自动变慢, 空闲渐回)."""
    try:
        t = float(base if base is not None else site.cfg.get("delay", 1.2))
    except Exception:
        t = 1.2
    try:
        mult = max(1.0, float(getattr(site, "delay_mult", 1.0) or 1.0))
        site.delay_mult = max(1.0, mult * 0.99)
    except Exception:
        mult = 1.0
    try:
        _jit = random.gauss(0.4, 0.2)
    except Exception:
        _jit = 0.4
    _jit = max(0.0, min(0.8, _jit))
    time.sleep(max(0.2, t) * mult + _jit)


def think(page, ms: int = 600) -> None:
    """拟人停顿 ±25% 抖动(防固定节拍被判脚本), 下限 100ms. 调用方传标称值即可."""
    try:
        jit = max(100, int(int(ms) * random.uniform(0.75, 1.25)))
    except Exception:
        jit = max(100, int(ms) if isinstance(ms, (int, float)) else 600)
    try:
        page.wait_for_timeout(jit)
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


def diagnose_http_challenge(status, headers, body_head):
    """HTTP 403 挑战分类(纯函数, 不存 body). 返回 (kind, hint).

    kind ∈ {cf-challenge, turnstile, datadome, forbidden, ""}.
    body 只取前 4KB 判定, 调用方负责截断/不落盘.
    geetest 只归浏览器侧 VERIFY_SELECTORS, 此处不判 datadome.
    """
    try:
        st = int(status)
    except Exception:
        return "", ""
    if st != 403:
        return "", ""
    try:
        h = {str(k).lower(): str(v).lower()
             for k, v in dict(headers or {}).items()}
    except Exception:
        h = {}
    try:
        b = str(body_head or "")[:4096].lower()
    except Exception:
        b = ""
    try:
        blob = " ".join(list(h.keys()) + list(h.values())) + " " + b
    except Exception:
        blob = b
    if "datadome" in blob:
        return ("datadome",
                "DataDome拦截: 换住宅出口后走wait人工验证, 数据中心IP勿重试.")
    if "cf-turnstile" in b or "challenge-platform" in b \
            or "cf-turnstile" in " ".join(h.keys()):
        return ("turnstile",
                "Turnstile验证: 走wait人工过验证, 勿高频重试.")
    if h.get("cf-mitigated", "") == "challenge" \
            or "attention required" in b \
            or "cf-challenge" in b \
            or ("just a moment" in b and "cloudflare" in b):
        return ("cf-challenge",
                "Cloudflare质询: 换住宅IP/换出口后走wait人工验证.")
    return ("forbidden",
            "纯403: 查Referer/UA防盗链, 非验证页, 先查伪装与来源页.")


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


def _proxy_dns_hint(proxy: str) -> str:
    """DNS 泄漏提示: socks5(非 h)远端解析走本地, 建议 socks5h."""
    try:
        scheme = urlsplit(proxy or "").scheme.lower()
    except Exception:
        return ""
    if scheme == "socks5":
        return "DNS可能本地解析, 建议换 socks5h://"
    return ""


def anon_level(site) -> int:
    """匿名等级: 0直连(暴露) / 1单代理 / 2轮换池. 每次运行身份束(run_id)恒更换."""
    if len(site._proxy_list()) >= 2:
        return 2
    p, _ = eff_proxy(site)
    return 1 if p else 0


def anon_report(site) -> int:
    """开工匿名简报: 等级 + 出口数 + DNS 提示 + 通道. 无代理即明示暴露风险."""
    try:
        lv = anon_level(site)
    except Exception:
        lv = 0
    names = {0: "L0直连(真实IP暴露)", 1: "L1单代理", 2: "L2轮换池(每次出口随机不同)"}
    try:
        ch = _eff_channel(site) or "chromium"
    except Exception:
        ch = "chromium"
    site.log("匿名: %s 身份束#%s 通道=%s"
             % (names.get(lv, "L?"), getattr(site, "run_id", "?"), ch or "chromium"))
    if lv == 0:
        site.log("WARNING 无代理: 服务端可见你的真实出口 IP, 隐匿要求高请配代理池")
    else:
        try:
            p, _ = eff_proxy(site)
            hint = _proxy_dns_hint(p)
            if hint:
                site.log("WARNING " + hint)
        except Exception:
            pass
    return lv


def _ipv6_available() -> bool:
    """本机 IPv6 栈+非回环地址探测(纯本地, 失败即 False)."""
    try:
        if not getattr(socket, "has_ipv6", False):
            return False
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6):
            ip = info[4][0]
            if ip != "::1" and not ip.startswith("fe80"):
                return True
        return False
    except Exception:
        return False


def _disk_ok(path: str, need_mb: int = 500) -> bool:
    try:
        return shutil.disk_usage(path).free >= need_mb * 1048576
    except Exception:
        return True


def _auto_jobs(n) -> int:
    """下载并发: >0 直接用(钳1-8); 0/非法 = 按 CPU 自动(min8,至少2)."""
    try:
        n = int(n)
    except Exception:
        return 3
    if n <= 0:
        try:
            c = os.cpu_count() or 4
        except Exception:
            c = 4
        return max(2, min(8, c // 2))
    return max(1, min(8, n))


def _locale_of(site):
    """语言/时区: 配置优先, 默认中文上海; camoufox geoip 开时代理出口自动覆盖."""
    loc = _cfg_str(site.cfg.get("locale")) or "zh-CN"
    tz = _cfg_str(site.cfg.get("timezone_id")) or "Asia/Shanghai"
    return loc, tz


def _accept_language_of(site) -> str:
    """requests 侧 Accept-Language: 与浏览器 locale 同源, 默认 zh-CN 不变.

    规则: 主值=locale 原样; 次值=locale 主语言; 英文兜底 q=0.8.
    非法 locale 回 zh-CN 全家桶. 只产 [A-Za-z-]+/q 值, 无注入面.
    """
    try:
        loc = _cfg_str(site.cfg.get("locale")) or "zh-CN"
    except Exception:
        loc = "zh-CN"
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})?", loc or ""):
        loc = "zh-CN"
    try:
        primary = (loc or "zh-CN").split("-")[0].lower() or "zh"
    except Exception:
        primary = "zh"
    if (loc or "").lower().startswith("en"):
        return "%s,%s;q=0.9" % (loc, primary)
    return "%s,%s;q=0.9,en;q=0.8" % (loc, primary)


def _browser_guard(site, url: str) -> bool:
    """浏览器导航守卫: 目标主机必须公网可解析, 拦元数据/内网直连.

    浏览器由站点自己解析, TOCTOU 只能拦静态私网(动态重绑定见下载层对端复检).
    """
    try:
        host = urlsplit(url).hostname or ""
    except Exception:
        return False
    if not host or not is_public_host(host):
        try:
            site.bump("skip_browser_ssrf")
            site.log("BROWSER-SSRF 拦截内网导航: %s" % url_for_log(url))
        except Exception:
            pass
        return False
    return True


def preflight(site) -> int:
    """开工预检: 代理已死直接拦下(返回2), 不带病空跑."""
    try:
        _check_session_perms(site)
    except Exception:
        pass
    try:
        if getattr(getattr(site, "args", None), "lock_session", False):
            if not _take_session_lock(site):
                try:
                    with open(os.path.join(site.root, ".session.lock"),
                              encoding="utf-8") as _lf:
                        _holder = (_lf.read() or "").strip().split()[0]
                except Exception:
                    _holder = "?"
                site.log("SESSION-LOCKED 会话锁被占用(持有者PID %s, %s), 退出. "
                         "若该进程已不在请删锁文件后重跑; 单次运行可去掉 --lock-session"
                         % (_holder, os.path.join(site.root, ".session.lock")))
                return 2
    except Exception:
        pass
    try:  # 攻击侧自测之劫持检测默认关, 开了才钉扎比对
        if site.hijack_on():
            _hijack_check(site)
    except Exception:
        pass
    p, origin = eff_proxy(site, "browser")
    if p and not proxy_alive(p):
        site.log("PROXY-DEAD 代理不可用(%s %s), 停止. 检查代理进程与端口."
                 % (origin, mask_proxy(p)))
        return 2
    if p:
        site.log("代理: %s(%s)" % (origin, mask_proxy(p)))
    try:
        anon_report(site)
    except Exception:
        pass
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
        try:
            if os.path.isfile(self.ckf):
                _chmod_0600(self.ckf)
        except Exception:
            pass
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
        try:
            self.cfg, _cfg_warns = _validate_config_dict(self.cfg)
            for _w in _cfg_warns:
                try:
                    print("WARNING " + _w, flush=True)
                except Exception:
                    pass
                try:
                    with open(self.logf, "a", encoding="utf-8") as _lf:
                        _lf.write("WARNING " + _w + "\n")
                except Exception:
                    pass
        except Exception:
            pass
        self.proxy = getattr(args, "proxy", "") or ""
        self.counters = defaultdict(int)
        self.learn = load_learn(self)
        self.fails = []
        self._proxy_idx = 0
        self._cloned_done = False
        self.run_id = "%08x" % random.getrandbits(32)  # 本次运行身份束编号
        self.delay_mult = 1.0  # 自适应限速乘子(拥塞抬升, 空闲衰减)
        self.last_proxy = ""  # 上次出口(轮换避重)
        self.proxy_cool = {}  # 代理 -> 冷却截止(unix 时间)
        self.proxy_stat = {}  # 代理 -> [成功, 失败]
        self.proxy_hist = {}  # 代理 -> 近10次成败(防刷白)
        self._sticky_proxy = ""  # 浏览器粘滞出口
        self._sticky_ts = 0.0
        self._alive_cache = {}  # 代理存活缓存 {proxy: (ts, bool)}
        self._camoufox_cm = None
        self._robots = None
        self._auto_channel = ""  # auto 重试梯子的通道覆盖(平时空=不干预)
        self.pick_identity()

    # -- 身份 --
    def pick_identity(self) -> None:
        global _BOT_WARNED
        sp = self.spoof_mode()
        if sp:
            self.UA = SPOOF_PRESETS[sp]["ua"]
            self.viewport = dict(random.choice(
                MOBILE_VIEWPORTS if SPOOF_PRESETS[sp]["mobile"] else VIEWPORTS))
            try:  # bot 伪装: 浏览器仍挂爬虫 UA, 易被喂精简页/判脚本(每进程只警告一次)
                if SPOOF_PRESETS[sp].get("bot") and not _BOT_WARNED:
                    _BOT_WARNED = True
                    self.log("WARNING bot伪装: 浏览器仍挂爬虫UA(易被喂精简页/判脚本), "
                             "建议仅配合快照/文本代理用, 正文站请去掉 --spoof")
            except Exception:
                pass
            return
        self.UA = random.choice(UA_POOL)
        self.viewport = dict(random.choice(VIEWPORTS))

    def spoof_mode(self) -> str:
        """请求伪装档: off(默认)/googlebot/bingbot/mobile. 未知值归 off."""
        m = _cfg_str(getattr(self.args, "spoof", "")) or \
            _cfg_str(self.cfg.get("spoof"))
        m = m.strip().lower()
        return m if m in SPOOF_PRESETS else ""

    def spoof_referer(self) -> str:
        """伪装 Referer: 必须是显式 http(s) 绝对 URL, 无 userinfo 无换行.

        无 scheme 自动补全是禁止的(会把 javascript: 洗成 http:// 前缀漏网).
        """
        r = _cfg_str(getattr(self.args, "spoof_referer", "")) or \
            _cfg_str(self.cfg.get("spoof_referer"))
        r = (r or "").strip()
        try:
            if any(c in r for c in ("\n", "\r", "\t", " ")):
                return ""
            p = urlsplit(r)
            if p.scheme not in ("http", "https") or not p.hostname:
                return ""
            if "@" in (p.netloc or ""):
                return ""
            return urlunsplit((p.scheme, p.netloc, p.path or "/", "", ""))
        except Exception:
            return ""

    def ref_for(self, referer: str) -> str:
        """Referer 生效点: 伪装值优先, 否则透传调用方."""
        return self.spoof_referer() or referer

    def extra_headers_for(self, host: str) -> dict:
        """Host 作用域附加头(M-Fetch rules.json 安全子集): 只收 Referer/Origin.

        cfg["extra_headers"] 形如 {host: {Referer: url, Origin: url}}.
        键大小写不敏感归一化为 Referer/Origin; 值必须 http(s) 且过
        _safe_url_for_cmd(无空白/控制符), 余键(含 Cookie)一律丢弃.
        """
        try:
            h = (host or "").strip().lower().rstrip(".")
        except Exception:
            return {}
        if not h:
            return {}
        try:
            raw = self.cfg.get("extra_headers")
        except Exception:
            return {}
        if not isinstance(raw, dict):
            return {}
        node = None
        try:
            for k, v in raw.items():
                if isinstance(k, str) and k.strip().lower().rstrip(".") == h:
                    node = v
                    break
        except Exception:
            return {}
        if not isinstance(node, dict):
            return {}
        out = {}
        for k, v in node.items():
            try:
                if not isinstance(k, str) or not isinstance(v, str):
                    continue
                kl = k.strip().lower()
                if kl == "referer":
                    ck = "Referer"
                elif kl == "origin":
                    ck = "Origin"
                else:
                    continue
                vv = (v or "").strip()
                if not vv or len(vv) > 2000:
                    continue
                if not _safe_url_for_cmd(vv):
                    continue
                p = urlsplit(vv)
                if p.scheme not in ("http", "https") or not p.hostname:
                    continue
                if "@" in (p.netloc or ""):
                    continue
                out[ck] = vv
            except Exception:
                continue
        return out

    def hls_key(self):
        """HLS 密钥透传: --hls-key URI[,IV] 原样收, 校验后回 (uri, iv).

        URI 须 http(s) 且过 _safe_url_for_cmd; IV 须 ^(0x)?[0-9a-fA-F]+$
        任一段非法则整体丢弃回 ("", "").
        """
        raw = _cfg_str(getattr(self.args, "hls_key", "")) or \
            _cfg_str(self.cfg.get("hls_key"))
        raw = (raw or "").strip()
        if not raw:
            return "", ""
        try:
            if re.search(r"\s|[\x00-\x1f\x7f]", raw):
                return "", ""
            if "," in raw:
                uri, iv = raw.split(",", 1)
            else:
                uri, iv = raw, ""
            uri = (uri or "").strip()
            iv = (iv or "").strip()
            if not _safe_url_for_cmd(uri):
                return "", ""
            p = urlsplit(uri)
            if p.scheme not in ("http", "https") or not p.hostname:
                return "", ""
            if "@" in (p.netloc or ""):
                return "", ""
            if iv:
                if not re.fullmatch(r"(?:0x)?[0-9a-fA-F]+", iv):
                    return "", ""
            return uri, iv
        except Exception:
            return "", ""

    def snapshot_mode(self) -> str:
        """快照档: off(默认)/wayback/archive/auto. 未知值归 off."""
        m = _cfg_str(getattr(self.args, "snapshot", "")) or \
            _cfg_str(self.cfg.get("snapshot"))
        m = m.strip().lower()
        return m if m in ("wayback", "archive", "auto") else ""

    def softwall_mode(self) -> str:
        """客户端干预档: off(默认)/strip/reader. 未知值归 off."""
        m = _cfg_str(getattr(self.args, "softwall", "")) or \
            _cfg_str(self.cfg.get("softwall"))
        m = m.strip().lower()
        return m if m in ("strip", "reader") else ""

    def text_proxy_base(self) -> str:
        """一站式文本代理前缀: 显式 http(s) 绝对 URL, 无 userinfo 无空白.

        不硬编码任何第三方(防投毒+防 ToS 连带); 目标 URL 由调用方
        quote 后拼接. 非法值丢弃.
        """
        t = _cfg_str(getattr(self.args, "text_proxy", "")) or \
            _cfg_str(self.cfg.get("text_proxy"))
        t = (t or "").strip()
        try:
            if not t or len(t) > 500:
                return ""
            if re.search(r"\s|[\x00-\x1f\x7f]", t):
                return ""
            p = urlsplit(t)
            if p.scheme not in ("http", "https") or not p.hostname:
                return ""
            if "@" in (p.netloc or ""):
                return ""
            return t
        except Exception:
            return ""

    def text_proxy_url(self, url: str) -> str:
        """代理请求地址: 前缀 + quote(目标). 前缀非法返回空."""
        base = self.text_proxy_base()
        if not base:
            return ""
        try:
            return base + quote(url or "", safe="")
        except Exception:
            return ""

    def hijack_on(self) -> bool:
        """劫持检测开关: 默认关, --hijack-check 或 cfg 显式开."""
        if getattr(self.args, "hijack_check", False):
            return True
        return bool(self.cfg.get("hijack_check", False))

    def _pinfile(self) -> str:
        return os.path.join(self.root, "certpin.txt")

    def tls_verify(self) -> bool:
        if getattr(self.args, "insecure", False):
            return False
        return not bool(self.cfg.get("insecure", False))

    # -- 代理 --
    def _proxy_list(self):
        raw = _cfg_list(self.cfg.get("proxies"))
        out = [c for c in (check_proxy(x) for x in raw) if c]
        return list(dict.fromkeys(out))  # 保序去重

    def _cooling(self, proxy: str) -> bool:
        try:
            return time.time() < float(self.proxy_cool.get(proxy, 0))
        except Exception:
            return False

    def report_proxy(self, proxy: str, ok: bool) -> None:
        """代理健康记账: 近10次滑窗失败≥5即熔断10分钟, 成功只衰减不洗白.

        防"2败1成"刷白钉死劣质出口.
        """
        if not proxy:
            return
        st = self.proxy_stat.get(proxy, [0, 0])
        hist = self.proxy_hist.get(proxy, []) if hasattr(self, "proxy_hist") else []
        if ok:
            st[0] += 1
            st[1] = max(0, st[1] - 1)
            hist = (hist + [True])[-10:]
        else:
            st[1] += 1
            hist = (hist + [False])[-10:]
            if hist.count(False) >= 5 and proxy not in self.proxy_cool:
                self.proxy_cool[proxy] = time.time() + 600
                self.log("代理熔断10分钟: %s" % mask_proxy(proxy))
        self.proxy_stat[proxy] = st
        self.proxy_hist[proxy] = hist

    def alive_ok(self, proxy: str, ttl: int = 60) -> bool:
        """存活检查带缓存(TTL 60s), 防每文件一次 TCP 探测拖慢."""
        now = time.time()
        try:
            ts, ok = self._alive_cache.get(proxy, (0, False))
            if now - ts < ttl:
                return ok
        except Exception:
            pass
        ok = proxy_alive(proxy)
        self._alive_cache[proxy] = (now, ok)
        return ok

    def rotate_proxy(self) -> str:
        """代理轮换: 随机取、避开上次与冷却中, 每次出口不同. 总池<2条回 ''."""
        total = self._proxy_list()
        if len(total) < 2:
            return ""
        avail = [p for p in total if not self._cooling(p)] or total
        cands = [p for p in avail if p != self.last_proxy] or avail
        p = random.choice(cands)
        self.last_proxy = p
        return p

    def sticky_proxy(self) -> str:
        """浏览器粘滞出口: 登录态/长流程 IP 稳定. 配置 proxy_sticky 优先,
        否则池内随机钉一个, TTL(proxy_sticky_ttl 分钟, 默认30)后重选."""
        cfg_one = check_proxy(_cfg_str(self.cfg.get("proxy_sticky")))
        if cfg_one:
            return cfg_one
        pool = [p for p in self._proxy_list() if not self._cooling(p)] \
            or self._proxy_list()
        if not pool:
            return ""
        try:
            ttl = float(self.cfg.get("proxy_sticky_ttl", 30) or 30) * 60
        except Exception:
            ttl = 1800.0
        now = time.time()
        if self._sticky_proxy and self._sticky_proxy in pool \
                and now - self._sticky_ts < ttl:
            return self._sticky_proxy
        cands = [p for p in pool if p != self._sticky_proxy] or pool
        self._sticky_proxy = random.choice(cands)
        self._sticky_ts = now
        return self._sticky_proxy

    def failover(self, sess) -> bool:
        """出口故障转移: 当前出口连败即换一个非冷却代理写入会话并重试."""
        try:
            cur = (getattr(sess, "proxies", {}) or {}).get("https", "")
        except Exception:
            cur = ""
        if cur:
            self.report_proxy(cur, False)
        pool = [p for p in self._proxy_list()
                if p != cur and not self._cooling(p)]
        if not pool:
            return False
        nxt = random.choice(pool)
        try:
            sess.proxies.update({"http": nxt, "https": nxt})
        except Exception:
            return False
        self.last_proxy = nxt
        self.log("代理故障转移 -> %s" % mask_proxy(nxt))
        return True

    def note_congestion(self) -> None:
        """拥塞反馈: 429/5xx 即抬升限速乘子(上限5x), 空闲时 polite_sleep 衰减."""
        try:
            self.delay_mult = min(5.0, float(self.delay_mult or 1.0) * 1.5)
        except Exception:
            self.delay_mult = 1.0
        try:  # 学习: 拥塞即把学习延迟上调 0.5s(上限 10s), 落盘在收尾
            if learn_on(self):
                cur = float((self.learn or {}).get("delay", 1.2) or 1.2)
                self.learn["delay"] = round(min(10.0, cur + 0.5), 1)
        except Exception:
            pass

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
            self.bump("robots-unknown")  # 取失败不再静默放行: 记账+惩罚性限速
            try:
                self.cfg["delay"] = float(self.cfg.get("delay", 1.2) or 1.2) + 1.0
            except Exception:
                pass
            self.log("robots获取失败(未知: 限速+1s)")
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
        try:  # why 自由文本可能回显全 URL(含 token): scrub 后再记
            _w = re.sub(r"https?://[^\s'\"]+",
                        lambda m: url_for_log(m.group(0)), str(why))
            _w = _TOKEN_Q_RE.sub("?", _w)
        except Exception:
            _w = str(why)
        if len(self.fails) < 3:
            self.fails.append("%s | %s" % (url_for_log(url), _w[:120]))
        self.bump("fetch_fail")

    def summary(self) -> None:
        parts = ["%s=%s" % (k, v) for k, v in sorted(self.counters.items())]
        self.log("SUMMARY " + (" ".join(parts) if parts else "(空)"))
        for f in self.fails:
            self.log("  fail样本: " + f)


def eff_proxy(site, purpose: str = "dl"):
    """代理生效顺序分池:
    browser(浏览器长流程): proxy_sticky配置 > 池内粘滞钉选(TTL) > 通用顺序;
    dl(下载遍历): 站点proxies随机轮换(>=2条, 避重避冷却) > 站点单条 >
    命令行手动 > 站点proxy > 系统代理."""
    lst = site._proxy_list()
    if purpose == "browser":
        sp = site.sticky_proxy()
        if sp:
            return sp, "sticky"
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


_IMPERSONATE_OK = ("chrome150", "chrome146", "chrome145", "chrome142",
                    "chrome136", "chrome131", "chrome124", "chrome120",
                    "chrome116", "chrome")


def _pick_impersonate(ua: str) -> str:
    """指纹与 UA 同代绑定: 取 UA 的 Chrome 大版本, 就近选 curl_cffi 支持的 preset.

    Mobile UA 用 chrome131_android 真指纹(缺失由 make_session 回落 requests);
    老指纹配新 UA 是教科书级脚本信号; preset 不存在则抛错由上层回落 requests.
    """
    if "Mobile" in (ua or ""):
        return "chrome131_android"
    m = re.search(r"Chrome/(\d+)", ua or "")
    major = int(m.group(1)) if m else 0
    for name in _IMPERSONATE_OK:
        if name == "chrome":
            return "chrome"
        if major >= int(name[6:]):
            return name
    return "chrome"


def verify_lock():
    """供应链版本钉死检查: 已安装版本必须 == requirements.lock, 漂移即报.

    返回 [(包, 锁定版, 实际版/状态)]. 离线可用, 是 hash 锁之外的第二道门.
    """
    out = []
    pins = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "requirements.lock"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s\\]+)", line)
                if m:
                    pins[m.group(1).lower().replace("-", "_")] = m.group(2)
    except Exception:
        return [("requirements.lock", "可读", "缺失")]
    try:
        from importlib.metadata import version, PackageNotFoundError
    except Exception:
        return [("importlib.metadata", "可用", "不可用")]
    for pkg, want in sorted(pins.items()):
        try:
            got = version(pkg)
        except PackageNotFoundError:
            got = "未安装"
        out.append((pkg, want, got if got == want else got + "≠漂移"))
    return out


def tls_selftest():
    """TLS preset 自测(纯本地零流量): 逐个试构造 curl_cffi Session, 返回 {preset: ok}."""
    out = {}
    try:
        from curl_cffi import requests as cr
    except Exception:
        return {}
    for name in _IMPERSONATE_OK:
        try:
            s = cr.Session(impersonate=name)
            try:
                s.close()
            except Exception:
                pass
            out[name] = True
        except Exception:
            out[name] = False
    return out


def _tls_kind_for(site) -> str:
    """TLS 通道选择: 仅 bot 伪装无对应 TLS preset, 强制 requests(防指纹错配).

    mobile 已有 chrome131_android 真指纹, 走 curl_cffi.
    返回 "curl_cffi" 或 "requests". 可单元测试, 不碰网络.
    """
    try:
        sp = site.spoof_mode()
        if sp and SPOOF_PRESETS[sp]["bot"]:
            return "requests"
        if sp == "mobile":
            return "curl_cffi"
    except Exception:
        pass
    return "curl_cffi"


# ================================================================ 会话交接(wait->dl/check/watch)
_CK_NAME_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+\-.^_`|~]+$")
_CK_MAX_PAIRS = 100
_CK_MAX_VAL = 4096


def _load_cookie_pairs(site):
    """读 wait 存的 cookies.txt -> [(name, value)]. 纯本地解析, 失败回 [].

    夹紧(防 cookies.txt 被投毒后走私进请求头):
    名必须 RFC6265 token(拦 CRLF/空白/分隔符, 堵 header 注入);
    值去首尾空白, 含 CTL/分号/逗号丢弃(cookie-octet 本就不含它们);
    值允许首个 = 之后再出现 =(base64 常见); 名长/值长/总对数封顶;
    同名取最后一次(与浏览器语义一致). 值永不打进日志.
    主文件缺失/空时读 cookies.txt.bak 本地备份(只读回退, 用后 WARNING 提示重跑 wait).
    """
    raw, used_bak = "", False
    try:
        with open(site.ckf, encoding="utf-8") as f:
            raw = f.read(65536)
    except Exception:
        raw = ""
    if not (raw or "").strip():
        try:
            with open(site.ckf + ".bak", encoding="utf-8") as f:
                raw = f.read(65536)
            used_bak = bool((raw or "").strip())
        except Exception:
            return []
        if not used_bak:
            return []
        try:
            site.bump("session-bak-used")
            site.log("WARNING 会话主文件缺失/空, 已启用本地备份(建议重跑 wait 刷新)")
        except Exception:
            pass
    pairs = []
    try:
        for seg in (raw or "").split(";"):
            if "=" not in seg:
                continue
            name, _, val = seg.partition("=")
            name = name.strip()
            val = val.strip()
            if not name or len(name) > 256 or not _CK_NAME_RE.match(name):
                continue
            if not val or len(val) > _CK_MAX_VAL:
                continue
            if any(ord(c) < 0x20 or ord(c) == 0x7f for c in val):
                continue
            if ";" in val or "," in val:
                continue
            pairs.append((name, val))
            if len(pairs) >= _CK_MAX_PAIRS:
                break
    except Exception:
        return []
    seen = {}
    for k, v in pairs:
        seen[k] = v
    return list(seen.items())


def _seed_ctx_cookies(site, ctx):
    """把 wait 会话喂给浏览器上下文. 成功 True; 无会话/失败 False(匿名继续).

    值与名永不落日志, 只记对数. 供 open_ctx 全分支调用
    (dl/check/watch 共用, watchflow 经 C.open_ctx 自动受益).
    """
    if ctx is None:
        return False
    try:
        pairs = _load_cookie_pairs(site)
    except Exception:
        return False
    if not pairs:
        return False
    try:
        host = site.host
    except Exception:
        return False
    if not host:
        return False
    try:
        ctx.add_cookies([{"name": k, "value": v, "domain": host, "path": "/"}
                         for k, v in pairs])
    except Exception:
        return False
    try:
        site.log("会话已注入浏览器(%d 对, 域名 %s)" % (len(pairs), host))
    except Exception:
        pass
    return True


def _dl_warn_empty(site, visited: int) -> bool:
    """反静默空跑: visited==0(首跳即断, 一页未进)或进过页但零下载即 WARNING.

    返回 True=告警过. 只记 dl_no_entry/empty_run 计数与一行日志, 不改退出码
    (退出码语义冻结: 0=流程走完, 4=验证拦截; 空跑是否算错由人按 WARNING 判).
    """
    try:
        if visited <= 0:
            if site.counters.get("downloaded", 0) <= 0:
                site.bump("dl_no_entry")
                site.log("WARNING 本轮未能进入任何页面(首跳即断/robots拦): "
                         "建议检查网络与URL, 或跑 diag 看能否建连")
                return True
            return False
        if site.counters.get("downloaded", 0) <= 0:
            site.bump("empty_run")
            site.log("WARNING 本轮零下载(空跑): 已进 %d 页但无一落盘. "
                     "建议跑 diag 看收割数(媒体0=被喂精简页/未渲染, "
                     "有媒体0下载=下载层被拦)" % visited)
            return True
    except Exception:
        pass
    return False


VIDEO_PRESET_KEYS = ("cdn", "video", "spoof", "snapshot", "softwall",
                     "http", "insecure", "lock")


def apply_video_preset(opts: dict):
    """一键视频配置(纯函数, 返回改动说明 list): 以拿到视频为目标收敛开关.

    开: cdn(视频多在 CDN/站外, 默认拦截会漏)/video(深层取流);
    关: spoof(爬虫 UA 易被喂精简页)/snapshot/softwall(与拿视频无关)/http/
    insecure(安全基座)/lock(单次运行免锁扰, 并发自取时请手动开回);
    不动: proxy/column/browser/clone/text_proxy/hls_key/hijack/learn/lang/
    batch/jobs(用户基础设施与偏好). 只收敛固定键, 永不记录用户自由文本.
    """
    target = {"cdn": True, "video": True, "spoof": "", "snapshot": "",
              "softwall": "", "http": False, "insecure": False, "lock": False}
    changes = []
    try:
        for k, v in target.items():
            try:
                old = opts.get(k)
            except Exception:
                continue
            if old != v:
                try:
                    opts[k] = v
                except Exception:
                    continue
                changes.append("%s: %r→%r" % (k, old, v))
    except Exception:
        pass
    return changes


def make_session(site):
    """下载会话: curl_cffi(chrome指纹)优先, 自检失败回落requests(每进程只警告一次).

    bot 伪装强制走 requests(_tls_kind_for); mobile 伪装同步
    Sec-CH-UA-Mobile=?1 与 Platform=Android, 保头身份一致.
    """
    global _TLS_WARNED
    try:
        sp = site.spoof_mode()
        preset = SPOOF_PRESETS.get(sp, {})
    except Exception:
        preset = {}
    try:
        _al = _accept_language_of(site)
    except Exception:
        _al = "zh-CN,zh;q=0.9,en;q=0.8"
    headers = {
        "User-Agent": site.UA,
        "Accept-Language": _al,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,*/*;q=0.8",
        "Sec-CH-UA": _sec_ch_ua(site.UA),
        "Sec-CH-UA-Mobile": "?1" if preset.get("mobile") else "?0",
        "Sec-CH-UA-Platform": preset.get("platform") or '"Windows"',
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    p, _ = eff_proxy(site)
    proxies = {"http": p, "https": p} if p else {}
    kind = "requests"
    use_tls_spoof = _tls_kind_for(site) == "curl_cffi"
    if not use_tls_spoof:
        if not _TLS_WARNED:
            site.log("WARNING bot伪装无TLS指纹(强制requests): 易被识别, "
                     "建议只配合快照/文本代理用")
            _TLS_WARNED = True
        s = requests.Session()
    else:
        try:
            from curl_cffi import requests as cr
            imp = _pick_impersonate(site.UA)
            try:
                _major = int((re.search(r"Chrome/(\d+)",
                                        site.UA or "") or [0, 0])[1])
            except Exception:
                _major = 0
            if _major > 150:
                site.log("WARNING UA超前指纹库(Chrome/%d>150): 用最高 preset, "
                         "易被识别, 建议升级curl_cffi" % _major)
            s = cr.Session(impersonate=imp)
            kind = "curl_cffi:" + imp
        except Exception as e:
            if not _TLS_WARNED:
                site.log("WARNING TLS伪装不可用(回落requests): %s" % str(e)[:100])
                _TLS_WARNED = True
            s = requests.Session()
    try:
        s.headers.update(headers)
    except Exception as e:
        site.log("WARNING 会话头设置失败: %s" % str(e)[:80])
    try:
        s.proxies.update(proxies)
    except Exception as e:
        site.log("WARNING 代理注入会话失败: %s" % str(e)[:80])
    try:
        s.verify = site.tls_verify()
    except Exception as e:
        site.log("WARNING TLS校验设置失败: %s" % str(e)[:80])
    try:
        s.trust_env = False
    except Exception as e:
        site.log("WARNING trust_env 设置失败(环境变量可能旁路代理): %s" % str(e)[:80])
    try:  # wait->dl 会话交接: cookies.txt -> Cookie 头(值永不落日志, 解析夹紧防投毒)
        _ck = _load_cookie_pairs(site)
        if _ck:
            s.headers.update({"Cookie": "; ".join("%s=%s" % kv for kv in _ck)})
    except Exception:
        pass
    try:
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
    loc, _tz = _locale_of(site)
    kw = dict(persistent_context=True, user_data_dir=prof, headless=headless,
              os="windows", locale=loc, block_webrtc=True, humanize=True,
              geoip=bool(proxy))
    if proxy:
        kw["proxy"] = {"server": proxy}
    cm = Camoufox(**kw)
    ctx = cm.__enter__()
    ctx._camoufox_cm = cm
    site._camoufox_cm = cm
    try:
        _seed_ctx_cookies(site, ctx)
    except Exception:
        pass
    return None, None, ctx, ctx.new_page()


def _eff_channel(site) -> str:
    """浏览器通道生效顺序: auto 重试覆盖 > 命令行 > 站点配置 > 默认."""
    try:
        o = (getattr(site, "_auto_channel", "") or "").strip().lower()
        if o:
            return o
    except Exception:
        pass
    try:
        return (_cfg_str(getattr(site.args, "browser", ""))
                or _cfg_str(site.cfg.get("browser", "")) or "").lower()
    except Exception:
        return ""


def _lock_held_by_other(site) -> bool:
    """会话锁是否被其他活进程持有(是则 auto 不重试, 重试也注定失败)."""
    try:
        with open(os.path.join(site.root, ".session.lock"),
                  encoding="utf-8") as f:
            holder = int((f.read() or "").strip().split()[0])
    except Exception:
        return False
    if holder == os.getpid():
        return False
    try:
        return bool(_pid_alive(holder))
    except Exception:
        return False


def open_ctx(site, headless: bool = True, proxy: str = ""):
    """打开浏览器上下文. 返回 (pw, browser, ctx, page); camoufox 通道 pw/browser 为 None.

    环境自适应: 指定通道缺失/启动失败自动回退 bundled chromium, 不直接崩.
    有代理时追加 WebRTC 内网 IP 封堵 flag.
    """
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    loc, tz = _locale_of(site)
    ch = _eff_channel(site)
    if ch == "camoufox":
        try:
            return _open_ctx_camoufox(site, headless, proxy)
        except Exception as e:
            site.log("WARNING camoufox 启动失败, 回退 chromium: %s" % str(e)[:100])
            ch = ""
    args = ["--disable-blink-features=AutomationControlled"]
    if proxy:
        args.append("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
    launch_kw = {"headless": headless, "args": args}
    if proxy:
        launch_kw["proxy"] = {"server": proxy}
    if ch in ("chrome", "edge"):
        launch_kw["channel"] = ch
    insecure = not site.tls_verify()

    def _boot_plain():
        browser = pw.chromium.launch(headless=headless, args=args,
                                     proxy=launch_kw.get("proxy"))
        ctx = browser.new_context(
            user_agent=site.UA, viewport=site.viewport, locale=loc,
            timezone_id=tz, ignore_https_errors=insecure)
        ctx.add_init_script(STEALTH_JS)
        try:
            _seed_ctx_cookies(site, ctx)
        except Exception:
            pass
        return pw, browser, ctx, ctx.new_page()

    try:
        if site.want_clone():
            prof = clone_profile_dir(site)
            ctx = pw.chromium.launch_persistent_context(
                prof, headless=headless, channel=launch_kw.get("channel"),
                user_agent=site.UA, viewport=site.viewport, locale=loc,
                timezone_id=tz, ignore_https_errors=insecure,
                proxy=launch_kw.get("proxy"))
            ctx.add_init_script(STEALTH_JS)
            try:
                _seed_ctx_cookies(site, ctx)
            except Exception:
                pass
            return pw, None, ctx, ctx.new_page()
        browser = pw.chromium.launch(**launch_kw)
        ctx = browser.new_context(
            user_agent=site.UA, viewport=site.viewport, locale=loc,
            timezone_id=tz, ignore_https_errors=insecure)
        ctx.add_init_script(STEALTH_JS)
        try:
            _seed_ctx_cookies(site, ctx)
        except Exception:
            pass
        return pw, browser, ctx, ctx.new_page()
    except Exception as e:
        if ch in ("chrome", "edge") or site.want_clone():
            site.log("WARNING 指定浏览器通道失败, 回退 bundled chromium: %s"
                     % str(e)[:100])
            try:
                return _boot_plain()
            except Exception as e2:
                close_ctx(pw, None, None)
                raise e2
        close_ctx(pw, None, None)
        raise


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


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def _bezier_path(x0, y0, x1, y1, rng=None):
    """三次贝塞尔路径点列: 起终连线法线单侧取控制点(防 S 形), spread 随距离."""
    import math
    rng = rng or random
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy)
    if dist < 8:
        return [(x1, y1)]
    nx, ny = -dy / dist, dx / dist
    side = rng.choice((-1.0, 1.0))
    spread = dist * rng.uniform(0.08, 0.2)
    j1 = rng.uniform(0.25, 0.45) * side * spread
    j2 = rng.uniform(0.25, 0.45) * side * spread
    c1 = (x0 + dx * 0.3 + nx * j1 * 3, y0 + dy * 0.3 + ny * j1 * 3)
    c2 = (x0 + dx * 0.7 + nx * j2 * 3, y0 + dy * 0.7 + ny * j2 * 3)
    n = max(25, min(110, int(dist / 8)))
    pts = []
    for i in range(1, n + 1):
        t = _ease_in_out(i / n)
        mt = 1.0 - t
        x = mt**3 * x0 + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t**3 * x1
        y = mt**3 * y0 + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t**3 * y1
        pts.append((x, y))
    return pts


def human_click(page, locator, timeout: int = 8000) -> bool:
    """拟人点击: 等可见 -> 贝塞尔路径(单侧控制点+ease速度) -> 远距偶发过冲修正 ->
    落点抖动+终点微颤 -> 思考停顿 -> 点."""
    try:
        locator.wait_for(state="visible", timeout=timeout)
        try:
            box = locator.bounding_box()
        except Exception:
            box = None
        if box:
            vw = box.get("width", 0) or 0
            vh = box.get("height", 0) or 0
            px = box["x"] + vw * random.uniform(0.3, 0.7)
            py = box["y"] + vh * random.uniform(0.3, 0.7)
            try:
                sx, sy = 120.0, 300.0
                try:
                    pos = page.mouse._pos if hasattr(page.mouse, "_pos") else None
                    if pos:
                        sx, sy = float(pos[0]), float(pos[1])
                except Exception:
                    pass
                import math
                dist = math.hypot(px - sx, py - sy)
                for x, y in _bezier_path(sx, sy, px, py):
                    try:
                        page.mouse.move(x, y)
                    except Exception:
                        break
                if dist > 500 and random.random() < 0.3:
                    try:  # 过冲后回拉修正
                        page.mouse.move(px + random.uniform(6, 14),
                                        py + random.uniform(-4, 4))
                        think(page, 120)
                        page.mouse.move(px, py)
                    except Exception:
                        pass
                for _ in range(random.randint(3, 5)):  # 终点微颤
                    try:
                        page.mouse.move(px + random.uniform(-1.5, 1.5),
                                        py + random.uniform(-1.5, 1.5))
                    except Exception:
                        break
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
def detect_verify(page, site=None) -> bool:
    """验证检测: 命中选择器即需人工. 只返布尔; 命中的选择器记 site._last_verify_sel."""
    sels = list(VERIFY_SELECTORS)
    try:
        if site is not None:
            sels += _cfg_list(site.cfg.get("extra_verify_selectors"))
    except Exception:
        pass
    for sel in sels:
        try:
            if page.query_selector(sel):
                try:
                    if site is not None:
                        site._last_verify_sel = sel
                except Exception:
                    pass
                return True
        except Exception:
            pass
    try:
        if site is not None:
            site._last_verify_sel = ""
    except Exception:
        pass
    return False


# ================================================================ 路径三: 客户端干预
# 只操作已加载 DOM, 不发额外请求. strip 删遮罩+解滚动锁(上限50节点,
# 误伤自负, 默认 off); reader 只回传计数(标题/段数/字数), 正文不出页面.
JS_SOFTWALL_STRIP = (
    "() => { const out = {removed: 0, unlocked: false};"
    " try { const all = document.querySelectorAll('*');"
    " for (const el of all) {"
    " const cn = (typeof el.className === 'string') ? el.className : '';"
    " const s = cn + ' ' + (el.id || '');"
    " if (/paywall|metering|subscription-wall|subs-gate|regwall/i.test(s)) {"
    " el.remove(); out.removed++;"
    " if (out.removed > 50) break; } } } catch (e) {}"
    " try { for (const t of [document.documentElement, document.body]) {"
    " if (!t) continue;"
    " const st = window.getComputedStyle(t);"
    " if (st && st.overflow === 'hidden')"
    " { t.style.overflow = 'auto'; out.unlocked = true; } } }"
    " catch (e) {} return out; }"
)
JS_SOFTWALL_READER = (
    "() => { let title = '';"
    " try { title = (document.title || '').slice(0, 80); } catch (e) {}"
    " let paras = 0, chars = 0;"
    " try { const ps = document.querySelectorAll("
    "'article p, main p, .post-content p, .article-body p');"
    " for (const e of ps) { const t = (e.innerText || '').trim();"
    " if (t.length > 20) { paras++; chars += t.length; } } }"
    " catch (e) {}"
    " return {title: title, paras: paras, chars: chars}; }"
)


def apply_softwall(page, site):
    """路径三执行: 返回 {mode, removed, unlocked, paras, chars, title_len}.

    reader 的 title 只记长度不记内容(防正文落日志); 全程 try 包裹,
    浏览器异常不中断主流程.
    """
    res = {"mode": "", "removed": 0, "unlocked": False,
           "paras": 0, "chars": 0, "title_len": 0}
    try:
        mode = site.softwall_mode()
    except Exception:
        return res
    res["mode"] = mode
    if not mode:
        return res
    try:
        if mode == "strip":
            d = page.evaluate(JS_SOFTWALL_STRIP) or {}
            res["removed"] = int(d.get("removed", 0) or 0)
            res["unlocked"] = bool(d.get("unlocked", False))
            site.bump("softwall_stripped")
        elif mode == "reader":
            d = page.evaluate(JS_SOFTWALL_READER) or {}
            res["paras"] = int(d.get("paras", 0) or 0)
            res["chars"] = int(d.get("chars", 0) or 0)
            res["title_len"] = len(str(d.get("title", "") or ""))
            site.bump("softwall_reader")
    except Exception:
        pass
    return res


def log_softwall(site, res) -> None:
    """干预结果日志: 只记数字, 正文零落盘零落日志."""
    try:
        if res.get("mode") == "strip":
            site.log("软墙干预(strip): 移除遮罩%d 滚动解锁=%s" %
                     (res.get("removed", 0), res.get("unlocked", False)))
        elif res.get("mode") == "reader":
            site.log("软墙干预(reader): 段落%d 字符%d(正文不出页面)" %
                     (res.get("paras", 0), res.get("chars", 0)))
    except Exception:
        pass


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
        _rsel = site_rules(site).get("detail_link_selector") or []
    except Exception:
        _rsel = []
    for _sel in _rsel:
        try:
            for _el in (page.query_selector_all(_sel) or [])[:200]:
                try:
                    _h = _el.get_attribute("href") or ""
                    _t = (_el.inner_text() or "").strip()[:24]
                except Exception:
                    continue
                _u = norm_link(site, page.url, _h)
                if not _u or _u in seen or not site.column_ok(_u):
                    continue
                seen.add(_u)
                out.append((_clean_nav_text(_t) or "(无标题)", _u))
        except Exception:
            continue
    if out:
        return out
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
        _site = getattr(page, "_site_ref", None)
        _nsel = site_rules(_site).get("next_page_selector") or [] if _site else []
    except Exception:
        _nsel = []
    for _sel in _nsel:
        try:
            _el = page.query_selector(_sel)
            if _el:
                _u = norm_link_from(page, url, _el.get_attribute("href") or "")
                if _u:
                    return _u
        except Exception:
            continue
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


# 外部引擎 SHA256 pin 表(tools/ 劫持防御): 有条目即校验, 不符回 "".
# 填入你信任的二进制哈希后, 同目录投毒即失效. 为空 = 不校验(默认, 保持开箱可用).
# 生成: python -X utf8 -c "import hashlib;print(hashlib.sha256(open('tools/yt-dlp.exe','rb').read()).hexdigest())"
ENGINE_SHA256 = {}

TOOLS_DIR = os.environ.get("AUTO_SITE_DL_TOOLS", "tools")


def _verify_exe(path: str, name: str) -> bool:
    want = ENGINE_SHA256.get(name, "")
    if not want:
        return True
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest().lower() == want.lower()
    except Exception:
        return False


def find_exe(names):
    """外部引擎查找: tools/ -> PATH. 禁自动下载/更新. tools/ 命中须过 pin 表."""
    if isinstance(names, str):
        names = [names]
    for n in names:
        p = os.path.join(TOOLS_DIR, n)
        if os.path.isfile(p) and _verify_exe(p, n):
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
    if t[:1] in ("＝", "＋", "－", "＠", "｜", "／"):
        return "'" + s
    return s


def record(site, url: str, path: str, source: str = "list", sha256: str = "") -> None:
    size = os.path.getsize(path) if os.path.isfile(path) else 0
    new = not os.path.isfile(site.invf)
    try:
        digest = sha256 or hash_file(path)
        with open(site.invf, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["url", "file", "bytes", "sha256", "source"])
            w.writerow([_csv_safe(url_for_log(url)), _csv_safe(os.path.basename(path)),
                        size, digest, _csv_safe(source)])
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


def _sess_proxy(sess) -> str:
    try:
        return (getattr(sess, "proxies", {}) or {}).get("https", "") or ""
    except Exception:
        return ""


def _peer_enforced(site, proxy: str) -> bool:
    """对端分级: 自建可信代理(proxy_trusted)同样验对端 IP;
    公共代理豁免并记 peer-skipped(可审计)."""
    if not proxy:
        return False
    try:
        trusted = _cfg_list(site.cfg.get("proxy_trusted"))
    except Exception:
        trusted = []
    if proxy in trusted:
        return True
    try:
        site.bump("peer-skipped")
    except Exception:
        pass
    return False


def session_fresh(site):
    """会话 TTL: cookies.txt 按 mtime 计龄, 超 session_ttl_h(默认24)即过期."""
    try:
        ttl = float(site.cfg.get("session_ttl_h", 24) or 24)
    except Exception:
        ttl = 24.0
    try:
        age_h = (time.time() - os.path.getmtime(site.ckf)) / 3600.0
    except Exception:
        return True, -1.0
    return age_h <= ttl, age_h


def _perm_too_open(path: str) -> bool:
    """会话/配置权限过宽嗅探(纯防御): posix 下组/其他可读写即 True; Windows/异常即 False."""
    try:
        st = os.stat(path)
        return bool(st.st_mode & 0o077)
    except Exception:
        return False


def _check_session_perms(site) -> None:
    """启动时检查: ckf 过宽则 WARNING; profile 目录同理只 WARNING(不做 ACL)."""
    try:
        if os.path.isfile(site.ckf) and _perm_too_open(site.ckf):
            site.log("WARNING 会话文件权限过宽(组/其他可读): %s 建议 chmod 600" % site.ckf)
            site.bump("session-perm-open")
    except Exception:
        pass
    try:
        prof = getattr(site, "prof", "")
        if prof and os.path.isdir(prof) and _perm_too_open(prof):
            site.log("WARNING 浏览器 profile 目录权限过宽: %s 不做 ACL, 仅提示" % prof)
            site.bump("profile-perm-open")
    except Exception:
        pass


def _pid_alive(pid: int) -> bool:
    """跨平台进程存活嗅探(纯本地, 无网络). 判不准时按"存活"处理(fail closed)."""
    try:
        pid = int(pid)
    except Exception:
        return True
    if pid == os.getpid():
        return True
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                             wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            h = kernel32.OpenProcess(0x1000, False, pid)
            if not h:
                return False
            try:
                return True
            finally:
                kernel32.CloseHandle(h)
        except Exception:
            return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return True


def _drop_session_lock(root: str) -> None:
    """释放会话锁: 只删自己持有的(文件内PID==当前PID才删, 防误释他人锁)."""
    try:
        lock = os.path.join(root, ".session.lock")
        with open(lock, encoding="utf-8") as f:
            holder = int((f.read() or "").strip().split()[0])
        if holder == os.getpid():
            os.remove(lock)
    except Exception:
        pass


def _take_session_lock(site) -> bool:
    """--lock-session 独占 + 崩溃自愈:
    sites/<host>/.session.lock(O_CREAT|O_EXCL, 内写持有者PID), 成功后 atexit 释放;
    已存在时: 持有者是自己→True; 持有者已死→删陈旧锁后重取(崩溃/杀进程自愈);
    持有者存活→False. 取锁失败不抛异常(调用方按 False 退出).
    """
    try:
        lock = os.path.join(site.root, ".session.lock")
    except Exception:
        return True
    try:
        import atexit
    except Exception:
        atexit = None
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("utf-8", "ignore"))
        finally:
            os.close(fd)
        try:
            if atexit is not None:
                atexit.register(_drop_session_lock, site.root)
        except Exception:
            pass
        return True
    except FileExistsError:
        pass
    except Exception:
        return True
    try:
        with open(lock, encoding="utf-8") as f:
            holder = int((f.read() or "").strip().split()[0])
    except Exception:
        return False
    if holder == os.getpid():
        return True
    if _pid_alive(holder):
        return False
    try:
        os.remove(lock)
    except Exception:
        return False
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("utf-8", "ignore"))
        finally:
            os.close(fd)
        try:
            if atexit is not None:
                atexit.register(_drop_session_lock, site.root)
        except Exception:
            pass
        return True
    except Exception:
        return False


# ================================================================ 自我学习(本地进化, 有限制)
# 限制(写死): 只存本站 learn.json, 不含 URL/Cookie/头/正文, 无外发;
# schema 固定 + 取值夹紧, 版本错配整节丢弃; --no-learn / cfg learn:false 一键全关.
LEARN_VERSION = 1
LEARN_FILE = "learn.json"


def learn_on(site) -> bool:
    """学习总开关: 默认开; --no-learn 或 cfg learn:false 即全关."""
    try:
        if getattr(site.args, "no_learn", False):
            return False
    except Exception:
        pass
    try:
        return bool(site.cfg.get("learn", True))
    except Exception:
        return True


def _learn_path(site) -> str:
    return os.path.join(site.root, LEARN_FILE)


def _clamp_learn(raw) -> dict:
    """学习档案清洗: 非 dict/版本错配回默认; 数值夹紧; 引擎榜只留前 8."""
    d = {"version": LEARN_VERSION, "delay": 1.2, "engine_hits": {},
         "last_challenge": "", "fails_429": 0, "updated": 0}
    try:
        if not isinstance(raw, dict) or raw.get("version") != LEARN_VERSION:
            return d
        try:
            d["delay"] = round(max(0.2, min(10.0, float(raw.get("delay", 1.2)))), 1)
        except Exception:
            pass
        try:
            hits = raw.get("engine_hits") or {}
            clean = {}
            for k, v in hits.items():
                if isinstance(k, str) and len(k) <= 32:
                    clean[k[:32]] = max(0, min(9999, int(v)))
            d["engine_hits"] = dict(sorted(clean.items(),
                                           key=lambda kv: -kv[1])[:8])
        except Exception:
            pass
        try:
            lc = str(raw.get("last_challenge", "") or "")[:32]
            d["last_challenge"] = lc if re.fullmatch(r"[A-Za-z0-9_\-]+", lc) else ""
        except Exception:
            pass
        try:
            d["fails_429"] = max(0, min(999999, int(raw.get("fails_429", 0))))
        except Exception:
            pass
        try:
            d["updated"] = max(0, min(9999999999, int(raw.get("updated", 0))))
        except Exception:
            pass
    except Exception:
        pass
    return d


def load_learn(site) -> dict:
    try:
        with open(_learn_path(site), encoding="utf-8") as f:
            return _clamp_learn(json.load(f))
    except Exception:
        return _clamp_learn(None)


def save_learn(site) -> None:
    """收尾落盘: 计数器回填(fails_429/ App 本轮挑战) + 时间戳. 关了就不写."""
    try:
        if not learn_on(site):
            return
        d = _clamp_learn(getattr(site, "learn", None))
        try:
            d["fails_429"] = max(d["fails_429"],
                                 int(site.counters.get("retry_429", 0) or 0))
        except Exception:
            pass
        try:
            best, bestn = "", 0
            for k, v in (site.counters or {}).items():
                if k.startswith("challenge-") and int(v or 0) > bestn:
                    best, bestn = k, int(v)
            if best:
                d["last_challenge"] = best[:32]
        except Exception:
            pass
        try:
            import time as _t
            d["updated"] = int(_t.time())
        except Exception:
            pass
        with open(_learn_path(site), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, sort_keys=True)
    except Exception:
        pass


def learn_hit(site, engine: str) -> None:
    """引擎命中记账(内存, 收尾落盘): 只记引擎名, 上限 8 名."""
    try:
        if not learn_on(site) or not engine:
            return
        eh = dict((site.learn or {}).get("engine_hits", {}) or {})
        eh[engine] = min(9999, int(eh.get(engine, 0) or 0) + 1)
        site.learn["engine_hits"] = dict(sorted(eh.items(),
                                                key=lambda kv: -kv[1])[:8])
    except Exception:
        pass


def apply_learn(site) -> None:
    """开工应用: 学习延迟高于当前下限即采用并明示; 引擎榜只建议不强制."""
    try:
        if not learn_on(site):
            return
        try:
            cur = float(site.cfg.get("delay", 1.2) or 1.2)
        except Exception:
            cur = 1.2
        try:
            want = float((site.learn or {}).get("delay", 1.2) or 1.2)
        except Exception:
            want = 1.2
        if want > cur:
            site.cfg["delay"] = round(want, 1)
            site.log("LEARN 延迟自适应%.1fs(历史拥塞学到, cfg/开关可覆盖, --no-learn 关)"
                     % round(want, 1))
        try:
            hits = (site.learn or {}).get("engine_hits") or {}
            if hits:
                top = max(hits.items(), key=lambda kv: kv[1])[0]
                site.log("LEARN 引擎榜首%s(仅建议, 引擎链顺序不变)" % top)
        except Exception:
            pass
    except Exception:
        pass


def _note_mitm(site, reason: str, url: str) -> None:
    """MITM 异常信号: 只记账+单行日志, 永不阻断(防误杀)."""
    try:
        if site is not None:
            site.bump("mitm-signal")
            site.log("MITM-SIGNAL %s %s" % (reason, url_for_log(url)))
    except Exception:
        pass


# ================================================================ 攻击侧自测(默认全关, 仅自有/授权站)
def _cert_fp(host: str, port: int = 443, timeout: int = 10) -> str:
    """取对端证书 SHA256(只指纹不校验, 标准库直连, 不走代理).

    失败回 "". 纯探测, 不发送应用数据.
    """
    try:
        import socket as _so
        import ssl as _ssl
        ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        s = _so.create_connection((host, port), timeout=timeout)
        try:
            t = ctx.wrap_socket(s, server_hostname=host)
            try:
                der = t.getpeercert(binary_form=True)
            finally:
                try:
                    t.close()
                except Exception:
                    pass
        except Exception:
            try:
                s.close()
            except Exception:
                pass
            return ""
    except Exception:
        return ""
    try:
        return hashlib.sha256(der).hexdigest() if der else ""
    except Exception:
        return ""


def _load_pin(site) -> set:
    try:
        with open(site._pinfile(), encoding="utf-8") as f:
            return {x.strip().lower() for x in f if len(x.strip()) == 64}
    except Exception:
        return set()


def _save_pin(site, fps: set) -> None:
    try:
        with open(site._pinfile(), "w", encoding="utf-8") as f:
            for x in sorted(fps):
                f.write(x + "\n")
        _chmod_0600(site._pinfile())
    except Exception:
        pass


def _hijack_check(site) -> None:
    """TOFU 证书钉扎: 首见保存并 TOFU 信任; 变更只 WARNING+记账, 不阻断.

    CDN 轮换/站方换证会误报, 误报后人工确认用 --repin 加钉.
    """
    try:
        p = urlsplit(site.url)
    except Exception:
        return
    if (p.scheme or "").lower() != "https":
        return
    try:
        port = p.port or 443
    except Exception:
        port = 443
    fp = _cert_fp(site.host, port)
    if not fp:
        site.bump("hijack-skipped")
        site.log("劫持检测跳过(证书直连失败, 可能需代理环境)")
        return
    pins = _load_pin(site)
    if not pins:
        _save_pin(site, {fp})
        site.bump("hijack-pinned")
        site.log("证书首钉(TOFU): %s… 已信任当前证书, 变更会告警" % fp[:16])
        return
    if getattr(getattr(site, "args", None), "repin", False):
        pins.add(fp)
        _save_pin(site, pins)
        site.bump("hijack-repinned")
        site.log("证书重钉: 已信任 %s…(共%d个, 你确认过站方换证)" % (fp[:16], len(pins)))
        return
    if fp not in pins:
        site.bump("hijack-cert-changed")
        site.log("WARNING 证书变更(可能被劫持/MITM/站方换证/CDN轮换): "
                 "当前%s… 与钉扎不符, 请人工确认, 确认合法后用 --repin 加钉" % fp[:16])


def _probe_page(site, sess, url: str):
    """只读探测一页: 返回 (status, 正文长度). 正文只内存计数."""
    try:
        r, _, st = _fetch_guarded(sess, url, site.url, "text/html")
        if r is None:
            return st, -1
        try:
            n = len(_read_capped(r, 65536))
        finally:
            _snap_close(r)
        return st, n
    except Exception:
        return 0, -1


def _diff_significant(st1, ln1, st2, ln2) -> bool:
    if st1 != st2:
        return True
    if ln1 < 0 or ln2 < 0:
        return False
    try:
        base = max(ln1, ln2, 1)
        return abs(ln1 - ln2) / float(base) > 0.05
    except Exception:
        return False


def cmd_replay(site) -> int:
    """cookie 重放自测(只读 GET, 仅自有/授权站).

    三步: 匿名 vs 带 cookie(特权差异?) -> 带 cookie 换 UA 重放(会话绑定?).
    Cookie 永不落日志, 只比较状态码与正文长度. 不下载媒体, 不改任何状态.
    """
    site.log("TARGET=%s MODE=replay(只读自测)" % site.url)
    site.log("WARNING 重放自测仅限自有/已授权站点; 本次只发 GET, 不下载媒体, Cookie 不落日志")
    try:
        with open(site.ckf, encoding="utf-8") as f:
            raw = f.read().strip()
    except Exception:
        raw = ""
    if not raw or len(raw) < 8:
        site.log("无会话(先跑 wait). 退出.")
        return 3
    if preflight(site) == 2:
        return 2
    sessA, _ = make_session(site)
    try:
        sessA.headers.update({"Cookie": raw})
    except Exception:
        pass
    sessB, _ = make_session(site)
    stA, lnA = _probe_page(site, sessA, site.url)
    stB, lnB = _probe_page(site, sessB, site.url)
    if lnA < 0 or lnB < 0:
        site.log("REPLAY-INCONCLUSIVE 探测失败(匿名%d/带券%d), 查网络后重跑" % (stB, stA))
        return 0
    if not _diff_significant(stA, lnA, stB, lnB):
        site.log("REPLAY-SAME 带券与匿名无差异(该页公开或会话已失效, 可换需登录页重测)")
        return 0
    site.log("REPLAY-DIFF 带券(%d,%dB) vs 匿名(%d,%dB): 会话携带特权" % (stA, lnA, stB, lnB))
    site.bump("replay-diff")
    try:
        site.pick_identity()
    except Exception:
        pass
    sessC, _ = make_session(site)
    try:
        sessC.headers.update({"Cookie": raw})
    except Exception:
        pass
    stC, lnC = _probe_page(site, sessC, site.url)
    if lnC >= 0 and not _diff_significant(stA, lnA, stC, lnC):
        site.log("REPLAY-UNBOUND 换 UA/指纹重放仍等效: 该站会话未绑定客户端特征, "
                 "cookie 失窃即被冒用(自有站请加绑定/短 TTL)")
        site.bump("replay-unbound")
    else:
        site.log("REPLAY-BOUND 换身份后响应变化: 该站可能做了会话绑定(好事), 以人工复核为准")
        site.bump("replay-bound")
    return 0


def _sec_fetch_for(url: str, referer: str, accept: str) -> dict:
    """媒体子资源 Sec-Fetch 覆盖: 同站 same-origin, 跨站 cross-site.

    Mode 恒 no-cors(子资源非导航); Dest 按 Accept 映射 video/image/empty.
    同源判定用主机全等(子域视 cross-site, 偏保守但无指纹风险).
    """
    try:
        th = (urlsplit(url).hostname or "").lower().rstrip(".")
    except Exception:
        th = ""
    try:
        rh = (urlsplit(referer or "").hostname or "").lower().rstrip(".")
    except Exception:
        rh = ""
    sf_site = "same-origin" if (th and rh and th == rh) else "cross-site"
    try:
        a = (accept or "").lower()
    except Exception:
        a = ""
    if a.startswith("video/"):
        dest = "video"
    elif a.startswith("image/"):
        dest = "image"
    else:
        dest = "empty"
    return {"Sec-Fetch-Site": sf_site, "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Dest": dest}


def _fetch_guarded(sess, url: str, referer: str, accept: str, max_hops: int = 5,
                   enforce_peer: bool = False, site=None):
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
            _hdrs = {"Referer": referer, "Accept": accept}
            try:
                _hdrs.update(_sec_fetch_for(cur, referer, accept))
            except Exception:
                pass
            try:
                _h = (urlsplit(cur).hostname or "").lower().rstrip(".")
            except Exception:
                _h = ""
            try:
                if site is not None and _h:
                    for _k, _v in (site.extra_headers_for(_h) or {}).items():
                        if _k.lower() not in (k.lower() for k in _hdrs):
                            _hdrs[_k] = _v
            except Exception:
                pass
            r = sess.get(cur, headers=_hdrs,
                         timeout=30, stream=True, allow_redirects=False)
        except Exception:
            return None, cur, -2
        try:
            status = getattr(r, "status_code", 0)
            if not isinstance(status, int) or isinstance(status, bool):
                status = 0  # 非 int 状态一律视为异常, 不信任
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
            nxt = urljoin(cur, loc.replace("\\", "/"))  # 与 norm_url 同语义, 防分裂
            if not re.match(r"^https?://", nxt):
                return None, cur, status  # javascript:/data:/file: 等直接拦
            cur = nxt
            continue
        if status != 200:
            if status == 403 and site is not None:
                try:
                    _hdrs = dict(getattr(r, "headers", None) or {})
                except Exception:
                    _hdrs = {}
                try:
                    _head = _read_capped(r, 4096)
                except Exception:
                    _head = ""
                try:
                    _kind, _hint = diagnose_http_challenge(
                        status, _hdrs, _head)
                    if _kind:
                        site.bump("challenge-" + _kind)
                        site.log("CHALLENGE %s kind=%s %s"
                                 % (url_for_log(cur), _kind, _hint))
                except Exception:
                    pass
            try:
                r.close()
            except Exception:
                pass
            return None, cur, status
        try:  # 响应头异常信号(只记不拦): 多 Set-Cookie 注入 / 超大 Content-Length
            _raw_hdrs = getattr(getattr(r, "raw", None), "headers", None)
            try:
                _nset = len(_raw_hdrs.getlist("Set-Cookie")) if _raw_hdrs is not None else 0
            except Exception:
                _nset = 0
            if _nset >= 4:
                _note_mitm(site, "multi-set-cookie=%d" % _nset, cur)
            try:
                _cl = int((getattr(r, "headers", None) or {}).get("Content-Length") or 0)
            except Exception:
                _cl = 0
            if _cl > 200 * 1048576:
                _note_mitm(site, "content-length-huge=%d" % _cl, cur)
        except Exception:
            pass
        if not _proxied(sess) or enforce_peer:
            if not _peer_is_public(r):
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


def _fetch_with_retry(site, sess, url: str, referer: str, accept: str,
                      enforce_peer: bool = False):
    """429/5xx 重试: 指数退避+抖动, 优先服从 Retry-After(封顶60s), 最多3次."""
    delays = [2.0, 4.0, 8.0]
    last = (None, url, 0)
    try:  # 路径一: 伪装 Referer 单点覆盖, 下游全链生效
        referer = site.ref_for(referer)
    except Exception:
        pass
    try:  # 对端分级自动接线: 可信代理验对端, 公共代理豁免+计数
        if _peer_enforced(site, _sess_proxy(sess)):
            enforce_peer = True
    except Exception:
        pass
    for i in range(4):
        r, final, status = _fetch_guarded(sess, url, referer, accept,
                                          enforce_peer=enforce_peer, site=site)
        if r is not None:
            return r, final, status
        if status in (403, 428):
            last = (None, final, status)
            break  # 留给下面的referer-fallback, 不进429/5xx退避
        if status not in (429, 500, 502, 503, 504):
            return None, final, status
        if i >= 3:
            return None, final, status
        try:
            site.note_congestion()
        except Exception:
            pass
        wait = delays[i] + random.random()
        site.bump("retry_%d" % status)
        time.sleep(min(wait, 60.0))
        last = (None, final, status)
    try:
        _, _, fb_status = last
    except Exception:
        fb_status = 0
    if fb_status in (403, 428):
        try:
            target_host = (urlsplit(url).hostname or "").lower()
        except Exception:
            target_host = ""
        try:
            ref_host = (urlsplit(referer or "").hostname or "").lower()
        except Exception:
            ref_host = ""
        if target_host and (not ref_host or ref_host != target_host):
            fb_referer = "https://%s/" % target_host
            r2, final2, status2 = _fetch_guarded(sess, url, fb_referer, accept,
                                                enforce_peer=enforce_peer)
            if r2 is not None:
                try:
                    site.bump("referer-fallback")
                except Exception:
                    pass
            return r2, final2, status2
    return last


def _safe_url_for_cmd(url: str) -> str:
    """subprocess 传参前最后一道: 必须 http(s):// 开头且无空白/控制符, 防 URL 即选项."""
    u = (url or "").strip()
    if not re.match(r"^https?://", u):
        return ""
    if re.search(r"\s|[\x00-\x1f\x7f]", u):
        return ""
    return u


_PL_MAX = 2 * 1048576  # 播放列表文本上限 2MB, 防内存 DoS
_PL_KEY_RE = re.compile(r"(?i)\buri\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^,\s>]+))")
_PL_SEG_EXT = (".ts", ".m4s", ".mp4", ".mov", ".webm", ".mkv", ".key", ".mpd")


# ================================================================ 路径二: 缓存快照
SNAPSHOT_DOMAINS = ("archive.ph", "archive.md", "archive.li", "archive.is")
_SNAP_BLOCK_RE = re.compile(
    r"just a moment|attention required|rate.{0,5}limit|too many requests"
    r"|access denied|cf-please-wait|challenge-platform|人机验证|访问受限",
    re.I,
)
_SNAP_MIN_HTML = 500  # 原始 HTML 下限(字节字符数), 太短必是错误页
_SNAP_MIN_TEXT = 200  # 去标签正文下限


def _read_capped(r, cap: int = 2097152) -> str:
    """流式读正文(上限封顶, 防内存 DoS). 失败返回空串."""
    data = b""
    try:
        for ch in r.iter_content(chunk=65536):
            if not ch:
                continue
            data += ch[:max(0, cap - len(data))]  # 精确封顶, 不超 cap
            if len(data) >= cap:
                break
    except Exception:
        pass
    try:
        return data.decode("utf-8", "ignore")
    except Exception:
        return ""


def _snap_text_ok(html: str) -> bool:
    """快照正文判定: 限流/验证页拒收, 去标签后须达下限."""
    if not html or len(html) < _SNAP_MIN_HTML:
        return False
    try:
        if _SNAP_BLOCK_RE.search(html[:20000]):
            return False
        txt = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ",
                     html, flags=re.I | re.S)
        txt = re.sub(r"\s+", " ", txt).strip()
        return len(txt) >= _SNAP_MIN_TEXT
    except Exception:
        return False


def _snap_close(r) -> None:
    try:
        r.close()
    except Exception:
        pass


def fetch_snapshot(site, sess, url: str):
    """路径二: 缓存快照只读探测. 返回 (ok, source, text_len).

    顺序: Wayback availability API -> archive.today 轮换域(/newest/, 前2域).
    每跳复用 _fetch_guarded(跳转守卫+SSRF+对端复检); 存档站走同一会话
    (代理/TLS/Referer 伪装全生效); 正文只在内存判定, 不落盘.
    """
    if not site.snapshot_mode():
        return False, "", 0
    mode = site.snapshot_mode()
    ref = site.url
    if mode in ("wayback", "auto"):
        try:
            api = ("https://archive.org/wayback/available?url=" +
                   quote(url, safe=""))
            r, _, st = _fetch_guarded(sess, api, ref, "application/json")
            surl = ""
            if r is not None and st == 200:
                try:
                    data = json.loads(_read_capped(r, 65536))
                finally:
                    _snap_close(r)
                try:
                    closest = (data.get("archived_snapshots") or {}).get(
                        "closest") or {}
                    surl = closest.get("url", "") or ""
                except Exception:
                    surl = ""
            if surl and re.match(r"^https?://", surl):
                r2, _, st2 = _fetch_guarded(sess, surl, ref, "text/html")
                if r2 is not None and st2 == 200:
                    try:
                        html = _read_capped(r2)
                    finally:
                        _snap_close(r2)
                    if _snap_text_ok(html):
                        return True, "wayback", len(html)
        except Exception:
            pass
        if mode == "wayback":
            return False, "", 0
    if mode in ("archive", "auto"):
        for d in SNAPSHOT_DOMAINS[:2]:
            try:
                r, _, st = _fetch_guarded(sess, "https://%s/newest/%s" % (d, url),
                                          ref, "text/html")
                if r is None or st != 200:
                    continue
                try:
                    html = _read_capped(r)
                finally:
                    _snap_close(r)
                if _snap_text_ok(html):
                    return True, d, len(html)
            except Exception:
                continue
    return False, "", 0


# ================================================================ 路径四: 一站式文本代理
def fetch_text_proxy(site, sess, url: str):
    """路径四: 通用文本代理只读探测. 返回 (ok, text_len).

    代理主机走 _fetch_guarded 全套守卫(SSRF/跳转/对端); 返回页复用
    _snap_text_ok 判定; 正文只内存判定不落盘; 日志只记数字.
    """
    if not site.text_proxy_base():
        return False, 0
    try:
        purl = site.text_proxy_url(url)
        if not purl:
            return False, 0
        r, _, st = _fetch_guarded(sess, purl, site.url, "text/html")
        if r is None or st != 200:
            return False, 0
        try:
            html = _read_capped(r)
        finally:
            _snap_close(r)
        if _snap_text_ok(html):
            return True, len(html)
    except Exception:
        pass
    return False, 0


def _playlist_guard_ok(site, sess, url: str, referer: str, depth: int = 2,
                       _seen=None) -> bool:
    """m3u8 播放列表守卫: 自取文本(2MB封顶), KEY/分片绝对地址逐条过 SSRF,
    子 playlist 递归跟进(深度≤2, 防 master->rendition->内网key).

    相对分片继承播放列表主机(已守卫). 引擎只负责下载, 不替我们做安全决策.
    """
    if _seen is None:
        _seen = set()
    if depth < 0 or url in _seen or len(_seen) >= 6:
        return depth >= 0 and url in _seen
    _seen.add(url)
    r, _, _ = _fetch_guarded(sess, url, referer, "*/*", site=site)
    if r is None:
        return False
    try:
        try:
            cl = int((r.headers or {}).get("Content-Length") or 0)
        except Exception:
            cl = 0
        if cl > _PL_MAX:
            return False
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > _PL_MAX:
                return False
        text = buf.decode("utf-8", "ignore")
    except Exception:
        return False
    finally:
        try:
            r.close()
        except Exception:
            pass
    head = text[:256].replace("﻿", "")
    if "#EXTM3U" not in head and "#extm3u" not in head.lower():
        return False
    bad = 0
    for m in _PL_KEY_RE.finditer(text):
        uri = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if not uri:
            continue
        u = urljoin(url, uri)  # 相对KEY继承播放列表URL, query由urljoin原样保留(不断query)
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
        if not re.match(r"^https?://", line):
            line = urljoin(url, line)  # 相对行继承播放列表URL(含token query原样保留)
            if not re.match(r"^https?://", line):
                continue
        low = line.lower().split("?")[0]
        if low.endswith(_PL_SEG_EXT):
            try:
                h = urlsplit(line).hostname or ""
            except Exception:
                h = ""
            if not h or not is_public_host(h):
                bad += 1
                if bad > 5:
                    break
        else:  # 疑似子 playlist: 递归跟进
            if not _playlist_guard_ok(site, sess, line, referer, depth - 1, _seen):
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
        if r is None and status == -2:
            try:  # 出口连败: 故障转移换代理重试一次
                if site.failover(sess):
                    r, final, status = _fetch_with_retry(site, sess, url, referer, acc)
            except Exception:
                pass
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
        CAP = 200 * (1 << 20)
        stem = re.sub(r"[^\w\-]+", "_", urlsplit(url).path.rsplit("/", 1)[-1]
                      .rsplit(".", 1)[0])[:80].strip("_") or "f"
        tmp = os.path.join(site.dl, "%05d_%s.part" % (idx, stem))
        h = hashlib.sha256()
        total = 0
        first = b""
        ext = None
        truncated = False
        discard = False
        try:
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    if not chunk:
                        continue
                    if ext is None:
                        if len(first) < 64:
                            first += chunk[:max(0, 64 - len(first))]
                        if len(first) >= 64:
                            # 首块满 64B 即验魔数, 非媒体早弃省带宽
                            ext = sniff_ext(first[:64])
                            if not ext or ext == ".m3u8":
                                discard = True
                                break
                    remain = CAP - total
                    if remain <= 0:
                        truncated = True
                        break
                    w = chunk[:remain]
                    f.write(w)
                    h.update(w)
                    total += len(w)
                    if total >= CAP:
                        truncated = True
                        break
        finally:
            try:
                r.close()
            except Exception:
                pass
        if discard:  # with 已退出(Windows 下开着的文件删不掉), 块外删
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            site.bump("skip_magic_early")
            site.note_fail(url, "nomagic")
            site.bump("skip_nomagic")
            return ""
        try:  # 声明与实收差一个量级(>10x 或 <0.1x)即信号, 不阻断
            _decl = int((getattr(r, "headers", None) or {}).get("Content-Length") or 0)
            if _decl > 0 and total > 0:
                _ratio = total / float(_decl)
                if _ratio > 10.0 or _ratio < 0.1:
                    _note_mitm(site, "length-mismatch decl=%d got=%d" % (_decl, total), url)
        except Exception:
            pass
        if total < 512:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            site.bump("skip_tiny")
            return ""
        if ext is None:
            ext = sniff_ext(first[:64])
        if not ext or ext == ".m3u8":
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            site.note_fail(url, "nomagic")
            site.bump("skip_nomagic")
            return ""
        final = os.path.join(site.dl, "%05d_%s%s" % (idx, stem, ext))
        try:
            os.replace(tmp, final)
        except Exception:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            return ""
        _chmod_0600(final)
        if truncated:
            site.bump("truncate")
        record(site, url, final, source, sha256=h.hexdigest())
        try:
            site.report_proxy(_sess_proxy(sess), True)
        except Exception:
            pass
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
        _chmod_0600(path)
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
        hk_uri, hk_iv = site.hls_key()
    except Exception:
        hk_uri, hk_iv = "", ""
    hk_raw = ("%s,%s" % (hk_uri, hk_iv)) if (hk_uri and hk_iv) else hk_uri
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
            if hk_uri:
                cmd += ["--custom-hls-key", hk_uri]
                if hk_iv:
                    cmd += ["--custom-hls-iv", hk_iv]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode == 0 and check_magic(final) == ".mp4":
                record(site, url, final, "m3u8:n_m3u8dl")
                learn_hit(site, "n_m3u8dl")
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
            if hk_raw:
                cmd += ["--hls-key", hk_raw]
            cmd += [url]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode == 0 and check_magic(final) == ".mp4":
                record(site, url, final, "m3u8:ytdlp")
                learn_hit(site, "ytdlp")
                return final
            err = (r.stderr or "").strip().splitlines()
            site.note_fail(url, "ytdlp:" + (err[-1][:100] if err else "rc=%s" % r.returncode))
            return ""
        exe = find_exe(["ffmpeg.exe", "ffmpeg"])
        if exe:
            global _HLS_FFMPEG_WARNED
            if hk_raw and not _HLS_FFMPEG_WARNED:
                try:
                    site.log("WARNING --hls-key 对 ffmpeg 无效, 已跳过"
                             "(仅 N_m3u8DL-RE/yt-dlp 生效)")
                except Exception:
                    pass
                _HLS_FFMPEG_WARNED = True
            cmd = [exe, "-y", "-i", url, "-c", "copy", final]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode == 0 and check_magic(final) == ".mp4":
                record(site, url, final, "m3u8:ffmpeg")
                learn_hit(site, "ffmpeg")
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
                try:  # 删前覆写清内容(防取证残留, cookie 小文件一次写可接受)
                    with open(ck, "r+b") as _f:
                        try:
                            _f.seek(0, 2)
                            _len = _f.tell()
                        except Exception:
                            _len = 0
                        try:
                            _f.seek(0)
                            _f.write(b"\x00" * min(_len, 1 << 20))
                            _f.flush()
                            os.fsync(_f.fileno())
                        except Exception:
                            pass
                except Exception:
                    pass
                os.remove(ck)
        except Exception:
            pass


# ================================================================ 页面收获
def _diag_snapshot(page, site):
    """diag 快照(只读零副作用): 标题/终址/正文体量/原始计数/验证态/沉降增量.

    只取计数与长度, 不落任何 URL 全串/正文/cookie: 标题去注行截断,
    终址经 url_for_log 脱敏到 path. 任何一步失败记默认值, 永不抛错.
    判读: raw 全 0=空壳页(精简/未渲染); raw 有数但媒体 0=全被过滤
    (blob:/data:/非媒体后缀); evaluate 整体失败 raw={} 即 JS 执行层问题.
    """
    snap = {"title": "", "final": "", "html_len": -1, "raw": {},
            "verify": "", "grew": 0}
    try:
        snap["title"] = _clean_nav_text(page.title())
    except Exception:
        pass
    try:
        snap["final"] = url_for_log(page.url)
    except Exception:
        pass
    try:
        snap["html_len"] = len(page.content() or "")
    except Exception:
        pass
    try:
        snap["raw"] = page.evaluate(
            "() => ({img: document.images.length, "
            "vid: document.querySelectorAll('video').length, "
            "src: document.querySelectorAll('source').length, "
            "a: document.querySelectorAll('a[href]').length})") or {}
    except Exception:
        snap["raw"] = {}
    try:
        _nv = detect_verify(page, site)
        snap["verify"] = getattr(site, "_last_verify_sel", "") if _nv else ""
    except Exception:
        pass
    try:
        snap["grew"] = settle_lazy_load(page, site)
    except Exception:
        pass
    return snap


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


_DIVE_KEY_RE = re.compile(r"detail|play|/vod/|/video/|watch|/p/")


def _same_host(site, url: str) -> bool:
    """同站判定(回退试探用, 防漫游站外): 主机全等即同站."""
    try:
        return (urlsplit(url).hostname or "").lower() == (site.host or "").lower()
    except Exception:
        return False


def deep_dive(page, site, sess, anchors, idx: int, budget: int,
              cap_bucket=None):
    """详情/观看页深挖: 每页至多2个, 全局预算封顶. 拿 video/source/m3u8 真流.

    两轮: 关键词命中优先; 零命中时回退试探同站前 2 个(门户页详情链无关键词
    时兜底, 如 /x/123.html 类; 同站约束防漫游, 同样走守卫/验证/预算, 记
    dive_fallback). 非标锚点不再抛错(直接跳过). 无锚点可跟记 dive_no_anchors.
    详情页加沉降(滚触发懒挂载播放器) + 即时排空网络捕获(不等下个列表迭代,
    无下页时不丢失; cap_bucket 传 net_cap, 消费即清).
    """
    got = []
    state = [0]  # 本页已跟进数(至多2)
    visited = set()
    matched = [0]
    if not anchors:
        try:
            site.bump("dive_no_anchors")
            site.log("详情无锚点可跟(页内无详情链, 真流只能靠列表直链/网络捕获)")
        except Exception:
            pass
        return got, False

    def _one(a):
        """跟进单个详情页. 返回 (reverify, descended)."""
        try:
            if a in visited:
                return False, False
            visited.add(a)
        except Exception:
            pass
        if not _browser_guard(site, a):
            return False, False
        try:
            page.goto(a, wait_until="domcontentloaded", timeout=30000)
            think(page, 800)
            settle_lazy_load(page, site)  # 滚触发懒挂载(播放器常此时才拉流)
        except Exception:
            return False, False
        nv = detect_verify(page, site)
        if nv:
            return True, False
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
        if cap_bucket is not None:  # 即时排空本页导航捕获(不等下个列表迭代)
            try:
                _drained = list(cap_bucket)
                del cap_bucket[:]
            except Exception:
                _drained = []
            for u in _drained:
                try:
                    if (u or "").lower().endswith(".m3u8"):
                        f = fetch_m3u8(site, u, idx[0], a)
                    else:
                        f = fetch_one(site, sess, u, idx[0], a, "deep")
                    if f:
                        got.append(f)
                        idx[0] += 1
                except Exception:
                    continue
        polite_sleep(site)
        return False, True

    for a in anchors or []:
        if state[0] >= 2 or budget[0] <= 0:
            break
        try:
            hit = bool(_DIVE_KEY_RE.search(a or ""))
        except Exception:
            continue
        if not hit:
            continue
        matched[0] += 1
        budget[0] -= 1
        state[0] += 1
        rv, _ = _one(a)
        if rv:
            return got, True
    if matched[0] <= 0 and anchors:
        same = []
        for a in anchors:
            try:
                if a and _same_host(site, a):
                    same.append(a)
            except Exception:
                continue
            if len(same) >= 2:
                break
        if same:
            try:
                site.bump("dive_fallback")
                site.log("详情回退: %d 个锚点无关键词命中, 试探同站前 %d 个"
                         % (len(anchors), len(same)))
            except Exception:
                pass
            for a in same:
                if state[0] >= 2 or budget[0] <= 0:
                    break
                budget[0] -= 1
                state[0] += 1
                rv, _ = _one(a)
                if rv:
                    return got, True
    return got, False


# ================================================================ 模式
def _goto(page, site, url: str) -> bool:
    """导航: 成功 True; 失败 False(已打 NAV-FAIL 日志, hint 落 site._last_nav_hint)."""
    if not _browser_guard(site, url):
        try:
            site._last_nav_hint = "内网目标已拦截"
        except Exception:
            pass
        return False
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return True
    except Exception as e:
        hint = diagnose_nav_error(str(e))
        try:
            site._last_nav_hint = hint
        except Exception:
            pass
        site.log("NAV-FAIL %s 诊断: %s" % (url_for_log(url), hint))
        return False


def _snapshot_intel(site, tail: str = "原站仍走 wait 验证") -> None:
    """路径二/四只读情报: 快照+文本代理探测, 只打日志不改变调用方结论. 永不抛错."""
    try:
        if not (site.snapshot_mode() or site.text_proxy_base()):
            return
        _ss, _ = make_session(site)
        if site.snapshot_mode():
            _ok, _src, _sz = fetch_snapshot(site, _ss, site.url)
            if _ok:
                site.log("快照可用(%s, 正文约%dKB): 仅情报参考, "
                         "%s" % (_src, _sz // 1024, tail))
            else:
                site.log("快照无可用存档")
        _tok, _tlen = fetch_text_proxy(site, _ss, site.url)
        if _tok:
            site.log("文本代理可用(正文约%dKB): 仅情报参考, "
                     "%s" % (_tlen // 1024, tail))
        elif site.text_proxy_base():
            site.log("文本代理无可用内容")
    except Exception:
        pass


def cmd_check(site) -> int:
    site.log("TARGET=%s MODE=check v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    p, _ = eff_proxy(site, "browser")
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
        if not _goto(page, site, site.url):
            return 2
        nv = detect_verify(page, site)
        if nv:
            why = getattr(site, "_last_verify_sel", "") or "?"
            site.log("CHECK %s -> VERIFY-NEEDED 需人工验证 (selector:%s)"
                     % (site.url, why))
            _snapshot_intel(site)  # 路径二/四: 快照+文本代理情报(只读探测, 不改变"需验证"结论)
            return 10
        site.log("CHECK %s -> OPEN 无验证, 可直接dl" % site.url)
        try:  # 路径三: 软墙情报(遮罩计数/正文规模, 不改变 OPEN 结论)
            log_softwall(site, apply_softwall(page, site))
        except Exception:
            pass
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
    p, _ = eff_proxy(site, "browser")
    pw, browser, ctx, page = open_ctx(site, False, p)
    try:
        if not _goto(page, site, site.url):
            try:
                input("页面未加载, 人工处理后回车继续(直接回车退出): ")
            except EOFError:
                return 2
        t0 = time.time()
        ok = False
        while time.time() - t0 < timeout:
            nv = detect_verify(page, site)
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
                _jar = "; ".join('%s=%s' % (c["name"], c["value"])
                                 for c in ctx.cookies())
                with open(site.ckf, "w", encoding="utf-8") as f:
                    f.write(_jar)
                _chmod_0600(site.ckf)
                try:  # 会话备份: 主文件被外部删除时兜底(只读回退, 建议重跑 wait)
                    _bak = site.ckf + ".bak"
                    with open(_bak, "w", encoding="utf-8") as f:
                        f.write(_jar)
                    _chmod_0600(_bak)
                except Exception:
                    pass
            except Exception as e:
                site.log("会话保存失败: %s" % str(e)[:100])
                return 1
            site.log("VERIFIED (%s) 会话已保存. 可运行 dl."
                     % (getattr(site, "_last_verify_sel", "") or "人工确认"))
            return 0
        site.log("TIMEOUT 未检测到验证.")
        return 1
    finally:
        close_ctx(pw, browser, ctx)


def cmd_dl(site, batch: int = 60, dl_jobs: int = 1) -> int:
    site.log("TARGET=%s MODE=dl v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    try:
        apply_learn(site)
    except Exception:
        pass
    if not _disk_ok(site.dl):
        site.log("WARNING 磁盘剩余不足500MB, 仍继续(可能中途失败)")
    if os.path.isfile(site.ckf):
        try:
            if os.path.getsize(site.ckf) < 8:
                site.log("会话为空, 先跑 wait.")
                return 3
        except Exception:
            pass
    try:
        fresh, age_h = session_fresh(site)
        if not fresh and age_h >= 0:
            site.log("会话已%0.1fh(超TTL), 建议重跑 wait 刷新. 继续用旧会话." % age_h)
            site.bump("session-stale")
    except Exception:
        pass
    sess, kind = make_session(site)
    site.log("下载层: " + kind)
    try:
        site.ensure_robots(sess)
    except Exception:
        pass
    p, _ = eff_proxy(site, "browser")
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
    except Exception as e:
        site.log("浏览器启动失败 诊断: " + diagnose_nav_error(str(e)))
        return 2
    try:  # rules 回退用: find_next 经 _site_ref 拿 site(失败不影响主流程)
        page._site_ref = site
    except Exception:
        pass
    idx = [_next_idx(site)]
    budget = [20]
    seen_page = set()
    net_cap = []  # 网络层响应捕获: 导航期间路过的流地址
    url = site.url
    stop_verify = False
    visited = 0
    try:
        _attach_capture(page, site, net_cap)
        for _ in range(max(1, batch)):
            if not url or url in seen_page:
                break
            if site.robot_denied(url):
                site.bump("skip_robots")
                break
            seen_page.add(url)
            if not _goto(page, site, url):
                break
            visited += 1
            settle_lazy_load(page, site)
            nv = detect_verify(page, site)
            if nv:
                site.log("REVERIFY 又出现验证, 停止. 请重跑 wait.")
                stop_verify = True
                break
            log_softwall(site, apply_softwall(page, site))  # 路径三: 遮罩挡收割先清
            media, anchors = harvest(page, site, url)
            if not media and not anchors:
                site.bump("harvest_zero")
                if site.counters.get("harvest_zero", 0) == 1:
                    site.log("WARNING 首个页面收割为0(无媒体无锚点): "
                             "可能被喂精简页(bot UA?)/未渲染, 可跑 diag 对照")
            for u in net_cap:  # 网络层捕获优先(播放器 JS 动态拉流 DOM 看不见)
                if u not in media:
                    media.append(u)
            net_cap.clear()
            media = sorted(set(media), key=lambda u: media_rank(u))
            try:
                _jobs_n = max(1, min(8, int(dl_jobs or 1)))
            except Exception:
                _jobs_n = 1
            if _jobs_n <= 1:
                for u in media:
                    if u.lower().endswith(".m3u8"):
                        if _TOKEN_Q_RE.search(u):
                            site.log("token短命即时下: %s" % url_for_log(u))
                        f = fetch_m3u8(site, u, idx[0], url)
                    else:
                        f = fetch_one(site, sess, u, idx[0], url, "list")
                    if f:
                        idx[0] += 1
                    polite_sleep(site, 0.4)
            else:  # 并发: 每 worker 独立会话(避开共享 sess 线程风险), 编号预取不断点
                from concurrent.futures import ThreadPoolExecutor
                from watchflow import LockedWriter as _DlLockedWriter
                _lw = _DlLockedWriter(site)
                _lw.idx[0] = idx[0]

                def _dl_one(_u):
                    _i = _lw.next_idx()
                    try:
                        _ss, _ = make_session(site)
                    except Exception:
                        _ss = sess
                    try:
                        if _u.lower().endswith(".m3u8"):
                            return fetch_m3u8(site, _u, _i, url, _ss)
                        return fetch_one(site, _ss, _u, _i, url, "list")
                    finally:
                        try:
                            if _ss is not sess:
                                _ss.close()
                        except Exception:
                            pass

                with ThreadPoolExecutor(max_workers=_jobs_n) as _ex:
                    _futs = [_ex.submit(_dl_one, _u) for _u in media]
                    for _f in _futs:
                        try:
                            _f.result()
                        except Exception:
                            pass
                        try:
                            polite_sleep(site, 0.4)
                        except Exception:
                            pass
                    try:  # 编号同步: worker 预取的最大值接回主计数, 跨页不断点不重号
                        idx[0] = max(idx[0], _lw.idx[0])
                    except Exception:
                        pass
            if site._video_first():
                _, reverify = deep_dive(page, site, sess, anchors, idx, budget,
                                        net_cap)
                if reverify:
                    site.log("REVERIFY 又出现验证, 停止. 请重跑 wait.")
                    stop_verify = True
                    break
            nxt = find_next(page, url)
            url = nxt if (nxt and nxt not in seen_page) else ""
            polite_sleep(site)
    finally:
        close_ctx(pw, browser, ctx)
    try:  # 末页网络捕获无下页可消费时不静默丢弃: 计数+指引(行为不变)
        if net_cap and not stop_verify:
            site.bump("net_remain")
            site.log("WARNING 网络捕获余 %d 条未消费(末页无下页): "
                     "若要深挖请跑 watch" % len(net_cap))
    except Exception:
        pass
    try:
        save_learn(site)
    except Exception:
        pass
    try:
        _dl_warn_empty(site, visited)
    except Exception:
        pass
    site.summary()
    return 4 if stop_verify else 0


AUTO_CHECK_TRIES = 3


def cmd_auto(site, batch: int = 60) -> int:
    """零配置自动驾驶: 用户只给网址+做人机验证+拿内容, 其余程序内部办.

    check 梯子(至多 3 次, 有界不死磕): 1照常; 2换身份束+退避(瞬时风控);
    3换浏览器通道(本机网络拦截常与通道代理配置有关, 真 Chrome 可能自带代理).
    梯子切到的通道会保留给后续 wait/dl 全程(跑完才清零), 不再 check 用完即丢.
    锁被其他活进程占用则不重试. 三振后: 配了快照/文本代理则只读情报兜底
    (不改变失败结论), 打处置 verdict 后返回原码. 成功仍走 wait/dl 老链.
    """
    site.log("TARGET=%s MODE=auto v%s" % (site.url, __version__))
    rc = 2
    for attempt in range(1, AUTO_CHECK_TRIES + 1):
        if attempt == 2:
            try:
                site.pick_identity()
                site.run_id = "%08x" % random.getrandbits(32)
                site.log("auto重试(%d/%d): 已换身份束" % (attempt, AUTO_CHECK_TRIES))
            except Exception:
                pass
        if attempt == 3:
            try:
                cur = (_cfg_str(getattr(site.args, "browser", "")) or "").lower()
                site._auto_channel = "chrome" if cur in ("", "chromium") else "chromium"
                site.pick_identity()
                site.run_id = "%08x" % random.getrandbits(32)
                site.log("auto重试(%d/%d): 换浏览器通道→%s"
                         % (attempt, AUTO_CHECK_TRIES, site._auto_channel))
            except Exception:
                pass
        rc = cmd_check(site)
        if rc != 2:
            break
        if attempt < AUTO_CHECK_TRIES:
            try:
                if _lock_held_by_other(site):
                    site.log("auto不重试: 会话锁被其他活进程占用, 等它做完再跑")
                    break
            except Exception:
                pass
            try:
                time.sleep(5 * attempt)
            except Exception:
                pass
    try:
        if rc == 10:
            rc = cmd_wait(site)
            if rc != 0:
                return rc
        elif rc != 0:
            try:
                if site.snapshot_mode() or site.text_proxy_base():
                    site.log("auto直连失败: 转快照/文本代理情报兜底(只读)")
                    _snapshot_intel(site, "原站直连失败")
            except Exception:
                pass
            try:
                _lh = getattr(site, "_last_nav_hint", "") or ""
            except Exception:
                _lh = ""
            try:
                if "证书" in _lh or "TLS" in _lh:
                    site.log("auto终止: 对端证书不可信(3次). 若确认是自家网络/代理CA, "
                             "可加 --insecure 重跑(跳过校验有中间人风险, "
                             "建议同时开 --hijack-check); 否则检查出口网络")
                elif "代理" in _lh:
                    site.log("auto终止: 代理链路失败(3次). 检查 --proxy 进程/端口/认证后重跑")
                else:
                    site.log("auto终止: 本机直连失败(3次). 请配 --proxy 代理后重跑, "
                             "或检查目标URL/出口网络")
                if not (site.snapshot_mode() or site.text_proxy_base()):
                    site.log("提示: 另可加 --snapshot wayback 碰运气(只读情报, 不下正文)")
            except Exception:
                pass
            return rc
        rc = cmd_dl(site, batch)
        try:
            save_learn(site)
        except Exception:
            pass
        return rc
    finally:
        try:
            site._auto_channel = ""
        except Exception:
            pass


def cmd_diag(site) -> int:
    site.log("TARGET=%s MODE=diag v%s" % (site.url, __version__))
    if preflight(site) == 2:
        return 2
    p, _ = eff_proxy(site, "browser")
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
        if not _goto(page, site, site.url):
            return 2
        _snap = _diag_snapshot(page, site)
        _raw = _snap.get("raw") or {}
        site.log("DIAG 页: 标题[%s] 终址 %s 正文%dB 验证=%s 沉降+%d"
                 % (_snap.get("title", ""), _snap.get("final", "?"),
                    _snap.get("html_len", -1),
                    _snap.get("verify") or "无", _snap.get("grew", 0)))
        site.log("DIAG 原始: img=%s vid=%s src=%s a=%s"
                 % (_raw.get("img", "?"), _raw.get("vid", "?"),
                    _raw.get("src", "?"), _raw.get("a", "?")))
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
    p, _ = eff_proxy(site, "browser")
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = open_ctx(site, True, p)
        if not _goto(page, site, site.url):
            return 2
        try:
            page._site_ref = site
        except Exception:
            pass
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


def cmd_verify(site) -> int:
    """离线自证(不联网): 按 inventory.csv 重算 sha256, 缺失/不符列出并记 verify-fail."""
    site.log("TARGET=%s MODE=verify(本地)" % site.url)
    rows = []
    try:
        with open(site.invf, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        site.log("VERIFY 无记账(inventory.csv 缺失)")
        return 2
    bad = 0
    for r in rows:
        try:
            fn = (r.get("file", "") or "").strip()
            want = (r.get("sha256", "") or "").strip().lower()
        except Exception:
            continue
        if not fn:
            continue
        path = os.path.join(site.dl, os.path.basename(fn))
        if not os.path.isfile(path):
            site.log("VERIFY-MISS %s" % fn)
            site.bump("verify-fail")
            bad += 1
            continue
        got = hash_file(path).lower()
        if not want or got != want:
            site.log("VERIFY-BAD %s 期望=%s 实测=%s" % (fn, want[:16], got[:16]))
            site.bump("verify-fail")
            bad += 1
    site.log("VERIFY 共%d行 异常%d" % (len(rows), bad))
    return 1 if bad else 0


UPDATE_REPO = "jjjjjjjjnnjnn/auto-site-dl"
UPDATE_API = "https://api.github.com/repos/%s/releases/latest" % UPDATE_REPO


def _ver_cmp(a: str, b: str) -> int:
    """纯函数版本号比较: 1/-1/0. 非法段按 0, 前导 v 忽略."""
    def _t(v):
        out = []
        for x in (v or "").strip().lstrip("vV").split("."):
            try:
                out.append(int("".join(c for c in x if c.isdigit()) or 0))
            except Exception:
                out.append(0)
        return (out + [0, 0, 0])[:3]
    ta, tb = _t(a), _t(b)
    return 1 if ta > tb else (-1 if ta < tb else 0)


def cmd_updatecheck(args=None) -> int:
    """更新检查(只通知, 永不下载/执行): 问 GitHub releases 最新 tag, 与本地比."""
    try:
        from i18n import set_lang as _set, _
        _set(getattr(args, "lang", "auto") or "auto")
    except Exception:
        def _(k, *a):
            try:
                return k % a if a else k
            except Exception:
                return k
    try:
        r = requests.get(UPDATE_API, timeout=15,
                         headers={"Accept": "application/vnd.github+json",
                                  "User-Agent": "auto-site-dl/%s" % __version__})
        tag = (r.json().get("tag_name", "") or "").strip()
    except Exception as e:
        print(_("upd_fail", str(e)[:80]))
        return 2
    if not tag:
        print(_("upd_fail", "empty tag"))
        return 2
    c = _ver_cmp(tag, __version__)
    if c > 0:
        print(_("upd_avail", tag, "v" + __version__))
    else:
        print(_("upd_ok", "v" + __version__))
    return 0


def _integrity_selfcheck():
    """完整性自检(轻量, 非 verify 替代): 入库 .py 的 LICENSE 头 + py_compile.

    诚实注明: 不做 hash, 对抗不了投毒, 只防文件损坏/AV 啃坏/半截写入.
    返回 (ok, note).
    """
    import py_compile
    base = os.path.dirname(os.path.abspath(__file__))
    files = ["site_crawler.py", "watchflow.py", "tui.py"]
    bad = []
    for name in files:
        p = os.path.join(base, name)
        try:
            with open(p, encoding="utf-8") as f:
                head = f.read(2048)
            if "SPDX-License-Identifier" not in head:
                bad.append(name + ":LICENSE头缺失")
                continue
            py_compile.compile(p, doraise=True)
        except Exception as e:
            bad.append("%s:%s" % (name, str(e)[:60]))
    if bad:
        return False, ";".join(bad)[:200]
    return True, "3个.py头+编译通过(非hash, 防损坏/AV误杀, 不防投毒)"


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
    drift = [x for x in verify_lock() if "≠" in x[2] or x[2] in ("未安装", "缺失", "不可用")]
    rep("版本锁定", not drift,
        "与requirements.lock一致" if not drift else "漂移:%s" % ",".join(
            "%s(%s->%s)" % (a, b, c) for a, b, c in drift))
    try:
        _iok, _inote = _integrity_selfcheck()
    except Exception:
        _iok, _inote = False, "自检异常"
    rep("完整性自检", _iok, _inote)
    st = tls_selftest()
    if st:
        cur = _pick_impersonate("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/150.0.0.0 Safari/537.36")
        rep("tls-presets", bool(st.get(cur)),
            "%d/%d可用, 当前%s" % (sum(1 for v in st.values() if v),
                                   len(st), cur if st.get(cur) else cur + "缺失"))
    else:
        rep("tls-presets", False, "curl_cffi 缺失")
    try:
        free_gb = shutil.disk_usage(os.getcwd()).free / (1 << 30)
        disk_note = "剩余%.1fGB" % free_gb
    except Exception:
        disk_note = "未知"
    rep("cpu/磁盘", True, "%s核/%s" % (os.cpu_count(), disk_note))
    rep("ipv6", _ipv6_available(), "本机v6可用" if _ipv6_available() else "仅v4(正常)")
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
                             "nav", "purge", "verify", "replay", "updatecheck",
                             "envcheck"])
    ap.add_argument("url", nargs="?", default="")
    ap.add_argument("batch", nargs="?", type=int, default=60)
    ap.add_argument("--allow-cdn", action="store_true")
    ap.add_argument("--allow-http", action="store_true")
    ap.add_argument("--proxy", default="")
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--lock-session", dest="lock_session", action="store_true",
                    help="会话独占锁(防他进程并发写cookies.txt, 抢锁失败退出码2)")
    ap.add_argument("--hijack-check", dest="hijack_check", action="store_true",
                    help="劫持检测: TOFU证书钉扎(默认关)")
    ap.add_argument("--repin", dest="repin", action="store_true",
                    help="证书重钉(人工确认合法后)")
    ap.add_argument("--lang", default="auto",
                    choices=["", "auto", "zh", "en"],
                    help="语言: auto=系统语言, 取不到回英语")
    ap.add_argument("--no-learn", dest="no_learn", action="store_true",
                    help="关闭自我学习(不读写learn.json)")
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
    ap.add_argument("--dl-jobs", type=int, default=3,
                    help="下载并发1-8, 0=按CPU自动(watch默认3; dl默认串行1, 显式传值才并发)")
    ap.add_argument("--spoof", default="",
                    choices=["", "off", "googlebot", "bingbot", "mobile"],
                    help="请求伪装: googlebot/bingbot/mobile(默认off, 桌面池)")
    ap.add_argument("--spoof-referer", default="",
                    help="伪装Referer(只收http(s), 默认空=透传)")
    ap.add_argument("--snapshot", default="",
                    choices=["", "off", "wayback", "archive", "auto"],
                    help="缓存快照探测(默认off)")
    ap.add_argument("--softwall", default="",
                    choices=["", "off", "strip", "reader"],
                    help="客户端干预(默认off)")
    ap.add_argument("--text-proxy", default="",
                    help="一站式文本代理前缀(默认空=不用)")
    ap.add_argument("--hls-key", dest="hls_key", default="",
                    help="HLS密钥透传 URI[,IV](默认空=不用; 非法整体丢弃)")
    ap.add_argument("--preset", default="",
                    choices=["", "video"],
                    help="一键配置: video=以拿到视频为目标收敛"
                         "(开cdn/视频优先; 不动代理/栏目/浏览器/密钥等)")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.mode == "envcheck":
        return cmd_envcheck()
    if a.mode == "updatecheck":
        return cmd_updatecheck(a)
    if not a.url:
        ap.error("需要目标URL")
    if not re.match(r"^https?://", a.url.strip()):
        print("URL 必须以 http(s):// 开头")
        return 2
    if getattr(a, "preset", "") == "video":  # 一键视频: 只补未显式设置的项
        if not a.allow_cdn:
            a.allow_cdn = True
            print("preset-video: 已开 CDN 媒体(视频多在 CDN/站外, 默认拦截会漏)")
        if a.video_first is None:
            a.video_first = True
            print("preset-video: 已开视频优先深挖(显式 --no-video-first 可覆盖)")
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
        try:
            _dlj = int(a.dl_jobs)
        except Exception:
            _dlj = 1
        if _dlj == 3:
            _dlj = 1
        else:
            _dlj = _auto_jobs(_dlj) if _dlj != 1 else 1
        return cmd_dl(site, a.batch, _dlj)
    if a.mode == "auto":
        return cmd_auto(site, a.batch)
    if a.mode == "diag":
        return cmd_diag(site)
    if a.mode == "nav":
        return cmd_nav(site)
    if a.mode == "purge":
        return cmd_purge(site)
    if a.mode == "verify":
        return cmd_verify(site)
    if a.mode == "replay":
        return cmd_replay(site)
    if a.mode == "watch":
        from watchflow import cmd_watch
        return cmd_watch(site, a.batch, _auto_jobs(a.dl_jobs))
    return 2


if __name__ == "__main__":
    sys.exit(main())
