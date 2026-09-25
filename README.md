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

**TUI（`tui.py`，纯标准库）**：站点页 → 操作页（11 种模式 auto/check/wait/dl/watch/nav/purge/verify/replay/envcheck/updatecheck + 20 组开关，危险区需输入 YES）→ 前台运行，Ctrl+C 停止。`python -u -X utf8 tui.py --lang en` 切英语。

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
├── tests/test_security.py 安全回归（红队自审，371 项，纯本地零网络）
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

## 维护

```powershell
python -u -X utf8 tests\test_security.py   # 回归闸门：371 项全过，exit 0
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
