# 操作手册（MANUAL）

对应版本：v1.9.11 ｜ 适用系统：Windows 10/11（PowerShell）｜ Python ≥ 3.9

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
- **操作页**：11 种模式 + 20 组开关。终端里 `↑↓` 移动、`→`/`Enter` 确认、`←`/`Esc` 返回（光标位置会被记住）；管道/重定向时自动降级为数字行模式
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
| 伪装 | off | 循环切：off→googlebot→bingbot→mobile |
| 伪装Referer | 无 | 只收 http(s) |
| 快照 | off | 循环切：off→wayback→archive→auto |
| 干预 | off | 循环切：off→strip→reader |
| 文本代理 | 无 | 通用前缀，不内置第三方 |
| HLS密钥 | 无 | `URI[,IV]` 透传 |
| 视频优先 | 开 | 关=图片视频全下 |
| 会话独占锁 | 关 | 防并发写 cookies.txt |
| 劫持检测 | 关 | TOFU 证书钉扎 |
| 证书重钉 | — | 跑 check + `--repin`（需输入 YES） |
| 一键视频配置 | — | 动作项：收敛为拿视频组合（开 CDN/视频优先，关伪装/快照/干预/http/明文/锁），代理/栏目/浏览器/密钥不动 |
| 自学习 | 开 | 关=不读写 learn.json |
| 语言 | auto | 循环切：auto→zh→en |
| 每轮页数 | 60 | dl/auto 上限 |
| 下载并发 | 3 | watch/dl 均生效（1–8；dl 默认 3 归一为串行，显式改 N 才并发） |

### 2.1 拿视频推荐配置（v1.9.3）

- TUI 里先选 `🎯 一键视频配置`，再跑 `auto`。CLI 等价：
  `python -u -X utf8 site_crawler.py auto https://example.com/ 60 --preset video`
- 原理：视频真流几乎都在 CDN/站外（不开 CDN 等于自断一路），深层取流（视频优先）负责点封面进观看页拿真流——**不要加 `--no-video-first`**（那是关掉拿视频的主力）；bot 伪装（googlebot/bingbot）会被喂精简页，正文站不要开；快照/干预只给情报不下载正文。
- 已登录的站：把 `浏览器` 切到 `chrome` 并开 `克隆profile`（只读复制本机登录态；需先人工用 Chrome 打开过目标站）。

### 2.2 需要打字输入的选项（怎么填）

| 选项 | 填什么 | 例子 |
|---|---|---|
| 中转代理 | 本地/远端代理地址。socks 必须 `socks5h://`（h=DNS 也走代理，防泄漏）；开工前自动预检，死了报 PROXY-DEAD | `http://127.0.0.1:8080`、`socks5h://127.0.0.1:1080` |
| 栏目过滤 | 只爬 URL 含该子串的栏目，不填=全站 | `/vod/`、`/column/sports` |
| 伪装Referer | 完整 `http(s)://` URL；不合规（含空格/`javascript:` 等）整条丢弃 | `https://www.google.com/` |
| 文本代理 | 通用前缀（程序把目标 URL 拼后面）；不内置任何第三方，自己搭或填可信镜像 | `https://你的镜像/?url=` |
| HLS密钥 | 自有/授权内容的加密 m3u8 密钥 `URI[,IV]`；IV 须 hex，非法整体丢弃 | `https://站/key.bin,0011223344556677` |
| 克隆profile | 本机 Chrome 用户数据目录路径（只读源）；TUI 开开关自动取默认路径，CLI 用 `--clone-profile PATH` | `C:\Users\你\AppData\Local\Google\Chrome\User Data` |
| 每轮页数/下载并发 | 纯数字（并发 1–8） | `60` / `3` |
| 证书重钉 | 输入大写 `YES`（其他一律取消） | `YES` |
| 会话重放自测 | 输入大写 `YES`，仅自有/授权站 | `YES` |

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
  "extra_verify_selectors": [".my-captcha"],
  "rules": {"version": 1, "detail_link_selector": [".list a.detail"],
            "next_page_selector": ["a.next"], "watch_button_selector": [".play-btn"]}
}
```
`rules` 为声明式扩展唯一入口（不加载任意 `.py`）：三键均为 CSS 选择器白名单（长度≤200，字符集 `[a-zA-Z0-9_.#\[\]=\\"':\-\s>]`，非法逐条丢弃，超 20 条截断）；`version!=1` 整节丢弃并 WARNING；命中时 `discover_nav/find_next/watch_one` 优先用规则，无命中回退原逻辑。

`proxies` ≥ 2 条时自动进入轮换池：每次出口随机且不与上次重复，单代理连败 3 次熔断 10 分钟并自动故障转移，浏览器上下文粘滞、下载逐次轮换。开工打匿名简报：L0直连（暴露）/L1单代理/L2轮换池；每次运行身份束（UA+视口+指纹+出口）全换。`socks5://` 会提示 DNS 泄漏风险，请用 `socks5h://`。

```json
{
  "proxies": ["http://127.0.0.1:8081", "http://127.0.0.1:8082"],
  "locale": "zh-CN",
  "timezone_id": "Asia/Shanghai"
}
```

`--dl-jobs 0` 按 CPU 自动（2–8）。拥塞（429/5xx）自动抬升限速、空闲衰减；Crawl-delay 自动遵守。外部引擎可用 `ENGINE_SHA256` pin 表防 `tools/` 投毒（见代码注释），依赖锁定见 `requirements.lock`。

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
| bot 伪装直接 403 | 强风控站识破非足迹流量；改 mobile 或关伪装走正常验证 |
| 快照无可用存档/限流 | archive.today 域名轮换+限流不稳定；`auto` 顺序有超时预算，失败即过不断点 |
| strip 后页面排版乱 | 误删正文容器（50 节点上限内）；关 `--softwall` 重进页面即恢复 |
| 403 但不知是哪种墙 | 看 `CHALLENGE kind=` 行：cf-challenge/turnstile 换住宅出口后 `wait`；datadome 同理勿重试；forbidden 查 Referer/UA 防盗链 |
| token 流下到一半 403 | 短命 token 过期；watch 已优先即时下载，仍失败则是秒级过期或私有签名，不支持 |

---

## 11. v1.5.0 已知限制松动说明

背景：对照"已知限制"四条逐条松动，思路学自 GitHub（M-Fetch 自动 Referer / yt-dlp #6567 variant_query+hls_key / xersbtt 拦截即下 / 2026 反检测三层模型基准）。政策线（DRM/打码）不动。

### 11.1 mobile 真指纹（限制 2 修复）

- curl_cffi 自带 `chrome131_android`（本机 0.16.3 实测 44 preset 中有），`--spoof mobile` 现绑定真 Android 指纹，不再强制 requests
- preset 表刷新到 chrome150，UA 池加 Chrome/142，超前阈值同步到 150；envcheck 自测行同步
- bot 类（googlebot/bingbot）全球无 preset，仍强制 requests+告警——这是诚实保留，不是没做
- 保鲜：`curl-cffi update`（免费档含 Chrome/Safari/Firefox 新指纹），季度跑一次

### 11.2 防盗链与 token 流（限制 3 松动）

- **自动 Referer 兜底**（学 M-Fetch）：403/428 且 Referer 与目标不同源时，用目标 host 重试一次，记 `referer-fallback`；429/5xx 退避路径零改动
- **playlist 相对行守卫补齐**：相对分片/KEY 行 `urljoin` 成绝对地址再过 SSRF（只加覆盖，不改交引擎行为）；token query 原样透传不断链；`//内网/seg.ts` 类协议相对攻击现被拦截（回归锁定）
- **短命优先**：m3u8 含 `token/expires/sign/auth/sig/deadline` query 时 watch 队首插队即时下（`token-fastpath`），dl 模式打提示行
- **Host 作用域附加头**（学 M-Fetch rules.json 的安全子集）：`config.json` 的 `extra_headers` 形如 `{"example.com": {"Referer": "…", "Origin": "…"}}`；只收两键，Cookie 等余键丢弃，值须 http(s) 无 userinfo；调用方显式 Referer 优先，只补缺
  ```json
  {"extra_headers": {"example.com": {"Referer": "https://example.com/"}}}
  ```
- **`--hls-key URI[,IV]`**（学 yt-dlp）：透传 N_m3u8DL-RE `--custom-hls-key/--custom-hls-iv` 与 yt-dlp `--hls-key`；ffmpeg 无等价旗标，跳过并 WARNING 一次；URI 非法/IV 非 hex 整体丢弃；命令走 list 传递无 shell
- 剩余盲区（诚实）：站内私有 seal 逆向、秒级过期 token

### 11.3 挑战分类（限制 4 的可操作化）

- 403 现场判定 `CHALLENGE kind=`：cf-challenge（`cf-mitigated`/Attention Required）/ turnstile / datadome / forbidden（纯防盗链），各给一句话动作；body 只读前 4KB 不落盘；geetest 仍归浏览器侧选择器，不误判 datadome
- 三层模型（TLS > IP > 行为）：IP 信誉是单最高信号——强风控站请用住宅出口，这是文档建议不是代码能修的

- 回归闸门：`tests/test_security.py` 310 项（[K2]移动指纹7 + [O]守卫兜底6 + [P]附加头与密钥18 + [Q]挑战分类与快道15）

---

## 7. 日常维护

```powershell
python -u -X utf8 tests\test_security.py   # 回归：422 项全过 exit 0（改代码必跑）
python -X utf8 -m py_compile site_crawler.py watchflow.py tui.py i18n.py
python -u -X utf8 site_crawler.py envcheck
python -u -X utf8 site_crawler.py verify https://example.com/   # 离线自证下载物
python -u -X utf8 site_crawler.py updatecheck   # 只通知新版本，永不自动下载
curl-cffi update   # 指纹保鲜：拉最新 TLS preset（免费档含 Chrome/Safari/Firefox）
```

- `sites/` 下的 `cookies.txt` 是会话凭证，不要外传、不要入库（`.gitignore` 已排除整个 `sites/`）
- 换机器：拷走 `sites/<域名>/cookies.txt` + `inventory.csv` 即可续传

---

## 8. Round2 安全加固说明（v1.2.0+）

- **守卫式下载**：不再让库自动跟跳转，手动逐跳（≤5）+ 每跳主机 SSRF 守卫 + 落定 URL 复检白名单；直连时做连接后对端 IP 复检（闭合 DNS 重绑定窗口，代理场景豁免）；429/5xx 指数退避重试（服从 Retry-After≤60s）
- **m3u8 播放列表守卫**：先自取文本，`EXT-X-KEY` 与绝对分片地址逐条过 SSRF 守卫再交引擎；传给 yt-dlp/ffmpeg 前 URL 必须 `http(s)://`（防 URL 即选项）
- **指纹对齐**：UA 大版本→curl_cffi preset 自动对齐（chrome136/131/124/120/116），老指纹配新 UA 会被直接判脚本
- **网络层捕获**：dl 模式监听 response，播放器 JS 动态拉的流也能收下
- **记账与日志**：CSV 防注入全集（含全角/前导空白/BOM/竖线）；日志恒单行；导航文本去换行分隔符；cookie 临时文件过滤注入行 + 0600 权限 + 用完即删
- **代理**：保留认证信息（user:pass@）、IPv6 方括号；Crawl-delay 自动抬高限速下限
- 回归闸门：`tests/test_security.py` 135 项（当时），详见仓库

---

## 9. Round4 说明（v1.3.0）

- **播放列表纵深守卫**：2MB 封顶流式读；KEY 正则大小写不敏感+双/单/无引号；子 playlist 递归跟进（深度 2、上限 6）；跟跳 Location 反斜杠转正、非 http(s) scheme 直接拦
- **熔断防刷白**：近 10 次滑窗失败≥5 熔断 10 分钟，成功只衰减不洗白
- **分池**：浏览器长流程走 sticky（`proxy_sticky` 定死或池内 TTL 钉选，默认 30 分钟），下载遍历走随机轮换；自建可信代理（`proxy_trusted`）同样验对端 IP，公共代理豁免并记 `peer-skipped`
- **会话 TTL**：`cookies.txt` 按 mtime 计龄（`session_ttl_h`，默认 24），过期提示重跑 `wait`
- **robots 惩罚**：取失败记 `robots-unknown` 并限速 +1s，不再静默放行
- **供应链**：`requirements.lock` 含 4 包 hash（`--require-hashes` 安装）+ 运行时 `verify_lock` 版本钉死 + envcheck 自测行；TLS preset 缺失/UA 超前会警告
- **拟人点击**：三次贝塞尔（单侧控制点）+ easeInOut 速度 + 远距过冲修正 + 终点微颤 + 框内随机落点
- 回归闸门：`tests/test_security.py` 229 项（当时）

---

## 10. 付费墙四路径扩展（v1.4.0，仅自有/授权内容，默认全关）

适用范围限定：四开关默认全部关闭，不开即零行为变化（回归 `spoof-off/snap-off/sw-off/tp-off` 锁定）。
仅供自有站点或已获授权的内容做测试研究；遵守目标站 ToS 与版权。

### 10.1 路径一：请求伪装 `--spoof` + `--spoof-referer`

```powershell
python -u -X utf8 site_crawler.py check https://example.com/ --spoof googlebot
python -u -X utf8 site_crawler.py dl https://example.com/ 60 --spoof mobile `
  --spoof-referer https://www.google.com/
```

- 三档：`googlebot` / `bingbot` / `mobile`；`config.json` 同名键亦可（`"spoof"`, `"spoof_referer"`）
- bot 类无对应 TLS preset，强制走 requests 并 WARNING（防"新 UA + 旧指纹"脚本信号）
- mobile 同步移动视口（412×915 档）+ `Sec-CH-UA-Mobile: ?1` + Platform Android，保头身份一致
- Referer 必须是显式 http(s) 绝对 URL，无 scheme 自动补全是禁止的（防 `javascript:` 洗白，回归锁定）；`javascript:/data:`、userinfo、换行注入一律丢弃
- 浏览器通道（chromium/chrome/edge/camoufox）不受 `--spoof` 影响（真浏览器自带指纹）
- 不装扩展的手动等价：DevTools → Network Conditions → 取消自动 → 粘贴 bot UA 刷新测试

### 10.2 路径二：缓存快照 `--snapshot wayback|archive|auto`

```powershell
python -u -X utf8 site_crawler.py check https://example.com/ --snapshot auto
```

- 顺序：Wayback availability API → archive.today 轮换域（`archive.ph/.md`，`/newest/`）
- 每跳复用跳转守卫（≤5 跳 + SSRF + 公网单播 + 对端复检），存档站走同一会话（代理/TLS/Referer 全生效）
- 正文判定：限流/验证页关键字拒收（`Just a moment` 等），去标签后 ≥200 字才算命中
- 正文只在内存判定、不落盘；check 只报"快照可用(来源, 约N KB)"情报，不改变"需验证"结论
- 手动等价：`curl -sL "https://archive.org/wayback/available?url=目标URL"`；
  archive.today 轮换域（`.ph → .md → .li → .is`）依次试 `/newest/目标URL`

### 10.3 路径三：客户端干预 `--softwall strip|reader`

```powershell
python -u -X utf8 site_crawler.py watch https://example.com/ 10 --softwall strip
```

- `strip`：删 class/id 命中 `paywall|metering|subscription-wall|subs-gate|regwall` 的节点（上限 50）+ 解 `overflow:hidden` 滚动锁；接在 dl 收割前 / watch 详情页 / check 情报三处真调用
- `reader`：只回传计数（段落数/字符数/标题长度），正文不出页面、不落盘、不落日志（回归锁定无泄漏）
- 只操作已加载 DOM，不发额外请求；浏览器异常不中断主流程
- 手动等价：计量墙清 Cookie/无痕模式；F12 搜正文句子确认软墙后删遮罩节点并把 `overflow:hidden` 改 `auto`；Stylus 持久化规则：
  ```css
  .paywall-overlay, [class*="paywall" i] { display: none !important; }
  html, body { overflow: auto !important; }
  ```
  纯文本软墙可直接按 F9（Firefox）/ Safari 阅读器视图

### 10.4 路径四：一站式文本代理 `--text-proxy PREFIX`

```powershell
python -u -X utf8 site_crawler.py check https://example.com/ `
  --text-proxy "https://proxyhost/articles?article="
```

- 通用前缀，不内置任何第三方域名（防投毒 + 防 ToS 连带）；示例 host 自行填写，风险自负
- 前缀校验：显式 http(s) + 无 userinfo + 无空白 + 长度 ≤500；目标 URL 全编码拼接
- 代理主机走全套守卫，返回页复用快照正文判定；日志只记数字，目标 query 零落盘（回归锁定）
- check 遇验证时报"文本代理可用(约N KB)"情报，原站仍走 `wait` 验证

---

## 12. 论文与真实案例研究（v1.6.0 设计依据）

本节把 v1.6.0 每个加固点的学术/实战出处写死，防"拍脑袋安全"。仅自有/授权内容研究测试。

### 12.1 TLS 指纹：单信号弱，组合+保鲜才是解

- **Matousek 等，ICDF2C 2020《On Reliability of JA3 Hashes》**：JA3 单用只能唯一识别 33% 应用；JA3+JA3S+SNI 组合到 91.7%。结论：任何单指纹（TLS 或 UA）都不够看，必须多层组合 + 指纹库随版本更新。→ 对应我们的 UA+TLS preset+头一致性三件套，以及 `curl-cffi update` 保鲜制度。
- **Heino 等，IEEE CSR 2022**：主张用 JA3 预哈希串替代 MD5（近似匹配+可解释）。→ 对应我们钉版本名（`chrome150`）而不是哈希比对；`verify_lock` 钉死已装版本。
- **McGrew 等，arXiv:2009.01939（Mercury）**：加入目标上下文（IP/端口/SNI）后进程识别 F1>0.99。→ 对应 Host 作用域 `extra_headers`、sticky 出口、locale/时区随代理走的"目标上下文一致"思想。

### 12.2 藏匿军备赛：JS 注入必被看穿，C++ 层+会话稳定才是正道

- **Mowery & Shacham 2012《Pixel Perfect》**：朴素随机噪声可被均值攻击抹掉；彻底防御要么统一渲染要么弹权限框。→ 对应我们：拟人抖动用截断正态（非机械均匀），且身份束会话内稳定（不做每请求换 UA 这种自杀式"随机"）。
- **Nguyen & Vadrevu 2025《Breaking the Shield》**：当前无完全可部署的 canvas 防御；随机化必须同时"不可预测+不可逆"。→ 对应贝塞尔 `run_id` 会话种子 + 落点框内随机；也对应已知限制里"不保证 100%"的诚实写法。
- **Acar 等，CCS 2014《The Web Never Forgets》**：军备赛定调之作。→ 我们选 Camoufox（C++ 层）而非加 stealth 插件，正是此结论的工程版。
- **FP-Radar，PETS 2022**：反制平均滞后滥用 1–7 年。→ 预设表必须滚动刷新，不能写死（v1.5.0 教训）。

### 12.3 HLS/Token 真实案例：按请求授权必被自动化打穿

- **2026-01 token-refresh 滥用案例**：预览 token 可无限刷新 + CDN 只验 URL 不验会话 → 整片被增量拖走。教训：授权必须绑会话/计数；威胁模型必须按自动化假设。→ 对应 token-fastpath（取到即下）、query 透传不断链。
- **2026-06 某 OTT 20 漏洞审计**：DRM 许可证端点无鉴权、通配符 CDN token、JS 内硬编码 AES key、长会话 cookie。→ 对应 KEY 分离守卫（manifest/key/segment 三处各查）、`--hls-key` 只透传不提取、会话 TTL、`--lock-session`。
- **Hydrolix 2025 防盗链复盘**：一家 broadcaster 50%+ 流量来自非法 Referer；token 复用+UA 异常是核心信号。→ 对应 Referer 自动兜底 + `CHALLENGE` 分类日志 + counters 可观测。

### 12.4 会话劫持：Bearer 必被盗，只能缩窗口+绑环境

- **OWASP Cookie Theft / Session Management 系列 + MITRE T1539**：session cookie 本质是 bearer token；Evilginx2 类 AiTM 专偷；缓解=短 TTL + Secure/HttpOnly/__Host- + 环境绑定 + 失窃后重认证。→ 对应 cookies.txt 0600 + 删前覆写 + 会话 TTL + 权限 WARNING + 独占锁（客户端能做的全做了）。
- 对应红线：我们不碰服务端会话——`verify` 只验本地下载物，不验任何凭证有效性；`replay` 是 OWASP WSTG 会话劫持测试的只读 GET 最小实现（见 §13）

- 回归闸门：`tests/test_security.py` 339 项（[S]纵深7 + [T]反劫持5 + [U]藏匿效率与规则17）

---

## 13. 攻击侧自测（v1.7.0，默认全关，仅自有/授权站）

TUI 危险区统一范式：开关默认关；`replay`/`repin` 执行前必须输入 `YES`（"是否需要"式确认），输错即取消。

### 13.1 `replay` cookie 重放自测（只读 GET）

```powershell
python -u -X utf8 site_crawler.py replay https://example.com/
```

- 三步：匿名 vs 带券（特权差异？）→ 带券换 UA/指纹重放（会话绑定？）；只比较状态码与正文长度，不下载媒体、不改任何状态
- 结论：`REPLAY-SAME`（公开页/会话失效）/ `REPLAY-DIFF`（会话带特权）+ `REPLAY-UNBOUND`（换身份仍等效=未绑定，cookie 失窃即冒用）/ `REPLAY-BOUND`（疑似绑定，以人工复核为准）
- Cookie 永不落日志（回归 `replay-noleak` 锁定）；无会话（未 `wait`）退出码 3
- 对应 OWASP WSTG 会话劫持测试的合法子集：只测自有站、只读、不碰服务端状态

### 13.2 `--hijack-check` TOFU 证书钉扎（劫持检测）

```powershell
python -u -X utf8 site_crawler.py check https://example.com/ --hijack-check
# 站方换证确认合法后：
python -u -X utf8 site_crawler.py check https://example.com/ --hijack-check --repin
```

- 标准库直连取对端证书 SHA256（只指纹不校验，不走代理，失败即跳过不拦）
- 首见保存 `sites/<host>/certpin.txt`（0600）并 TOFU 信任；变更只 WARNING + `hijack-cert-changed`，**永不阻断**（CDN 轮换/换证误报率高，阻断即自残）
- 钉扎文件是集合（容忍多证书轮换）；`--repin` 须人工确认合法后加钉
- 局限（诚实）：只能发现"证书变了"，分不清 MITM/换证/轮换——最终靠人工确认；http 站自动跳过；代理环境直连失败即跳过

### 13.3 做与不做

| 需求 | 结论 |
|---|---|
| cookie 重放 | 做（本节，只读自测+YES 门） |
| 劫持检测 | 做（本节，TOFU 钉扎只告警） |
| 流量劫持（主动中间人） | 不做（攻击他人流量，无合法场景） |
| AV 免杀 | 不做（纯 malware tradecraft；对应需求由完整性自检 + AV 信任区覆盖，见 README） |

- 回归闸门：`tests/test_security.py` 351 项（[V]攻击侧自测12）

---

## 14. 自我学习/更新/收集/进化（v1.8.0，有限制）+ 语言选择

### 14.1 学什么、存在哪、谁能关

- 档案：`sites/<host>/learn.json`，固定 schema 六键（version/delay/engine_hits/last_challenge/fails_429/updated），版本错配整节丢弃
- 学三样：拥塞自适应延迟（每次拥塞 +0.5s，上限 10s，下轮超当前下限即采用并明示）/ 引擎命中榜（只建议不强制改链）/ 挑战记忆（收尾从 counters 回填）
- 不学四样：URL、Cookie/凭证、请求头、正文——学习函数只碰计数器与延迟数字（回归 `learn-clamp` 锁定 `url/cookie` 键被丢弃）
- 总开关：`--no-learn` 或 `config.json` 的 `"learn": false`，一键停读写；TUI 有"自学习"开关
- 无外发：learn.json 永不离开本站目录；更新检查只读 GitHub releases tag，不上报任何本机信息

### 14.2 更新检查（只通知）

```powershell
python -u -X utf8 site_crawler.py updatecheck
```

- 问 `api.github.com` 最新 release tag，与本地 `__version__` 比；有新版只打印"请手动 git pull"，**永不自动下载/执行**（供应链红线）
- 失败（网络/代理）返回 2 并明示原因，不静默

### 14.3 进化边界（诚实）

- 会进化的：延迟下限、引擎建议、挑战记忆——都是"同一策略的参数"，不改变安全基座（SSRF/守卫/脱敏零豁免）
- 不进化的：白名单、守卫阈值、脱敏规则——安全基座只能由人改代码 + 过回归，不能被"学"松（否则就是用学习挖洞）
- 引擎链顺序不变：榜首只打建议日志，防止学偏导致冷门引擎饥饿

### 14.4 语言选择（i18n）

- `i18n.py`（纯标准库）：优先级 `--lang` > cfg `lang` > 环境 LANG/LANGUAGE > 系统 locale > 英语
- 系统探测：locale 含 zh 即中文，其余一律英语；探测失败回英语（按需求）
- 缺键回退链：当前语言 → 英语 → key 本身，永不抛（回归锁定中英键集合相等）
- 覆盖：TUI 全量双语（含危险区 YES 确认）；引擎日志暂中文（增量中）；`--lang` 已直通引擎，TUI 有"语言"开关（auto→zh→en 循环）
- 用法：`python -u -X utf8 tui.py --lang en`；`site_crawler.py … --lang en`

- 回归闸门：`tests/test_security.py` 422 项（[X]23 + [Y]19 + [Z]7 + [AA]3 + [AB]3 + [AC]5 + [AD]3 + [AE]3 + [AF]3 + [AG]会话备份 2）

> v1.8.1 热修：`tui.py pick()` 的 `for i, (label, _)` 把 i18n 函数 `_` 遮蔽成字符串，TUI 启动即 `TypeError`。修为 `val`，教训——冒烟只验了键集合相等、没真调一次 `pick`；现回归用 mock input 喂 `1`/`q` 真调，`_` 再被遮蔽当场被抓。
>
> v1.9.0 方向键 TUI：终端下 `pick()` 改走 `msvcrt.getch()`（Windows）/`termios`（POSIX）方向键菜单，首尾循环、记住各页光标；`AUTO_SITE_DL_LINE=1` 或管道时回数字行模式。文本输入（代理/栏目/YES 门）仍走 `input()`。
>
> v1.9.1 会话交接（修真站 `wait→dl` 必现 REVERIFY）：此前 `wait` 存的 `cookies.txt` 两边都没人用——`open_ctx` 全分支开全新匿名上下文、`make_session` 也不读会话，`dl` 首个页面即撞滑块验证退出 4。现 `_load_cookie_pairs` 解析（夹紧：名须 RFC6265 token、值禁 CTL/分号逗号、名/值/总数封顶、同名取末）→ `_seed_ctx_cookies` 经 `add_cookies` 喂浏览器（open_ctx 四分支：camoufox/clone/plain/_boot_plain，失败静默匿名继续）+ `make_session` 置 `Cookie` 头。值与名永不落日志，只记对数与域名。`check`/`watch` 同受益（`watch` 经 `watchflow.C.open_ctx`）。注意：会话有时效（TTL），过期仍需重跑 `wait`；换浏览器通道后首次也建议重跑一次 `wait`。
>
> v1.9.2 空跑可观测（修"退出 0 但什么都没下"的静默）：实战发现 `dl` 收割为 0 时 SUMMARY 只有权限计数、无声 exit 0。现单页无媒体无锚点记 `harvest_zero`（首现 WARNING 一次，提示 bot UA/未渲染并指引 `diag` 对照）；收尾 `_dl_warn_empty` 整轮零下载追加 WARNING（判读指引：`diag` 媒体 0=被喂精简页/未渲染，有媒体 0 下载=下载层被拦）。退出码语义冻结（0=走完，4=验证拦），空跑是否算错由人按 WARNING 判。同版 A 方案：`--spoof googlebot|bingbot` 在 `pick_identity` 打 WARNING 一次（浏览器仍挂爬虫 UA，真 Chromium 配爬虫 UA 是机器人强信号且易被喂精简页；bot 档建议仅配合快照/文本代理，正文站请去掉 `--spoof`）。分身份方案（浏览器真人 UA + 请求层 bot UA）暂不做，待实战 `diag` 对照后再议。
>
> v1.9.3 锁自愈 + 视频预设：`--lock-session` 的 `.session.lock` 从无释放逻辑，第一次运行后**每次**都 SESSION-LOCKED 退出 2（之前误报为"另一进程持有"，实为自己的残留）。现持有者是自己则重入放行、持有者已死则删锁重取（`_pid_alive`：Windows 用 OpenProcess，POSIX 用 kill 0，判不准按存活处理）、正常退出经 atexit 只删自己的锁；报错改给持有者 PID + 锁路径 + 处理指引。回归把 `sess-lock` 更新为新契约（同进程重入 True），另补 lock-take/self/release/stale/held/pid-self。同版：TUI `🎯 一键视频配置` + CLI `--preset video`（`apply_video_preset` 纯函数，收敛 cdn/视频优先开、spoof/快照/干预/http/明文/锁关，不动代理/栏目/浏览器/密钥等）；MANUAL §2.1/§2.2 新增拿视频推荐配置与输入项填写指南。测试侧另修两层竞态：NTFS 隧道化（删后速建继承 48h 前 mtime，`os.utime` 钉 now）与亚微秒时钟差（`getmtime` 比 `time.time()` 新约 0.24µs，`sess-fresh` 下界加 `-0.001` epsilon；引擎判定不受影响）。
>
> v1.9.4 随机默认（每次运行自动换身份，安全基座不动）：审计确认已随机项——UA、视口、`run_id` 身份束、代理轮换/粘滞、限速高斯抖动、鼠标拟人、重试抖动；本轮补两处——UA 池 6→12（Chrome 131/132/136/142/144/145/146/148/150 + Edge 130/144 + Firefox 133，逐条对齐 TLS preset，Chrome 大版本全 ≤150 无超前警告）与 `think()` ±25% 均匀抖动（下限 100ms，调用方传标称值即可）。刻意**不随机**：TLS 校验、http/明文、伪装、锁、劫持、浏览器通道（求稳，有缺失回退）、指纹（必须与 UA 同代绑定，错配即脚本信号）。`[Z]` 把安全默认钉死：解析器默认值全关断言 + 池卫生（Mozilla 前缀/版本封顶/数量下限）+ 全池指纹对齐 + think 上下界 + 随机流经全局 RNG（seed 可复现）+ 视口范围。
>
> v1.9.5 diag 只读快照（定位"会话有效但 0 媒体 0 锚点"的空跑）：实战出现 wait 已验证、dl 注入 21 对、页进了但收割全空。`_diag_snapshot` 只读取数——标题（去注行截断）/终址（脱敏到 path）/正文体量（只记字节数）/原始计数（img/vid/src/a 个数）/验证态/沉降增量，`[AA]` 锁定脱敏与永不抛错。判读：raw 全 0=空壳页（精简/未渲染/SPA 未挂载）；raw 有数但媒体 0=全被过滤（重点查 `blob:`——MSE 播流的 video 标签 src 就是 blob，正被 `norm_media` 丢弃，及 `is_media_url` 后缀门）；raw 缺失=JS 执行层问题。下一步候选（待 diag 定夺）：blob/流式收割增强，或 wait 暖机的上下文复用（persistent profile）。
>
> v1.9.6 详情回退（修门户页空跑）：`diag` 实锤——门户页 344 链 0 媒体（287KB 索引页，视频全在详情链后），而 `deep_dive` 关键词门（detail|play|/vod/|/video/|watch|/p/）零命中即静默跳过全部 297 锚点。现两轮：关键词优先；零命中回退试探**同站**前 2 个（防漫游站外，同样走 `_browser_guard`/验证/预算，记 `dive_fallback` 并打一行日志）。同站用主机全等判定；非字符串锚点不再抛错（旧代码 `re.search` 遇非标输入可崩整轮）。另 `net_cap` 末页余量记 `net_remain` + WARNING（行为不变，只不再无声丢弃）。`[AB]` 锁定：回退只进同站（站外锚点不碰）、关键词存在时不回退、详情页撞验证即停并上报。注意：回退每页至多 2 个、全局预算 20，先看它能不能咬住详情链；若详情页本身是 JS 播放器（流地址只在网络层出现），下一步给 `deep_dive` 加网络捕获排空或转 `watch` 模式。
>
> v1.9.7 auto 自动驾驶（用户只给网址+做验证+拿内容，配置程序内部办）：实战 `ERR_NETWORK_ACCESS_DENIED`（本机出口被拦，直连 TLS 与导航同失败）导致 `auto` 首败即退。现 check 梯子至多 3 次有界重试——第 2 次换身份束 + 退避 5s（瞬时风控），第 3 次换浏览器通道 + 退避 10s（真 Chrome 可能自带代理配置；缺失通道由 `open_ctx` 原有回退接住），通道覆盖经 `site._auto_channel` 生效、用后清零，顺序由 `_eff_channel` 收敛。锁被其他活进程占用直接不重试。三振后：配了快照/文本代理则 `_snapshot_intel` 只读兜底（不改变失败结论），再打 verdict（配 `--proxy` 后重跑）并返回原码。退出码语义不变（2=基础设施失败），`[AC]` 锁定重试次数/兜底调用/覆盖清零/活锁跳过/通道顺序。注意：硬出口封锁重试救不了，verdict 会明说配代理；`wait` 仍是人机交互，不自动。
>
> v1.9.8 诚实梯子（修重试"换了个寂寞"）：实战发现梯子第 2 步日志写"已换身份束"但身份束号不变（只换了 UA/视口，`run_id` 未动），第 3 步写"换通道→chrome"但匿名简报仍显示 chromium（显示绕过了 `_eff_channel`）。现重试真换 `run_id`，简报显示有效通道。另 `_goto` 落盘 `_last_nav_hint`，verdict 按末次错误分类给处置：证书类→ `--insecure` 须知（跳过校验有中间人风险，建议同开 `--hijack-check`）；代理类→查 `--proxy` 链路；其他→配代理/查 URL；未配快照/文本时代理提示 `--snapshot wayback` 碰运气（只读情报）。程序永不自动降 TLS 校验（红线，须用户显式承担）。`[AD]` 锁定通道显示/导航 hint 落盘/身份轮换。
>
> v1.9.11 会话备份（实战：`sites/seyou9.sbs/cookies.txt` 在两次运行之间凭空消失，非程序删除——引擎内除 purge 外无删除会话代码）：`wait` 存会话时同写 `cookies.txt.bak`（0600）；`_load_cookie_pairs` 主文件缺失/空时只读兜底备份（记 `session-bak-used` + WARNING 提示重跑 wait），主备双无保持返回空。`[AG]` 锁定兜底与主优先。注意：备份只防文件丢失，不防会话过期；盲测 harness（blindreap，repo 外个人 PPE）实测证实新鲜上下文即使注入 cookie 仍吃滑块壳（3.3KB），信任绑在暖机上下文——persistent profile 上下文复用列为下版候选，需拍板（稳定身份 vs 每轮换身份的取舍）。
>
> v1.9.9 通道保持（修"check 切 chrome 能进、dl 掉回 chromium 又撞墙"）：梯子第 3 步切到的通道旧版在 check 结束即清零，wait/dl 全走默认通道。现覆盖保留到 `auto` 整轮结束（try/finally 跑完才清），wait 与 dl 同享胜利通道。另补两处静默：`dl` 首跳即断（visited=0）旧版无任何计数，现记 `dl_no_entry` + WARNING；`deep_dive` 无锚点可跟旧版无声跳过，现记 `dive_no_anchors` + 一行日志——与"有链不跟"（`dive_fallback` 未触发/关键词命中）区分开。`[AE]` 锁定：dl 阶段读到的确为 escalated 通道、结束后清零、零进入与无锚点计数。
>
> v1.9.10 布尔契约（内部逻辑只返布尔，文字只在展示点拼）：`_goto` 旧版直接返回诊断文本串（""=成功）作流程控制，`detect_verify` 旧版返回（布尔，选择器串）。现 `_goto` 返 True/False（NAV-FAIL 日志照打，hint 照落 `site._last_nav_hint`），`detect_verify` 返 True/False（命中选择器照落 `site._last_verify_sel`）；6 处调用方（check/wait/dl/diag/nav + watchflow 两处）同步翻转，旧 `sess-lock` 外的旧断言（`goto-guard-block`/`goto-hint`）按新契约更新。`diagnose_nav_error` 仍返文本（它本身就是展示文本工厂，不在契约内），`cmd_*` 退出码与数据元组（session/fresh/快照）保持不动。`[AF]` 锁定真假分支与落盘字段。
