# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 jjjjjjjjnnjnn
"""终端交互UI(纯标准库): 三层菜单, 子进程前台运行, Ctrl+C 停止任务.

站点页 -> 操作页 -> 运行(跟日志).
终端下方向键菜单(↑↓移动 →/Enter确认 ←/Esc返回); 管道/重定向时自动降级为数字行模式.
双语: --lang auto|zh|en (默认 auto=系统语言, 取不到回英语).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from i18n import _, set_lang  # noqa: E402

PY = sys.executable


def site_stats(root: str):
    files, total, rows = 0, 0, 0
    dl = os.path.join(root, "downloads")
    try:
        for x in os.listdir(dl):
            p = os.path.join(dl, x)
            if os.path.isfile(p):
                files += 1
                total += os.path.getsize(p)
    except Exception:
        pass
    inv = os.path.join(root, "inventory.csv")
    try:
        with open(inv, encoding="utf-8-sig") as f:
            rows = max(0, sum(1 for _ in f) - 1)
    except Exception:
        pass
    return files, total, rows


def fmt_size(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%d%s" % (n, u)
        n //= 1024
    return "%dTB" % n


def _onoff(v) -> str:
    return _("v_on") if v else _("v_off")


def pick(title: str, items):
    """items: [(显示, 值)]. 返回值或None(返回/取消). 终端=方向键菜单, 否则数字行模式."""
    labels = [lab for (lab, _v) in items]
    if _arrow_ok() and labels:
        start = _LAST.get(title, 0)
        try:
            r = _menu(title, labels, start)
        except (EOFError, KeyboardInterrupt):
            return None
        if r is None:
            return None
        _LAST[title] = r
        return items[r][1]
    # 行模式: 管道/重定向/测试/AUTO_SITE_DL_LINE=1
    print("\n== %s ==" % title)
    for i, (label, _v) in enumerate(items, 1):
        print("  %d. %s" % (i, label))
    print(_("pick_back"))
    while True:
        try:
            s = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if s in ("q", "quit", "exit"):
            return None
        if s.isdigit() and 1 <= int(s) <= len(items):
            return items[int(s) - 1][1]
        print(_("pick_hint"))


_LAST = {}


def _arrow_ok() -> bool:
    """方向键模式可用? 需双端TTY + 有按键读取手段. 测试/管道用行模式."""
    if os.environ.get("AUTO_SITE_DL_LINE") == "1":
        return False
    try:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return False
    except Exception:
        return False
    if sys.platform == "win32":
        try:
            import msvcrt  # noqa: F401
            return True
        except Exception:
            return False
    try:
        import termios  # noqa: F401
        return True
    except Exception:
        return False


def _getkey() -> str:
    """读一键, 归一为 up/down/left/right/enter/esc/单字符."""
    if sys.platform == "win32":
        import msvcrt
        c = msvcrt.getch()
        if c in (b"\xe0", b"\x00"):
            c2 = msvcrt.getch()
            return {b"H": "up", b"P": "down",
                    b"K": "left", b"M": "right"}.get(c2, "")
        if c == b"\r":
            return "enter"
        if c == b"\x1b":
            return "esc"
        try:
            return c.decode("utf-8", "ignore").lower()
        except Exception:
            return ""
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        c = sys.stdin.read(1)
        if c == "\x1b":
            c += sys.stdin.read(2)
            return {"\x1b[A": "up", "\x1b[B": "down",
                    "\x1b[C": "right", "\x1b[D": "left"}.get(c, "esc")
        if c in ("\r", "\n"):
            return "enter"
        return c.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _menu(title: str, labels, start: int = 0):
    """方向键菜单. 返回下标或None(返回/取消). 首尾循环."""
    idx = max(0, min(start, len(labels) - 1))
    while True:
        sys.stdout.write("\x1b[2J\x1b[H")
        print("== %s ==" % title)
        for i, lab in enumerate(labels):
            mark = "> " if i == idx else "  "
            print("%s%d. %s" % (mark, i + 1, lab))
        print(_("pick_keys"))
        sys.stdout.flush()
        k = _getkey()
        if k == "up":
            idx = (idx - 1) % len(labels)
        elif k == "down":
            idx = (idx + 1) % len(labels)
        elif k in ("enter", "right"):
            return idx
        elif k in ("esc", "left", "q"):
            return None


def run_cmd(cmd):
    print(_("run_exec") + " ".join(cmd[3:]))
    print(_("run_stop"))
    proc = subprocess.Popen(cmd, cwd=ROOT)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print(_("run_stopping"))
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    print(_("run_exit") % proc.returncode)
    try:
        input(_("run_continue"))
    except (EOFError, KeyboardInterrupt):
        pass
    return proc.returncode


def build_cmd(mode: str, url: str, opts: dict):
    cmd = [PY, "-u", "-X", "utf8", "site_crawler.py", mode, url,
           str(int(opts.get("batch", 60)))]
    if opts.get("cdn"):
        cmd.append("--allow-cdn")
    if opts.get("http"):
        cmd.append("--allow-http")
    if opts.get("insecure"):
        cmd.append("--insecure")
    if opts.get("browser"):
        cmd += ["--browser", opts["browser"]]
    if opts.get("clone"):
        src = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                           "Google", "Chrome", "User Data")
        if os.path.isdir(src):
            cmd += ["--clone-profile", src]
        else:
            print(_("clone_miss"))
    if opts.get("proxy"):
        cmd += ["--proxy", opts["proxy"]]
    if opts.get("column"):
        cmd += ["--column", opts["column"]]
    if opts.get("video"):
        cmd.append("--video-first")
    else:
        cmd.append("--no-video-first")
    if opts.get("spoof"):
        cmd += ["--spoof", opts["spoof"]]
    if opts.get("spoof_referer"):
        cmd += ["--spoof-referer", opts["spoof_referer"]]
    if opts.get("snapshot"):
        cmd += ["--snapshot", opts["snapshot"]]
    if opts.get("softwall"):
        cmd += ["--softwall", opts["softwall"]]
    if opts.get("text_proxy"):
        cmd += ["--text-proxy", opts["text_proxy"]]
    if opts.get("hls_key"):
        cmd += ["--hls-key", opts["hls_key"]]
    if opts.get("lock"):
        cmd += ["--lock-session"]
    if opts.get("hijack"):
        cmd += ["--hijack-check"]
    if opts.get("lang") and opts.get("lang") != "auto":
        cmd += ["--lang", opts["lang"]]
    if not opts.get("learn", True):
        cmd += ["--no-learn"]
    if mode in ("watch", "dl"):
        cmd += ["--dl-jobs", str(int(opts.get("jobs", 3)))]
    return cmd


def action_page(url: str, opts: dict):
    host = url.split("//", 1)[-1].split("/", 1)[0]
    while True:
        root = os.path.join(ROOT, "sites", host)
        files, total, rows = site_stats(root)
        tg, st = _("act_toggle"), _("act_set")
        r = pick(
            _("fmt_stats", host, files, fmt_size(total), rows),
            [((_("m_auto"), "auto")),
             ((_("m_check"), "check")),
             ((_("m_wait"), "wait")),
             ((_("m_dl"), "dl")),
             ((_("m_watch"), "watch")),
             ((_("m_nav"), "nav")),
             ((_("m_purge"), "purge")),
             ((_("m_verify"), "verify")),
             ((_("m_replay"), "replay")),
             ((_("m_envcheck"), "envcheck")),
             ((_("m_updatecheck"), "updatecheck")),
             ((_("fmt_opt", _("L_cdn"), _onoff(opts["cdn"]), tg), "t_cdn")),
             ((_("fmt_opt", _("L_http"), _onoff(opts["http"]), tg), "t_http")),
             ((_("fmt_opt", _("L_ins"), _onoff(opts["insecure"]), tg), "t_ins")),
             ((_("fmt_opt", _("L_browser"),
                 opts["browser"] or _("v_browser_default"), tg), "t_browser")),
             ((_("fmt_opt", _("L_clone"), _onoff(opts["clone"]), tg), "t_clone")),
             ((_("fmt_opt", _("L_proxy"), opts["proxy"] or _("v_none"), st),
               "t_proxy")),
             ((_("fmt_opt", _("L_column"), opts["column"] or _("v_none"), st),
               "t_column")),
             ((_("fmt_opt", _("L_spoof"), opts["spoof"] or "off", tg), "t_spoof")),
             ((_("fmt_opt", _("L_spoofref"), opts["spoof_referer"] or _("v_none"),
                 st), "t_spoofref")),
             ((_("fmt_opt", _("L_snap"), opts["snapshot"] or "off", tg), "t_snap")),
             ((_("fmt_opt", _("L_soft"), opts["softwall"] or "off", tg), "t_soft")),
             ((_("fmt_opt", _("L_textpx"), opts["text_proxy"] or _("v_none"), st),
               "t_textpx")),
             ((_("fmt_opt", _("L_hlskey"), opts["hls_key"] or _("v_none"), st),
               "t_hlskey")),
             ((_("fmt_opt", _("L_video"), _onoff(opts["video"]), tg), "t_video")),
             ((_("fmt_opt", _("L_lock"), _onoff(opts["lock"]), tg), "t_lock")),
             ((_("fmt_opt", _("L_hijack"), _onoff(opts["hijack"]), tg), "t_hijack")),
             ((_("fmt_repin"), "t_repin")),
             ((_("fmt_opt", _("L_learn"), _onoff(opts.get("learn", True)), tg),
               "t_learn")),
             ((_("fmt_opt", _("L_lang"), opts.get("lang", "auto"), tg), "t_lang")),
             ((_("fmt_opt", _("L_batch"), opts["batch"], st), "t_batch")),
             ((_("fmt_opt", _("L_jobs"), opts["jobs"], st), "t_jobs")),
             ])
        if r is None:
            return
        if r == "t_cdn":
            opts["cdn"] = not opts["cdn"]
            continue
        if r == "t_http":
            opts["http"] = not opts["http"]
            continue
        if r == "t_ins":
            opts["insecure"] = not opts["insecure"]
            continue
        if r == "t_browser":
            order = ["", "chrome", "edge", "camoufox"]
            opts["browser"] = order[(order.index(opts["browser"]) + 1) % len(order)] \
                if opts["browser"] in order else "camoufox"
            continue
        if r == "t_clone":
            opts["clone"] = not opts["clone"]
            continue
        if r == "t_proxy":
            try:
                opts["proxy"] = input(_("p_proxy")).strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_spoof":
            order = ["", "googlebot", "bingbot", "mobile"]
            opts["spoof"] = order[(order.index(opts["spoof"]) + 1) % len(order)] \
                if opts["spoof"] in order else "googlebot"
            continue
        if r == "t_spoofref":
            try:
                opts["spoof_referer"] = input(_("p_spoofref")).strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_snap":
            order = ["", "wayback", "archive", "auto"]
            opts["snapshot"] = order[(order.index(opts["snapshot"]) + 1) % len(order)] \
                if opts["snapshot"] in order else "wayback"
            continue
        if r == "t_soft":
            order = ["", "strip", "reader"]
            opts["softwall"] = order[(order.index(opts["softwall"]) + 1) % len(order)] \
                if opts["softwall"] in order else "strip"
            continue
        if r == "t_textpx":
            try:
                opts["text_proxy"] = input(_("p_textpx")).strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_hlskey":
            try:
                opts["hls_key"] = input(_("p_hlskey")).strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_column":
            try:
                opts["column"] = input(_("p_column")).strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_video":
            opts["video"] = not opts["video"]
            continue
        if r == "t_lock":
            opts["lock"] = not opts["lock"]
            continue
        if r == "t_hijack":
            opts["hijack"] = not opts["hijack"]
            continue
        if r == "t_repin":
            try:
                _yn = input(_("p_repin")).strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if _yn != "YES":
                print(_("p_cancelled"))
                continue
            _cmd = build_cmd("check", url, opts) + ["--repin"]
            run_cmd(_cmd)
            continue
        if r == "replay":
            try:
                _yn = input(_("p_replay")).strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if _yn != "YES":
                print(_("p_cancelled"))
                continue
        if r == "t_learn":
            opts["learn"] = not opts.get("learn", True)
            continue
        if r == "t_lang":
            order = ["auto", "zh", "en"]
            opts["lang"] = order[(order.index(opts.get("lang", "auto")) + 1)
                                 % len(order)] \
                if opts.get("lang", "auto") in order else "auto"
            set_lang(opts["lang"])
            continue
        if r == "t_batch":
            try:
                opts["batch"] = max(1, int(input(_("p_batch")).strip()))
            except (EOFError, KeyboardInterrupt, ValueError):
                pass
            continue
        if r == "t_jobs":
            try:
                opts["jobs"] = max(1, min(8, int(input(_("p_jobs")).strip())))
            except (EOFError, KeyboardInterrupt, ValueError):
                pass
            continue
        run_cmd(build_cmd(r, url, opts))


def site_page(opts: dict):
    while True:
        sdir = os.path.join(ROOT, "sites")
        sites = []
        try:
            sites = sorted(x for x in os.listdir(sdir)
                           if os.path.isdir(os.path.join(sdir, x)))
        except Exception:
            pass
        items = []
        for s in sites:
            files, total, rows = site_stats(os.path.join(sdir, s))
            items.append((_("fmt_site", s, files, fmt_size(total)), s))
        items.append((_("p_newsite"), "__new__"))
        r = pick(_("p_sites", len(sites)), items)
        if r is None:
            return
        if r == "__new__":
            try:
                u = input(_("p_newurl")).strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if not u.startswith(("http://", "https://")):
                print(_("p_urlerr"))
                continue
            action_page(u, opts)
        else:
            action_page("https://" + r + "/", opts)


def main() -> int:
    lang = "auto"
    try:
        for i, a in enumerate(sys.argv):
            if a == "--lang" and i + 1 < len(sys.argv):
                lang = sys.argv[i + 1]
    except Exception:
        pass
    set_lang(lang)
    import site_crawler as _sc
    ver = getattr(_sc, "__version__", "?")
    opts = {"cdn": True, "http": False, "batch": 60, "proxy": "", "column": "",
            "video": True, "jobs": 3, "insecure": False, "browser": "",
            "clone": False, "spoof": "", "spoof_referer": "", "snapshot": "",
            "softwall": "", "text_proxy": "", "hls_key": "", "lock": False,
            "hijack": False, "learn": True, "lang": lang}
    print(_("tui_title", ver))
    site_page(opts)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(0)
