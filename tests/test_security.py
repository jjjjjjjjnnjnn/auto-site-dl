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
import os
import shutil
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
sA.report_proxy("http://127.0.0.1:18081", False)
atk("cool-three-hit", sA._cooling("http://127.0.0.1:18081") is True)
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

print("\nREDTEAM: %d 项全部守住" % N)
for x in (s, s2, s2h, s2v, s2i, s6, s7, s7b, s8, s_col, s_ns, s9, _sg,
          sA, sB, sC, sD, sD2):
    try:
        shutil.rmtree(x.root, ignore_errors=True)
    except Exception:
        pass
sys.exit(0)
