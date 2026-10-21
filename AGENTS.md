# auto_site_dl — AI Maintainer & Agent Guide (AGENTS.md)

> **Project Identity**: High-resilience, automated media crawler and site archiver featuring human-in-the-loop CAPTCHA detection, video stream deep-diving, TUI interface, and a red-team verified security sandbox.
> **Language**: Python 3.9+ (Zero async bloat, sync Playwright / Camoufox / Requests)
> **License**: Apache-2.0

---

## 🎯 Architecture & Core Modules

```
User / CLI / TUI (tui.py)
       │
       ▼
site_crawler.py  ──►  Security Sandbox (SSRF / DNS re-check / TLS Pinning)
       │         ──►  Browser Layer (Camoufox C++ fingerprint / Real Chrome)
       │         ──►  Human-in-the-Loop CAPTCHA Gate (detect_verify / wait)
       │
       ▼
watchflow.py     ──►  Video Deep-Dive State Machine (Cover -> Watch -> Real Stream)
                 ──►  Threaded Parallel Downloader Pool (dl-jobs 1-8)
```

- **`site_crawler.py`**: Monolithic, self-contained core runtime. Implements state machine (`auto`, `check`, `wait`, `dl`, `nav`, `purge`), security boundaries, download engines, and learning cache.
- **`watchflow.py`**: Video stream extraction pipeline handling lazy-loaded players, network interception, and HLS/m3u8 stream resolution.
- **`tui.py`**: Pure Python standard-library interactive Terminal UI (bilingual, zero curses/external dependency).
- **`tests/test_security.py`**: Comprehensive red-team security regression test suite (426 tests, 100% offline, zero network dependency).

---

## ⚡ Standard Verification & Regression Suite

Before committing or pushing any modification to this repository, an AI agent **MUST** run:

```powershell
# 1. Security Regression Gate (Must pass 426/426 tests with exit 0)
python -u -X utf8 tests\test_security.py

# 2. Syntax compilation across all core modules
python -X utf8 -m py_compile site_crawler.py watchflow.py tui.py i18n.py

# 3. Environment diagnostic check
python -u -X utf8 site_crawler.py envcheck
```

---

## 🛑 Strict Iron Laws for AI Maintainers

1. **Test Integrity Rule (Zero Weakening)**:
   - `tests/test_security.py` is the red-team regression gate. If any assertion fails during development: **FIX THE CODE, NEVER WEAKEN THE TEST**.
2. **Legal & Security Boundaries (Non-negotiable)**:
   - Do NOT implement automated CAPTCHA bypassing, OCR cracking, or DRM breaking. Human-in-the-loop (`wait` mode) is the intentional, ethical boundary.
   - All network calls must pass through the security perimeter (SSRF prevention, private IP blocking unless explicitly overridden).
3. **Encoding & Execution**:
   - Always invoke Python with `-X utf8` to prevent Windows GBK terminal encoding corruption.
