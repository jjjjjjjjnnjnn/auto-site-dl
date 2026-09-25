# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 jjjjjjjjnnjnn
"""终端交互UI(纯标准库): 三层菜单, 子进程前台运行, Ctrl+C 停止任务.

站点页 -> 操作页 -> 运行(跟日志).
数字 选择, Enter 确认, q 返回.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
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


def pick(title: str, items):
    """items: [(显示, 值)]. 返回值或None(q退出). 支持数字快捷键."""
    print("\n== %s ==" % title)
    for i, (label, _) in enumerate(items, 1):
        print("  %d. %s" % (i, label))
    print("  q. 返回")
    while True:
        try:
            s = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if s in ("q", "quit", "exit"):
            return None
        if s.isdigit() and 1 <= int(s) <= len(items):
            return items[int(s) - 1][1]
        print("输入序号或 q")


def run_cmd(cmd):
    print("执行: " + " ".join(cmd[3:]))
    print("(Ctrl+C 停止)")
    proc = subprocess.Popen(cmd, cwd=ROOT)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n正在停止…")
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    print("退出码: %d" % proc.returncode)
    try:
        input("回车继续…")
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
            print("⚠ 未找到本机 Chrome profile, 跳过克隆")
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
    if mode == "watch":
        cmd += ["--dl-jobs", str(int(opts.get("jobs", 3)))]
    return cmd


def action_page(url: str, opts: dict):
    host = url.split("//", 1)[-1].split("/", 1)[0]
    while True:
        root = os.path.join(ROOT, "sites", host)
        files, total, rows = site_stats(root)
        r = pick(
            "%s (文件%d %s 记账%d行)" % (host, files, fmt_size(total), rows),
            [(("🚀 全流程 auto", "auto")),
             (("🔍 检测 check", "check")),
             (("🪟 人工验证 wait", "wait")),
             (("⬇ 下载 dl", "dl")),
             (("🎬 深层视频 watch", "watch")),
             (("🧭 栏目测绘 nav", "nav")),
             (("🧹 清扫 purge", "purge")),
             (("🩺 环境自检 envcheck", "envcheck")),
             (("⚙ CDN媒体: %s (切)" % ("开" if opts["cdn"] else "关"), "t_cdn")),
             (("⚙ 允许http: %s (切)" % ("开" if opts["http"] else "关"), "t_http")),
             (("⚠ 忽略证书: %s (切)" % ("开" if opts["insecure"] else "关"), "t_ins")),
             (("⚙ 浏览器: %s (切)" % (opts["browser"] or "chromium"), "t_browser")),
             (("⚙ 克隆profile: %s (切)" % ("开" if opts["clone"] else "关"), "t_clone")),
             (("⚙ 中转代理: %s (设)" % (opts["proxy"] or "无"), "t_proxy")),
              (("⚙ 栏目过滤: %s (设)" % (opts["column"] or "无"), "t_column")),
              (("⚙ 伪装: %s (切)" % (opts["spoof"] or "off"), "t_spoof")),
              (("⚙ 伪装Referer: %s (设)" % (opts["spoof_referer"] or "无"),
                "t_spoofref")),
              (("⚙ 快照: %s (切)" % (opts["snapshot"] or "off"), "t_snap")),
              (("⚙ 干预: %s (切)" % (opts["softwall"] or "off"), "t_soft")),
              (("⚙ 文本代理: %s (设)" % (opts["text_proxy"] or "无"),
                "t_textpx")),
              (("⚙ HLS密钥: %s (设)" % (opts["hls_key"] or "无"),
                "t_hlskey")),
             (("⚙ 视频优先: %s (切)" % ("开" if opts["video"] else "关"), "t_video")),
             (("⚙ 每轮页数: %d (设)" % opts["batch"], "t_batch")),
             (("⚙ 下载并发: %d (设)" % opts["jobs"], "t_jobs")),
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
                opts["proxy"] = input("代理URL(空=清除): ").strip()
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
                opts["spoof_referer"] = input("伪装Referer(空=清除): ").strip()
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
                opts["text_proxy"] = input("文本代理前缀(空=清除): ").strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_hlskey":
            try:
                opts["hls_key"] = input("HLS密钥 URI[,IV](空=清除): ").strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_column":
            try:
                opts["column"] = input("栏目子串(空=清除): ").strip()
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if r == "t_video":
            opts["video"] = not opts["video"]
            continue
        if r == "t_batch":
            try:
                opts["batch"] = max(1, int(input("每轮页数: ").strip()))
            except (EOFError, KeyboardInterrupt, ValueError):
                pass
            continue
        if r == "t_jobs":
            try:
                opts["jobs"] = max(1, min(8, int(input("下载并发1-8: ").strip())))
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
            items.append(("%s (文件%d %s)" % (s, files, fmt_size(total)), s))
        items.append(("＋ 新网址", "__new__"))
        r = pick("站点 (共%d)" % len(sites), items)
        if r is None:
            return
        if r == "__new__":
            try:
                u = input("网址(https://…): ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if not u.startswith(("http://", "https://")):
                print("URL 必须以 http(s):// 开头")
                continue
            action_page(u, opts)
        else:
            action_page("https://" + r + "/", opts)


def main() -> int:
    opts = {"cdn": True, "http": False, "batch": 60, "proxy": "", "column": "",
            "video": True, "jobs": 3, "insecure": False, "browser": "",
            "clone": False, "spoof": "", "spoof_referer": "", "snapshot": "",
            "softwall": "", "text_proxy": "", "hls_key": ""}
    print("auto_site_dl TUI v1.5.0 (q 返回, Ctrl+C 停止任务)")
    site_page(opts)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(0)
