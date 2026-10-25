# -*- coding: utf-8 -*-
"""Pomme 博客小工具（Windows 图形界面）

功能：
  1. 上传周报 PDF：自动转成和第一篇周报一样的网页文章（文字 + 截图 + 表格 + 代码高亮），
     图片自动压缩，然后通过 GitHub API 自动提交（不需要本机装 git），Actions 自动部署上线。
  2. 外观设置：换顶部背景（内置粉色星云 / 黑洞 / 自己的图片），改站点标题、副标题、作者。
  3. 状态：查看仓库状态、一键打开网站 / 仓库 / Actions。

依赖：pymupdf、Pillow；需要 Windows 里保存好的 GitHub Token（首次使用会提示粘贴，之后加密保存）。
运行：双击「启动Pomme工具.bat」
"""

import os
import queue
import re
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from PIL import Image, ImageTk

REPO = Path(__file__).resolve().parent.parent
GITHUB_REPO = 'xunshichen-2008/Pomme-project'
SITE_URL = 'https://xunshichen-2008.github.io/Pomme-project/'
BRANCH = 'main'

BG_PRESETS = {
    '粉色星云（当前）': 'banner-pink.jpg',
    '黑洞': 'banner-blackhole.jpg',
}


# ---------------- 通用 ----------------
def site_config_from_text(text):
    cfg = dict(title='', subtitle='', author='')
    for key in cfg:
        m = re.search(r'(?m)^%s:\s*(.*)$' % key, text or '')
        if m:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in '"\'':
                val = val[1:-1]
            cfg[key] = val
    return cfg


def apply_site_config(text, title=None, subtitle=None, author=None):
    def q(v):
        if v is None:
            return None
        if v == '':
            return "''"
        return '"%s"' % v.replace('\\', '\\\\').replace('"', '\\"')

    for key, value in (('title', title), ('subtitle', subtitle), ('author', author)):
        if value is None:
            continue
        text = re.sub(r'(?m)^%s:.*$' % key, lambda m: '%s: %s' % (key, q(value)), text, count=1)
    return text


def make_banner(src, size=(1920, 480), bright=0.86):
    """把任意图片裁成 4:1 横幅并压暗（为了白字清晰），返回 JPEG bytes。"""
    import io
    from PIL import ImageEnhance
    im = Image.open(src).convert('RGB')
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    nw, nh = max(tw, int(im.width * scale + 0.5)), max(th, int(im.height * scale + 0.5))
    im = im.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    im = im.crop((left, top, left + tw, top + th))
    im = ImageEnhance.Brightness(im).enhance(bright)
    im = ImageEnhance.Color(im).enhance(1.05)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=88, optimize=True, progressive=True)
    return buf.getvalue()


def thumb(path, max_w=460, max_h=150):
    im = Image.open(path).convert('RGB')
    ratio = min(max_w / im.width, max_h / im.height)
    im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))), Image.LANCZOS)
    return ImageTk.PhotoImage(im)


def get_api():
    from token_store import load_token
    from github_api import GitHubAPI
    token = load_token()
    if not token:
        return None
    return GitHubAPI(token, GITHUB_REPO, BRANCH)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Pomme 博客小工具')
        self.geometry('1000x720')
        self.minsize(920, 660)
        self.log_queue = queue.Queue()
        self.pdfs = []
        self.bg_choice = tk.StringVar(value='粉色星云（当前）')
        self.bg_custom = None
        self.bg_image = None
        self.api = None

        self._build_ui()
        self._refresh_banner_preview()
        self.after(200, self._drain_log)
        threading.Thread(target=self._check_token, daemon=True).start()

    # ---------------- UI ----------------
    def _build_ui(self):
        try:
            ttk.Style(self).theme_use('vista')
        except Exception:
            pass

        header = ttk.Frame(self, padding=(14, 10, 14, 4))
        header.pack(fill='x')
        ttk.Label(header, text='Pomme 博客小工具', font=('Microsoft YaHei UI', 15, 'bold')).pack(side='left')
        ttk.Button(header, text='打开网站', command=lambda: webbrowser.open(SITE_URL)).pack(side='right', padx=4)
        ttk.Button(header, text='打开 GitHub 仓库',
                   command=lambda: webbrowser.open('https://github.com/' + GITHUB_REPO)).pack(side='right', padx=4)

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=12, pady=6)
        self.tab_pdf = ttk.Frame(nb, padding=10)
        self.tab_style = ttk.Frame(nb, padding=10)
        self.tab_status = ttk.Frame(nb, padding=10)
        nb.add(self.tab_pdf, text='  上传周报 PDF  ')
        nb.add(self.tab_style, text='  外观设置  ')
        nb.add(self.tab_status, text='  状态  ')
        self._build_pdf_tab()
        self._build_style_tab()
        self._build_status_tab()

        log_frame = ttk.LabelFrame(self, text='运行日志', padding=6)
        log_frame.pack(fill='both', expand=False, padx=12, pady=(0, 10))
        self.log_text = tk.Text(log_frame, height=8, wrap='word', font=('Consolas', 9))
        self.log_text.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=sb.set)

    def _build_pdf_tab(self):
        f = self.tab_pdf
        ttk.Label(f, text='① 选择 PDF 文件（可以一次选多个）').pack(anchor='w')
        row = ttk.Frame(f)
        row.pack(fill='x', pady=4)
        self.pdf_list = tk.Listbox(row, height=5)
        self.pdf_list.pack(side='left', fill='both', expand=True)
        btn = ttk.Frame(row)
        btn.pack(side='left', padx=6, fill='y')
        ttk.Button(btn, text='添加 PDF…', command=self.add_pdfs).pack(fill='x', pady=2)
        ttk.Button(btn, text='移除选中', command=self.remove_pdf).pack(fill='x', pady=2)

        form = ttk.LabelFrame(f, text='② 文章信息（可留空自动识别）', padding=8)
        form.pack(fill='x', pady=8)
        self.var_title = tk.StringVar()
        self.var_date = tk.StringVar(value=time.strftime('%Y-%m-%d'))
        self.var_tags = tk.StringVar(value='周报')
        self.var_cat = tk.StringVar(value='学习笔记')
        rows = [('标题：', self.var_title), ('日期：', self.var_date),
                ('标签（逗号分隔）：', self.var_tags), ('分类：', self.var_cat)]
        for r, (label, var) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky='e', pady=2)
            ttk.Entry(form, textvariable=var, width=62).grid(row=r, column=1, sticky='we', pady=2, padx=4)
        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(f)
        btns.pack(fill='x', pady=6)
        ttk.Button(btns, text='③ 上传并发布（自动转换、上传、等部署）',
                   command=self.start_upload).pack(side='left')
        ttk.Label(btns, text='   单篇 50 页约 1~2 分钟').pack(side='left')

    def _build_style_tab(self):
        f = self.tab_style
        ttk.Label(f, text='顶部背景（4:1 宽幅，会自动裁剪 + 压暗让白字清楚）').pack(anchor='w')
        self.bg_preview = ttk.Label(f)
        self.bg_preview.pack(pady=6)
        box = ttk.LabelFrame(f, text='选择背景', padding=8)
        box.pack(fill='x')
        for name in list(BG_PRESETS) + ['我的图片…']:
            ttk.Radiobutton(box, text=name, value=name, variable=self.bg_choice,
                            command=self._on_bg_choice).pack(anchor='w', pady=1)

        info = ttk.LabelFrame(f, text='站点信息（保存后会一起发布）', padding=8)
        info.pack(fill='x', pady=8)
        self.var_site_title = tk.StringVar()
        self.var_site_sub = tk.StringVar()
        self.var_site_author = tk.StringVar()
        for r, (label, var) in enumerate([('站点标题：', self.var_site_title),
                                          ('副标题：', self.var_site_sub),
                                          ('作者：', self.var_site_author)]):
            ttk.Label(info, text=label).grid(row=r, column=0, sticky='e', pady=2)
            ttk.Entry(info, textvariable=var, width=46).grid(row=r, column=1, sticky='we', pady=2, padx=4)
        info.columnconfigure(1, weight=1)

        ttk.Button(f, text='保存并发布', command=self.start_style_save).pack(anchor='w', pady=8)

    def _build_status_tab(self):
        f = self.tab_status
        self.status_text = tk.Text(f, height=16, wrap='word', font=('Consolas', 9))
        self.status_text.pack(fill='both', expand=True)
        bar = ttk.Frame(f)
        bar.pack(fill='x', pady=6)
        ttk.Button(bar, text='刷新状态', command=self.refresh_status).pack(side='left')
        ttk.Button(bar, text='设置 GitHub Token', command=self.ask_token).pack(side='left', padx=6)
        ttk.Button(bar, text='打开 Actions',
                   command=lambda: webbrowser.open('https://github.com/%s/actions' % GITHUB_REPO)).pack(side='left')
        ttk.Button(bar, text='本地预览',
                   command=lambda: webbrowser.open('http://localhost:4000/Pomme-project/')).pack(side='left', padx=6)

    # ---------------- logging ----------------
    def log(self, msg):
        self.log_queue.put(str(msg))

    def _drain_log(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.insert('end', msg.rstrip() + '\n')
            self.log_text.see('end')
        self.after(120, self._drain_log)

    # ---------------- token ----------------
    def _check_token(self):
        from token_store import load_token
        if not load_token():
            self.log('还没有保存 GitHub Token，点「设置 GitHub Token」粘贴一次即可（会加密保存）。')
        else:
            api = get_api()
            try:
                sha = api.latest_commit_sha()
                self.api = api
                self.log('Token 可用，远端最新提交：' + sha[:10])
                cfg_text, _ = api.get_text('_config.yml')
                cfg = site_config_from_text(cfg_text)
                self.after(0, lambda: (self.var_site_title.set(cfg['title']),
                                       self.var_site_sub.set(cfg['subtitle']),
                                       self.var_site_author.set(cfg['author'])))
                self.after(0, self.refresh_status)
            except Exception as e:
                self.log('Token 校验失败：%s' % e)

    def ask_token(self):
        token = simpledialog.askstring('设置 GitHub Token',
                                       '粘贴 GitHub Personal Access Token（只需一次，会加密保存）：',
                                       show='*')
        if not token:
            return
        from token_store import save_token
        from github_api import GitHubAPI
        save_token(token.strip())
        try:
            api = GitHubAPI(token.strip(), GITHUB_REPO, BRANCH)
            sha = api.latest_commit_sha()
            self.api = api
            self.log('Token 保存成功，最新提交：' + sha[:10])
            self._check_token()
        except Exception as e:
            messagebox.showerror('Token 无效', str(e))

    # ---------------- pdf tab ----------------
    def add_pdfs(self):
        files = filedialog.askopenfilenames(title='选择 PDF', filetypes=[('PDF 文件', '*.pdf')])
        for f in files:
            if f and f not in self.pdfs:
                self.pdfs.append(f)
                self.pdf_list.insert('end', Path(f).name)
        if files and not self.var_title.get().strip():
            try:
                from pdf2post import extract_title, open_doc
                d = open_doc(files[0])
                self.var_title.set(extract_title(d, files[0]))
                d.close()
            except Exception:
                pass
        if files:
            self.log('已添加 %d 个 PDF' % len(files))

    def remove_pdf(self):
        for idx in reversed(list(self.pdf_list.curselection())):
            self.pdf_list.delete(idx)
            self.pdfs.pop(idx)

    def start_upload(self):
        if not self.pdfs:
            messagebox.showwarning('提示', '先添加 PDF 文件')
            return
        api = self.api or get_api()
        if not api:
            messagebox.showwarning('提示', '先点「状态 → 设置 GitHub Token」')
            return
        title = self.var_title.get().strip()
        date_str = self.var_date.get().strip()
        tags = [t.strip() for t in re.split(r'[,，]', self.var_tags.get()) if t.strip()]
        cats = [t.strip() for t in re.split(r'[,，]', self.var_cat.get()) if t.strip()]
        pdfs = list(self.pdfs)

        def job():
            try:
                from pdf2post import convert_pdf
                for pdf in pdfs:
                    self.log('—— 开始转换：%s' % Path(pdf).name)
                    t = title if (len(pdfs) == 1 and title) else None
                    res = convert_pdf(pdf, str(REPO), title=t, date_str=date_str,
                                      tags=tags, categories=cats, log=self.log)
                    files = {}
                    md_bytes = Path(res['md_path']).read_bytes()
                    files['source/_posts/' + Path(res['md_path']).name] = md_bytes
                    for img in Path(res['image_dir']).glob('*'):
                        if img.is_file():
                            rel = img.relative_to(REPO).as_posix()
                            files[rel] = img.read_bytes()
                    self.log('—— 上传到 GitHub（%d 个文件）……' % len(files))
                    sha = api.commit_files(files, 'feat: 上传周报《%s》' % res['title'])
                    state = api.run_status(sha, log=self.log)
                    if state == 'success':
                        self.log('✅ 已上线：%s （首页/Archives 里能看到新文章）' % SITE_URL)
                    else:
                        self.log('⚠️ 部署状态：%s（去 Actions 看看）' % state)
                self.log('全部完成 🎉')
            except Exception as e:
                self.log('❌ 出错：%s' % e)
                messagebox.showerror('出错', str(e))

        threading.Thread(target=job, daemon=True).start()

    # ---------------- style tab ----------------
    def _on_bg_choice(self):
        if self.bg_choice.get() == '我的图片…':
            f = filedialog.askopenfilename(title='选择背景图片',
                                           filetypes=[('图片', '*.jpg *.jpeg *.png *.webp *.bmp')])
            if not f:
                self.bg_choice.set('粉色星云（当前）')
                self._refresh_banner_preview()
                return
            self.bg_custom = f
        self._refresh_banner_preview()

    def _selected_bg_source(self):
        choice = self.bg_choice.get()
        if choice == '我的图片…':
            return self.bg_custom
        name = BG_PRESETS.get(choice)
        if name:
            return REPO / 'source' / 'images' / name
        return None

    def _refresh_banner_preview(self):
        try:
            src = self._selected_bg_source()
            if src and Path(src).exists():
                self.bg_image = thumb(src)
            else:
                self.bg_image = thumb(REPO / 'source' / 'images' / 'banner.jpg')
            self.bg_preview.config(image=self.bg_image)
        except Exception as e:
            self.log('预览失败：%s' % e)

    def start_style_save(self):
        api = self.api or get_api()
        if not api:
            messagebox.showwarning('提示', '先点「状态 → 设置 GitHub Token」')
            return
        title = self.var_site_title.get().strip()
        subtitle = self.var_site_sub.get().strip()
        author = self.var_site_author.get().strip()
        bg_src = self._selected_bg_source()

        def job():
            try:
                files = {}
                if bg_src and Path(bg_src).exists():
                    data = make_banner(bg_src)
                    files['source/images/banner.jpg'] = data
                    (REPO / 'source' / 'images' / 'banner.jpg').write_bytes(data)
                    self.log('背景已生成：%s' % Path(bg_src).name)
                cfg_text, _ = api.get_text('_config.yml')
                new_cfg = apply_site_config(cfg_text or '', title=title,
                                            subtitle=subtitle, author=author)
                files['_config.yml'] = new_cfg.encode('utf-8')
                (REPO / '_config.yml').write_text(new_cfg, encoding='utf-8', newline='\n')
                self.log('站点信息：%s / %s / %s' % (title, subtitle, author))
                sha = api.commit_files(files, 'style: 更新背景与站点信息')
                state = api.run_status(sha, log=self.log)
                self.log('✅ 已发布（%s）：%s' % (state, SITE_URL))
                self.after(0, self._refresh_banner_preview)
                self.after(0, self.refresh_status)
            except Exception as e:
                self.log('❌ 出错：%s' % e)
                messagebox.showerror('出错', str(e))

        threading.Thread(target=job, daemon=True).start()

    # ---------------- status tab ----------------
    def refresh_status(self):
        lines = ['仓库：https://github.com/%s' % GITHUB_REPO,
                 '站点：%s' % SITE_URL, '本地目录：%s' % REPO, '']
        api = self.api or get_api()
        if not api:
            lines.append('GitHub Token：未设置（点下面「设置 GitHub Token」）')
        else:
            try:
                sha = api.latest_commit_sha()
                lines.append('GitHub Token：已保存（加密）')
                lines.append('远端最新提交：' + sha[:10])
                cfg_text, _ = api.get_text('_config.yml')
                cfg = site_config_from_text(cfg_text)
                lines.append('当前站点信息：标题=%s 副标题=%s 作者=%s'
                             % (cfg['title'], cfg['subtitle'], cfg['author']))
                runs = api.latest_run()
                run = runs
                if run:
                    lines.append('最近部署：%s / %s' % (run['status'], run.get('conclusion')))
            except Exception as e:
                lines.append('状态查询失败：%s' % e)
        self.status_text.delete('1.0', 'end')
        self.status_text.insert('end', '\n'.join(lines))


def main():
    os.chdir(str(REPO))
    App().mainloop()


if __name__ == '__main__':
    main()
