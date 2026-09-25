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
seq = [C.eff_proxy(s7)[0] for _ in range(4)]
atk("proxy-rotate-order",
    seq == ["http://127.0.0.1:18081", "http://127.0.0.1:18082"] * 2)
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
atk("safehost-under", C._safe_host("a_b.com") == "")
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

print("\nREDTEAM: %d 项全部守住" % N)
for x in (s, s2, s2h, s2v, s2i, s6, s7, s7b, s8, s_col, s_ns, s9, _sg):
    try:
        shutil.rmtree(x.root, ignore_errors=True)
    except Exception:
        pass
sys.exit(0)
