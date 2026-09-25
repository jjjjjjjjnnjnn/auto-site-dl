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

**TUI（`tui.py`，纯标准库）**：站点页 → 操作页（auto/check/wait/dl/watch/nav/purge/envcheck + 8 组开关）→ 前台运行，Ctrl+C 停止。

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

## 目录结构

```
auto-site-dl/
├── site_crawler.py       主程序（模式入口 + 安全基座 + 下载引擎链）
├── watchflow.py          视频深层流程（取流状态机 + 并行下载池）
├── tui.py                终端交互 UI
├── tests/test_security.py 安全回归（红队自审，266 项，纯本地零网络）
├── requirements.txt
├── MANUAL.md             操作手册
├── LICENSE               Apache-2.0
└── sites/<域名>/         每站独立隔离区（运行时生成，永不入库）
    ├── downloads/        媒体文件（00001_stem.jpg / 00001.mp4）
    ├── profile/          独立浏览器 profile
    ├── inventory.csv     记账：url,file,bytes,sha256,source
    ├── cookies.txt       会话凭证（敏感，勿外传）
    └── crawl.log         运行日志（URL 已脱敏到 path）
```

## 安全设计（摘要）

- **SSRF**：下载目标必须解析为公网单播 IP；跳转终点复检 scheme+主机+SSRF；反斜杠/userinfo 攻击先规范化再判定
- **媒体完整性**：白名单后缀 + Content-Type + 文件头魔数三重校验（魔数是地面真相）；`<512B` 追踪像素丢弃
- **反追踪**：每运行随机 UA+视口、Sec-CH-UA 身份一致、curl_cffi TLS 指纹（自检回落）、stealth 注入、拟人点击、限速抖动、WebRTC 防泄漏、Camoufox 可选后端
- **付费墙四路径（仅自有/授权内容，默认全关）**：`--spoof` 请求伪装（bot/mobile 预设+Referer 覆盖）/`--snapshot` 缓存快照情报（Wayback/archive.today 轮换）/`--softwall` 客户端干预（strip 删遮罩+解滚动锁/reader 只计数，正文零落盘）/`--text-proxy` 通用文本代理前缀；快照与代理复用跳转守卫+SSRF+正文判定，check 只报情报不改变验证结论。详见 MANUAL §10。
- **运维安全**：日志 URL 只到 path、Cookie/代理凭证永不打印、代理开工前预检、导航错误 11 类诊断、robots 默认遵守

## 维护

```powershell
python -u -X utf8 tests\test_security.py   # 回归闸门：266 项全过，exit 0
python -X utf8 -m py_compile site_crawler.py watchflow.py tui.py
python -u -X utf8 site_crawler.py envcheck
```

改动代码后必须跑上面三条。任何 assert 失败都代表被攻破——修代码，不改测试。

## 杀毒软件误报说明

本工具含浏览器自动化、代理支持、TLS 指纹伪装等字样，部分杀毒软件（McAfee、腾讯电脑管家等）可能误报为 HackTool 并隔离 `.py` 文件。代码完全开源可审计；如遇隔离，请将项目目录加入杀毒软件信任区/排除列表后从隔离区恢复。

## 已知限制

- 只下载公开可访问的媒体：不破 DRM、不做验证码打码（人工验证是唯一通道）；四路径扩展默认全关，仅限自有/授权内容研究测试
- bot 伪装（googlebot/bingbot）对强风控站大概率 403，且无对应 TLS 指纹（强制 requests+告警）；mobile 伪装的 TLS 指纹仍是桌面 preset（curl_cffi 无移动端 preset），指纹错配风险自负
- SESSION 混淆的站（如需 APP 级 token 的 m3u8）可能取不到流，看日志 `fetch_fail` 样本
- 反追踪是纵深防御，不保证 100% 绕过强风控

## License

Apache-2.0 © 2026 jjjjjjjjnnjnn，见 [LICENSE](LICENSE)。
