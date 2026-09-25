# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 jjjjjjjjnnjnn
"""视频深层流程: 点封面 -> 点观看 -> 等加载 -> 下真流.

自适应状态机(预算50s, 早退):
  播即走(已有可播流直接拿) -> 剥遮罩+点播放 -> 点封面 -> 点线路tab ->
  轮询点跳过 -> 分片反推m3u8. 假缓冲(STILL)识别3轮止损.
收获串行(守礼貌) + 下载并行(--dl-jobs 线程池, CSV记账加锁).
广告拦截: 广告域名路由 abort + 弹窗页自关 + 分片广告关键字过滤.

用法: python -u -X utf8 site_crawler.py watch <url> [batch] [--dl-jobs N] ...
"""
import argparse
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

DETAIL_PAT = re.compile(r"detail|/vod/|/video/|/p/\d|watch\?|/play/", re.I)
PLAY_PAT = re.compile(r"play|/vod/play|player|watch", re.I)
PLAY_TEXT = ["播放", "立即播放", "在线观看", "开始播放", "▶", "播放视频",
             "Play", "PLAY", "观看"]
SKIP_TEXT = ["跳过", "跳过广告", "Skip", "SKIP", "关闭", "×", "X", "继续观看"]
LINE_TEXT = ["线路", "源", "HD", "高清", "线路1", "线路2", "源1", "源2",
             "Line", "Source"]
STALL_TEXT = ["缓冲", "加载中", "loading", "buffer", "下载APP", "下载App",
              "APP", "安装", "请安装"]
_STALL_NORM = [s.lower().replace(" ", "") for s in STALL_TEXT]
AD_HOSTS = ["doubleclick", "googlesyndication", "popads", "adserver",
            "advert", "preroll", "tracking", "analytics", "pushsdk",
            "hmtracker", "umeng", "51.la"]
_TOKEN_Q_RE = re.compile(r"[?&](token|expires?|sign|auth|sig|deadline)=", re.I)

STRIP_JS = """() => {
  const sels = ['.modal', '.popup', '.overlay-full', '.ad-cover',
                '[id*=ad][id*=cover]', '[class*=ad-cover]'];
  for (const s of sels) {
    document.querySelectorAll(s).forEach(e => {
      const r = e.getBoundingClientRect();
      if (r.width > innerWidth * 0.5 && r.height > innerHeight * 0.5) e.remove();
    });
  }
}"""


def is_ad_host(url: str) -> bool:
    u = (url or "").lower()
    return any(h in u for h in AD_HOSTS)


def resolve_from_segments(urls):
    """分片反推m3u8(纯逻辑, 不联网): 取ts/m4s公共前缀, 拼 index.m3u8 候选."""
    segs = [u for u in (urls or [])
            if re.search(r"\.(ts|m4s)(\?|$)", u, re.I)]
    if not segs:
        return ""
    first = segs[0]
    base = first.rsplit("/", 1)[0] + "/"
    return urljoin(base, "index.m3u8")


def _video_state(page):
    """播放器状态: paused/currentTime/readyState/有无src."""
    try:
        return page.evaluate("""() => {
          const v = document.querySelector('video');
          if (!v) return {has: false};
          return {has: true, paused: v.paused, t: v.currentTime || 0,
                  rs: v.readyState || 0,
                  src: v.currentSrc || v.src || ''};
        }""") or {"has": False}
    except Exception:
        return {"has": False}


def _player_text(page):
    try:
        t = page.evaluate(
            "() => (document.body ? document.body.innerText.slice(0,4000) : '')")
        return t or ""
    except Exception:
        return ""


def _click_cover(page, C, site) -> bool:
    """点封面: video海报区 / 大播放按钮 / 含播放文字的可点元素."""
    try:
        v = page.query_selector("video")
        if v and C.human_click(page, v, timeout=4000):
            return True
    except Exception:
        pass
    try:
        _rsel = C.site_rules(site).get("watch_button_selector") or []
    except Exception:
        _rsel = []
    for sel in (list(_rsel) + ["[class*=play-btn]", "[class*=playBtn]",
                               "[class*=big-play]", ".vjs-big-play-button",
                               "[id*=playBtn]"]):
        try:
            el = page.query_selector(sel)
            if el and C.human_click(page, el, timeout=3000):
                return True
        except Exception:
            pass
    try:
        for el in page.query_selector_all("a,button,div,span")[:400]:
            try:
                t = (el.inner_text() or "").strip()
            except Exception:
                continue
            if t in PLAY_TEXT and el.is_visible():
                if C.human_click(page, el, timeout=3000):
                    return True
    except Exception:
        pass
    return False


def _try_skip(page, C) -> bool:
    hit = False
    try:
        for el in page.query_selector_all("a,button,div,span")[:400]:
            try:
                t = (el.inner_text() or "").strip()
            except Exception:
                continue
            if t in SKIP_TEXT and el.is_visible():
                if C.human_click(page, el, timeout=3000):
                    hit = True
                    break
    except Exception:
        pass
    return hit


def _click_line(page, C) -> bool:
    try:
        for el in page.query_selector_all("a,button,li,div,span")[:500]:
            try:
                t = (el.inner_text() or "").strip()
            except Exception:
                continue
            if t in LINE_TEXT and el.is_visible():
                if C.human_click(page, el, timeout=3000):
                    return True
    except Exception:
        pass
    return False


def _collect_media(page, C, site, base):
    """当前页可播流: video/source直链 + m3u8正则."""
    out = []
    try:
        data = page.evaluate(C.JS_HARVEST)
    except Exception:
        data = {}
    for key in ("vid", "src"):
        for s in (data or {}).get(key, []) or []:
            u = C.norm_media(site, base, s)
            if u and site.media_ok(u):
                out.append(u)
    try:
        html = page.content()
    except Exception:
        html = ""
    for m in re.findall(r"https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*", html):
        u = C.norm_url(m)
        if u and site.media_ok(u):
            out.append(u)
    return sorted(set(out))


def watch_one(site, page, idx: int, referer: str, budget: int = 50, sess=None):
    """单视频自适应取流. 返回 (media_url, kind). kind: direct/m3u8/segments/''."""
    import site_crawler as C
    t0 = time.time()
    stall_rounds = 0
    last_t = -1.0
    try:
        page.evaluate(STRIP_JS)
    except Exception:
        pass
    while time.time() - t0 < budget:
        st = _video_state(page)
        if st.get("has") and not st.get("paused", True) and st.get("t", 0) > 0.5:
            src = st.get("src", "")
            u = C.norm_media(site, referer, src) if src else ""
            if u and site.media_ok(u):
                if u.lower().endswith(".m3u8"):
                    return u, "m3u8"
                return u, "direct"
        media = _collect_media(page, C, site, referer)
        for u in media:
            if u.lower().endswith(".m3u8"):
                return u, "m3u8"
        if media:
            return media[0], "direct"
        txt = _player_text(page).lower().replace(" ", "")
        if any(k in txt for k in _STALL_NORM):
            stall_rounds += 1
            if stall_rounds >= 3:
                site.log("假缓冲(APP引流)止损: %s" % C.url_for_log(referer))
                site.bump("watch_stall")
                break
        else:
            stall_rounds = 0
        if _try_skip(page, C):
            C.think(page, 1500)
            continue
        if _click_cover(page, C, site):
            C.think(page, 2500)
            continue
        if _click_line(page, C):
            C.think(page, 2500)
            continue
        try:
            st2 = _video_state(page)
            if st2.get("has") and abs(st2.get("t", 0) - last_t) < 0.01:
                C.think(page, 2000)
            last_t = st2.get("t", 0)
        except Exception:
            pass
        C.think(page, 1500)
    site.bump("watch_empty")
    return "", ""


class LockedWriter:
    """线程池下载记账锁: 收获串行, 下载并行, 写CSV串行."""
    def __init__(self, site):
        self.site = site
        self.lock = threading.Lock()
        self.idx = [0]

    def next_idx(self) -> int:
        with self.lock:
            import site_crawler as C
            if self.idx[0] == 0:
                self.idx[0] = C._next_idx(self.site)
            v = self.idx[0]
            self.idx[0] += 1
            return v

    def save(self, kind, url, referer, sess=None):
        import site_crawler as C
        i = self.next_idx()
        with self.lock:
            if kind == "m3u8":
                return C.fetch_m3u8(self.site, url, i, referer)
            return C.fetch_one(self.site, sess, url, i, referer, "watch")


def cmd_watch(site, batch: int = 10, dl_jobs: int = 3) -> int:
    """watch模式: 列表页收详情链(串行) -> 逐个取流 -> 线程池下载."""
    import site_crawler as C
    site.log("TARGET=%s MODE=watch v%s jobs=%d" % (site.url, C.__version__, dl_jobs))
    if C.preflight(site) == 2:
        return 2
    if not C._disk_ok(site.dl):
        site.log("WARNING 磁盘剩余不足500MB, 仍继续(可能中途失败)")
    sess, kind = C.make_session(site)
    site.log("下载层: " + kind)
    try:
        site.ensure_robots(sess)
    except Exception:
        pass
    p, _ = C.eff_proxy(site, "browser")
    pw, browser, ctx, page = None, None, None, None
    try:
        pw, browser, ctx, page = C.open_ctx(site, True, p)
    except Exception as e:
        site.log("浏览器启动失败 诊断: " + C.diagnose_nav_error(str(e)))
        return 2
    try:
        ctx.route("**/*", lambda r: r.abort()
                  if is_ad_host(r.request.url) else r.continue_())
    except Exception:
        pass
    try:
        ctx.on("page", lambda pg: (pg.close() if pg != page else None))
    except Exception:
        pass
    bucket = []  # 网络层捕获: 列表页路过的直链流
    C._attach_capture(page, site, bucket)
    details, seen = [], set()
    url = site.url
    try:
        for _ in range(max(1, min(batch, 30))):
            if not url or url in seen:
                break
            seen.add(url)
            if C._goto(page, site, url):
                break
            C.settle_lazy_load(page, site)
            nv, _ = C.detect_verify(page, site)
            if nv:
                site.log("REVERIFY 又出现验证, 停止. 请重跑 wait.")
                site.summary()
                return 4
            try:
                hrefs = page.evaluate(
                    "() => Array.from(document.querySelectorAll('a[href]'))"
                    ".map(e => e.href || '')")
            except Exception:
                hrefs = []
            for h in hrefs or []:
                u = C.norm_link(site, url, h)
                if u and DETAIL_PAT.search(u) and u not in seen \
                        and site.column_ok(u) and len(details) < batch:
                    seen.add(u)
                    details.append(u)
            url = C.find_next(page, url) or ""
            C.polite_sleep(site)
        site.log("watch 收获详情页%d" % len(details))
        jobs = []
        for d in details:
            if not C._browser_guard(site, d):
                continue
            try:
                page.goto(d, wait_until="domcontentloaded", timeout=30000)
                C.think(page, 1000)
            except Exception:
                continue
            nv, _ = C.detect_verify(page, site)
            if nv:
                site.log("REVERIFY 又出现验证, 停止. 请重跑 wait.")
                break
            C.log_softwall(site, C.apply_softwall(page, site))  # 路径三: 遮罩挡播放先清
            mu, mkind = watch_one(site, page, 0, d, 50, sess)
            if mu:
                if mkind == "m3u8" and _TOKEN_Q_RE.search(mu):
                    jobs.insert(0, (mkind, mu, d))
                    site.bump("token-fastpath")
                else:
                    jobs.append((mkind, mu, d))
            C.polite_sleep(site)
        seen_urls = {u for _, u, _ in jobs}
        for u in bucket:
            if u not in seen_urls:
                seen_urls.add(u)
                _k = "m3u8" if u.lower().endswith(".m3u8") else "direct"
                if _k == "m3u8" and _TOKEN_Q_RE.search(u):
                    jobs.insert(0, (_k, u, site.url))
                    site.bump("token-fastpath")
                else:
                    jobs.append((_k, u, site.url))
        site.log("watch 取到流%d, 并行下载…" % len(jobs))
        lw = LockedWriter(site)
        with ThreadPoolExecutor(max_workers=max(1, min(8, dl_jobs))) as ex:
            futs = [ex.submit(lw.save, k, u, r, sess) for k, u, r in jobs]
            for f in futs:
                try:
                    f.result()
                except Exception:
                    pass
    finally:
        C.close_ctx(pw, browser, ctx)
    site.summary()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="watchflow.py")
    ap.add_argument("url", nargs="?", default="")
    ap.add_argument("batch", nargs="?", type=int, default=10)
    ap.add_argument("--allow-cdn", action="store_true")
    ap.add_argument("--allow-http", action="store_true")
    ap.add_argument("--proxy", default="")
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--browser", default="",
                    choices=["", "chromium", "chrome", "edge", "camoufox"])
    ap.add_argument("--clone-profile", default="")
    ap.add_argument("--column", default="")
    ap.add_argument("--video-first", dest="video_first", action="store_const",
                    const=True, default=None)
    ap.add_argument("--no-video-first", dest="video_first", action="store_const",
                    const=False)
    ap.add_argument("--dl-jobs", type=int, default=3,
                    help="下载并发1-8, 0=按CPU自动")
    a = ap.parse_args(argv)
    if not a.url:
        ap.error("需要目标URL")
    if not re.match(r"^https?://", a.url.strip()):
        print("URL 必须以 http(s):// 开头")
        return 2
    import site_crawler as C
    try:
        site = C.Site(a.url.strip(), a)
    except ValueError as e:
        print("非法目标主机: %s" % e)
        return 2
    return cmd_watch(site, a.batch, C._auto_jobs(a.dl_jobs))


if __name__ == "__main__":
    sys.exit(main())
