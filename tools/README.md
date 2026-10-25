# Pomme 博客小工具

双击 **`启动Pomme工具.bat`** 打开图形界面。

## 功能

### 1. 上传周报 PDF

1. 点 **添加 PDF…** 选择文件（可以一次选多个）
2. 标题/日期/标签/分类可以留空或修改（标题默认自动从 PDF 里识别）
3. 点 **上传并发布**

工具会自动：

- 把 PDF 转成和第一篇周报一样的网页文章：正文文字、截图、表格、代码高亮（不需要点 PDF）
- 图片压缩成 JPEG 并放到 `source/images/weekly-<标题>/`
- 生成 `source/_posts/日期-标题.md`
- `git commit` + 推送到 GitHub
- 等 GitHub Actions 构建完成，告诉你是否上线

### 2. 外观设置

- **换背景**：内置「粉色星云」「黑洞」，或选「我的图片…」上传任意图片，
  会自动裁成 4:1 宽幅并压暗（保证白色标题清晰）
- **改站点信息**：站点标题、副标题、作者
- 点 **保存并发布** 后自动提交部署

### 3. 状态

查看仓库路径、最近提交、工作区改动、站点信息，一键打开网站 / 仓库 / Actions。

## 环境

- 依赖 `pymupdf`、`Pillow`（本机已装）
- 优先使用 DSH 自带 Python；没有时用系统 Python（需 `pip install pymupdf pillow`）
- GitHub 凭据取自 Windows 凭据管理器里的 `git:https://github.com`（用户 `xunshichen-2008`）

## 文件说明

| 文件 | 作用 |
|---|---|
| `pomme_tool.py` | 图形界面主程序 |
| `pdf2post.py` | PDF → Markdown 转换（文字/截图/表格/代码块） |
| `启动Pomme工具.bat` | 双击启动 |

> 工具目录 `tools/` 不会被 Hexo 发布到网站上，只存在于仓库里。
