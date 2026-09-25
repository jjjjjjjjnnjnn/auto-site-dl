# 操作手册（MANUAL）

对应版本：v1.2.0 ｜ 适用系统：Windows 10/11（PowerShell）｜ Python ≥ 3.9

---

## 1. 安装与环境

```powershell
cd auto-site-dl
pip install -r requirements.txt
python -m playwright install chromium
python -m camoufox fetch          # 可选：--browser camoufox 要用它
```

外部引擎（按需安装，缺失自动降级）：

| 引擎 | 安装 | 缺失时 |
|---|---|---|
| ffmpeg | `winget install Gyan.FFmpeg` | m3u8 失去直录兜底 |
| yt-dlp | `pip install yt-dlp` 或放 `tools/` | m3u8 失去主力引擎 |
| N_m3u8DL-RE | GitHub Releases 或放 `tools/` | m3u8 跳过该引擎 |

装完先跑自检（纯本地，不碰目标站）：

```powershell
python -u -X utf8 site_crawler.py envcheck
```

逐行 `[OK]` 即正常；`[MISS]` 表示该项缺失、对应功能自动降级（见输出说明）。
只有 `python/requests/playwright-py/chromium` 缺失会导致 `FAIL`。

> 杀毒软件可能误报隔离 `.py` 文件（见 README 说明）：先把项目目录加入信任区。

---

## 2. TUI 使用（推荐）

```powershell
python -u -X utf8 tui.py
```

- **站点页**：列出 `sites/` 下已有站点（文件数/体积），或选 `＋ 新网址` 输入 `https://…`
- **操作页**：8 种模式 + 8 组开关。数字选择，`q` 返回
- **运行**：子进程前台执行，实时看输出；`Ctrl+C` 停止

开关说明：

| 开关 | 默认 | 说明 |
|---|---|---|
| CDN媒体 | 开 | 关=只收本站媒体 |
| 允许http | 关 | 开=允许 http 明文 |
| 忽略证书 | 关 | 仅可信内网/MITM 代理开 |
| 浏览器 | chromium | 循环切：chromium→chrome→edge→camoufox |
| 克隆profile | 关 | 开=克隆本机 Chrome profile（需先人工打开过目标站） |
| 中转代理 | 无 | 填 `http://`/`socks5h://host:port` |
| 栏目过滤 | 无 | 只爬 URL 含该子串的栏目 |
| 视频优先 | 开 | 关=图片视频全下 |
| 每轮页数 | 60 | dl/auto 上限 |
| 下载并发 | 3 | 仅 watch 生效（1–8） |

---

## 3. 命令行手册

### 3.1 标准流程（新站第一次）

```powershell
# 1) 检测
python -u -X utf8 site_crawler.py check https://example.com/
# OPEN      -> 直接第 3 步
# VERIFY-NEEDED(返回10) -> 第 2 步

# 2) 人工验证（弹浏览器，人过验证后自动存会话）
python -u -X utf8 site_crawler.py wait https://example.com/

# 3) 下载（断点续传，可反复跑）
python -u -X utf8 site_crawler.py dl https://example.com/ 60 --allow-cdn

# 或一步到位
python -u -X utf8 site_crawler.py auto https://example.com/ 60 --allow-cdn
```

### 3.2 视频站（列表只有封面、真流在播放页）

```powershell
python -u -X utf8 site_crawler.py watch https://example.com/ 10 --allow-cdn --dl-jobs 3
```

watch 干的事：列表页串行收详情链 → 逐个进页自适应取流（播即走→剥遮罩点播放→点封面→切线路→点跳过→分片反推，50s 预算早退，假缓冲 3 轮止损）→ 线程池并行下载。

### 3.3 测绘与诊断

```powershell
python -u -X utf8 site_crawler.py nav  https://example.com/   # 栏目清单 -> columns.txt
python -u -X utf8 site_crawler.py diag https://example.com/   # 媒体分布统计（不存文件）
```

### 3.4 清扫修复（纯本地）

```powershell
python -u -X utf8 site_crawler.py purge https://example.com/
```

按文件头魔数纠正扩展名、无魔数文件隔离到 `rejected/`、重写 `inventory.csv`（保留原列）。

### 3.5 常用组合

```powershell
# 强风控站：真浏览器 + 克隆登录态 + 代理
python -u -X utf8 site_crawler.py auto https://example.com/ 30 --browser chrome `
  --clone-profile "$env:LOCALAPPDATA\Google\Chrome\User Data" `
  --proxy socks5h://127.0.0.1:1080 --allow-cdn

# 只下某栏目视频
python -u -X utf8 site_crawler.py dl https://example.com/ 60 --allow-cdn --column vod/type

# 公司网/MITM 抓包环境（确认可信再用）
python -u -X utf8 site_crawler.py check https://example.com/ --insecure

# 只下图片（关视频优先）
python -u -X utf8 site_crawler.py dl https://example.com/ 60 --allow-cdn --no-video-first
```

---

## 4. 站点配置 `sites/<域名>/config.json`（可选）

命令行开关与配置做 OR 合并（更宽松一边生效）：

```json
{
  "batch": 60,
  "delay": 1.2,
  "allow_cdn": true,
  "allow_http": false,
  "video_first": true,
  "proxy": "socks5h://127.0.0.1:1080",
  "proxies": ["http://127.0.0.1:8081", "http://127.0.0.1:8082"],
  "tls_spoof": true,
  "insecure": false,
  "column": "vod/type",
  "ad_keywords": "advert|preroll",
  "lazy_rounds": 3,
  "browser": "camoufox",
  "clone_profile": "",
  "extra_verify_selectors": [".my-captcha"]
}
```

`proxies` ≥ 2 条时 `dl/check` 自动轮换（日志标 `rotated`）。

---

## 5. 退出码与日志

| 码 | 含义 | 动作 |
|---|---|---|
| 0 | 成功/无验证 | — |
| 1 | 等待验证超时 | 人工确认后重跑 |
| 2 | 环境缺失/代理已死/导航失败 | 看 `诊断:` 行，按提示修 |
| 3 | 会话未验证 | 跑 `wait` |
| 4 | 中途重现验证 | 跑 `wait` 后续传 |
| 10 | 需人机验证 | 跑 `wait`（`auto` 自动接） |

- 日志：`sites/<域名>/crawl.log`（URL 脱敏到 path，query 不落盘）
- 记账：`sites/<域名>/inventory.csv`（url,file,bytes,sha256,source）
- 每轮结束打 `SUMMARY` 计数 + 最多 3 条脱敏失败样本

---

## 6. 故障速查

| 现象 | 处理 |
|---|---|
| `ERR_CERT_AUTHORITY_INVALID` | 公司网/抓包代理；可信环境加 `--insecure`，否则装代理 CA |
| `ERR_NETWORK_ACCESS_DENIED`/直连失败 | 配 `--proxy`（优先 `socks5h`）；不配则自动读系统代理 |
| `PROXY-DEAD` | 代理没启动/端口错；开工前即拦下 |
| `CHECK … OPEN` 但下不到 | 看 `诊断:` 行；页面没加载出来会退出码 2 |
| `假缓冲(APP引流)` | 该线路是引流假流，程序切线路后止损；分片反推仍失败则此片无网页流 |
| 下的全是图片 | 视频优先被关了；或站只暴露封面，视频须走 `watch` |
| 文件无扩展名 | 旧版遗留；跑 `purge` 补 |
| `TLS伪装不可用(回落requests)` | 装 `pip install curl-cffi`（每进程只报一次） |
| 浏览器报毒/文件被隔离 | 杀毒软件误报；加信任区后从隔离区恢复 |

---

## 7. 日常维护

```powershell
python -u -X utf8 tests\test_security.py   # 回归：80 项全过 exit 0（改代码必跑）
python -X utf8 -m py_compile site_crawler.py watchflow.py tui.py
python -u -X utf8 site_crawler.py envcheck
```

- `sites/` 下的 `cookies.txt` 是会话凭证，不要外传、不要入库（`.gitignore` 已排除整个 `sites/`）
- 换机器：拷走 `sites/<域名>/cookies.txt` + `inventory.csv` 即可续传
