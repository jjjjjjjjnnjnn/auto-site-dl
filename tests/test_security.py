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

print("\nREDTEAM: %d 项全部守住" % N)
for x in (s, s2, s2h, s2v, s2i, s6, s7, s7b, s8):
    try:
        shutil.rmtree(x.root, ignore_errors=True)
    except Exception:
        pass
sys.exit(0)
