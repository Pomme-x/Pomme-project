---
title: Hello Pomme
date: 2026-10-25 12:00:00
tags:
  - 开始
categories:
  - 随笔
---

这是 **Pomme** 的第一篇文章。

## 如何写一篇新文章

```bash
# 新建文章（会自动生成 source/_posts/2026-10-25-标题.md）
pnpm new "我的文章标题"

# 本地预览 http://localhost:4000/Pomme-project/
pnpm server

# 构建静态文件到 public/
pnpm build
```

文章正文用 Markdown 写，图片放到 `source/images/` 下，正文里用 `/Pomme-project/images/xxx.png` 引用。

## 你可以删掉这篇文章

写好自己的第一篇文章后，直接删除 `source/_posts/hello-pomme.md` 即可。
