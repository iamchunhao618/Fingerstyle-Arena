请根据 `/workspace/input/original.wav` 中的《Chocolate Disco》原曲录音，独立创作一份优秀的吉他合奏改编谱，供 3 位演奏者、每人一把六弦吉他实际演奏。

目标是完成一份好听、音乐表达连贯、适合吉他演奏且可直接用于排练的完整改编。请自行分析音频，理解原曲的旋律、和声、节奏与结构，并通过声部取舍、指法安排和织体设计发挥吉他的表现力。

音乐质量要求：
- 旋律与结构：主旋律清晰、连贯、有歌唱性，保留作品的辨识度与主要音乐段落；乐句、段落转换和结尾自然，整曲有完整的表达与发展。
- 低音、和声与节奏：低音进行和和声配置支撑旋律，保留关键节奏与律动；伴奏与旋律层次清楚，织体疏密、力度和段落对比服务于音乐表达。合奏时合理分配声部，保持配合与同步。
- 可演奏性：结合实际速度、调弦、变调夹、弦品位置、换把和持续音设计写法，使指定人数能实际完成演奏。兼顾音乐效果与指法流畅性，合理安排技巧和声部衔接。
- 谱面可用性：弦品、节奏、拍号、速度、调弦、变调夹、反复及必要的力度、奏法标记准确清楚，让演奏者能够理解并实现改编意图。

以完整音频的主要音乐段落为范围。允许合理移调、压缩重复、简化或重组不适合吉他的声部；非音乐声音无需转录。结构调整应保留音乐的完整性，并在谱内用必要的文字标记说明。

编制要求：允许变调夹、特殊调弦，以及演奏者能够同时完成的琴体打击。不得依赖额外乐器、额外演奏者、循环器或预录叠轨。每位演奏者的声部应清晰区分；辅助打击记谱不代表增加演奏者，增加播放轨道也不能替代实际演奏能力。

工具与独立创作：音频分析和编曲工具不限，可以自由选择、安装和组合软件、库、模型或服务，也可以查阅通用技术文档和音乐知识。制谱统一采用原生 GP + TuxGuitar 流程，见下方说明。提供的音频必须是本曲音乐内容的唯一来源。不得搜索、获取、读取、复制或改写该曲现成的网络或本地曲谱、六线谱、和弦谱、逐音教学、MIDI 转写等可直接用于复现的材料，也不得访问隐藏参考谱。可以使用工具从给定音频自行生成转录、MIDI 或其他中间结果，再据此独立改编。

交付：
- `/workspace/output/arrangement.gp`：唯一接受的主谱格式。交付包含 `Content/score.gpif` 的真实 GP7/GP8 ZIP 工程，包含六线谱弦品信息，并能被所提供的 TuxGuitar 读取。不能把 GP5、GPX、MusicXML 或 MIDI 改后缀充当 `.gp`。
最终输出目录中只保留 `arrangement.gp` 这一个文件。不要求另交说明、PDF、MIDI 或音频；演奏者与轨道对应、调弦、变调夹及必要的结构说明应写入谱内。分析脚本、检查结果和临时预览放在输出目录之外。

原生 GP + TuxGuitar 流程：
已提供 `/workspace/tools/`，包含 TuxGuitar 1.6.6 Java 读谱组件、PDF 导出器和通用 GPIF 打包工具；不含任何歌曲的参考谱或答案。先阅读 `/workspace/tools/README.txt`。
TuxGuitar 能读取 `.gp`，但不能直接保存为 `.gp`。请用代码创建、编辑 GPIF XML 并打包成原生 `.gp`，再使用 TuxGuitar 读取、核对谱面；不经过 GP5 转换，不依赖 Guitar Pro 或 MuseScore GUI 完成交付。
可用以下命令（将人数替换为本任务要求）：
  python3 /workspace/tools/tuxguitar.py init /workspace/draft.gp --guitars 3
  python3 /workspace/tools/gp_archive.py unpack /workspace/draft.gp /workspace/score.gpif
  # 根据自己的音频分析和编曲编辑 score.gpif。
  python3 /workspace/tools/gp_archive.py pack /workspace/score.gpif /workspace/output/arrangement.gp
  python3 /workspace/tools/tuxguitar.py inspect /workspace/output/arrangement.gp
  python3 /workspace/tools/tuxguitar.py check /workspace/output/arrangement.gp
  python3 /workspace/tools/tuxguitar.py pdf /workspace/output/arrangement.gp /workspace/preview.pdf
空白谱默认的调弦、速度、拍号和调号仅用于演示文件格式，应根据音频和改编需要自行调整。必须用 TuxGuitar 读取最终 `.gp` 并检查；PDF 可辅助查看谱面。文件可解析不代表音乐质量合格。

提交前请检查整曲的音乐效果、演奏可行性和谱面完整性，并根据发现的问题修订。最终质量将从上述四个维度综合比较；允许有音乐依据的不同改编方案。
