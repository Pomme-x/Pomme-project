# -*- coding: utf-8 -*-
"""Pomme 博客小工具（Windows 图形界面）

功能：
  1. 上传周报 PDF：自动转成网页文章（文字 + 截图 + 表格 + 代码高亮），图片压缩，
     自动放到 /周报/ 目录下，通过 GitHub API 提交（本机不需要 git），Actions 自动部署。
  2. 外观设置：换顶部背景（粉色星云 / 黑洞 / 自己的图片），改站点标题、副标题、作者。
  3. 仓库管理：浏览 / 编辑 / 上传 / 删除仓库文件，改仓库简介、重命名仓库、重新开启 Pages。
  4. 状态：Token 状态、最近部署，一键进入博客 / 仓库 / Actions。

依赖：pymupdf、Pillow；GitHub Token 用 Windows DPAPI 加密保存。
运行：双击「启动Pomme工具.bat」
"""

import json
import os
import queue
import re
import threading
import time
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from PIL import Image, ImageTk

TOOLS_DIR = Path(__file__).resolve().parent
REPO = TOOLS_DIR.parent
CONFIG_FILE = TOOLS_DIR / 'config.json'
DEFAULT_REPO = 'Pomme-x/Pomme-project'
BRANCH = 'main'

BG_PRESETS = {
    '粉色星云（当前）': 'banner-pink.jpg',
    '黑洞': 'banner-blackhole.jpg',
}
TEXT_SUFFIXES = ('.md', '.yml', '.yaml', '.txt', '.json', '.js', '.py', '.html',
                 '.css', '.styl', '.ejs', '.bat', '.toml', '.csv', '.xml')


# ---------------- 配置 ----------------
def site_url_for(full_name):
    owner, _, name = full_name.partition('/')
    if not name:
        name = full_name
    if name.lower() == (owner + '.github.io').lower():
        return 'https://%s.github.io/' % owner.lower()
    return 'https://%s.github.io/%s/' % (owner.lower(), name)


def root_for(full_name):
    owner, _, name = full_name.partition('/')
    if not name:
        name = full_name
    if name.lower() == (owner + '.github.io').lower():
        return '/'
    return '/%s/' % name


def load_config():
    cfg = {'repo': DEFAULT_REPO}
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding='utf-8')))
    except Exception:
        pass
    cfg.setdefault('repo', DEFAULT_REPO)
    cfg['site_url'] = site_url_for(cfg['repo'])
    return cfg


def save_config(cfg):
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


# ---------------- 小工具函数 ----------------
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


def get_api(cfg=None):
    from token_store import load_token
    from github_api import GitHubAPI
    token = load_token()
    if not token:
        return None
    cfg = cfg or load_config()
    return GitHubAPI(token, cfg['repo'], BRANCH)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Pomme 博客小工具')
        self.geometry('1040x760')
        self.minsize(960, 700)
        self.cfg = load_config()
        self.log_queue = queue.Queue()
        self.ui_queue = queue.Queue()
        self.pdfs = []
        self.bg_choice = tk.StringVar(value='粉色星云（当前）')
        self.bg_custom = None
        self.bg_image = None
        self.api = None
        self.repo_path = ''
        self.dir_entries = []
        self.status_labels = {}

        self._build_ui()
        self._refresh_banner_preview()
        self.after(200, self._drain_log)
        threading.Thread(target=self._init_async, daemon=True).start()

    # ---------------- UI ----------------
    def _build_ui(self):
        try:
            ttk.Style(self).theme_use('vista')
        except Exception:
            pass

        header = ttk.Frame(self, padding=(14, 10, 14, 4))
        header.pack(fill='x')
        ttk.Label(header, text='Pomme 博客小工具', font=('Microsoft YaHei UI', 15, 'bold')).pack(side='left')
        ttk.Button(header, text=' 进入博客 ', command=self.open_blog).pack(side='right', padx=6)
        ttk.Button(header, text='GitHub 仓库', command=self.open_repo_page).pack(side='right', padx=4)

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=12, pady=6)
        self.tab_pdf = ttk.Frame(nb, padding=10)
        self.tab_style = ttk.Frame(nb, padding=10)
        self.tab_repo = ttk.Frame(nb, padding=10)
        self.tab_status = ttk.Frame(nb, padding=10)
        nb.add(self.tab_pdf, text='  上传周报 PDF  ')
        nb.add(self.tab_style, text='  外观设置  ')
        nb.add(self.tab_repo, text='  仓库管理  ')
        nb.add(self.tab_status, text='  状态  ')
        self._build_pdf_tab()
        self._build_style_tab()
        self._build_repo_tab()
        self._build_status_tab()

        log_frame = ttk.LabelFrame(self, text='运行日志', padding=6)
        log_frame.pack(fill='both', expand=False, padx=12, pady=(0, 10))
        self.log_text = tk.Text(log_frame, height=7, wrap='word', font=('Consolas', 9))
        self.log_text.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=sb.set)
        self.log('仓库：%s   站点：%s' % (self.cfg['repo'], self.cfg['site_url']))

    def _build_pdf_tab(self):
        f = self.tab_pdf
        ttk.Label(f, text='① 选择 PDF 文件（可一次选多个；文章会自动放到 /周报/ 目录下）').pack(anchor='w')
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
        self.var_cat = tk.StringVar(value='周报')
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

    def _build_repo_tab(self):
        f = self.tab_repo
        info = ttk.Frame(f)
        info.pack(fill='x')
        for i, (key, text) in enumerate([('repo', '仓库：-'), ('site', '站点：-'),
                                         ('pages', 'Pages：-'), ('run', '最近部署：-')]):
            lab = ttk.Label(info, text=text)
            lab.grid(row=i // 2, column=i % 2, sticky='w', padx=(0, 24), pady=2)
            self.status_labels[key] = lab

        bar = ttk.Frame(f)
        bar.pack(fill='x', pady=(8, 2))
        ttk.Button(bar, text='上一级', command=self.repo_up).pack(side='left')
        ttk.Button(bar, text='刷新', command=self.repo_refresh).pack(side='left', padx=4)
        self.path_var = tk.StringVar(value='/')
        ttk.Label(bar, text='路径：').pack(side='left', padx=(10, 0))
        ttk.Entry(bar, textvariable=self.path_var, width=58, state='readonly').pack(side='left')
        self.repo_list = tk.Listbox(f, height=10)
        self.repo_list.pack(fill='both', expand=True, pady=4)
        self.repo_list.bind('<Double-Button-1>', lambda e: self.repo_open())

        btns = ttk.Frame(f)
        btns.pack(fill='x', pady=4)
        ttk.Button(btns, text='打开 / 编辑', command=self.repo_open).pack(side='left')
        ttk.Button(btns, text='上传文件…', command=self.repo_upload).pack(side='left', padx=4)
        ttk.Button(btns, text='新建文件…', command=self.repo_new_file).pack(side='left')
        ttk.Button(btns, text='删除', command=self.repo_delete).pack(side='left', padx=4)

        admin = ttk.LabelFrame(f, text='仓库设置（需要管理员权限）', padding=8)
        admin.pack(fill='x', pady=(6, 0))
        ttk.Label(admin, text='仓库简介：').grid(row=0, column=0, sticky='e')
        self.var_desc = tk.StringVar()
        ttk.Entry(admin, textvariable=self.var_desc, width=56).grid(row=0, column=1, sticky='we', padx=4)
        ttk.Button(admin, text='保存简介', command=self.save_description).grid(row=0, column=2, padx=2)
        ttk.Label(admin, text='重命名仓库：').grid(row=1, column=0, sticky='e', pady=4)
        self.var_rename = tk.StringVar()
        ttk.Entry(admin, textvariable=self.var_rename, width=56).grid(row=1, column=1, sticky='we', padx=4)
        ttk.Button(admin, text='应用', command=self.rename_repo).grid(row=1, column=2, padx=2)
        ttk.Button(admin, text='重新开启 / 修复 GitHub Pages', command=self.fix_pages).grid(
            row=2, column=0, columnspan=3, sticky='w', pady=4)
        admin.columnconfigure(1, weight=1)

    def _build_status_tab(self):
        f = self.tab_status
        self.status_text = tk.Text(f, height=13, wrap='word', font=('Consolas', 9))
        self.status_text.pack(fill='both', expand=True)
        bar = ttk.Frame(f)
        bar.pack(fill='x', pady=6)
        ttk.Button(bar, text='刷新状态', command=self.refresh_status).pack(side='left')
        ttk.Button(bar, text='设置 GitHub Token', command=self.ask_token).pack(side='left', padx=6)
        ttk.Button(bar, text='打开 Actions',
                   command=lambda: webbrowser.open(self.repo_url() + '/actions')).pack(side='left')

    # ---------------- 通用 ----------------
    def repo_url(self):
        return 'https://github.com/' + self.cfg['repo']

    def open_blog(self):
        webbrowser.open(self.cfg['site_url'])

    def open_repo_page(self):
        webbrowser.open(self.repo_url())

    def log(self, msg):
        self.log_queue.put(str(msg))

    def ui(self, fn, *args):
        """从后台线程安全地回到主线程执行界面操作。"""
        self.ui_queue.put((fn, args))

    def _drain_log(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.insert('end', msg.rstrip() + '\n')
            self.log_text.see('end')
        while True:
            try:
                fn, args = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception as e:
                self.log('界面更新失败：%s' % e)
        self.after(120, self._drain_log)

    # ---------------- 初始化 ----------------
    def _init_async(self):
        from token_store import load_token
        if not load_token():
            self.log('还没有保存 GitHub Token，去「状态 → 设置 GitHub Token」粘贴一次即可。')
            return
        api = get_api(self.cfg)
        try:
            api.get_repo()
            self.api = api
            self.log('Token 可用，仓库：' + self.cfg['repo'])
            self.ui(self._load_site_info)
            self.ui(self.refresh_status)
            self.ui(self.repo_refresh)
        except Exception as e:
            self.log('Token 校验失败：%s' % e)

    def _load_site_info(self):
        try:
            text, _ = self.api.get_text('_config.yml')
            cfg = site_config_from_text(text)
            self.var_site_title.set(cfg['title'])
            self.var_site_sub.set(cfg['subtitle'])
            self.var_site_author.set(cfg['author'])
        except Exception as e:
            self.log('读取站点信息失败：%s' % e)

    # ---------------- token ----------------
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
            api = GitHubAPI(token.strip(), self.cfg['repo'], BRANCH)
            api.get_repo()
            self.api = api
            self.log('Token 保存成功')
            self._init_async()
        except Exception as e:
            messagebox.showerror('Token 无效', str(e))

    # ---------------- PDF ----------------
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
        api = self.api or get_api(self.cfg)
        if not api:
            messagebox.showwarning('提示', '先设置 GitHub Token（状态页）')
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
                    files = {'source/_posts/' + Path(res['md_path']).name:
                             Path(res['md_path']).read_bytes()}
                    for img in Path(res['image_dir']).glob('*'):
                        if img.is_file():
                            files[img.relative_to(REPO).as_posix()] = img.read_bytes()
                    self.log('—— 上传到 GitHub（%d 个文件）……' % len(files))
                    sha = api.commit_files(files, 'feat: 上传周报《%s》' % res['title'])
                    state = api.run_status(sha, log=self.log)
                    if state == 'success':
                        self.log('✅ 已上线：%s周报/' % self.cfg['site_url'])
                    else:
                        self.log('⚠️ 部署状态：%s' % state)
                self.ui(self.repo_refresh)
                self.log('全部完成 🎉')
            except Exception as e:
                self.log('❌ 出错：%s' % e)
                self.ui(messagebox.showerror, '出错', str(e))

        threading.Thread(target=job, daemon=True).start()

    # ---------------- 外观 ----------------
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
        return (REPO / 'source' / 'images' / name) if name else None

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
        api = self.api or get_api(self.cfg)
        if not api:
            messagebox.showwarning('提示', '先设置 GitHub Token（状态页）')
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
                sha = api.commit_files(files, 'style: 更新背景与站点信息')
                state = api.run_status(sha, log=self.log)
                self.log('✅ 已发布（%s）：%s' % (state, self.cfg['site_url']))
                self.ui(self._refresh_banner_preview)
                self.ui(self.refresh_status)
            except Exception as e:
                self.log('❌ 出错：%s' % e)
                self.ui(messagebox.showerror, '出错', str(e))

        threading.Thread(target=job, daemon=True).start()

    # ---------------- 仓库管理 ----------------
    def repo_refresh(self):
        api = self.api or get_api(self.cfg)
        if not api:
            return

        def job():
            try:
                entries = api.list_dir(self.repo_path)
                entries = sorted(entries, key=lambda e: (e['type'] != 'dir', e['name'].lower()))
                repo = api.get_repo()
                pages = api.get_pages()
                run = api.latest_run()
                self.ui(self._apply_repo_data, entries, repo, pages, run)
            except Exception as e:
                self.log('读取仓库失败：%s' % e)

        threading.Thread(target=job, daemon=True).start()

    def _apply_repo_data(self, entries, repo, pages, run):
        self.dir_entries = entries
        self._fill_repo_list(entries)
        if not self.var_desc.get():
            self.var_desc.set(repo.get('description') or '')
        self.status_labels['repo'].config(text='仓库：' + repo['full_name'])
        self.status_labels['site'].config(text='站点：' + self.cfg['site_url'])
        self.status_labels['pages'].config(
            text='Pages：' + (pages.get('html_url') if pages else '未开启'))
        if run:
            self.status_labels['run'].config(
                text='最近部署：%s / %s' % (run['status'], run.get('conclusion')))

    def _fill_repo_list(self, entries):
        self.repo_list.delete(0, 'end')
        for e in entries:
            mark = '📁 ' if e['type'] == 'dir' else '📄 '
            self.repo_list.insert('end', mark + e['name'])
        self.path_var.set('/' + self.repo_path)

    def repo_up(self):
        if not self.repo_path:
            return
        self.repo_path = '/'.join(self.repo_path.split('/')[:-1])
        self.repo_refresh()

    def _selected_entry(self):
        sel = self.repo_list.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx >= len(self.dir_entries):
            return None
        return self.dir_entries[idx]

    def repo_open(self):
        entry = self._selected_entry()
        if not entry:
            return
        if entry['type'] == 'dir':
            self.repo_path = entry['path']
            self.repo_refresh()
            return
        api = self.api or get_api(self.cfg)
        try:
            data, _ = api.get_file(entry['path'])
        except Exception as e:
            messagebox.showerror('打开失败', str(e))
            return
        if data is None:
            messagebox.showwarning('提示', '读取失败')
            return
        if not entry['name'].lower().endswith(TEXT_SUFFIXES):
            if not messagebox.askyesno('二进制文件',
                                       '%s 可能不是文本文件，仍要以文本方式打开吗？' % entry['name']):
                return
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            messagebox.showinfo('提示', '这个文件不是 UTF-8 文本，无法编辑')
            return
        self._open_editor(entry['path'], text)

    def _open_editor(self, path, text):
        win = tk.Toplevel(self)
        win.title('编辑：' + path)
        win.geometry('900x640')
        frame = ttk.Frame(win, padding=8)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=path, font=('Consolas', 10, 'bold')).pack(anchor='w')
        editor = tk.Text(frame, wrap='none', undo=True, font=('Consolas', 10))
        editor.pack(fill='both', expand=True, pady=6)
        editor.insert('1.0', text)
        bar = ttk.Frame(frame)
        bar.pack(fill='x')

        def save():
            api = self.api or get_api(self.cfg)
            new_text = editor.get('1.0', 'end-1c')
            try:
                sha = api.commit_files({path: new_text.encode('utf-8')}, 'edit: 更新 %s' % path)
                self.log('已提交：%s（%s）' % (path, sha[:8]))
                api.run_status(sha, log=lambda m: None)
                win.destroy()
                self.repo_refresh()
            except Exception as e:
                messagebox.showerror('保存失败', str(e))

        ttk.Button(bar, text='保存并发布', command=save).pack(side='left')
        ttk.Button(bar, text='取消', command=win.destroy).pack(side='left', padx=6)

    def repo_upload(self):
        files = filedialog.askopenfilenames(title='上传文件到当前目录')
        if not files:
            return
        api = self.api or get_api(self.cfg)

        def job():
            try:
                uploads = {}
                for f in files:
                    name = Path(f).name
                    target = (self.repo_path + '/' + name).strip('/')
                    uploads[target] = Path(f).read_bytes()
                    self.log('上传：' + target)
                sha = api.commit_files(uploads, 'upload: %s' % ', '.join(Path(f).name for f in files))
                api.run_status(sha, log=self.log)
                self.ui(self.repo_refresh)
            except Exception as e:
                self.log('上传失败：%s' % e)

        threading.Thread(target=job, daemon=True).start()

    def repo_new_file(self):
        name = simpledialog.askstring('新建文件', '文件名（可写路径，例如 source/_posts/2026-10-26-note.md）：')
        if not name:
            return
        target = name.strip().strip('/')
        if self.repo_path and '/' not in target:
            target = self.repo_path + '/' + target
        self._open_editor(target, '')

    def repo_delete(self):
        entry = self._selected_entry()
        if not entry:
            return
        if entry['type'] == 'dir':
            messagebox.showinfo('提示', '目录不能直接删除，请进入后再删文件')
            return
        if not messagebox.askyesno('确认删除', '确定删除 %s 吗？' % entry['path']):
            return
        api = self.api or get_api(self.cfg)

        def job():
            try:
                sha = api.commit_files({}, 'delete: 删除 %s' % entry['path'], deletions=[entry['path']])
                api.run_status(sha, log=self.log)
                self.ui(self.repo_refresh)
            except Exception as e:
                self.log('删除失败：%s' % e)

        threading.Thread(target=job, daemon=True).start()

    def save_description(self):
        api = self.api or get_api(self.cfg)
        try:
            api.set_description(self.var_desc.get())
            self.log('仓库简介已更新')
        except Exception as e:
            messagebox.showerror('失败', str(e))

    def rename_repo(self):
        new_name = self.var_rename.get().strip()
        if not new_name:
            return
        if not messagebox.askyesno('确认重命名',
                                   '把仓库重命名为 %s 吗？\n网站地址也会变，工具会自动更新配置。' % new_name):
            return
        api = self.api or get_api(self.cfg)
        try:
            full = api.rename_repo(new_name)
            self.cfg['repo'] = full
            self.cfg['site_url'] = site_url_for(full)
            save_config(self.cfg)
            self.log('仓库已重命名：' + full)
            text, _ = api.get_text('_config.yml')
            root = root_for(full)
            text = re.sub(r'(?m)^url:.*$', 'url: %s' % self.cfg['site_url'].rstrip('/'), text)
            text = re.sub(r'(?m)^root:.*$', 'root: %s' % root, text)
            (REPO / '_config.yml').write_text(text, encoding='utf-8', newline='\n')
            sha = api.commit_files({'_config.yml': text.encode('utf-8')},
                                   'chore: 仓库改名后同步站点 url/root')
            state = api.run_status(sha, log=self.log)
            self.log('新站点：%s（部署 %s）' % (self.cfg['site_url'], state))
            self.after(0, self.repo_refresh)
            self.after(0, self.refresh_status)
        except Exception as e:
            messagebox.showerror('重命名失败', str(e))

    def fix_pages(self):
        api = self.api or get_api(self.cfg)
        try:
            pages = api.get_pages()
            if pages:
                self.log('Pages 已开启：' + pages.get('html_url', ''))
                messagebox.showinfo('Pages', 'Pages 已开启：\n' + pages.get('html_url', ''))
                return
            api.create_pages()
            self.log('Pages 已重新开启')
            self.repo_refresh()
        except Exception as e:
            messagebox.showerror('失败', str(e))

    # ---------------- 状态 ----------------
    def refresh_status(self):
        lines = ['仓库：https://github.com/%s' % self.cfg['repo'],
                 '站点：%s' % self.cfg['site_url'],
                 '本地目录：%s' % REPO, '']
        api = self.api or get_api(self.cfg)
        if not api:
            lines.append('GitHub Token：未设置')
        else:
            try:
                repo = api.get_repo()
                lines.append('GitHub Token：已保存（DPAPI 加密）')
                lines.append('仓库名：%s' % repo['full_name'])
                lines.append('可见性：%s' % ('私有' if repo.get('private') else '公开'))
                text, _ = api.get_text('_config.yml')
                cfg = site_config_from_text(text)
                lines.append('站点信息：%s / %s / %s' % (cfg['title'], cfg['subtitle'], cfg['author']))
                pages = api.get_pages()
                lines.append('Pages：%s' % (pages.get('html_url') if pages else '未开启'))
                run = api.latest_run()
                if run:
                    lines.append('最近部署：%s / %s' % (run['status'], run.get('conclusion')))
            except Exception as e:
                lines.append('查询失败：%s' % e)
        self.status_text.delete('1.0', 'end')
        self.status_text.insert('end', '\n'.join(lines))


def main():
    os.chdir(str(REPO))
    App().mainloop()


if __name__ == '__main__':
    main()
