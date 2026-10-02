原生 GP + TuxGuitar 工具（不包含任何歌曲答案）

使用 TuxGuitar 1.6.6 Java 读谱和 PDF 导出组件，不需要启动 GUI、Guitar Pro 或 MuseScore。
TuxGuitar 只读取 GP7 .gp，不能直接另存为 .gp；使用下面的 GPIF 打包工具写原生工程。

python3 tools/tuxguitar.py init draft.gp --guitars 2
python3 tools/gp_archive.py unpack draft.gp score.gpif
# 编辑 GPIF XML；所有音乐内容必须自行从给定音频分析和改编。
python3 tools/gp_archive.py pack score.gpif output/arrangement.gp
python3 tools/tuxguitar.py inspect output/arrangement.gp > score-inspection.json
python3 tools/tuxguitar.py check output/arrangement.gp
python3 tools/tuxguitar.py pdf output/arrangement.gp preview.pdf

init 只创建标准调弦、120 BPM、4/4 的空白谱；这些默认值不代表歌曲信息或任务限制。
GPIF 数据表 Tracks、MasterBars、Bars、Voices、Beats、Notes、Rhythms 通过 id/ref 相连。
修改小节数、人数、节奏和音符时须同步维护引用。允许多声部、不同调弦、变调夹及演奏技巧。
inspect 输出 TuxGuitar 导入后的轨道、弦/品、节奏和技巧信息，并保留已知的 GP7 变调夹修复。
check 仅检查原生 GP 容器和非空音符，不能证明音乐质量或实际可演奏性。
PDF 使用项目已有的 Unicode 字体补丁，谱面渲染支持范围受固定 TuxGuitar 导入器限制。
不要为迎合渲染器而删除有音乐意义的写法；必要时记录显示限制。
最小 GP7 ZIP 可被本工具读取，不等于已经在所有商业 Guitar Pro 版本中验证兼容性。
Java 可通过 JAVA 或 JAVA_HOME 指定；本机启动器会写入 runtime.json，容器使用 PATH 中的 java。
软件及字体不随交接包分发，按根目录 README.md 自行下载配置。实验操作者运行 configure_tools.py 后会在 vendor/ 生成运行时依赖。PDF 补丁源码与许可证保存在交接包 patches/pdf-unicode/。
