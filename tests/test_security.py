# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 jjjjjjjjnnjnn
"""安全回归测试(红队自审): 用恶意输入攻击自己的代码. 纯本地, 零网站流量.

运行: python -X utf8 tests/test_security.py   (在项目根目录)
覆盖: userinfo/反斜杠/子域混淆、SSRF 变体、文件类型嗅探、代理校验与日志注入、
      视频优先默认值、MITM 降级开关、导航错误诊断、系统代理形状、轮换顺序。
凡 assert 失败 = 被攻破, 必须修代码而不是改测试.
退出码 0 = 全部守住.
"""
import argparse
import hashlib
import os
import shutil
import stat
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import site_crawler as C  # noqa: E402

N = 0


def atk(name, cond):
    global N
    assert cond, "BREACHED: " + name
    N += 1
    print("  HOLD " + name)


def NS(**kw):
    d = dict(allow_cdn=False, allow_http=False, video_first=None, proxy="",
             column="", insecure=False, browser="", clone_profile="")
    d.update(kw)
    return argparse.Namespace(**d)


print("[A] URL归一化/SSRF")
atk("backslash", C.norm_url("https:\\\\evil.example\\x") == "https://evil.example/x")
atk("userinfo-strip", C.norm_url("https://evil.example@good.example/") ==
    "https://good.example/")
atk("userinfo-port", C.norm_url("https://u:p@good.example:8443/a").endswith(":8443/a"))
atk("host-lower", C.norm_url("HTTPS://GOOD.EXAMPLE/A") == "https://good.example/A")
atk("log-nopath-query", C.url_for_log("https://h.example/a?k=v#f") == "https://h.example/a")
atk("log-userinfo", "@" not in C.url_for_log("https://u:p@h.example/a"))
atk("ssrf-public-ip", C.is_public_host("8.8.8.8") is True)
atk("ssrf-loopback", C.is_public_host("127.0.0.1") is False)
atk("ssrf-private", C.is_public_host("10.0.0.5") is False)
atk("ssrf-linklocal", C.is_public_host("169.254.1.1") is False)
atk("ssrf-localhost", C.is_public_host("localhost") is False)
atk("ssrf-empty", C.is_public_host("") is False)
atk("ssrf-unresolvable", C.is_public_host("example.invalid") is False)

print("[B] 文件类型嗅探(魔数为准)")
atk("sniff-jpg", C.sniff_ext(b"\xff\xd8\xff\xe0xxxx") == ".jpg")
atk("sniff-png", C.sniff_ext(b"\x89PNG\r\n\x1a\nxxxx") == ".png")
atk("sniff-gif", C.sniff_ext(b"GIF89axxxx") == ".gif")
atk("sniff-webp", C.sniff_ext(b"RIFF....WEBPxxxx") == ".webp")
atk("sniff-mp4", C.sniff_ext(b"\x00\x00\x00\x18ftypmp42") == ".mp4")
atk("sniff-webm", C.sniff_ext(b"\x1aE\xdf\xa3xxxx") == ".webm")
atk("sniff-m3u8", C.sniff_ext(b"#EXTM3U\n#EXT-X-VERSION:3\n") == ".m3u8")
atk("sniff-m3u8-nonl", C.sniff_ext(b"#EXTM3U") is None)
atk("sniff-html", C.sniff_ext(b"<html><body>hi") is None)
atk("sniff-empty", C.sniff_ext(b"") is None)
fd, tmp = tempfile.mkstemp(suffix=".bin")
os.write(fd, b"\xff\xd8\xff\xe0" + b"0" * 100)
os.close(fd)
atk("check-magic-file", C.check_magic(tmp) == ".jpg")
os.remove(tmp)
atk("check-magic-missing", C.check_magic(os.path.join(tempfile.gettempdir(),
                                                      "no-such-file-xyz.bin")) is None)
atk("rank-m3u8", C.media_rank("https://h/x.m3u8") == 0)
atk("rank-mp4", C.media_rank("https://h/x.mp4") == 1)
atk("rank-img", C.media_rank("https://h/x.jpg") == 2)
atk("ismedia-ok", C.is_media_url("https://h/x.mp4") is True)
atk("ismedia-no", C.is_media_url("https://h/x.html") is False)
atk("ismedia-query", C.is_media_url("https://h/x.mp4?k=v") is True)

print("[C] 代理校验/日志注入")
atk("proxy-ok", C.check_proxy("http://127.0.0.1:8080") == "http://127.0.0.1:8080")
atk("proxy-socks", C.check_proxy("socks5h://127.0.0.1:1080") == "socks5h://127.0.0.1:1080")
atk("proxy-space", C.check_proxy("http://127.0.0.1:8080 evil") == "")
atk("proxy-newline", C.check_proxy("http://127.0.0.1:8080\nEVIL: 1") == "")
atk("proxy-noport", C.check_proxy("http://127.0.0.1") == "")
atk("proxy-badscheme", C.check_proxy("ftp://127.0.0.1:21") == "")
atk("proxy-empty", C.check_proxy("") == "")
atk("mask-singleline", "\n" not in C.mask_proxy("http://user:pass@127.0.0.1:8080"))
atk("mask-noleak", "pass" not in C.mask_proxy("http://user:pass@127.0.0.1:8080"))
atk("mask-empty", C.mask_proxy("") == "")

print("[D] 站点过滤/默认开关")
s = C.Site("https://example.invalid/", NS())
atk("media-self", s.media_ok("https://example.invalid/a.mp4") is True)
atk("media-sub", s.media_ok("https://cdn.example.invalid/a.mp4") is True)
atk("media-off-nocdn", s.media_ok("https://evil.example/a.mp4") is False)
s2 = C.Site("https://example.invalid/", NS(allow_cdn=True))
atk("media-off-cdn", s2.media_ok("https://evil.example/a.mp4") is True)
atk("media-http-block", s.media_ok("http://example.invalid/a.mp4") is False)
s2h = C.Site("https://example.invalid/", NS(allow_http=True))
atk("media-http-allow", s2h.media_ok("http://example.invalid/a.mp4") is True)
atk("media-noscheme", s.media_ok("ftp://example.invalid/a.mp4") is False)
atk("vfirst-default", s._video_first() is True)
s2v = C.Site("https://example.invalid/", NS(video_first=False))
atk("vfirst-off", s2v._video_first() is False)
atk("tls-default", s.tls_verify() is True)
s2i = C.Site("https://example.invalid/", NS(insecure=True))
atk("tls-insecure", s2i.tls_verify() is False)
atk("link-js", C.norm_link(s, "https://example.invalid/", "javascript:void(0)") == "")
atk("link-login", C.norm_link(s, "https://example.invalid/",
                              "/login?next=/") == "")
atk("link-offsite", C.norm_link(s, "https://example.invalid/",
                                "https://evil.example/") == "")
atk("link-ok", C.norm_link(s, "https://example.invalid/",
                           "/vod/type/id/1.html") ==
    "https://example.invalid/vod/type/id/1.html")
atk("nmedia-data", C.norm_media(s, "https://example.invalid/",
                                "data:image/png;base64,xx") == "")
atk("csv-inject", C._csv_safe("=cmd|'/c calc'!A0") == "'=cmd|'/c calc'!A0")
atk("csv-normal", C._csv_safe("https://h/a") == "https://h/a")
atk("find-exe-miss", C.find_exe(["no-such-engine-xyz"]) == "")

print("[E] 诊断/预检/代理链")
atk("diag-cert", "证书" in C.diagnose_nav_error("ERR_CERT_AUTHORITY_INVALID"))
atk("diag-denied", "代理" in C.diagnose_nav_error("ERR_NETWORK_ACCESS_DENIED")
    or "网络" in C.diagnose_nav_error("ERR_NETWORK_ACCESS_DENIED"))
atk("diag-tunnel", "代理" in C.diagnose_nav_error("ERR_TUNNEL_CONNECTION_FAILED"))
atk("diag-unknown", "envcheck" in C.diagnose_nav_error("weird-xyz-123"))
atk("proxy-dead-local", C.proxy_alive("http://127.0.0.1:1") is False)
atk("proxy-no-port", C.proxy_alive("http://127.0.0.1") is False)
a6 = NS(proxy="http://127.0.0.1:1")
s6 = C.Site("https://example.invalid/", a6)
atk("preflight-dead-proxy", C.preflight(s6) == 2)
sp = C.detect_system_proxy()
atk("sysproxy-shape", sp == "" or C.check_proxy(sp) != "")
a7 = NS(proxy="http://127.0.0.1:18080")
s7 = C.Site("https://example.invalid/", a7)
p7, o7 = C.eff_proxy(s7)
atk("eff-manual-first", p7 == "http://127.0.0.1:18080" and o7 == "manual")
s7.cfg["proxies"] = ["http://127.0.0.1:18081", "http://127.0.0.1:18082"]
seq = [C.eff_proxy(s7)[0] for _ in range(6)]
atk("proxy-rotate-norepeat",
    len(seq) == 6 and all(a != b for a, b in zip(seq, seq[1:]))
    and set(seq) == {"http://127.0.0.1:18081", "http://127.0.0.1:18082"})
atk("proxy-rotate-origin", C.eff_proxy(s7)[1] == "rotated")
s7b = C.Site("https://example.invalid/", NS())
s7b.cfg["proxies"] = ["http://127.0.0.1:18081"]
p7b, o7b = C.eff_proxy(s7b)
atk("proxy-single-site", p7b == "http://127.0.0.1:18081" and o7b == "site")

print("[F] 克隆/记账/失败样本")
s8 = C.Site("https://example.invalid/", NS())
atk("clone-off", s8.want_clone() is False)
s8.args.clone_profile = "C:\\Windows"
atk("clone-on", s8.want_clone() is True)
atk("clone-missing-dir", C.clone_profile_dir(s) == s.prof)
s8.note_fail("https://example.invalid/a?k=v#f", "x" * 500)
s8.note_fail("https://example.invalid/b", "y")
s8.note_fail("https://example.invalid/c", "z")
s8.note_fail("https://example.invalid/d", "w")
atk("fail-cap", len(s8.fails) == 3)
atk("fail-desens", all("?" not in f and "#" not in f for f in s8.fails))

print("[G] watchflow纯逻辑")
import watchflow as W  # noqa: E402
atk("ad-host", W.is_ad_host("https://popads.net/p.js") is True)
atk("ad-clean", W.is_ad_host("https://cdn.example.invalid/v.mp4") is False)
atk("seg-resolve", W.resolve_from_segments(
    ["https://h/v/seg1.ts", "https://h/v/seg2.ts"]) == "https://h/v/index.m3u8")
atk("seg-empty", W.resolve_from_segments([]) == "")

print("[H] 蓝队补丁回归(round2)")
atk("port-huge", C.norm_url("https://h:99999/x.m3u8") == "")
atk("port-zero", C.norm_url("https://h:0/x") == "")
atk("port-keep", C.norm_url("https://h:8443/a") == "https://h:8443/a")
atk("safehost-dotdot", C._safe_host("..") == "")
atk("safehost-doubledot", C._safe_host("a..b") == "")
atk("safehost-dash", C._safe_host("-a.com") == "")
atk("safehost-under", C._safe_host("a_b.corp") == "a_b.corp")
atk("safehost-lead-under", C._safe_host("_a.com") == "")
atk("safehost-trail-under", C._safe_host("a_.com") == "")
atk("safehost-colon", C._safe_host("a:b") == "")
atk("safehost-ok", C._safe_host("OK-site123.com") == "ok-site123.com")
try:
    C.Site("https://../", NS())
    atk("site-traversal-block", False)
except ValueError:
    atk("site-traversal-block", True)
atk("proxy-ipv6", C.check_proxy("http://[::1]:8080") == "http://[::1]:8080")
atk("proxy-auth", C.check_proxy("http://user:pass@127.0.0.1:8080") ==
    "http://user:pass@127.0.0.1:8080")
atk("mask-ipv6", "\n" not in C.mask_proxy("http://[::1]:8080"))
atk("csv-tab", C._csv_safe("\t=cmd") == "'\t=cmd")
atk("csv-cr", C._csv_safe("\r=cmd") == "'\r=cmd")
atk("csv-space", C._csv_safe(" =cmd") == "' =cmd")
atk("csv-pipe", C._csv_safe("|'/c calc'!A0") == "'|'/c calc'!A0")
atk("csv-fw", C._csv_safe("＝cmd") == "'＝cmd")
atk("csv-bom", C._csv_safe("﻿=cmd") == "'﻿=cmd")
atk("sniff-bm-short", C.sniff_ext(b"BM") is None)
atk("sniff-ftyp-zero", C.sniff_ext(b"\x00\x00\x00\x00ftyp") is None)
atk("sniff-sp-m3u8", C.sniff_ext(b"  #EXTM3U\r") is None)
atk("sniff-bom-m3u8", C.sniff_ext("﻿#EXTM3U\n#EXT-X-VERSION:3\n".encode("utf-8")) == ".m3u8")
atk("sniff-riff-trunc", C.sniff_ext(b"RIFF\x00\x00") is None)
atk("pub-v6loop", C.is_public_host("::1") is False)
atk("pub-zero", C.is_public_host("0.0.0.0") is False)
atk("pub-mapped", C.is_public_host("::ffff:127.0.0.1") is False)
atk("pub-dec", C.is_public_host("2130706433") is False)
atk("pub-hex", C.is_public_host("0x7f.0.0.1") is False)
atk("pub-oct", C.is_public_host("0177.0.0.1") is False)
atk("pub-localdot", C.is_public_host("LOCALHOST.") is False)
atk("cfg-str-dict", C._cfg_str({"a": 1}) == "")
atk("cfg-list-str", C._cfg_list("a|b;c") == ["a", "b", "c"])
atk("cfg-list-list", C._cfg_list(["a", "b"]) == ["a", "b"])
atk("cfg-list-dict", C._cfg_list({"a": 1}) == [])
s_col = C.Site("https://example.invalid/", NS())
s_col.cfg["column"] = {"a": 1}
atk("column-dict-safe", s_col.column_ok("https://example.invalid/x") is True)
s_col.cfg["proxies"] = {"a": 1}
atk("proxies-dict-safe", C.eff_proxy(s_col) == ("", ""))
atk("safe-cmd-dash", C._safe_url_for_cmd("-o evil") == "")
atk("safe-cmd-space", C._safe_url_for_cmd("https://h/a b") == "")
atk("safe-cmd-ok", C._safe_url_for_cmd("https://h/a.m3u8?k=v") == "https://h/a.m3u8?k=v")
atk("nav-clean", C._clean_nav_text("a\nb|c\td") == "a b c d")
atk("imp-136", C._pick_impersonate("Mozilla/5.0 Chrome/136.0.0.0") == "chrome136")
atk("imp-120", C._pick_impersonate("Mozilla/5.0 Chrome/120.0.0.0") == "chrome120")
atk("imp-old", C._pick_impersonate("Mozilla/5.0 Chrome/99.0") == "chrome")
atk("imp-ff", C._pick_impersonate("Mozilla/5.0 Firefox/133.0") == "chrome")
s9 = C.Site("https://example.invalid/", NS())
s9.log("line1\nline2")
with open(s9.logf, encoding="utf-8") as _f:
    _last = _f.read().strip().splitlines()[-1]
atk("log-singleline", _last == "line1\\nline2")
s_ns = C.Site("https://example.invalid/", NS())
with open(s_ns.ckf, "w", encoding="utf-8") as _f:
    _f.write("a=b\n.evil\tTRUE / TRUE 0 x y\n#c=commented")
_ns_tmp = os.path.join(tempfile.gettempdir(), "ns_test_cookies.txt")
try:
    os.remove(_ns_tmp)
except OSError:
    pass
atk("netscape-write", C._write_netscape(s_ns, _ns_tmp) is True)
with open(_ns_tmp, encoding="utf-8") as _f:
    _ns = _f.read().splitlines()
atk("netscape-no-inject", len(_ns) == 2 and not any(
    l.startswith(".evil") or l.startswith("#c") for l in _ns[1:]))
try:
    os.remove(_ns_tmp)
except OSError:
    pass


class _FakeRaw:
    def __init__(self, peer=None):
        self._connection = type(" Cn", (), {
            "sock": None if peer is None else type("Sk", (), {
                "getpeername": (lambda self=None: (peer, 443))})()})()


class _FakeResp:
    def __init__(self, status=200, headers=None, url="", text="", peer=None):
        self.status_code = status
        self.headers = headers or {}
        self.url = url
        self.text = text
        self.raw = _FakeRaw(peer)
        self.closed = False

    def iter_content(self, chunk=65536):
        data = (self.text or "").encode("utf-8", "ignore")
        for i in range(0, len(data), chunk):
            yield data[i:i + chunk]

    def close(self):
        self.closed = True


class _FakeSess:
    def __init__(self, script, proxies=None):
        self._script = list(script)
        self.proxies = proxies or {}

    def get(self, url, **kw):
        if not self._script:
            raise RuntimeError("no more scripted responses")
        return self._script.pop(0)


_sg = C.Site("https://example.invalid/", NS())
_fs = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/x.mp4")])
_r, _fu, _st = C._fetch_guarded(_fs, "https://8.8.8.8/x.mp4", "https://example.invalid/", "video/*")
atk("guard-direct-ok", _r is not None and _st == 200)
_fs2 = _FakeSess([_FakeResp(302, {"Location": "http://127.0.0.1/x"}, "https://8.8.8.8/x")])
_r2, _fu2, _st2 = C._fetch_guarded(_fs2, "https://8.8.8.8/x", "https://example.invalid/", "*/*")
atk("guard-redirect-ssrf", _r2 is None and _st2 == -1)
_fs3 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/x", peer="10.0.0.1")])
_r3, _fu3, _st3 = C._fetch_guarded(_fs3, "https://8.8.8.8/x", "https://example.invalid/", "*/*")
atk("guard-peer-rebind", _r3 is None and _st3 == -3)
_fs4 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/x", peer="10.0.0.1")],
                 proxies={"https": "http://127.0.0.1:8080"})
_r4, _fu4, _st4 = C._fetch_guarded(_fs4, "https://8.8.8.8/x", "https://example.invalid/", "*/*")
atk("guard-proxy-peer-skip", _r4 is not None and _st4 == 200)
_pl_ok = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"keys/k\"\nseg1.ts\n"
_fs5 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_ok)])
atk("playlist-relative-ok",
    C._playlist_guard_ok(_sg, _fs5, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is True)
_pl_bad = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"http://127.0.0.1/k\"\nseg1.ts\n"
_fs6 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_bad)])
atk("playlist-key-ssrf",
    C._playlist_guard_ok(_sg, _fs6, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_fs7 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text="<html>nope")])
atk("playlist-not-m3u8",
    C._playlist_guard_ok(_sg, _fs7, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_fs8 = _FakeSess([_FakeResp(429, {}, "https://8.8.8.8/x"),
                  _FakeResp(200, {}, "https://8.8.8.8/x")])
_r8, _fu8, _st8 = C._fetch_with_retry(_sg, _fs8, "https://8.8.8.8/x",
                                      "https://example.invalid/", "*/*")
atk("retry-429-then-ok", _r8 is not None and _st8 == 200 and
    _sg.counters.get("retry_429", 0) == 1)

print("[I] round3: 匿名/适配/守卫")
atk("csv-pipe-fw", C._csv_safe("｜calc") == "'｜calc")
atk("csv-slash-fw", C._csv_safe("／x") == "'／x")
sA = C.Site("https://example.invalid/", NS())
sA.cfg["proxies"] = ["http://127.0.0.1:18081", "http://127.0.0.1:18082"]
sA.report_proxy("http://127.0.0.1:18081", False)
sA.report_proxy("http://127.0.0.1:18081", False)
atk("cool-two-ok", sA._cooling("http://127.0.0.1:18081") is False)
for _ in range(3):
    sA.report_proxy("http://127.0.0.1:18081", False)
atk("cool-five-hit", sA._cooling("http://127.0.0.1:18081") is True)
picks = [sA.rotate_proxy() for _ in range(6)]
atk("cool-avoid", all(p == "http://127.0.0.1:18082" for p in picks))
sA.report_proxy("http://127.0.0.1:18082", True)
atk("cool-stat", sA.proxy_stat["http://127.0.0.1:18082"] == [1, 0])


class _FakeSess2:
    def __init__(self, proxy=""):
        self.proxies = {"http": proxy, "https": proxy} if proxy else {}


_fs9 = _FakeSess2("http://127.0.0.1:18081")
atk("failover-switch", sA.failover(_fs9) is True
    and _fs9.proxies["https"] == "http://127.0.0.1:18082"
    and sA.last_proxy == "http://127.0.0.1:18082")
sB = C.Site("https://example.invalid/", NS())
sB.cfg["proxies"] = ["http://127.0.0.1:18081"]
_fs10 = _FakeSess2("http://127.0.0.1:18081")
atk("failover-single-no", sB.failover(_fs10) is False)
atk("sess-proxy", C._sess_proxy(_fs9) == "http://127.0.0.1:18082")
atk("sess-proxy-empty", C._sess_proxy(_FakeSess2()) == "")
atk("proxied-yes", C._proxied(_fs9) is True)
atk("proxied-no", C._proxied(_FakeSess2()) is False)
sC = C.Site("https://example.invalid/", NS())
sC.note_congestion()
atk("congest-up", abs(sC.delay_mult - 1.5) < 1e-9)
sC.note_congestion()
atk("congest-up2", abs(sC.delay_mult - 2.25) < 1e-9)
sC.delay_mult = 4.0
sC.note_congestion()
atk("congest-cap", abs(sC.delay_mult - 5.0) < 1e-9)
atk("anon-noproxy", C.anon_level(C.Site("https://example.invalid/", NS())) in (0, 1))
atk("anon-pool", C.anon_level(sA) == 2)
atk("dns-hint-socks5", C._proxy_dns_hint("socks5://127.0.0.1:1080") != "")
atk("dns-hint-socks5h", C._proxy_dns_hint("socks5h://127.0.0.1:1080") == "")
atk("dns-hint-http", C._proxy_dns_hint("http://127.0.0.1:8080") == "")
atk("jobs-auto", 2 <= C._auto_jobs(0) <= 8)
atk("jobs-clamp", C._auto_jobs(99) == 8)
atk("jobs-bad", C._auto_jobs("x") == 3)
atk("disk-ok", C._disk_ok(tempfile.gettempdir(), 1) is True)
atk("disk-huge", C._disk_ok(tempfile.gettempdir(), 10 ** 12) is False)
atk("locale-default", C._locale_of(sC) == ("zh-CN", "Asia/Shanghai"))
sC.cfg["locale"] = "en-US"
sC.cfg["timezone_id"] = "Europe/Berlin"
atk("locale-cfg", C._locale_of(sC) == ("en-US", "Europe/Berlin"))
atk("ipv6-bool", isinstance(C._ipv6_available(), bool))
sD = C.Site("https://example.invalid/", NS())
atk("guard-public", C._browser_guard(sD, "https://8.8.8.8/x") is True)
atk("guard-private", C._browser_guard(sD, "http://127.0.0.1/x") is False)
atk("guard-bump", sD.counters.get("skip_browser_ssrf", 0) == 1)


class _FakePage:
    def __init__(self):
        self.gotos = []
        self.handlers = {}

    def goto(self, url, **kw):
        self.gotos.append(url)

    def on(self, ev, fn):
        self.handlers[ev] = fn


_fp = _FakePage()
atk("goto-guard-block", C._goto(_fp, sD, "http://127.0.0.1/x") != ""
    and _fp.gotos == [])


class _FakeEvResp:
    def __init__(self, url):
        self.url = url


_fp2 = _FakePage()
_bk = []
C._attach_capture(_fp2, sD, _bk)
_fp2.handlers["response"](_FakeEvResp("https://cdn.evil.invalid/v/seg.m3u8"))
_fp2.handlers["response"](_FakeEvResp("https://cdn.evil.invalid/v/a.mp4"))
_fp2.handlers["response"](_FakeEvResp("https://cdn.evil.invalid/v/a.html"))
sD2 = C.Site("https://example.invalid/", NS(allow_cdn=True))
_bk2 = []
C._attach_capture(_fp2, sD2, _bk2)
_fp2.handlers["response"](_FakeEvResp("https://cdn.evil.invalid/v/seg.m3u8"))
atk("capture-cdn-off", _bk == [])
atk("capture-cdn-on", _bk2 == ["https://cdn.evil.invalid/v/seg.m3u8"])

_tmp_tools = tempfile.mkdtemp(prefix="tools_")
_old_tools = os.environ.get("AUTO_SITE_DL_TOOLS")
_old_pin = dict(C.ENGINE_SHA256)
try:
    os.environ["AUTO_SITE_DL_TOOLS"] = _tmp_tools
    import importlib as _il
    _il.reload(C)
    _fake_exe = os.path.join(_tmp_tools, "probe-engine-xyz.exe")
    with open(_fake_exe, "wb") as _f:
        _f.write(b"fake-binary")
    atk("exe-nopin", C.find_exe(["probe-engine-xyz.exe"]) == _fake_exe)
    import hashlib as _hl
    _good = _hl.sha256(b"fake-binary").hexdigest()
    C.ENGINE_SHA256["probe-engine-xyz.exe"] = "0" * 64
    atk("exe-pin-mismatch", C.find_exe(["probe-engine-xyz.exe"]) == "")
    C.ENGINE_SHA256["probe-engine-xyz.exe"] = _good
    atk("exe-pin-match", C.find_exe(["probe-engine-xyz.exe"]) == _fake_exe)
finally:
    C.ENGINE_SHA256.clear()
    C.ENGINE_SHA256.update(_old_pin)
    if _old_tools is None:
        os.environ.pop("AUTO_SITE_DL_TOOLS", None)
    else:
        os.environ["AUTO_SITE_DL_TOOLS"] = _old_tools
    _il.reload(C)
    shutil.rmtree(_tmp_tools, ignore_errors=True)

print("[J] round4: 递归守卫/分池/贝塞尔/自测")
_pl_sq = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI='http://127.0.0.1/k'\nseg1.ts\n"
_fsJ1 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_sq)])
atk("playlist-squote",
    C._playlist_guard_ok(_sg, _fsJ1, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_pl_lw = "#EXTM3U\n#ext-x-key:METHOD=AES-128,URI=\"http://127.0.0.1/k\"\nseg1.ts\n"
_fsJ2 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_lw)])
atk("playlist-lower",
    C._playlist_guard_ok(_sg, _fsJ2, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_pl_nq = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=http://127.0.0.1/k\nseg1.ts\n"
_fsJ3 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_nq)])
atk("playlist-noquote",
    C._playlist_guard_ok(_sg, _fsJ3, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_pl_master = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=100\nhttps://8.8.8.8/v/r.m3u8\n"
_pl_rend = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"http://127.0.0.1/k\"\nseg1.ts\n"
_fsJ4 = _FakeSess([
    _FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_master),
    _FakeResp(200, {}, "https://8.8.8.8/v/r.m3u8", text=_pl_rend)])
atk("playlist-nested",
    C._playlist_guard_ok(_sg, _fsJ4, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_pl_master_ok = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=100\nrend/r.m3u8\n"
_pl_rend_ok = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"keys/k\"\nseg1.ts\n"
_fsJ5 = _FakeSess([
    _FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_master_ok),
    _FakeResp(200, {}, "https://8.8.8.8/v/rend/r.m3u8", text=_pl_rend_ok)])
atk("playlist-nested-ok",
    C._playlist_guard_ok(_sg, _fsJ5, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is True)
_fsJ6 = _FakeSess([_FakeResp(200, {"Content-Length": str(3 * 1048576)},
                             "https://8.8.8.8/v/index.m3u8", text="#EXTM3U\n")])
atk("playlist-oversize",
    C._playlist_guard_ok(_sg, _fsJ6, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
for _loc in ["javascript:alert(1)", "data:text/html,hi", "file:///etc/passwd"]:
    _fsJ7 = _FakeSess([_FakeResp(302, {"Location": _loc}, "https://8.8.8.8/x")])
    _rJ, _, _sJ = C._fetch_guarded(_fsJ7, "https://8.8.8.8/x",
                                   "https://example.invalid/", "*/*")
    atk("hop-scheme-" + _loc.split(":")[0], _rJ is None)
_fsJ8 = _FakeSess([_FakeResp(302, {"Location": "https:\\\\127.0.0.1\\x"},
                             "https://8.8.8.8/x")])
_rJ8, _, _ = C._fetch_guarded(_fsJ8, "https://8.8.8.8/x", "https://example.invalid/", "*/*")
atk("hop-backslash", _rJ8 is None)
_fsJ9 = _FakeSess([_FakeResp(307, {"Location": "/a"}, "https://8.8.8.8/x")] * 6)
_rJ9, _, _sJ9 = C._fetch_guarded(_fsJ9, "https://8.8.8.8/x", "https://example.invalid/", "*/*")
atk("hop-loop-converge", _rJ9 is None)
_fsJ10 = _FakeSess([_FakeResp(302, ["Location", "http://127.0.0.1/"], "https://8.8.8.8/x")])
_rJ10, _, _ = C._fetch_guarded(_fsJ10, "https://8.8.8.8/x", "https://example.invalid/", "*/*")
atk("hop-bad-headers", _rJ10 is None)
_fsJ11 = _FakeSess([_FakeResp("200", {}, "https://8.8.8.8/x")])
_rJ11, _, _sJ11 = C._fetch_guarded(_fsJ11, "https://8.8.8.8/x", "https://example.invalid/", "*/*")
atk("hop-bad-status", _rJ11 is None and _sJ11 == 0)
sE = C.Site("https://example.invalid/", NS())
sE.cfg["proxies"] = ["http://127.0.0.1:18081", "http://127.0.0.1:18082"]
for _ in range(5):
    sE.report_proxy("http://127.0.0.1:18081", False)
    sE.report_proxy("http://127.0.0.1:18081", False)
    sE.report_proxy("http://127.0.0.1:18081", True)
atk("cool-brushwhite", sE._cooling("http://127.0.0.1:18081") is True)
atk("cool-stat-decay", sE.proxy_stat["http://127.0.0.1:18081"][1] == 5)
sE.report_proxy("http://127.0.0.1:18081", True)
atk("cool-stat-decay2", sE.proxy_stat["http://127.0.0.1:18081"][1] == 4)
atk("peer-noproxy", C._peer_enforced(sE, "") is False)
atk("peer-public", C._peer_enforced(sE, "http://127.0.0.1:18081") is False)
atk("peer-skipped-bump", sE.counters.get("peer-skipped", 0) >= 1)
sE.cfg["proxy_trusted"] = ["http://127.0.0.1:18081"]
atk("peer-trusted", C._peer_enforced(sE, "http://127.0.0.1:18081") is True)
sT = C.Site("https://example.invalid/", NS())
sT.cfg["proxy_trusted"] = ["http://127.0.0.1:18081"]
_fsT1 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/x", peer="10.0.0.1")],
                  proxies={"https": "http://127.0.0.1:18081"})
_rT1, _, _sT1 = C._fetch_with_retry(sT, _fsT1, "https://8.8.8.8/x",
                                    "https://example.invalid/", "*/*")
atk("enforce-wired-trusted", _rT1 is None and _sT1 == -3)
sT2 = C.Site("https://example.invalid/", NS())
_fsT2 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/x", peer="10.0.0.1")],
                  proxies={"https": "http://127.0.0.1:18081"})
_rT2, _, _sT2 = C._fetch_with_retry(sT2, _fsT2, "https://8.8.8.8/x",
                                    "https://example.invalid/", "*/*")
atk("enforce-wired-public", _rT2 is not None and _sT2 == 200
    and sT2.counters.get("peer-skipped", 0) >= 1)
_fsJ12 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/x", peer="10.0.0.1")],
                   proxies={"https": "http://127.0.0.1:18081"})
_rJ12, _, _sJ12 = C._fetch_guarded(_fsJ12, "https://8.8.8.8/x",
                                   "https://example.invalid/", "*/*",
                                   enforce_peer=True)
atk("guard-enforce-peer", _rJ12 is None and _sJ12 == -3)
sF = C.Site("https://example.invalid/", NS())
sF.cfg["proxies"] = ["http://127.0.0.1:18081", "http://127.0.0.1:18082"]
_p1, _o1 = C.eff_proxy(sF, "browser")
atk("pool-sticky", _o1 == "sticky" and _p1 in sF._proxy_list())
_p2, _ = C.eff_proxy(sF, "browser")
atk("pool-sticky-ttl", _p2 == _p1)
sF.cfg["proxy_sticky"] = "http://127.0.0.1:18099"
atk("pool-sticky-cfg", C.eff_proxy(sF, "browser")[0] == "http://127.0.0.1:18099")
sF.cfg.pop("proxy_sticky")
sF._sticky_ts = 0
_p3, _ = C.eff_proxy(sF, "browser")
atk("pool-sticky-expire", _p3 in sF._proxy_list())
sF2 = C.Site("https://example.invalid/", NS())
atk("pool-dl-single", C.eff_proxy(sF2, "dl") == ("", ""))
atk("ease-0", C._ease_in_out(0) == 0.0)
atk("ease-1", C._ease_in_out(1) == 1.0)
atk("ease-half", abs(C._ease_in_out(0.5) - 0.5) < 1e-9)
atk("ease-mono", C._ease_in_out(0.25) < C._ease_in_out(0.75))
_pts = C._bezier_path(0, 0, 400, 300)
atk("bezier-n", 25 <= len(_pts) <= 110)
atk("bezier-end", abs(_pts[-1][0] - 400) < 1e-6 and abs(_pts[-1][1] - 300) < 1e-6)
atk("bezier-short", C._bezier_path(0, 0, 3, 4) == [(3, 4)])
atk("bezier-oneside", len({1 if (y - 0.75 * x) > 0 else -1 if (y - 0.75 * x) < 0 else 0
                           for x, y in _pts}) <= 3)
sG = C.Site("https://example.invalid/", NS())
try:
    os.remove(sG.ckf)
except OSError:
    pass
_fresh1, _age1 = C.session_fresh(sG)
atk("sess-nofile", _fresh1 is True and _age1 == -1.0)
with open(sG.ckf, "w", encoding="utf-8") as _f:
    _f.write("a=b")
_fresh2, _age2 = C.session_fresh(sG)
atk("sess-fresh", _fresh2 is True and 0 <= _age2 < 1)
import time as _t
_old = _t.time() - 48 * 3600
os.utime(sG.ckf, (_old, _old))
_fresh3, _age3 = C.session_fresh(sG)
atk("sess-stale", _fresh3 is False and _age3 >= 47)
sG.cfg["session_ttl_h"] = 72
atk("sess-ttl-cfg", C.session_fresh(sG)[0] is True)


class _BoomSess:
    proxies = {}

    def get(self, url, **kw):
        raise RuntimeError("dns down")


sH = C.Site("https://example.invalid/", NS())
sH.ensure_robots(_BoomSess())
atk("robots-unknown", sH.counters.get("robots-unknown", 0) == 1)
atk("robots-penalty", float(sH.cfg.get("delay", 0)) >= 2.0)
sH.ensure_robots(_BoomSess())
atk("robots-once", sH.counters.get("robots-unknown", 0) == 1)
_locks = C.verify_lock()
atk("lock-shape", isinstance(_locks, list) and len(_locks) == 4)
atk("lock-match", all("≠" not in c and c not in ("未安装", "缺失", "不可用")
                      for _, _, c in _locks))
_tlsst = C.tls_selftest()
atk("tls-selftest-shape", isinstance(_tlsst, dict) and len(_tlsst) >= 5)
atk("imp-future", C._pick_impersonate("Mozilla/5.0 Chrome/999.0.0.0") == "chrome150")
atk("guard-data", C._browser_guard(sH, "data:text/html,hi") is False)
atk("guard-blob", C._browser_guard(sH, "blob:https://example.invalid/x") is False)
atk("guard-v6loop", C._browser_guard(sH, "http://[::1]/") is False)
atk("guard-userhost", C._browser_guard(sH, "http://evil@127.0.0.1/") is False)
atk("guard-trail", C._browser_guard(sH, "http://127.0.0.1./x") is False)
atk("guard-upper", C._browser_guard(sH, "HTTP://127.0.0.1/X") is False)

print("[K] 路径一: 请求伪装")
sK0 = C.Site("https://example.invalid/", NS())
atk("spoof-off", sK0.spoof_mode() == "" and sK0.UA in C.UA_POOL)
atk("spoof-unknown",
    C.Site("https://example.invalid/", NS(spoof="evil")).spoof_mode() == "")
sK1 = C.Site("https://example.invalid/", NS(spoof="googlebot"))
atk("spoof-bot-ua", "Googlebot" in sK1.UA)
atk("spoof-bot-tls", C._tls_kind_for(sK1) == "requests")
atk("spoof-bot-tls-off", C._tls_kind_for(sK0) == "curl_cffi")
sK2 = C.Site("https://example.invalid/", NS(spoof="mobile"))
atk("spoof-mobile-vp", sK2.viewport["width"] <= 412 and "Mobile" in sK2.UA)
sK3 = C.Site("https://example.invalid/",
             NS(spoof_referer="https://www.google.com/"))
atk("spoof-ref-ok",
    sK3.ref_for("https://example.invalid/") == "https://www.google.com/")
atk("spoof-ref-evil",
    C.Site("https://example.invalid/",
           NS(spoof_referer="javascript:alert(1)")).spoof_referer() == "")
atk("spoof-ref-inject",
    C.Site("https://example.invalid/",
           NS(spoof_referer="https://h/x\nX: 1")).spoof_referer() == "")
atk("spoof-ref-userinfo",
    C.Site("https://example.invalid/",
           NS(spoof_referer="https://u@h/")).spoof_referer() == "")
_sessK, _kindK = C.make_session(sK1)
atk("spoof-bot-sess", _kindK == "requests"
    and "Googlebot" in _sessK.headers.get("User-Agent", ""))
_sessM, _kindM = C.make_session(sK2)
atk("spoof-mobile-hdr",
    _sessM.headers.get("Sec-CH-UA-Mobile") == "?1"
    and _sessM.headers.get("Sec-CH-UA-Platform") == '"Android"')
atk("spoof-mobile-tls", C._tls_kind_for(sK2) == "curl_cffi")
atk("spoof-mobile-imp", C._pick_impersonate(sK2.UA) == "chrome131_android")
atk("spoof-mobile-kind", "android" in _kindM)
atk("spoof-bot-still-req", C._tls_kind_for(sK1) == "requests" and _kindK == "requests")
atk("imp-142", C._pick_impersonate("Mozilla/5.0 Chrome/142.0.0.0") == "chrome142")
atk("imp-150", C._pick_impersonate("Mozilla/5.0 Chrome/150.0.0.0") == "chrome150")
atk("imp-future150", C._pick_impersonate("Mozilla/5.0 Chrome/999.0.0.0") == "chrome150")

print("[L] 路径二: 缓存快照")
sL0 = C.Site("https://example.invalid/", NS())
atk("snap-off", C.fetch_snapshot(sL0, _FakeSess([]),
                                 "https://example.invalid/a") == (False, "", 0))
atk("snap-unknown",
    C.Site("https://example.invalid/",
           NS(snapshot="evil")).snapshot_mode() == "")
atk("snap-cap", len(C._read_capped(
    _FakeResp(200, {}, "u", text="x" * 100), 10)) <= 10)
_orig_pub = C.is_public_host
C.is_public_host = lambda h: True if h in (
    "archive.org", "web.archive.org", "archive.ph",
    "archive.md") else _orig_pub(h)
try:
    _good_html = "<html><body>" + "正文内容填充 " * 120 + "</body></html>"
    _api = ('{"archived_snapshots": {"closest": {"url": '
            '"https://web.archive.org/web/2024/https://example.invalid/a", '
            '"status": "200"}}}')
    sL1 = C.Site("https://example.invalid/", NS(snapshot="wayback"))
    _fsL1 = _FakeSess([
        _FakeResp(200, {}, "https://archive.org/wayback/available?url=x",
                  text=_api),
        _FakeResp(200, {},
                  "https://web.archive.org/web/2024/https://example.invalid/a",
                  text=_good_html)])
    _ok1, _src1, _len1 = C.fetch_snapshot(sL1, _fsL1,
                                          "https://example.invalid/a")
    atk("snap-wayback-hit",
        _ok1 is True and _src1 == "wayback" and _len1 > 0)
    sL2 = C.Site("https://example.invalid/", NS(snapshot="wayback"))
    _fsL2 = _FakeSess([_FakeResp(
        200, {}, "https://archive.org/wayback/available?url=x",
        text='{"archived_snapshots": {}}')])
    atk("snap-wayback-miss",
        C.fetch_snapshot(sL2, _fsL2,
                         "https://example.invalid/a") == (False, "", 0))
    sL3 = C.Site("https://example.invalid/", NS(snapshot="archive"))
    _fsL3 = _FakeSess([_FakeResp(200, {}, "https://archive.ph/newest/x",
                                 text=_good_html)])
    _ok3, _src3, _len3 = C.fetch_snapshot(sL3, _fsL3,
                                          "https://example.invalid/a")
    atk("snap-archive-hit",
        _ok3 is True and _src3 == "archive.ph" and _len3 > 0)
    sL4 = C.Site("https://example.invalid/", NS(snapshot="archive"))
    _blocked = "Just a moment, please wait. " + "填充 " * 300
    _fsL4 = _FakeSess([_FakeResp(200, {}, "https://archive.ph/newest/x",
                                 text=_blocked)])
    atk("snap-blocked",
        C.fetch_snapshot(sL4, _fsL4,
                         "https://example.invalid/a") == (False, "", 0))
    sL5 = C.Site("https://example.invalid/", NS(snapshot="auto"))
    _fsL5 = _FakeSess([_FakeResp(200, {}, "https://archive.ph/newest/x",
                                 text="<html><body>hi</body></html>")])
    atk("snap-short",
        C.fetch_snapshot(sL5, _fsL5,
                         "https://example.invalid/a")[0] is False)
    sL6 = C.Site("https://example.invalid/", NS(snapshot="archive"))
    _fsL6 = _FakeSess([_FakeResp(403, {}, "https://archive.ph/newest/x")])
    atk("snap-archive-err",
        C.fetch_snapshot(sL6, _fsL6,
                         "https://example.invalid/a") == (False, "", 0))
    sL7 = C.Site("https://example.invalid/", NS(snapshot="wayback"))
    _api_evil = ('{"archived_snapshots": {"closest": {"url": '
                 '"http://127.0.0.1/evil", "status": "200"}}}')
    _fsL7 = _FakeSess([_FakeResp(
        200, {}, "https://archive.org/wayback/available?url=x",
        text=_api_evil)])
    atk("snap-evil-surl",
        C.fetch_snapshot(sL7, _fsL7,
                         "https://example.invalid/a") == (False, "", 0))
finally:
    C.is_public_host = _orig_pub
atk("snap-unpatched", C.is_public_host == _orig_pub)


class _FakePage:
    def __init__(self, script):
        self._script = list(script)

    def evaluate(self, js):
        if not self._script:
            raise RuntimeError("no more scripted values")
        v = self._script.pop(0)
        if isinstance(v, Exception):
            raise v
        return v


print("[M] 路径三: 客户端干预")
sM0 = C.Site("https://example.invalid/", NS())
_pg0 = _FakePage([{"removed": 99}])
_rM0 = C.apply_softwall(_pg0, sM0)
atk("sw-off", _rM0["mode"] == "" and _rM0["removed"] == 0
    and len(_pg0._script) == 1)
atk("sw-unknown",
    C.Site("https://example.invalid/",
           NS(softwall="evil")).softwall_mode() == "")
sM1 = C.Site("https://example.invalid/", NS(softwall="strip"))
_rM1 = C.apply_softwall(_FakePage([{"removed": 2, "unlocked": True}]), sM1)
atk("sw-strip", _rM1["removed"] == 2 and _rM1["unlocked"] is True
    and sM1.counters.get("softwall_stripped", 0) >= 1)
sM2 = C.Site("https://example.invalid/", NS(softwall="reader"))
_rM2 = C.apply_softwall(
    _FakePage([{"paras": 10, "chars": 5000, "title": "秘密标题内容"}]), sM2)
atk("sw-reader", _rM2["paras"] == 10 and _rM2["chars"] == 5000
    and "秘密" not in str(_rM2))
C.log_softwall(sM2, _rM2)
atk("sw-noleak", "秘密" not in open(sM2.logf, encoding="utf-8").read())
sM3 = C.Site("https://example.invalid/", NS(softwall="strip"))
_rM3 = C.apply_softwall(_FakePage([RuntimeError("boom")]), sM3)
atk("sw-boom", _rM3["removed"] == 0 and _rM3["unlocked"] is False)

print("[N] 路径四: 一站式文本代理")
sN0 = C.Site("https://example.invalid/", NS())
atk("tp-off", sN0.text_proxy_base() == "" and sN0.text_proxy_url(
    "https://example.invalid/a") == "")
atk("tp-evil-scheme",
    C.Site("https://example.invalid/",
           NS(text_proxy="ftp://h:21/x")).text_proxy_base() == "")
atk("tp-inject",
    C.Site("https://example.invalid/",
           NS(text_proxy="https://h/x\nX: 1")).text_proxy_base() == "")
atk("tp-userinfo",
    C.Site("https://example.invalid/",
           NS(text_proxy="https://u@h/x")).text_proxy_base() == "")
_orig_pub2 = C.is_public_host
C.is_public_host = lambda h: True if h in (
    "proxy.example.invalid",) else _orig_pub2(h)
try:
    sN1 = C.Site("https://example.invalid/",
                 NS(text_proxy="https://proxy.example.invalid/a?u="))
    atk("tp-join", sN1.text_proxy_url("https://example.invalid/x?k=v") ==
        "https://proxy.example.invalid/a?u=https%3A%2F%2Fexample.invalid%2Fx%3Fk%3Dv")
    _goodN = "<html><body>" + "代理正文填充 " * 120 + "</body></html>"
    _fsN = _FakeSess([_FakeResp(
        200, {}, "https://proxy.example.invalid/a?u=...", text=_goodN)])
    _okN, _lenN = C.fetch_text_proxy(
        sN1, _fsN, "https://example.invalid/x?token=SECRET123")
    atk("tp-hit", _okN is True and _lenN > 0)
    atk("tp-noleak", "SECRET123" not in open(
        sN1.logf, encoding="utf-8").read())
finally:
    C.is_public_host = _orig_pub2
atk("tp-unpatched", C.is_public_host == _orig_pub2)

print("[O] A3/A4补丁回归(相对守卫/referer-fallback)")


class _FakeSessKw:
    def __init__(self, script, proxies=None):
        self._script = list(script)
        self.proxies = proxies or {}
        self.calls = []

    def get(self, url, **kw):
        self.calls.append((url, kw))
        if not self._script:
            raise RuntimeError("no more scripted responses")
        return self._script.pop(0)


_sgO = C.Site("https://example.invalid/", NS())
_pl_rel_seg = "#EXTM3U\n//127.0.0.1/seg.ts\n"
_fsO1 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_rel_seg)])
atk("playlist-relative-seg-ssrf",
    C._playlist_guard_ok(_sgO, _fsO1, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_pl_rel_key = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"//127.0.0.1/k?token=abc\"\nseg1.ts\n"
_fsO2 = _FakeSess([_FakeResp(200, {}, "https://8.8.8.8/v/index.m3u8", text=_pl_rel_key)])
atk("playlist-relative-key-ssrf",
    C._playlist_guard_ok(_sgO, _fsO2, "https://8.8.8.8/v/index.m3u8",
                         "https://example.invalid/") is False)
_sgO2 = C.Site("https://example.invalid/", NS())
_fsO3 = _FakeSessKw([_FakeResp(403, {}, "https://8.8.8.8/x"),
                      _FakeResp(200, {}, "https://8.8.8.8/x")])
_rO3, _fO3, _sO3 = C._fetch_with_retry(_sgO2, _fsO3, "https://8.8.8.8/x", "", "*/*")
atk("referer-fallback-retry", _rO3 is not None and _sO3 == 200 and len(_fsO3.calls) == 2)
atk("referer-fallback-hdr",
    (_fsO3.calls[1][1].get("headers") or {}).get("Referer") == "https://8.8.8.8/")
atk("referer-fallback-bump", _sgO2.counters.get("referer-fallback", 0) == 1)

print("[P] B5 extra_headers / B6 hls-key")
sP = C.Site("https://example.invalid/", NS())
sP.cfg["extra_headers"] = {
    "example.invalid": {"Referer": "https://example.invalid/",
                        "Origin": "https://example.invalid",
                        "Cookie": "a=b", "X-Evil": "1"},
    "other.invalid": {"Referer": "https://other.invalid/"},
}
atk("xh-only-two-keys",
    set(sP.extra_headers_for("example.invalid").keys()) <= {"Referer", "Origin"})
atk("xh-cookie-drop", "Cookie" not in sP.extra_headers_for("example.invalid"))
atk("xh-evil-key-drop", "X-Evil" not in sP.extra_headers_for("example.invalid"))
atk("xh-host-scope", sP.extra_headers_for("other.invalid") == {
    "Referer": "https://other.invalid/"})
atk("xh-host-miss", sP.extra_headers_for("evil.example") == {})
sP.cfg["extra_headers"] = {"example.invalid": {"Referer": "javascript:alert(1)"}}
atk("xh-bad-scheme-drop", sP.extra_headers_for("example.invalid") == {})
sP.cfg["extra_headers"] = {"example.invalid": {"Origin": "https://h/a b"}}
atk("xh-space-drop", sP.extra_headers_for("example.invalid") == {})
sP.cfg["extra_headers"] = {"example.invalid": {"Referer": "https://u@h/"}}
atk("xh-userinfo-drop", sP.extra_headers_for("example.invalid") == {})
sP.cfg["extra_headers"] = "not-a-dict"
atk("xh-nondict-safe", sP.extra_headers_for("example.invalid") == {})


class _CapSess:
    def __init__(self):
        self.proxies = {}
        self.got = None

    def get(self, url, **kw):
        self.got = kw.get("headers", {})

        class _R:
            status_code = 200
            headers = {}
            url = url

            def close(self):
                pass

        return _R()


sP2 = C.Site("https://example.invalid/", NS())
sP2.cfg["extra_headers"] = {"8.8.8.8": {"Referer": "https://cfg.invalid/",
                                        "Origin": "https://cfg.invalid"}}
_orig_pub3 = C.is_public_host
C.is_public_host = lambda h: True
try:
    _cap = _CapSess()
    C._fetch_guarded(_cap, "https://8.8.8.8/x", "https://explicit.invalid/",
                     "*/*", site=sP2)
finally:
    C.is_public_host = _orig_pub3
atk("xh-no-override-referer", _cap.got.get("Referer") == "https://explicit.invalid/")
atk("xh-fill-origin", _cap.got.get("Origin") == "https://cfg.invalid")
atk("hk-ok-uri", C.Site("https://example.invalid/",
                         NS(hls_key="https://k.invalid/k")).hls_key() == (
    "https://k.invalid/k", ""))
atk("hk-ok-iv", C.Site("https://example.invalid/",
                        NS(hls_key="https://k.invalid/k,0xabcdef12")).hls_key() == (
    "https://k.invalid/k", "0xabcdef12"))
atk("hk-bad-iv-drop", C.Site("https://example.invalid/",
                              NS(hls_key="https://k.invalid/k,zz!!")).hls_key() == (
    "", ""))
atk("hk-space-drop", C.Site("https://example.invalid/",
                             NS(hls_key="https://k.invalid/k a")).hls_key() == (
    "", ""))
atk("hk-semi-ok", C.Site("https://example.invalid/",
                           NS(hls_key="https://k.invalid/k;evil")).hls_key() == (
    "https://k.invalid/k;evil", ""))
atk("hk-newline-drop", C.Site("https://example.invalid/",
                               NS(hls_key="https://k.invalid/k\nX: 1")).hls_key() == (
    "", ""))
atk("hk-scheme-drop", C.Site("https://example.invalid/",
                              NS(hls_key="ftp://k.invalid/k")).hls_key() == (
    "", ""))

print("[Q] B7挑战分类/B8 token快道")
atk("ch-cf-hdr", C.diagnose_http_challenge(
    403, {"cf-mitigated": "challenge"}, "")[0] == "cf-challenge")
atk("ch-cf-body", C.diagnose_http_challenge(
    403, {}, "<title>Attention Required! | Cloudflare</title>")[0] == "cf-challenge")
atk("ch-turnstile", C.diagnose_http_challenge(
    403, {}, '<div class="cf-turnstile"></div>')[0] == "turnstile")
atk("ch-turnstile-plat", C.diagnose_http_challenge(
    403, {}, "challenge-platform script")[0] == "turnstile")
atk("ch-datadome", C.diagnose_http_challenge(
    403, {"x-datadome": "1"}, "datadome captcha")[0] == "datadome")
atk("ch-datadome-body", C.diagnose_http_challenge(
    403, {}, "DataDome device check")[0] == "datadome")
atk("ch-geetest-not-dd", C.diagnose_http_challenge(
    403, {}, "geetest captcha")[0] != "datadome")
atk("ch-forbidden", C.diagnose_http_challenge(
    403, {}, "<html>forbidden</html>")[0] == "forbidden")
atk("ch-non403-empty", C.diagnose_http_challenge(
    200, {}, "Attention Required")[0] == "")
atk("ch-hint-str", isinstance(C.diagnose_http_challenge(
    403, {}, "x")[1], str) and len(C.diagnose_http_challenge(
    403, {}, "x")[1]) > 0)
sQ = C.Site("https://example.invalid/", NS())
_fsQ = _FakeSess([_FakeResp(403, {"cf-mitigated": "challenge"},
                            "https://8.8.8.8/x", text="Attention Required")])
_rQ, _fQ, _sQ = C._fetch_with_retry(sQ, _fsQ, "https://8.8.8.8/x",
                                    "https://8.8.8.8/page", "*/*")
atk("ch-bump", _rQ is None and _sQ == 403
    and sQ.counters.get("challenge-cf-challenge", 0) == 1)
atk("token-re", W._TOKEN_Q_RE.search("https://h/v/a.m3u8?token=abc") is not None
    and W._TOKEN_Q_RE.search("https://h/v/a.m3u8?expires=123") is not None
    and W._TOKEN_Q_RE.search("https://h/v/a.m3u8?sig=x") is not None
    and W._TOKEN_Q_RE.search("https://h/v/a.m3u8") is None)
_jobsQ = []
for _mkQ, _muQ, _rfQ in [("m3u8", "https://8.8.8.8/v/a.m3u8", "d1"),
                         ("m3u8", "https://8.8.8.8/v/b.m3u8?token=abc", "d2"),
                         ("direct", "https://8.8.8.8/v/c.mp4", "d3")]:
    if _mkQ == "m3u8" and W._TOKEN_Q_RE.search(_muQ):
        _jobsQ.insert(0, (_mkQ, _muQ, _rfQ))
    else:
        _jobsQ.append((_mkQ, _muQ, _rfQ))
atk("fastpath-head", _jobsQ[0][1] == "https://8.8.8.8/v/b.m3u8?token=abc"
    and len(_jobsQ) == 3)
sQ2 = C.Site("https://example.invalid/", NS())
sQ2.bump("token-fastpath")
atk("fastpath-bump", sQ2.counters.get("token-fastpath", 0) == 1)

print("[S] C1纵深安全/流式落盘")
sS0 = C.Site("https://example.invalid/", NS())
C._chmod_0600(sS0.ckf) if os.path.isfile(sS0.ckf) else None
_tmpS = os.path.join(sS0.root, "perm_probe.txt")
with open(_tmpS, "w", encoding="utf-8") as _f:
    _f.write("x")
C._chmod_0600(_tmpS)
atk("chmod-survive", os.path.isfile(_tmpS))
if os.name == "nt":
    atk("chmod-win-bool", isinstance(C._perm_too_open(_tmpS), bool))
else:
    atk("chmod-600", stat.S_IMODE(os.stat(_tmpS).st_mode) == 0o600)
    os.chmod(_tmpS, 0o644)
    atk("perm-open", C._perm_too_open(_tmpS) is True)
    os.chmod(_tmpS, 0o600)
    atk("perm-closed", C._perm_too_open(_tmpS) is False)
try:
    os.remove(_tmpS)
except Exception:
    pass
sS0.note_fail("https://example.invalid/x?token=SECRET9",
              "ytdlp:https://cdn.invalid/v?token=SECRET9 err")
atk("why-scrub", "SECRET9" not in sS0.fails[-1])


class _StreamResp:
    def __init__(self, chunks):
        self._ch = list(chunks)
        self.headers = {}
        self.consumed = 0

    def iter_content(self, n=65536):
        for c in self._ch:
            self.consumed += 1
            yield c

    def close(self):
        pass


_orig_retry = C._fetch_with_retry
_orig_pubS = C.is_public_host
C.is_public_host = lambda h: True
try:
    sS1 = C.Site("https://example.invalid/", NS())
    sS1.robot_denied = lambda u: False
    _bad_chunks = [b"NOTMEDIA" * 8 for _ in range(10)]
    C._fetch_with_retry = lambda site, sess, url, ref, acc, **k: (
        _StreamResp(_bad_chunks), url, 200)
    _rS1 = C.fetch_one(sS1, None, "https://example.invalid/a.mp4", 91001,
                       "https://example.invalid/", "list")
    atk("stream-early-discard", _rS1 == ""
        and sS1.counters.get("skip_magic_early", 0) >= 1
        and sS1.counters.get("skip_nomagic", 0) >= 1)
    atk("stream-no-part",
        not [x for x in os.listdir(sS1.dl) if x.endswith(".part")])
    _mp4 = b"\x00\x00\x00\x18ftypmp42" + os.urandom(2048)
    _chunks = [_mp4[i:i + 700] for i in range(0, len(_mp4), 700)]
    C._fetch_with_retry = lambda site, sess, url, ref, acc, **k: (
        _StreamResp(_chunks), url, 200)
    _rS2 = C.fetch_one(sS1, None, "https://example.invalid/b.mp4", 91002,
                       "https://example.invalid/", "list")
    atk("stream-ok", _rS2 != "" and os.path.isfile(_rS2))
    _want = hashlib.sha256(open(_rS2, "rb").read()).hexdigest()
    _got = ""
    with open(sS1.invf, encoding="utf-8-sig") as _f:
        _rows = list(_f.readlines())
    for _ln in _rows[1:]:
        if os.path.basename(_rS2) in _ln:
            _got = _ln.strip().split(",")[3]
    atk("stream-sha", _got == _want and _want != "")
finally:
    C._fetch_with_retry = _orig_retry
    C.is_public_host = _orig_pubS

print("[T] C2反劫持/verify/配置校验")
sT = C.Site("https://example.invalid/", NS())
sT.cfg["__evil_key__"] = 1
sT.cfg["proxies"] = 123
_cfg2, _warns2 = C._validate_config_dict(dict(sT.cfg))
atk("cfg-unknown-warn", any("__evil_key__" in w for w in _warns2))
atk("cfg-badtype-fallback", _cfg2.get("proxies") == []
    and any("proxies" in w for w in _warns2))
_l1 = C._take_session_lock(sT)
_l2 = C._take_session_lock(sT)
atk("sess-lock", _l1 is True and _l2 is False)
try:
    os.remove(os.path.join(sT.root, ".session.lock"))
except Exception:
    pass
C._note_mitm(sT, "unit-probe", "https://example.invalid/x")
atk("mitm-bump", sT.counters.get("mitm-signal", 0) >= 1)
sV = C.Site("https://example.invalid/", NS())
with open(os.path.join(sV.dl, "00001_good.mp4"), "wb") as _f:
    _f.write(b"\x00\x00\x00\x18ftypmp42" + b"v" * 600)
_gh = C.hash_file(os.path.join(sV.dl, "00001_good.mp4"))
with open(sV.invf, "w", encoding="utf-8-sig", newline="") as _f:
    _f.write("url,file,bytes,sha256,source\n")
    _f.write("https://example.invalid/g,00001_good.mp4,600,%s,list\n" % _gh)
    _f.write("https://example.invalid/m,00002_miss.mp4,600,%s,list\n" % _gh)
    _f.write("https://example.invalid/b,00001_good.mp4,600,%s,list\n" % ("0" * 64))
atk("verify-rc", C.cmd_verify(sV) == 1
    and sV.counters.get("verify-fail", 0) == 2)

print("[U] C3藏匿一致/效率 + C4 rules")
sU0 = C.Site("https://example.invalid/", NS())
_sessU0, _ = C.make_session(sU0)
atk("lang-default",
    _sessU0.headers.get("Accept-Language") == "zh-CN,zh;q=0.9,en;q=0.8")
sU1 = C.Site("https://example.invalid/", NS())
sU1.cfg["locale"] = "en-US"
atk("lang-follow-locale", C._accept_language_of(sU1) == "en-US,en;q=0.9")
_sessU1, _ = C.make_session(sU1)
atk("lang-sess-sync",
    _sessU1.headers.get("Accept-Language") == "en-US,en;q=0.9")
sU1.cfg["locale"] = "javascript:alert(1)"
atk("lang-evil-fallback",
    C._accept_language_of(sU1) == "zh-CN,zh;q=0.9,en;q=0.8")
atk("sf-samesite", C._sec_fetch_for("https://example.invalid/v/a.mp4",
    "https://example.invalid/p/1", "video/*") == {
    "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Dest": "video"})
atk("sf-crosssite", C._sec_fetch_for("https://cdn.evil.invalid/v/a.mp4",
    "https://example.invalid/p/1", "video/*")["Sec-Fetch-Site"] == "cross-site")
atk("sf-img-dest", C._sec_fetch_for("https://cdn.evil.invalid/a.jpg",
    "https://example.invalid/p/1", "image/*,*/*;q=0.8")["Sec-Fetch-Dest"] == "image")
_capU = _CapSess()
_orig_pubU = C.is_public_host
C.is_public_host = lambda h: True
try:
    C._fetch_guarded(_capU, "https://cdn.evil.invalid/v/a.mp4",
                     "https://example.invalid/p/1", "video/*", site=sU0)
finally:
    C.is_public_host = _orig_pubU
atk("sf-wire-cross", _capU.got.get("Sec-Fetch-Site") == "cross-site")
atk("sf-wire-nocors", _capU.got.get("Sec-Fetch-Mode") == "no-cors")
atk("dl-default-serial", C.cmd_dl.__defaults__ == (60, 1))
atk("dl-parser-help",
    "dl" in C.build_parser().format_help())
_orig_gai = C.socket.getaddrinfo
_calls = [0]


def _fake_gai(host, port, *a, **k):
    _calls[0] += 1
    return [(2, 1, 6, "", ("8.8.8.8", 0))]


C.socket.getaddrinfo = _fake_gai
try:
    C._DNS_CACHE.pop("dns-cache.invalid", None)
    atk("dns-first",
        C._resolve_ips("dns-cache.invalid") == ["8.8.8.8"] and _calls[0] == 1)
    atk("dns-hit",
        C._resolve_ips("dns-cache.invalid") == ["8.8.8.8"] and _calls[0] == 1)
    atk("dns-cached-shape", "dns-cache.invalid" in C._DNS_CACHE)
finally:
    C.socket.getaddrinfo = _orig_gai
    try:
        C._DNS_CACHE.pop("dns-cache.invalid", None)
    except Exception:
        pass
sR = C.Site("https://example.invalid/", NS())
sR.cfg["rules"] = {"version": 1,
                   "detail_link_selector": [".ok", "a[evil]", "x" * 201,
                                            "a,div", "<script>", 123]}
atk("rule-evil-drop",
    C.site_rules(sR).get("detail_link_selector") == [".ok", "a[evil]", "123"])
sR.cfg["rules"] = {"version": 999, "detail_link_selector": [".ok"]}
atk("rule-ver-drop", C.site_rules(sR) == {}
    and "WARNING" in open(sR.logf, encoding="utf-8").read())
sR.cfg["rules"] = {"version": 1, "next_page_selector": [".nxt"]}


class _FakeRulePage:
    def __init__(self):
        self._site_ref = sR
        self.url = "https://example.invalid/list/1.html"

    def query_selector(self, sel):
        class _E:
            def get_attribute(self, k):
                return "/list/2.html" if sel == ".nxt" else ""
        return _E() if sel == ".nxt" else None

    def query_selector_all(self, sel):
        return []


_orig_nlf = C.norm_link_from
C.norm_link_from = lambda page, base, href: "https://example.invalid/list/2.html" \
    if href == "/list/2.html" else ""
try:
    atk("rule-priority", C.find_next(_FakeRulePage(),
                                     "https://example.invalid/list/1.html")
        == "https://example.invalid/list/2.html")
finally:
    C.norm_link_from = _orig_nlf

print("[V] 攻击侧自测(replay/钉扎, 零网络)")
atk("diff-same", C._diff_significant(200, 1000, 200, 1000) is False)
atk("diff-status", C._diff_significant(200, 1000, 403, 1000) is True)
atk("diff-len", C._diff_significant(200, 1000, 200, 500) is True)
atk("diff-fail", C._diff_significant(200, -1, 200, 500) is False)
atk("certfp-empty", C._cert_fp("", 443) == "")
atk("certfp-invalid", C._cert_fp("example.invalid", 443) == "")
sV2 = C.Site("https://example.invalid/", NS())
atk("hijack-default-off", sV2.hijack_on() is False)
atk("hijack-flag-on",
    C.Site("https://example.invalid/", NS(hijack_check=True)).hijack_on() is True)
C._save_pin(sV2, {"a" * 64, "xyz", "A" * 64})
atk("pin-roundtrip", C._load_pin(sV2) == {"a" * 64})
try:
    os.remove(sV2._pinfile())
except Exception:
    pass
sW = C.Site("https://example.invalid/", NS())
with open(sW.ckf, "w", encoding="utf-8") as _f:
    _f.write("sess=validtoken123")
_callsW = [0]


def _fake_probe(site, sess, url):
    _callsW[0] += 1
    if _callsW[0] == 2:
        return 200, 500
    return 200, 1000


_orig_probe = C._probe_page
C._probe_page = _fake_probe
try:
    _rcW = C.cmd_replay(sW)
finally:
    C._probe_page = _orig_probe
atk("replay-diff-unbound", _rcW == 0 and _callsW[0] == 3
    and sW.counters.get("replay-diff", 0) == 1
    and sW.counters.get("replay-unbound", 0) == 1)
atk("replay-noleak", "validtoken123" not in open(sW.logf, encoding="utf-8").read())
sW3 = C.Site("https://example.invalid/", NS())
try:
    os.remove(sW3.ckf)
except Exception:
    pass
atk("replay-no-session", C.cmd_replay(sW3) == 3)

print("[X] 自我学习限制 + i18n")
import i18n as I18N  # noqa: E402
atk("i18n-keys-equal", set(I18N.STRINGS["zh"].keys()) == set(I18N.STRINGS["en"].keys()))
I18N.set_lang("en")
atk("i18n-en", I18N._("m_dl") == "⬇ Download dl")
I18N.set_lang("zh")
atk("i18n-zh", I18N._("m_dl") == "⬇ 下载 dl")
atk("i18n-fallback", I18N._("no_such_key_qqq") == "no_such_key_qqq")
atk("i18n-resolve-bad", I18N.resolve_lang("fr") == "en")
atk("i18n-detect-shape", I18N.detect_system_lang() in ("zh", "en"))
I18N.set_lang("auto")
import tui as TUI  # noqa: E402
from unittest import mock as _mock
with _mock.patch.object(TUI, "_arrow_ok", return_value=False), \
        _mock.patch("builtins.input", side_effect=["1"]):
    atk("tui-pick-num", TUI.pick("t", [("a", "A"), ("b", "B")]) == "A")
with _mock.patch.object(TUI, "_arrow_ok", return_value=False), \
        _mock.patch("builtins.input", side_effect=["zzz", "q"]):
    atk("tui-pick-quit", TUI.pick("t", [("a", "A")]) is None)
atk("tui-i18n-alive", callable(I18N._) and I18N._("pick_back") != "pick_back")
TUI._LAST.clear()
with _mock.patch.object(TUI, "_arrow_ok", return_value=True), \
        _mock.patch.object(TUI, "_getkey", side_effect=["down", "down", "enter"]):
    atk("tui-arrow-nav", TUI.pick("ta", [("a", "A"), ("b", "B"), ("c", "C")]) == "C")
with _mock.patch.object(TUI, "_arrow_ok", return_value=True), \
        _mock.patch.object(TUI, "_getkey", side_effect=["esc"]):
    atk("tui-arrow-esc", TUI.pick("tb", [("a", "A")]) is None)
with _mock.patch.object(TUI, "_arrow_ok", return_value=True), \
        _mock.patch.object(TUI, "_getkey", side_effect=["up", "right"]):
    atk("tui-arrow-wrap", TUI.pick("tc", [("a", "A"), ("b", "B")]) == "B")
sX = C.Site("https://example.invalid/", NS())
atk("learn-default-on", C.learn_on(sX) is True)
atk("learn-killed",
    C.learn_on(C.Site("https://example.invalid/", NS(no_learn=True))) is False)
sX.cfg["learn"] = False
atk("learn-cfg-off", C.learn_on(sX) is False)
sX.cfg["learn"] = True
_evil = {"version": 1, "delay": 9999, "engine_hits": {"a": 5, "K" * 40: 9},
         "last_challenge": "challenge-x;rm", "fails_429": -3,
         "url": "https://evil/", "cookie": "a=b"}
_cl = C._clamp_learn(_evil)
atk("learn-clamp", _cl["delay"] == 10.0 and _cl["fails_429"] == 0
    and "K" * 40 not in _cl["engine_hits"]
    and _cl["last_challenge"] == "" and "url" not in _cl and "cookie" not in _cl)
atk("learn-ver-drop", C._clamp_learn({"version": 999})["delay"] == 1.2)
with open(os.path.join(sX.root, "learn.json"), "w", encoding="utf-8") as _f:
    _f.write('{"version": 1, "delay": "oops", "engine_hits": [1]}')
atk("learn-load-evil", C.load_learn(sX)["delay"] == 1.2
    and C.load_learn(sX)["engine_hits"] == {})
sX.learn = {"version": 1, "delay": 2.5, "engine_hits": {}, "last_challenge": "",
            "fails_429": 0, "updated": 0}
sX.counters["retry_429"] = 7
sX.counters["challenge-turnstile"] = 2
C.save_learn(sX)
_re = C.load_learn(sX)
atk("learn-save", _re["delay"] == 2.5 and _re["fails_429"] == 7
    and _re["last_challenge"] == "challenge-turnstile" and _re["updated"] > 0)
C.learn_hit(sX, "ytdlp")
C.learn_hit(sX, "")
atk("learn-hit", sX.learn["engine_hits"].get("ytdlp") == 1)
sX2 = C.Site("https://example.invalid/", NS(no_learn=True))
sX2.learn = {"version": 1, "delay": 5.0, "engine_hits": {}, "last_challenge": "",
             "fails_429": 0, "updated": 0}
C.save_learn(sX2)
atk("learn-nosave", C.load_learn(sX2)["delay"] == 2.5)
sX.note_congestion()
atk("learn-nudge", sX.learn["delay"] == 3.0)
atk("ver-cmp", C._ver_cmp("v1.10.0", "1.9.9") == 1
    and C._ver_cmp("1.7.0", "1.7.0") == 0
    and C._ver_cmp("1.6", "1.7.0") == -1)

print("[Y] wait->dl 会话交接")
with open(os.path.join(sX.root, "cookies.txt"), "w", encoding="utf-8") as _f:
    _f.write("sess=abc123; theme=dark")
atk("ck-parse", C._load_cookie_pairs(sX) == [("sess", "abc123"),
                                             ("theme", "dark")])
with open(os.path.join(sX.root, "cookies.txt"), "w", encoding="utf-8") as _f:
    _f.write("good=a; bad name=b; inject=x\r\ny: 1; noval; multi=a=b=c; "
             "ctl=\x01; comma=a,b; toolong=" + "v" * 5000 + "; dup=1; dup=2")
_ckd = dict(C._load_cookie_pairs(sX))
atk("ck-clamp", _ckd.get("good") == "a" and "bad name" not in _ckd
    and "inject" not in _ckd and _ckd.get("multi") == "a=b=c"
    and "ctl" not in _ckd and "comma" not in _ckd and "toolong" not in _ckd
    and _ckd.get("dup") == "2")
atk("ck-missing", C._load_cookie_pairs(
    C.Site("https://no-such.invalid/", NS())) == [])


class _FakeCtx:
    def __init__(self):
        self.added = None

    def add_cookies(self, cs):
        self.added = cs


with open(os.path.join(sX.root, "cookies.txt"), "w", encoding="utf-8") as _f:
    _f.write("sess=abc123")
_fc = _FakeCtx()
atk("ck-seed", C._seed_ctx_cookies(sX, _fc) is True
    and _fc.added == [{"name": "sess", "value": "abc123",
                       "domain": sX.host, "path": "/"}])
atk("ck-seed-none", C._seed_ctx_cookies(sX, None) is False)
_sess, _kind = C.make_session(sX)
atk("ck-sess", (_sess.headers.get("Cookie") or "") == "sess=abc123")
try:
    _sess.close()
except Exception:
    pass

print("\nREDTEAM: %d 项全部守住" % N)
for x in (s, s2, s2h, s2v, s2i, s6, s7, s7b, s8, s_col, s_ns, s9, _sg,
          sA, sB, sC, sD, sD2, sE, sF, sF2, sG, sH, sT, sT2,
          sK0, sK1, sK2, sK3, sL0, sL1, sL2, sL3, sL4, sL5, sL6, sL7,
          sM0, sM1, sM2, sM3, sN0, sN1, sP, sP2, sQ, sQ2):
    try:
        shutil.rmtree(x.root, ignore_errors=True)
    except Exception:
        pass
sys.exit(0)
