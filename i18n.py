# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 jjjjjjjjnnjnn
"""i18n(纯标准库): 系统语言探测, zh/en 双语, 缺键回退英语.

优先级: --lang 显式 > cfg lang > 环境 LANG/LANGUAGE > 系统 locale > 英语.
仅 zh/en 有译表; 其他系统语言一律回退英语(按需求).
site_crawler 引擎日志暂保持中文(增量覆盖中), TUI 已全量双语.
"""
import ctypes
import locale
import os

SUPPORTED = ("zh", "en")

STRINGS = {
    "zh": {
        "tui_title": "auto_site_dl TUI v%s (q 返回, Ctrl+C 停止任务)",
        "pick_back": "  q. 返回",
        "pick_hint": "输入序号或 q",
        "pick_keys": "↑↓ 移动  →/Enter 确认  ←/Esc 返回  q 退出",
        "run_exec": "执行: ",
        "run_stop": "(Ctrl+C 停止)",
        "run_stopping": "\n正在停止…",
        "run_exit": "退出码: %d",
        "run_continue": "回车继续…",
        "clone_miss": "⚠ 未找到本机 Chrome profile, 跳过克隆",
        "m_auto": "🚀 全流程 auto",
        "m_check": "🔍 检测 check",
        "m_wait": "🪟 人工验证 wait",
        "m_dl": "⬇ 下载 dl",
        "m_watch": "🎬 深层视频 watch",
        "m_nav": "🧭 栏目测绘 nav",
        "m_purge": "🧹 清扫 purge",
        "m_verify": "✅ 离线自证 verify",
        "m_replay": "☠ 会话重放自测 replay(需YES确认)",
        "m_envcheck": "🩺 环境自检 envcheck",
        "m_updatecheck": "🔄 检查更新 updatecheck",
        "v_on": "开",
        "v_off": "关",
        "v_none": "无",
        "v_browser_default": "chromium",
        "fmt_opt": "⚙ %s: %s (%s)",
        "fmt_repin": "⚠ 证书重钉 repin(跑check)",
        "act_toggle": "切",
        "act_set": "设",
        "L_cdn": "CDN媒体",
        "L_http": "允许http",
        "L_ins": "忽略证书",
        "L_browser": "浏览器",
        "L_clone": "克隆profile",
        "L_proxy": "中转代理",
        "L_column": "栏目过滤",
        "L_spoof": "伪装",
        "L_spoofref": "伪装Referer",
        "L_snap": "快照",
        "L_soft": "干预",
        "L_textpx": "文本代理",
        "L_hlskey": "HLS密钥",
        "L_video": "视频优先",
        "L_lock": "会话独占锁",
        "L_hijack": "劫持检测",
        "L_batch": "每轮页数",
        "L_jobs": "下载并发",
        "L_learn": "自学习",
        "L_lang": "语言/Language",
        "fmt_stats": "%s (文件%d %s 记账%d行)",
        "fmt_site": "%s (文件%d %s)",
        "p_proxy": "代理URL(空=清除): ",
        "p_spoofref": "伪装Referer(空=清除): ",
        "p_textpx": "文本代理前缀(空=清除): ",
        "p_hlskey": "HLS密钥 URI[,IV](空=清除): ",
        "p_column": "栏目子串(空=清除): ",
        "p_batch": "每轮页数: ",
        "p_jobs": "下载并发1-8: ",
        "p_repin": "确认站方换证合法？输入 YES 重钉：",
        "p_replay": "☠ 确认目标为自有/已授权站？只发GET。输入 YES 继续：",
        "p_cancelled": "已取消",
        "p_newurl": "网址(https://…): ",
        "p_urlerr": "URL 必须以 http(s):// 开头",
        "p_sites": "站点 (共%d)",
        "p_newsite": "＋ 新网址",
        "upd_avail": "发现新版本 %s(当前 %s)：请手动 git pull 更新，本工具永不自动下载",
        "upd_ok": "已是最新 %s",
        "upd_fail": "更新检查失败(网络/代理)：%s",
    },
    "en": {
        "tui_title": "auto_site_dl TUI v%s (q back, Ctrl+C to stop)",
        "pick_back": "  q. Back",
        "pick_hint": "Enter number or q",
        "pick_keys": "Up/Down move  Right/Enter confirm  Left/Esc back  q quit",
        "run_exec": "Run: ",
        "run_stop": "(Ctrl+C to stop)",
        "run_stopping": "\nStopping…",
        "run_exit": "Exit code: %d",
        "run_continue": "Press Enter…",
        "clone_miss": "⚠ No local Chrome profile found, skip cloning",
        "m_auto": "🚀 Full auto",
        "m_check": "🔍 Probe check",
        "m_wait": "🪟 Manual verify wait",
        "m_dl": "⬇ Download dl",
        "m_watch": "🎬 Deep video watch",
        "m_nav": "🧭 Sitemap nav",
        "m_purge": "🧹 Purge",
        "m_verify": "✅ Offline verify",
        "m_replay": "☠ Session replay test (needs YES)",
        "m_envcheck": "🩺 Env check envcheck",
        "m_updatecheck": "🔄 Update check updatecheck",
        "v_on": "on",
        "v_off": "off",
        "v_none": "none",
        "v_browser_default": "chromium",
        "fmt_opt": "⚙ %s: %s (%s)",
        "fmt_repin": "⚠ Re-pin cert repin (runs check)",
        "act_toggle": "toggle",
        "act_set": "set",
        "L_cdn": "CDN media",
        "L_http": "Allow http",
        "L_ins": "Skip TLS verify",
        "L_browser": "Browser",
        "L_clone": "Clone profile",
        "L_proxy": "Proxy",
        "L_column": "Column filter",
        "L_spoof": "Spoof",
        "L_spoofref": "Spoof Referer",
        "L_snap": "Snapshot",
        "L_soft": "Softwall",
        "L_textpx": "Text proxy",
        "L_hlskey": "HLS key",
        "L_video": "Video first",
        "L_lock": "Session lock",
        "L_hijack": "Hijack check",
        "L_batch": "Pages/round",
        "L_jobs": "DL concurrency",
        "L_learn": "Self-learn",
        "L_lang": "语言/Language",
        "fmt_stats": "%s (%d files %s, %d ledger rows)",
        "fmt_site": "%s (%d files %s)",
        "p_proxy": "Proxy URL (empty=clear): ",
        "p_spoofref": "Spoof Referer (empty=clear): ",
        "p_textpx": "Text proxy prefix (empty=clear): ",
        "p_hlskey": "HLS key URI[,IV] (empty=clear): ",
        "p_column": "Column substring (empty=clear): ",
        "p_batch": "Pages per round: ",
        "p_jobs": "Concurrency 1-8: ",
        "p_repin": "Cert rotation confirmed legit? Type YES to re-pin: ",
        "p_replay": "☠ Confirm target is own/authorized? GET only. Type YES: ",
        "p_cancelled": "Cancelled",
        "p_newurl": "URL (https://…): ",
        "p_urlerr": "URL must start with http(s)://",
        "p_sites": "Sites (%d)",
        "p_newsite": "+ New URL",
        "upd_avail": "New version %s (current %s): run git pull manually, never auto-downloads",
        "upd_ok": "Already latest %s",
        "upd_fail": "Update check failed (network/proxy): %s",
    },
}

_LANG = "en"


def detect_system_lang() -> str:
    """系统语言探测: 仅 zh 回中文, 其余/失败一律英语(按需求回退英语)."""
    try:
        loc = (locale.getdefaultlocale()[0] or "")
        if loc.lower().startswith("zh"):
            return "zh"
    except Exception:
        pass
    try:
        lang = (os.environ.get("LANG") or "") + (os.environ.get("LANGUAGE") or "")
        if lang.lower().startswith("zh"):
            return "zh"
    except Exception:
        pass
    try:
        windll = ctypes.windll.kernel32  # noqa: F821 (仅 Windows 有 windll)
        lcid = int(windll.GetUserDefaultUILanguage())
        if (lcid & 0x3FF) in (0x04, 0x7C, 0x0C):
            return "zh"
    except Exception:
        pass
    return "en"


def resolve_lang(explicit: str = "") -> str:
    """显式值归一化: auto/空走系统探测; 未知值回英语."""
    try:
        v = (explicit or "").strip().lower()
    except Exception:
        return "en"
    if v in SUPPORTED:
        return v
    if v in ("", "auto", "default"):
        return detect_system_lang()
    return "en"


def set_lang(lang: str) -> str:
    global _LANG
    _LANG = resolve_lang(lang)
    return _LANG


def get_lang() -> str:
    return _LANG


def _(key: str, *a):
    """取串: 当前语言 -> 英语 -> key 本身. % 格式化失败回模板."""
    try:
        t = STRINGS.get(_LANG, {}).get(key)
        if t is None:
            t = STRINGS["en"].get(key, key)
        return t % a if a else t
    except Exception:
        try:
            return STRINGS["en"].get(key, key)
        except Exception:
            return key
