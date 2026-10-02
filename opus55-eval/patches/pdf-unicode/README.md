# PDF 中文字体补丁源码

仅包含 `PDFFont.java`、`PDFPainter.java` 两份修改后的 GPL 源码及许可证，不含编译后的软件。
来自 [TuxGuitar 1.6.6 固定提交](https://github.com/helge17/tuxguitar/tree/4414c9ccf1ea8d7f229afc6af73410e75ed9c91c/common/TuxGuitar-pdf/src/org/herac/tuxguitar/io/pdf)，用于复现历史脚本的中日文字体回退与宽度测量。
运行者先自行下载 TuxGuitar、Rhino、字体，再执行根目录 `configure_tools.py`，由本机 JDK 编译补丁。
编译目标是 Java 17；编译器版本及产物 SHA256 会记录，原厂 JAR 不会被修改。主说明见 `../../README.md`。
