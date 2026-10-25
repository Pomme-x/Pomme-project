# Pomme
- 仓库：<https://github.com/Pomme-x/Pomme-project>
- 站点（部署后）：<https://pomme-x.github.io/Pomme-project/>
- 本地目录：`F:\ctf\Pomme`

---

## 1. 目录结构

```
Pomme/
├─ _config.yml                 # 站点主配置（标题、URL、主题、插件）
├─ _config.landscape.yml       # 主题配置（导航、侧边栏、favicon、评论）
├─ package.json                # 依赖与脚本（pnpm）
├─ pnpm-lock.yaml              # 锁定版本，Actions 里用 --frozen-lockfile
├─ scaffolds/                  # hexo new 生成文章的模板
├─ source/
│  ├─ _posts/                  # 文章（.md）
│  ├─ about/index.md           # “关于”页面
│  ├─ images/                  # 图片（正文用 /images/xxx.png 引用，Hexo 会自动加仓库根路径）
│  └─ favicon.png              # 站点图标
└─ .github/workflows/pages.yml # 推送到 main 后自动构建并发布到 GitHub Pages
```

备注：仓库里原有的 `周报/` 文件夹不会被 Pages 发布（Pages 只发布构建出来的 `public/`），它仍然留在仓库里可正常下载。

## 2. 本地预览

本机没有全局 Node/npm，用的是 DSH 自带的 Node：

```bash
# 一次性：把自带 node 加进 PATH（Git Bash 里）
export PATH="/c/Users/tom/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin:$PATH"
cd /f/ctf/Pomme

# 依赖已安装（pnpm），启动预览：
node /c/Users/tom/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/pnpm/bin/pnpm.mjs server
# 打开 http://localhost:4000/Pomme-project/
```

> 有全局 Node 的机器上直接 `pnpm install && pnpm server` 即可。

## 3. 写文章

```bash
pnpm new "从两个 C 语言题读懂栈"     # 生成 source/_posts/2026-10-25-从两个-C-语言题读懂栈.md
pnpm build                          # 只构建到 public/
pnpm clean                          # 清理缓存
```

> 本机没有全局 pnpm 时，把上面的 `pnpm xxx` 换成：
> `node /c/Users/tom/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/pnpm/bin/pnpm.mjs xxx`

写好自己的第一篇文章后，可以删掉示例文章 `source/_posts/hello-pomme.md`（不删也不影响部署）。

文章头部（front-matter）：

```yaml
---
title: 文章标题
date: 2026-10-25 20:00:00
tags:
  - 二进制安全
  - CTF
categories:
  - 笔记
---
```

图片：放到 `source/images/`，正文写 `![说明](/images/xxx.png)`（**不要**带 `/Pomme-project` 前缀，Hexo 会自动加）。

### 3.1 不装环境：直接在 GitHub 网页上传文件

打开 <https://github.com/Pomme-x/Pomme-project>，用 **Add file → Upload files**（或 **Create new file**）即可，提交到 `main` 后 Actions 会自动构建，约 1 分钟上线。

- **想发成一篇博客文章**：复制仓库根目录的 [文章模板.md](文章模板.md)，改名成 `2026-10-26-我的标题.md`，放到 `source/_posts/`，开头必须是 front-matter：
  ```yaml
  ---
  title: 我的周报
  date: 2026-10-25 20:00:00
  tags:
    - 周报
  ---

  正文（Markdown）……
  ```
  提交后首页/归档/标签页会自动出现这篇文章。
- **附件 / PDF**：放到 `source/` 下会随站点一起发布（例如 `source/files/xxx.pdf` → `https://pomme-x.github.io/Pomme-project/files/xxx.pdf`）。仓库根目录的 `周报/` 不参与构建。
- **图片**：放到 `source/images/`，正文用 `/images/xxx.png` 引用（**不要**带 `/Pomme-project`，Hexo 会自动加）。
- **周报（是一个目录）**：顶部导航「周报」→ `https://pomme-x.github.io/Pomme-project/周报/` 是**周报目录页**，会自动列出所有分类/标签带「周报」的文章，每篇放在 `/周报/<英文短名>/` 下。
  文件位置：目录页是 `source/周报/index.md`；每篇周报是 `source/_posts/` 里分类为「周报」的文章（正文内嵌 PDF 内容，不用点 PDF）。
  新周报直接用下面 3.2 的小工具上传即可，会自动出现在列表里。

### 3.2 图形小工具（最省事，推荐）

双击 **`tools\启动Pomme工具.bat`**，打开「Pomme 博客小工具」：

- **上传周报 PDF**：选 PDF → 点「上传并发布」，自动完成
  PDF→网页文章（文字 + 截图 + 表格 + 代码高亮）、图片压缩、自动放到 `/周报/` 目录、提交、等 Actions 部署。
- **外观设置**：换顶部背景（粉色星云 / 黑洞 / 自己的图片，自动裁成 4:1 并压暗）、改站点标题/副标题/作者，
  点「保存并发布」就上线。
- **导航菜单**：自己添加/编辑/排序/删除顶部导航（Home / 周报 / 关于…），新菜单可以顺带创建对应页面。
- **文章管理**：改文章的标题/日期/分类/标签/永久链接（分类页、标签云自动更新）、删除文章、把文章移动到「周报」「Wp」等分区。
- **仓库管理**：浏览目录、双击编辑文件、上传/新建/删除文件，改仓库简介、重命名仓库、修复 GitHub Pages。
- **进入博客**：标题栏右上角按钮，一键打开网站；也有 GitHub 仓库、Actions 入口。

详见 [tools/README.md](tools/README.md)。工具用 GitHub API 直接提交，**本机不需要装 git**；GitHub Token 用 Windows DPAPI 加密保存在 `%APPDATA%\Pomme\token.bin`。依赖 `pymupdf`、`Pillow`（本机已装）。

## 4. 部署状态（已完成）

- 站点：<https://pomme-x.github.io/Pomme-project/>（已上线，HTTPS 已强制）
- 仓库：<https://github.com/Pomme-x/Pomme-project>，`main` 每次推送 → `.github/workflows/pages.yml` 自动构建发布
- Pages 设置：**Settings → Pages → Source = GitHub Actions**（已开启，`build_type: workflow`）
- 首次部署的 Actions 运行记录：<https://github.com/Pomme-x/Pomme-project/actions>

本地开发时用：

```bash
cd /f/ctf/Pomme
git pull                       # 先同步网页上改的内容
# 改文章 / 改配置后：
git add -A && git commit -m "update" && git push
```

> 本机已保存 GitHub 凭据（Windows 凭据管理器，用户 `Pomme-x`），推送时用 `GIT_SSL_NO_VERIFY=true` 绕过本机证书吊销检查即可。

## 5. 修改站点信息

- 站点标题/副标题/作者：`_config.yml` 的 `title`、`subtitle`、`author`
- 导航（Home / Archives / 关于）、右上角社交图标、侧边栏组件、评论：`_config.landscape.yml`
- 顶部横幅图：把图片放到 `source/images/banner.jpg`，并在 `_config.landscape.yml` 把 `banner` 改成 `"/Pomme-project/images/banner.jpg"`（项目页必须带仓库名前缀；当前用主题自带的星空图）
- 换主题：`pnpm add hexo-theme-<名字>` 后把 `_config.yml` 的 `theme` 改掉

## 6. 当前状态

- [x] Hexo 7.3.0 + Landscape 主题，`hexo generate` 构建通过，本地预览正常（Home / Archives / 关于 / 文章页 / atom.xml）
- [x] 示例文章 `hello-pomme`、`关于` 页、小苹果 favicon
- [x] GitHub Actions Pages 工作流（pnpm + Node 22 + `actions/deploy-pages@v5`）
- [x] 站点 url/root 已指向 `Pomme-x/Pomme-project`
- [x] 首次 `git push` 完成，Actions 部署成功
- [x] 仓库 Pages 已开启（Source = GitHub Actions），站点已上线
- [x] 周报 PDF 已转成网页内容内嵌到「周报」页（51 页、64 张截图、2 个表格，无需点 PDF）
- [ ] 后续周报/文章自己上传，或发我转换
