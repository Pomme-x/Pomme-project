# Pomme

一个和 <https://fryy13427.github.io/> 同款结构的 **Hexo 博客**（Hexo 7.3.0 + Landscape 主题 + GitHub Actions 自动构建部署）。

- 仓库：<https://github.com/xunshichen-2008/Pomme-project>
- 站点（部署后）：<https://xunshichen-2008.github.io/Pomme-project/>
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
│  ├─ images/                  # 图片（正文用 /Pomme-project/images/xxx.png 引用）
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

图片：放到 `source/images/`，正文写 `![说明](/Pomme-project/images/xxx.png)`。

## 4. 部署（已全部配好，只差一次推送）

`_config.yml` 里已经按你的仓库配好：

```yaml
url: https://xunshichen-2008.github.io/Pomme-project
root: /Pomme-project/
```

正式推送步骤：

```bash
cd /f/ctf/Pomme
git push -u origin main        # 第一次推送
```

然后在仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
之后每次 push 到 `main`，`.github/workflows/pages.yml` 会自动构建并发布，访问：

<https://xunshichen-2008.github.io/Pomme-project/>

> 首次推送需要 GitHub 凭据。GitHub 已不接受账号密码，要用 Personal Access Token（fine-grained token，仓库 `Pomme-project`，权限 `Contents: Read and write`；若用公开仓库的经典 token 勾 `repo` 即可）当密码。
> 把 token 发我，我直接推送并盯着 Actions 跑完；或者用 GitHub Desktop / VS Code 登录后自己点推送。

## 5. 修改站点信息

- 站点标题/副标题/作者：`_config.yml` 的 `title`、`subtitle`、`author`
- 导航（Home / Archives / 关于）、右上角社交图标、侧边栏组件、评论：`_config.landscape.yml`
- 顶部横幅图：把图片放到 `source/images/banner.jpg`，并在 `_config.landscape.yml` 把 `banner` 改成 `"/Pomme-project/images/banner.jpg"`（项目页必须带仓库名前缀；当前用主题自带的星空图）
- 换主题：`pnpm add hexo-theme-<名字>` 后把 `_config.yml` 的 `theme` 改掉

## 6. 当前状态

- [x] Hexo 7.3.0 + Landscape 主题，`hexo generate` 构建通过，本地预览正常（Home / Archives / 关于 / 文章页 / atom.xml）
- [x] 示例文章 `hello-pomme`、`关于` 页、小苹果 favicon
- [x] GitHub Actions Pages 工作流（pnpm + Node 22 + `actions/deploy-pages@v5`）
- [x] 站点 url/root 已指向 `xunshichen-2008/Pomme-project`
- [ ] 首次 `git push`（等 GitHub token）
- [ ] 仓库 Settings → Pages 选 GitHub Actions
