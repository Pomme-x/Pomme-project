# Pomme 博客小工具

双击 **`启动Pomme工具.bat`** 打开图形界面（不会弹黑色命令行窗口）。

## 功能

### 1. 上传周报 PDF

1. 点 **添加 PDF…** 选择文件（可以一次选多个）
2. 标题/日期/标签/分类可留空自动识别（标题自动取 PDF 第一页最大的字）
3. 点 **上传并发布**

工具会自动：

- 把 PDF 转成和第一篇周报一样的网页文章：正文文字、截图、表格、代码高亮（不需要点 PDF）
- 图片压缩成 JPEG，放到文章的独立图片目录
- 生成文章 Markdown 到 `source/_posts/`
- **通过 GitHub API 直接提交**（本机不需要装 git，也不用手动 push）
- 等 GitHub Actions 部署完成，告诉你是否上线

### 2. 外观设置

- **换背景**：内置「粉色星云」「黑洞」，或选「我的图片…」上传任意图片，
  会自动裁成 4:1 宽幅并压暗（保证白色标题清晰）
- **改站点信息**：站点标题、副标题、作者
- 点 **保存并发布** 后自动提交部署

### 3. 状态

查看 Token 状态、远端最新提交、最近一次部署结果，一键打开网站 / 仓库 / Actions。

## 首次使用：设置 GitHub Token

- 打开 **状态 → 设置 GitHub Token**，粘贴一个 GitHub Personal Access Token（经典 token 勾 `repo` 即可，或用 fine-grained token 给本仓库 `Contents: Read and write` 权限）
- Token 用 **Windows DPAPI 加密**后保存在 `%APPDATA%\Pomme\token.bin`，只有当前 Windows 用户能解密
- 换电脑/换用户需要重新设置；想清除就直接删掉这个文件

## 依赖

- Python 3（优先用 DSH 自带 Python，其次用系统 Python）
- `pymupdf`、`Pillow`（本机两套 Python 都已装）
- 需要能访问 GitHub 的网络

## 原理 / 文件说明

| 文件 | 作用 |
|---|---|
| `pomme_tool.py` | 图形界面主程序 |
| `pdf2post.py` | PDF → Markdown 转换（文字/截图/表格/代码块） |
| `github_api.py` | 用 GitHub REST API 一次性提交多个文件（Git Data API）|
| `token_store.py` | Windows DPAPI 加密保存 Token |
| `启动Pomme工具.bat` | 双击启动 |

> 工具目录 `tools/` 不会被 Hexo 发布到网站上，只存在于仓库里。
> 用工具发布后，本地 `F:\ctf\Pomme` 的 git 记录可能落后于 GitHub，这不影响网站；需要本地同步时执行 `git fetch origin && git reset --hard origin/main`。
