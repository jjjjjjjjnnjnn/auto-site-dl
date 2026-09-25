# auto_site_dl

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)

通用站点媒体下载器：填网址 → 自动检测人机验证 → 需验证则弹窗等人工 → 验证通过后自动全站下载图片/视频。

针对视频站做了深层交互（点封面 → 点观看 → 等加载 → 拿真流），并内置反追踪伪装与网络安全防护（SSRF、跳转复检、日志脱敏、TLS 强制校验、robots 遵守）。

> **使用声明**：本工具仅用于下载你有权访问的公开媒体内容。付费墙四路径扩展（`--spoof/--snapshot/--softwall/--text-proxy`，默认全关）仅供你在自有站点或已获授权的内容上测试与研究使用；请遵守目标网站服务条款与 robots 规则，尊重版权；因滥用产生的一切后果由使用者承担。

## 快速开始

```powershell
cd auto-site-dl
pip install -r requirements.txt
python -m playwright install chromium
python -m camoufox fetch          # 可选：C++ 层指纹后端
python -u -X utf8 site_crawler.py envcheck   # 环境自检，全 OK 再开工
python -u -X utf8 tui.py                      # 终端交互 UI（推荐入口）
```

详细操作见 [MANUAL.md](MANUAL.md)（安装、TUI/CLI 手册、站点配置、排障、维护）。

## 两种用法

**TUI（`tui.py`，纯标准库）**：站点页 → 操作页（11 种模式 auto/check/wait/dl/watch/nav/purge/verify/replay/envcheck/updatecheck + 20 组开关，危险区需输入 YES）→ 前台运行，Ctrl+C 停止。终端里 `↑↓` 移动、`→`/`Enter` 确认、`←`/`Esc` 返回（管道时自动降级数字选择）。`python -u -X utf8 tui.py --lang en` 切英语。

**命令行**：

```powershell
# 全流程：检测 →（需验证则弹窗等人工）→ 自动下载
python -u -X utf8 site_crawler.py auto https://example.com/ 60 --allow-cdn

# 视频站深层下载（点封面→点观看→等加载→下真流），3 并发
python -u -X utf8 site_crawler.py watch https://example.com/ 10 --allow-cdn --dl-jobs 3

# 分步
python -u -X utf8 site_crawler.py check https://example.com/
python -u -X utf8 site_crawler.py wait  https://example.com/
python -u -X utf8 site_crawler.py dl    https://example.com/ 60 --allow-cdn
python -u -X utf8 site_crawler.py nav   https://example.com/
python -u -X utf8 site_crawler.py purge https://example.com/
```

退出码：`0` 成功 ｜ `1` 等待超时 ｜ `2` 环境缺失/代理已死/导航失败 ｜ `3` 未验证 ｜ `4` 中途重现验证 ｜ `10` 需人机验证

## 常用参数

| 参数 | 说明 |
|---|---|
| `--browser camoufox\|chrome\|edge` | 浏览器通道：`camoufox`=C++ 层指纹；`chrome/edge`=本机真实浏览器；默认 bundled chromium |
| `--clone-profile PATH` | 克隆真实浏览器 profile（只复制身份文件，源只读） |
| `--proxy URL` | 路由中转；不设时自动读系统代理 |
| `--insecure` | 忽略证书校验（仅可信内网/MITM，默认强制校验） |
| `--allow-cdn` | 媒体允许本站外 CDN（默认只收本站） |
| `--video-first` / `--no-video-first` | 视频优先（默认开） |
| `--column SUB` | 只爬 URL 含该子串的栏目 |
| `--dl-jobs N` | watch 下载并发 1–8（默认 3） |
| `--spoof googlebot\|bingbot\|mobile` | 请求伪装（默认 off；bot 类强制 requests+告警） |
| `--spoof-referer URL` | 伪装 Referer（只收 http(s)） |
| `--snapshot wayback\|archive\|auto` | 缓存快照探测（默认 off，check 报情报） |
| `--softwall strip\|reader` | 客户端干预：删遮罩/只计数（默认 off） |
| `--text-proxy PREFIX` | 一站式文本代理前缀（通用，不内置第三方） |
| `--hls-key URI[,IV]` | HLS 密钥透传（N_m3u8DL-RE/yt-dlp 生效，ffmpeg 跳过） |
| `--lock-session` | 会话独占锁（防并发写 cookies.txt） |
| `--hijack-check` / `--repin` | 劫持检测：TOFU 证书钉扎（默认关）/ 人工确认后重钉 |
| `--lang auto\|zh\|en` | 语言（默认 auto=系统语言，取不到回英语；TUI 已双语） |
| `--no-learn` | 关闭自我学习（不读写 learn.json） |

## 目录结构

```
auto-site-dl/
├── site_crawler.py       主程序（模式入口 + 安全基座 + 下载引擎链）
├── watchflow.py          视频深层流程（取流状态机 + 并行下载池）
├── tui.py                终端交互 UI（中英双语）
├── i18n.py               语言探测与译表（纯标准库）
├── tests/test_security.py 安全回归（红队自审，426 项，纯本地零网络）
├── requirements.txt
├── MANUAL.md             操作手册
├── LICENSE               Apache-2.0
└── sites/<域名>/         每站独立隔离区（运行时生成，永不入库）
    ├── downloads/        媒体文件（00001_stem.jpg / 00001.mp4）
    ├── profile/          独立浏览器 profile
    ├── inventory.csv     记账：url,file,bytes,sha256,source
    ├── cookies.txt       会话凭证（敏感，勿外传）
    ├── certpin.txt       证书钉扎集合（hijack-check 用）
    ├── learn.json        学习档案（延迟/引擎榜/挑战记忆，无敏感物）
    └── crawl.log         运行日志（URL 已脱敏到 path）
```

## 安全设计（摘要）

- **SSRF**：下载目标必须解析为公网单播 IP；跳转终点复检 scheme+主机+SSRF；反斜杠/userinfo 攻击先规范化再判定
- **媒体完整性**：白名单后缀 + Content-Type + 文件头魔数三重校验（魔数是地面真相）；`<512B` 追踪像素丢弃
- **反追踪**：每运行随机 UA+视口、Sec-CH-UA 身份一致、curl_cffi TLS 指纹（自检回落）、stealth 注入、拟人点击、限速抖动、WebRTC 防泄漏、Camoufox 可选后端
- **付费墙四路径（仅自有/授权内容，默认全关）**：`--spoof` 请求伪装（bot/mobile 预设+Referer 覆盖）/`--snapshot` 缓存快照情报（Wayback/archive.today 轮换）/`--softwall` 客户端干预（strip 删遮罩+解滚动锁/reader 只计数，正文零落盘）/`--text-proxy` 通用文本代理前缀；快照与代理复用跳转守卫+SSRF+正文判定，check 只报情报不改变验证结论。详见 MANUAL §10。
- **指纹保鲜**：TLS preset 表跟踪 curl_cffi 实装（chrome150/android 真指纹，mobile 伪装已绑定 `chrome131_android`）；bot 类全球无 preset，仍强制 requests+告警。定期跑 `curl-cffi update` 保鲜指纹库
- **防盗链与 token 流**：403/428 自动 Referer 兜底（目标 host 重试一次）；playlist 相对行同样过 SSRF 守卫且 token query 原样透传；token 短命 m3u8 优先即时下载；`extra_headers`（Host 作用域，仅 Referer/Origin）+ `--hls-key` 透传
- **挑战分类**：403 现场判定 cf-challenge/turnstile/datadome/纯 403，给出对症动作（住宅 IP/换出口/wait 人工）
- **纵深安全 v1.6.0**：cookies/netscape 0600 + 删前覆写；下载流式落盘（首块魔数早弃+边下边 hash）；`verify` 离线自证；config 未知键/类型校验；MITM 只记信号不阻断；why 文本 scrub
- **藏匿一致 v1.6.0**：Accept-Language 随 locale；媒体请求 Sec-Fetch 修正（same-origin/cross-site + no-cors + Dest）；正态节奏抖动；DNS 缓存（只存公网）；dl 可选并发（默认串行）
- **声明式扩展 v1.6.0**：`config.json/rules` 三选择器白名单（version 钉死，不加载任意 `.py`）；envcheck 完整性自检；研究依据见 MANUAL §12
- **攻击侧自测 v1.7.0（默认全关，仅自有/授权站，TUI 需输入 YES）**：`replay` cookie 重放自测（只读 GET：匿名 vs 带券 vs 换身份，报告会话绑定情况）；`--hijack-check` TOFU 证书钉扎（首钉信任、变更只告警不阻断、`--repin` 人工确认后加钉）。**AV 免杀不做**（纯 malware tradecraft，与开源可审计立场冲突；对应需求由完整性自检 + AV 信任区覆盖）
- **运维安全**：日志 URL 只到 path、Cookie/代理凭证永不打印、代理开工前预检、导航错误 11 类诊断、robots 默认遵守
- **自我学习 v1.8.0（有限制，见 MANUAL §14）**：本站 `learn.json` 自适应延迟（拥塞+0.5s/上限10s）+ 引擎命中榜 + 挑战记忆；无外发、不存敏感物、schema 夹紧、`--no-learn` 一键关
- **更新检查 v1.8.0**：`updatecheck` 只问 GitHub releases 最新 tag 并通知，永不自动下载/执行
- **i18n v1.8.0**：`i18n.py` 系统语言探测（仅 zh 回中文，其余/失败回英语），TUI 已全量双语，`--lang` 直通引擎
- **TUI 热修 v1.8.1**：`pick()` 循环变量遮蔽 `_` 致启动即崩，已改名 + 补真调用回归（mock input 喂 `1`/`q`）
- **方向键 TUI v1.9.0**：终端下方向键菜单（首尾循环、记住光标），`AUTO_SITE_DL_LINE=1`/管道时回数字行模式
- **会话交接 v1.9.1**：`wait` 存的 `cookies.txt` 自动喂给 `dl`/`check`/`watch` 的浏览器（`add_cookies`）与下载会话（`Cookie` 头）；解析夹紧防投毒（名须 token、值禁 CTL/分号逗号、封顶），值永不落日志
- **空跑可观测 v1.9.2**：单页收割为 0 记 `harvest_zero` + 首现 WARNING；整轮零下载追加 WARNING（指引跑 `diag` 对照）；`--spoof googlebot|bingbot` 打 WARNING（浏览器仍挂爬虫 UA，易被喂精简页，建议仅配合快照/文本代理）
- **锁自愈+视频预设 v1.9.3**：`.session.lock` 从不释放致 `--lock-session` 第二次必卡死，现持有者死则删锁重取 + 正常退出 atexit 释放 + 报错给 PID/路径；TUI `🎯 一键视频配置` / CLI `--preset video` 收敛拿视频组合（开 cdn/视频优先，关 spoof/快照/干预/http/明文/锁）；`sess-fresh` 修 NTFS 隧道化与亚微秒时钟竞态
- **随机默认 v1.9.4**：UA 池 6→12（Chrome 131–150 + Edge 144 + Firefox，各对齐 TLS preset 无超前警告）+ `think()` ±25% 抖动；已有随机（视口/run_id/代理轮换/延迟高斯抖动/鼠标拟人）保持；安全基座默认锁定（cdn/http/明文/spoof/快照/锁/劫持全关）并 en 回归钉死
- **diag 只读快照 v1.9.5**：`diag` 新增标题/终址/正文体量/原始计数(img/vid/src/a)/验证态/沉降增量，定位空跑（raw 全 0=空壳页、有数但媒体 0=被过滤、raw 缺失=JS 执行层问题），全脱敏零正文落盘
- **详情回退 v1.9.6**：门户页（有链无媒体）`deep_dive` 关键词零命中时试探同站前 2 锚点（同站约束防漫游，走守卫/验证/预算，记 `dive_fallback`）；末页网络捕获余量记 `net_remain` 不再无声丢弃；非标锚点不再抛错
- **auto 自动驾驶 v1.9.7**：`auto` 不再首败即退——check 梯子至多 3 次（1 照常；2 换身份束+退避；3 换浏览器通道，真 Chrome 可能自带代理配置），锁被活进程占则不重试；三振后配了快照/文本代理则只读情报兜底，再打处置 verdict；`_snapshot_intel` 抽取复用，`_eff_channel` 通道顺序可测
- **诚实梯子 v1.9.8**：重试真换 `run_id`（旧版只换 UA 不换号，日志身份束不变）；`anon_report` 显示有效通道（含 auto 覆盖）；`_goto` 落 `_last_nav_hint`，verdict 按末次错误分类（证书→ `--insecure` 须知+中间人风险、代理→查链路、其他→配代理/查 URL，未配快照则提示 `--snapshot wayback`）
- **通道保持 v1.9.9**：梯子切到的通道保留给 wait/dl 全程（旧版 check 用完即清，dl 掉回默认通道重撞墙）；`dl` 首跳即断记 `dl_no_entry`（旧版 visited=0 无声）；深挖无锚点记 `dive_no_anchors`（区分"有链不跟"与"无链可跟"）
- **布尔契约 v1.9.10**：`_goto`/`detect_verify` 只返布尔（旧版直接返回诊断文本/选择器串作流程控制）；诊断文本由 `diagnose_nav_error` 在展示点拼，导航 hint 落 `site._last_nav_hint`、验证选择器落 `site._last_verify_sel`，6 处调用方（含 watchflow）同步翻转
- **会话备份 v1.9.11**：`wait` 成功即写 `cookies.txt.bak`（0600）；主文件被外部删除/清空时只读兜底（记 `session-bak-used` + WARNING 提示重跑 wait），双无则保持原样返回空
- **深挖排空 v1.9.12**：详情页加沉降（滚触发懒挂载播放器，之前只 think 800ms）+ 即时排空网络捕获（`net_cap` 传进深挖消费即清，不等下个列表迭代，无下页不丢失）
- **假缓冲收窄 v1.9.13**：`STALL_TEXT` 剔裸 `APP`（子串匹配误杀 happy/apple 等全页正文；引流意图由下载app/安装/请安装覆盖）+ 抽 `_is_stall_text` 纯函数

## 维护

```powershell
python -u -X utf8 tests\test_security.py   # 回归闸门：426 项全过，exit 0
python -X utf8 -m py_compile site_crawler.py watchflow.py tui.py i18n.py
python -u -X utf8 site_crawler.py envcheck
```

改动代码后必须跑上面三条。任何 assert 失败都代表被攻破——修代码，不改测试。

## 杀毒软件误报说明

本工具含浏览器自动化、代理支持、TLS 指纹伪装等字样，部分杀毒软件（McAfee、腾讯电脑管家等）可能误报为 HackTool 并隔离 `.py` 文件。代码完全开源可审计；如遇隔离，请将项目目录加入杀毒软件信任区/排除列表后从隔离区恢复。

## 已知限制

- 政策线（不可松）：不破 DRM、不做验证码打码（人工验证是唯一通道）；四路径扩展默认全关，仅限自有/授权内容研究测试。APP 私有签名（站内逆向 seal 类）不在支持范围
- bot 伪装（googlebot/bingbot）对强风控站大概率 403，且全球无对应 TLS 指纹（强制 requests+告警）；mobile 伪装已绑定 `chrome131_android` 真指纹（v1.5.0 修复，旧版"无移动端 preset"的说法已作废）
- token 流：已支持 Referer 自动兜底（403/428）、query 透传、`--hls-key`、短命优先下载；剩余盲区只有站内私有加密与秒级过期 token（取到即下仍可能超时）
- 反追踪是三层模型（TLS 指纹 > IP 信誉 > 行为），不保证 100% 绕过强风控；IP 信誉是单最高信号，强风控站请用住宅出口，数据中心 IP 再完美的指纹也会被挑战

## License

Apache-2.0 © 2026 jjjjjjjjnnjnn，见 [LICENSE](LICENSE)。
