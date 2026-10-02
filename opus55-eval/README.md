# Windows 吉他编曲评测交接：Opus 5.5

这是运行者的总 README。**交接包只有任务、评测脚本、依赖清单和两份 PDF 补丁源码；不包含歌曲音频、软件安装包、JAR、字体或登录信息。** 所有软件由接收方按链接自行下载和配置。

默认评测：**Claude Code + `claude-opus-5-5`、`high`、并发上限 2、每首 60 分钟**。Windows 10/11 原生 PowerShell 可运行，不要求 Docker 或 WSL。

**任务要求与此前完全相同，版本保持 v0.2.2：最终每首只交一个原生 `arrangement.gp`。** 七首 `instruction.md` 和 `task.toml` 原样保留；本 README 只说明 Windows 的环境配置和交接步骤，不覆盖或放宽任务规则。

## 1. 软件由对方自行安装

| 软件 | 要求 / 用途 | 官方下载与配置链接 |
|---|---|---|
| Python | 推荐 Windows Python 3.12，带 `py` 启动器 | [Python Windows 下载](https://www.python.org/downloads/windows/) |
| Claude Code | Windows 原生客户端，登录自己的账号并确认 Opus 5.5 权限 | [Windows 安装说明](https://code.claude.com/docs/en/setup#set-up-on-windows) |
| Git for Windows | 按 Claude Code 官方安装说明配置所需 shell | [Windows 下载](https://git-scm.com/downloads/win) |
| TuxGuitar | 原任务的读谱/制谱辅助工具；固定文件验证使用 1.6.6 的 Java 库 | [TuxGuitar 1.6.6 发布页](https://github.com/helge17/tuxguitar/releases/tag/1.6.6) · [Windows ZIP](https://github.com/helge17/tuxguitar/releases/download/1.6.6/tuxguitar-1.6.6-windows-swt-x86_64.zip) |
| Guitar Pro 8 | 可自行安装用于打开、查看 GP 文件；具体使用范围以原始 instruction 为准 | [官方 Windows 下载入口](https://www.guitar-pro.com/download-guitar-pro) |
| JDK 21 | 验证工具运行及小型 PDF 补丁编译；需包含 `java.exe` 和 `javac.exe` | [Temurin 21 下载，选择 Windows](https://adoptium.net/temurin/releases/?version=21) |
| yt-dlp | 按指定链接下载音频 | [官方安装页](https://github.com/yt-dlp/yt-dlp#installation) · [Windows exe](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe) |
| FFmpeg | 解码原曲 WAV，不改变音乐内容 | [官方下载入口，选择 Windows builds](https://ffmpeg.org/download.html#build-windows) |
| Rhino 1.7.15 | Java 脚本桥，文件名 `rhino-1.7.15.jar` | [官方发布页](https://github.com/mozilla/rhino/releases/tag/Rhino1_7_15_Release) · [Maven JAR](https://repo.maven.apache.org/maven2/org/mozilla/rhino/1.7.15/rhino-1.7.15.jar) |
| Noto Sans CJK SC | 脚本 PDF 的中文字体，Regular 与 Bold 两份，固定版本 | [Regular](https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf) · [Bold](https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Bold.otf) |

交付格式与软件安装是两回事。无论安装哪些软件，交付仍是同一个 `.gp` 文件，工具使用须遵循各任务原始 instruction。固定 verifier 需要 TuxGuitar Java 库；仅安装 Guitar Pro 8 不会自动装好验证依赖。

按各官方安装页配置环境，之后重新打开 PowerShell。建议把交接包放到 `C:\guitar-eval\opus55-eval`。Python 命令示例统一使用 `py -3 -X utf8`，以正确处理中文任务和日志。

确认基础命令可用：

```powershell
py -3 --version
claude --version
java -version
javac -version
yt-dlp --version
ffmpeg -version
```

若 Java 不在 PATH，可在当前 PowerShell 会话中设置实际安装目录：

```powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\你的JDK21目录'
$env:JAVA = "$env:JAVA_HOME\bin\java.exe"
$env:FFMPEG = 'C:\Tools\ffmpeg\bin\ffmpeg.exe'
```

操作者负责开始前的软件安装、登录与环境配置，不在测试中替 agent 编曲、听写或修改提交。软件安装链接不是额外的任务权限或流程变更。

## 2. 配置固定的文件验证 / PDF 依赖

先自行下载并解压 TuxGuitar 1.6.6，下载 Rhino JAR 和两份字体。然后将下面的示例路径换成实际下载路径，在交接目录执行：

```powershell
py -3 -X utf8 configure_tools.py --tuxguitar 'C:\Tools\tuxguitar-1.6.6' --rhino 'C:\Tools\rhino-1.7.15.jar' --font-regular 'C:\Tools\NotoSansCJKsc-Regular.otf' --font-bold 'C:\Tools\NotoSansCJKsc-Bold.otf' --javac 'javac'
```

这个脚本**不下载软件、不安装应用、不改全局配置**。它从你指定的解压目录中找出所需 JAR，检查 [dependencies.json](dependencies.json) 中的历史文件哈希，复制到本包的运行目录，再编译两份 PDF 字体补丁源码。配置产物由你本地生成，不在交接 ZIP 中。

若 Windows 发行包的 JAR 哈希与历史版本不同，不要静默跳过检查；可从[历史使用的 1.6.6 发行包](https://github.com/helge17/tuxguitar/releases/download/1.6.6/tuxguitar-1.6.6-macosx-swt-cocoa-x86_64.app.tar.gz)解压后，把解压目录传给 `--tuxguitar`。这里只取跨平台 Java 库，**不执行其中的 macOS 应用或 JDK**，运行时仍使用你安装的 Windows JDK。

字体和 JAR 哈希都匹配后，脚本会打印配置信息。PDF 补丁使用同一源码，实际编译器和生成 JAR 的 SHA256 会记录在 `tools/vendor/dependency-state.json`；编译器差异不会被伪装成字节相同。

PDF 是可选的谱面辅助检查，最终交付不包含 PDF。任务仍使用原生 GP + TuxGuitar 流程，固定 GP 文件 verifier 保持原有解析逻辑。

## 3. 原曲链接：下载同一版本

以下是此前实验实际使用的来源，既有 MV，也有官方专辑音轨和歌词视频。不要按曲名另外搜索替换；尤其 Smooth Criminal 使用的是 2012 Remaster 专辑音轨，不是长版 MV。

| 任务 | 原曲链接 | 指定版本 | 频道 | 时长（秒） | 吉他数 |
|---|---|---|---|---:|---:|
| `02-fix-you` | [Fix You](https://www.youtube.com/watch?v=Oncu0bgdcXU) | 《X&Y》官方专辑音轨 | Coldplay | 295.533 | 1 |
| `03-payphone` | [Payphone](https://www.youtube.com/watch?v=5FlQSQuv_mg) | 官方 Lyric Video（feat. Wiz Khalifa） | Maroon 5 | 231.515 | 1 |
| `04-zenzenzense` | [前前前世](https://www.youtube.com/watch?v=PDSkFeMVNFs) | movie ver. 官方 MV | RADWIMPS | 292.328 | 1 |
| `06-christmas-eve` | [Christmas Eve](https://www.youtube.com/watch?v=1-xwxyHOyVw) | 官方 Christmas Eve MV | 山下達郎   Tatsuro Yamashita | 260.969 | 1 |
| `08-smooth-criminal` | [Smooth Criminal](https://www.youtube.com/watch?v=wkJTd_wKl0k) | 《Bad》2012 Remaster 官方专辑音轨（不是长版 MV） | Michael Jackson | 257.760 | 2 |
| `09-chocolate-disco` | [Chocolate Disco](https://www.youtube.com/watch?v=1WTy2yqKI4w) | 官方 MV | Perfume | 229.611 | 3 |
| `10-koi` | [恋](https://www.youtube.com/watch?v=KMdTrqzEI0I) | 官方单曲音轨 | 星野源 Gen Hoshino | 253.333 | 3 |

完整网页标题、视频 ID、格式 ID、历史 PCM 哈希和输出路径见 [audio-sources.json](audio-sources.json)，简表见 [tasks.csv](tasks.csv)。这些信息来自历史下载记录，本次打包未重新下载，不保证当前各地区均可访问。

```powershell
py -3 -X utf8 audio.py list
py -3 -X utf8 audio.py download
py -3 -X utf8 audio.py check
```

下载器使用历史音轨格式 `251`（Opus/WebM），转换为 **48 kHz、双声道、16-bit PCM WAV**，保存到 `tasks/<任务ID>/environment/original.wav`。全曲解码，不剪裁、不调速、不归一化。原始流和来源记录在 `downloads/`；不会导出到结果包。

单曲下载示例：

```powershell
py -3 -X utf8 audio.py download --tasks 04-zenzenzense
```

也可自行从表中同一链接下载，再解码：

```powershell
ffmpeg -i 'C:\Downloads\Fix You.webm' -map 0:a:0 -vn -ar 48000 -ac 2 -c:a pcm_s16le -map_metadata -1 '.\tasks\02-fix-you\environment\original.wav'
py -3 -X utf8 audio.py check --tasks 02-fix-you
```

检查以解码 PCM 哈希为准，WAV 文件头变化不会影响判定。若链接/格式不可用或哈希不一致，先反馈组织者，不要换另一段音轨顶替。经确认需要保留同录音的重新编码变体时，可显式加 `run --allow-audio-variant`，结果会标记输入差异，不能称为完全相同输入。

## 4. 自检和启动七首

```powershell
py -3 -X utf8 run.py doctor
py -3 -X utf8 run.py probe
py -3 -X utf8 run.py run
```

`doctor` 检查静态文件、外部依赖、音频、Java 和 CLI。`probe` 是一次真实最小模型调用，会消耗少量额度；确认实际为 Opus 5.5。模型 ID 与客户端支持请参考[官方模型配置](https://code.claude.com/docs/en/model-config)，不要使用浮动别名或 fallback 顶替。

把实际软件环境记入本次实验的示例：

```powershell
py -3 -X utf8 run.py run --agent claude-code --model claude-opus-5-5 --effort high --concurrency 2 --timeout 3600 --environment-notes 'Windows 11；TuxGuitar 1.6.6；JDK 21；工具路径：请填写实际配置'
```

每首正式改编提示词来自原样保留的 instruction；`--environment-notes` 只填写路径、版本等客观环境信息，不添加音乐提示或改变工具要求。

PowerShell 窗口在运行时保持打开，机器不要休眠或重启。每次 `run` 建立新批次和新会话，不自动续聊、重试或挑选最好结果。当前最多两个并行任务，不要另开第二批。

```powershell
# 将路径换为启动时打印的 BATCH
py -3 -X utf8 run.py status '.\runs\batch-实际编号'

# 仅准备工作区，不调用模型；仍需配置软件和原曲
py -3 -X utf8 run.py run --prepare-only
```

Ctrl+C 会停止本批次并保留日志。Windows 超时/中断使用进程树终止；独立于 agent 进程树启动的软件不在自动终止范围。机器重启后的陈旧状态由 `status` 提醒，重试应另建批次。

## 5. 交付与回传

每首最终只交 `workspace/output/arrangement.gp`，是包含 `Content/score.gpif` 的原生 GP7/8 文件。原任务用代码创建或编辑 GPIF 并打包，再用 TuxGuitar 读取检查。不能把其他格式改后缀充当 `.gp`。

中间分析结果、脚本和 PDF 放在 `output` 以外，具体制谱与中间格式约束按原 instruction 执行。输入音乐内容只来自给定音频，禁止获取现成网络谱、和弦谱、MIDI 答案或隐藏参考谱。

结束后执行：

```powershell
py -3 -X utf8 run.py export '.\runs\batch-实际编号' --output '.\opus55-results.zip'
```

回传 `opus55-results.zip`，包含 GP、运行设置、轨迹、实际耗时和验证报告；不含音频、软件、缓存或认证文件。失败与超时也保留，不手工修改模型提交。

`parseable_score=1` 仅代表固定 TuxGuitar 解析器读到了非空谱；不是音乐质量、编制合规或可演奏性评分。GP8 能打开而固定解析器失败时，保留文件及错误供人工核查，不能直接把“工具不支持”当作“谱损坏”。额外输出单独记录为 `sole_gp_output`，不改变历史解析器的评分口径。

## 6. 任务版本与后续评审

此 Windows 交接任务保持 **v0.2.2**。七首 instruction 和 task.toml 与此前版本逐字节一致，原曲、人数、音乐质量要求、工具约束、唯一 GP 交付和独立创作规则均未改变。只调整了跨平台启动与外部软件配置方式，历史提交未改写。

这批应记录为 **Claude Code + Opus 5.5 / Windows / v0.2.2**，并附实际软件与版本。任务相同，但 agent 和操作系统与历史批次不同，结果不能只归因于底层模型；跨厂商 `high` 也不是相同算力。

组织者在另一环境保管 `organizer-only.zip`，含参考谱、四模型 28 份历史提交、A/B 准备与汇总脚本。运行者不需这个包。Codex 与人类后续独立比较同曲 reference + 匿名 A/B，四个维度和总体 verdict 仅取 `A/B/tie/undetermined`；交换 A/B 后用新会话复评。当前没有音乐质量排名。

## 7. 文件结构及验证范围

```text
README.md                本说明
dependencies.json        外部依赖下载信息与历史哈希
configure_tools.py       使用接收方已下载文件完成本地配置
audio-sources.json       七首原曲链接、版本、时长与 PCM 哈希
audio.py                 原曲下载与检查
run.py                   运行、进度、验证和结果导出
tasks/                   七份 instruction、task.toml 及 Dockerfile
tools/                   评测自带的 Python/JavaScript 辅助脚本，无软件二进制
verifier/                原始解析逻辑；JAR 由接收方配置
patches/pdf-unicode/     两份 PDF 补丁源码及 GPL 许可证
checksums.json           交接包内静态文本文件校验
```

保留原 Harbor 元数据。如需完整逐任务目录，在音频与依赖配置好后执行 `py -3 -X utf8 run.py export-harbor --output harbor-tasks`。本次交接使用 Windows 本机入口，不要求 Docker；原 task.toml 中容器的 CPU/内存限制不会施加到本机。

已验证：在本机用外部依赖重新配置、编译同一补丁、GP 读取和中文 PDF，以及模拟 agent 的流程。Windows 进程分支采用独立逻辑检查；**尚未在 Windows 真机执行七首或真实 Opus 测试**，接收方须按上面的 doctor/probe 完成环境自检。
