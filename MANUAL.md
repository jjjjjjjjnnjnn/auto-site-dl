# 操作手册（MANUAL）

对应版本：v1.6.0 ｜ 适用系统：Windows 10/11（PowerShell）｜ Python ≥ 3.9

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
python -u -X utf8 tests\test_security.py   # 回归：339 项全过 exit 0（改代码必跑）
python -X utf8 -m py_compile site_crawler.py watchflow.py tui.py
python -u -X utf8 site_crawler.py envcheck
python -u -X utf8 site_crawler.py verify https://example.com/   # 离线自证下载物
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
- 对应红线：我们不碰服务端会话、不做 cookie 重放测试——`verify` 只验本地下载物，不验任何凭证有效性。

- 回归闸门：`tests/test_security.py` 339 项（[S]纵深7 + [T]反劫持5 + [U]藏匿效率与规则17）
