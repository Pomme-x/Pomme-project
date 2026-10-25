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
import sys
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


MENU_LINE_RE = re.compile(r'^menu:\s*$')
MENU_ITEM_RE = re.compile(r'^\s+("(?:[^"\\]|\\.)*"|\'[^\']*\'|[^:]+?):\s*(.*?)\s*$')


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in '"\'':
        body = s[1:-1]
        return body.replace('\\"', '"').replace('\\\\', '\\')
    return s


def menu_yaml_key(s):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"')
    return '"%s"' % s


def menu_yaml_val(s):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"')
    return '"%s"' % s


def parse_menu(text):
    """从 _config.landscape.yml 文本里解析 menu 列表，返回 (items, start, end)。"""
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if MENU_LINE_RE.match(line):
            start = idx
            break
    if start is None:
        return [], None, None
    items = []
    idx = start + 1
    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue
        if not line[0].isspace():
            break
        m = MENU_ITEM_RE.match(line)
        if m:
            items.append({'label': _unquote(m.group(1)), 'url': _unquote(m.group(2))})
        idx += 1
    return items, start, idx


def replace_menu_block(text, items):
    lines = text.splitlines()
    old_items, start, end = parse_menu(text)
    if start is None:
        block = ['menu:']
        block += ['  %s: %s' % (menu_yaml_key(it['label']), menu_yaml_val(it['url'])) for it in items]
        return text.rstrip('\n') + '\n\n' + '\n'.join(block) + '\n'
    block = ['menu:']
    block += ['  %s: %s' % (menu_yaml_key(it['label']), menu_yaml_val(it['url'])) for it in items]
    new_lines = lines[:start] + block + lines[end:]
    return '\n'.join(new_lines) + ('\n' if text.endswith('\n') else '')


def page_path_for(url):
    """把 /notes 这样的链接转成 source/notes/index.md；根路径/外部链接返回 None。"""
    u = (url or '').strip()
    if not u or not u.startswith('/'):
        return None
    slug = u.strip('/')
    if not slug:
        return None
    return 'source/%s/index.md' % slug


def parse_front_matter(text):
    """解析文章 front-matter，返回 (data, body)。data: title/date/tags/categories/permalink"""
    data = {'title': '', 'date': '', 'tags': [], 'categories': [], 'permalink': ''}
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?', text, re.S)
    if not m:
        return data, text
    fm, body = m.group(1), text[m.end():]
    key = None
    for line in fm.splitlines():
        lm = re.match(r'^\s*-\s+(.*)$', line)
        if lm and key in ('tags', 'categories'):
            data[key].append(_unquote(lm.group(1)))
            continue
        km = re.match(r'^([A-Za-z_]+):\s*(.*)$', line)
        if not km:
            continue
        k, v = km.group(1), km.group(2).strip()
        if k in ('tags', 'categories'):
            key = k
            data[k] = []
            if v.startswith('[') and v.endswith(']'):
                inner = v[1:-1].strip()
                if inner:
                    data[k] = [_unquote(x) for x in inner.split(',')]
                key = None
        elif k in ('title', 'date', 'permalink'):
            data[k] = _unquote(v)
            key = None
    return data, body


def build_front_matter(data, body):
    def q(v):
        return '"%s"' % str(v).replace('\\', '\\\\').replace('"', '\\"')

    lines = ['---', 'title: %s' % q(data.get('title', '')),
             'date: %s' % str(data.get('date') or time.strftime('%Y-%m-%d %H:%M:%S')).strip()]
    if data.get('tags'):
        lines.append('tags:')
        lines += ['  - %s' % q(t) for t in data['tags']]
    if data.get('categories'):
        lines.append('categories:')
        lines += ['  - %s' % q(c) for c in data['categories']]
    if data.get('permalink'):
        lines.append('permalink: %s' % q(data['permalink']))
    lines.append('---')
    return '\n'.join(lines) + '\n\n' + body.lstrip('\n')


def article_slug(path, permalink):
    if permalink:
        tail = permalink.rstrip('/').split('/')[-1]
        if tail:
            return tail
    stem = Path(path).stem
    return re.sub(r'^\d{4}-\d{2}-\d{2}-', '', stem) or 'post'


def section_page_markdown(section):
    return ('---\ntitle: %s\ndate: %s\ntype: page\n---\n\n'
            '<div class="section-list" data-section="%s"></div>\n'
            % (menu_yaml_val(section), time.strftime('%Y-%m-%d %H:%M:%S'), section))


def page_markdown(label, now=None):
    now = now or time.strftime('%Y-%m-%d %H:%M:%S')
    return ('---\ntitle: %s\ndate: %s\ntype: page\n---\n\n'
            '这里是「%s」页面。可以在「仓库管理」里编辑这篇文件写内容，也可以上传图片后引用。\n'
            % (menu_yaml_val(label), now, label))


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
        self.minsize(980, 740)
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
    BASE_BG = '#f4f5fa'
    CARD_BG = '#ffffff'
    BORDER = '#e3e6f0'
    TEXT = '#1f2430'
    MUTED = '#6b7280'
    ACCENT = '#d6336c'
    ACCENT_DARK = '#b02758'
    HEADER_BG = '#151a24'
    FONT = 'Microsoft YaHei UI'

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        f = self.FONT
        style.configure('.', font=(f, 10), background=self.BASE_BG, foreground=self.TEXT)
        style.configure('TFrame', background=self.BASE_BG)
        style.configure('TLabel', background=self.BASE_BG, foreground=self.TEXT)
        style.configure('Muted.TLabel', foreground=self.MUTED)
        style.configure('Header.TFrame', background=self.HEADER_BG)
        style.configure('HeaderTitle.TLabel', background=self.HEADER_BG,
                        foreground='#ffffff', font=(f, 18, 'bold'))
        style.configure('HeaderSub.TLabel', background=self.HEADER_BG,
                        foreground='#9aa3b5', font=(f, 9))
        style.configure('Card.TFrame', background=self.CARD_BG)
        style.configure('Accent.TButton', background=self.ACCENT, foreground='#ffffff',
                        borderwidth=0, focusthickness=0, padding=(16, 9),
                        font=(f, 10, 'bold'))
        style.map('Accent.TButton',
                  background=[('active', self.ACCENT_DARK), ('pressed', self.ACCENT_DARK)])
        style.configure('Ghost.TButton', background=self.CARD_BG, foreground=self.TEXT,
                        borderwidth=0, focusthickness=0, padding=(12, 7), font=(f, 10))
        style.map('Ghost.TButton', background=[('active', '#eef1f8'), ('pressed', '#e4e8f2')])
        style.configure('HeaderGhost.TButton', background=self.HEADER_BG, foreground='#dfe4ee',
                        borderwidth=0, padding=(12, 8), font=(f, 9))
        style.map('HeaderGhost.TButton', background=[('active', '#262d3b')])
        style.configure('TNotebook', background=self.BASE_BG, borderwidth=0,
                        tabmargins=(0, 0, 0, 0))
        style.configure('TNotebook.Tab', background='#e9ecf5', foreground=self.MUTED,
                        padding=(20, 9), borderwidth=0, font=(f, 10))
        style.map('TNotebook.Tab',
                  background=[('selected', self.CARD_BG)],
                  foreground=[('selected', self.ACCENT)])
        style.configure('TEntry', fieldbackground=self.CARD_BG, bordercolor=self.BORDER,
                        lightcolor=self.BORDER, darkcolor=self.BORDER, padding=6)
        style.configure('Vertical.TScrollbar', background='#d9dde8',
                        troughcolor=self.BASE_BG, borderwidth=0, arrowsize=12)

    def _card(self, parent, title=None, subtitle=None, pady=(0, 10), expand=False):
        outer = tk.Frame(parent, bg=self.CARD_BG, highlightbackground=self.BORDER,
                         highlightthickness=1, bd=0)
        outer.pack(fill='both' if expand else 'x', expand=expand, pady=pady)
        inner = tk.Frame(outer, bg=self.CARD_BG)
        inner.pack(fill='both', expand=True, padx=14, pady=12)
        if title:
            tk.Label(inner, text=title, bg=self.CARD_BG, fg=self.TEXT,
                     font=(self.FONT, 11, 'bold')).pack(anchor='w')
        if subtitle:
            tk.Label(inner, text=subtitle, bg=self.CARD_BG, fg=self.MUTED,
                     font=(self.FONT, 9)).pack(anchor='w', pady=(3, 0))
        body = tk.Frame(inner, bg=self.CARD_BG)
        body.pack(fill='both', expand=True, pady=(8, 0) if title else (0, 0))
        return body

    def _styled_listbox(self, parent, height=6):
        frame = tk.Frame(parent, bg=self.CARD_BG, highlightbackground=self.BORDER,
                         highlightthickness=1, bd=0)
        lb = tk.Listbox(frame, height=height, bd=0, highlightthickness=0,
                        bg='#fbfcff', fg=self.TEXT, selectbackground='#f7dbe7',
                        selectforeground=self.TEXT, activestyle='none',
                        font=(self.FONT, 10))
        lb.pack(side='left', fill='both', expand=True, padx=2, pady=2)
        sb = ttk.Scrollbar(frame, command=lb.yview)
        sb.pack(side='right', fill='y')
        lb.config(yscrollcommand=sb.set)
        return frame, lb

    def _init_icon(self):
        try:
            icon = Image.open(REPO / 'source' / 'favicon.png')
            self._icon_img = ImageTk.PhotoImage(icon)
            self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _center_window(self):
        w, h = 1080, 880
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2 - 20)
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))

    def _build_ui(self):
        self._setup_style()
        self._init_icon()
        self._center_window()

        header = ttk.Frame(self, style='Header.TFrame', padding=(22, 15))
        header.pack(fill='x')
        left = ttk.Frame(header, style='Header.TFrame')
        left.pack(side='left')
        ttk.Label(left, text='Pomme 博客小工具',
                  style='HeaderTitle.TLabel').pack(anchor='w')
        ttk.Label(left, text='%s   ·   %s' % (self.cfg['repo'], self.cfg['site_url']),
                  style='HeaderSub.TLabel').pack(anchor='w', pady=(4, 0))
        right = ttk.Frame(header, style='Header.TFrame')
        right.pack(side='right')
        ttk.Button(right, text='进入博客', style='Accent.TButton',
                   command=self.open_blog).pack(side='right', padx=(10, 0))
        ttk.Button(right, text='GitHub 仓库', style='HeaderGhost.TButton',
                   command=self.open_repo_page).pack(side='right')

        tk.Frame(self, bg=self.ACCENT, height=3).pack(fill='x')

        # 底部状态栏先占位，避免被内容挤掉
        self.status_bar = tk.Label(self, text='  就绪', anchor='w', bg='#e9ecf5',
                                   fg=self.MUTED, font=(self.FONT, 9), padx=14, pady=6)
        self.status_bar.pack(fill='x', side='bottom')

        body = tk.Frame(self, bg=self.BASE_BG)
        body.pack(fill='both', expand=True, padx=18, pady=(12, 10))

        # 日志面板固定在下方
        log_card = tk.Frame(body, bg='#161a23')
        log_card.pack(fill='x', side='bottom', pady=(12, 0))
        log_head = tk.Frame(log_card, bg='#161a23')
        log_head.pack(fill='x', padx=14, pady=(9, 0))
        tk.Label(log_head, text='运行日志', bg='#161a23', fg='#8b93a7',
                 font=(self.FONT, 9, 'bold')).pack(side='left')
        self.log_text = tk.Text(log_card, height=4, bd=0, highlightthickness=0, wrap='word',
                                bg='#161a23', fg='#d7dae0', insertbackground='#d7dae0',
                                font=('Consolas', 9), padx=14, pady=6)
        self.log_text.pack(fill='x', padx=2, pady=(4, 8))

        self.nb = nb = ttk.Notebook(body)
        nb.pack(fill='both', expand=True)
        self.tab_pdf = tk.Frame(nb, bg=self.BASE_BG)
        self.tab_style = tk.Frame(nb, bg=self.BASE_BG)
        self.tab_menu = tk.Frame(nb, bg=self.BASE_BG)
        self.tab_articles = tk.Frame(nb, bg=self.BASE_BG)
        self.tab_repo = tk.Frame(nb, bg=self.BASE_BG)
        self.tab_status = tk.Frame(nb, bg=self.BASE_BG)
        nb.add(self.tab_pdf, text='上传周报 PDF')
        nb.add(self.tab_style, text='外观设置')
        nb.add(self.tab_menu, text='导航菜单')
        nb.add(self.tab_articles, text='文章管理')
        nb.add(self.tab_repo, text='仓库管理')
        nb.add(self.tab_status, text='状态')
        self._build_pdf_tab()
        self._build_style_tab()
        self._build_menu_tab()
        self._build_articles_tab()
        self._build_repo_tab()
        self._build_status_tab()
        self.nb.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        self.log('仓库：%s   站点：%s' % (self.cfg['repo'], self.cfg['site_url']))

    def _build_pdf_tab(self):
        f = self.tab_pdf
        self.var_title = tk.StringVar()
        self.var_date = tk.StringVar(value=time.strftime('%Y-%m-%d'))
        self.var_tags = tk.StringVar(value='周报')
        self.var_cat = tk.StringVar(value='周报')

        c1 = self._card(f, '① 选择 PDF 文件',
                        '可一次选多个；转换后自动放到 /周报/ 目录，并出现在周报列表里')
        row = tk.Frame(c1, bg=self.CARD_BG)
        row.pack(fill='x')
        holder, self.pdf_list = self._styled_listbox(row, height=5)
        holder.pack(side='left', fill='both', expand=True)
        side = tk.Frame(row, bg=self.CARD_BG)
        side.pack(side='left', padx=(12, 0), fill='y')
        ttk.Button(side, text='添加 PDF…', style='Accent.TButton',
                   command=self.add_pdfs).pack(fill='x')
        ttk.Button(side, text='移除选中', style='Ghost.TButton',
                   command=self.remove_pdf).pack(fill='x', pady=(8, 0))

        c2 = self._card(f, '② 文章信息', '标题留空会自动识别；日期决定文章时间')
        grid = tk.Frame(c2, bg=self.CARD_BG)
        grid.pack(fill='x')
        for r, (label, var) in enumerate([('标题', self.var_title), ('日期', self.var_date),
                                          ('标签', self.var_tags), ('分类', self.var_cat)]):
            tk.Label(grid, text=label, bg=self.CARD_BG, fg=self.MUTED,
                     font=(self.FONT, 10)).grid(row=r, column=0, sticky='e', padx=(0, 12), pady=5)
            ttk.Entry(grid, textvariable=var).grid(row=r, column=1, sticky='we', pady=5)
        grid.columnconfigure(1, weight=1)

        bottom = tk.Frame(f, bg=self.BASE_BG)
        bottom.pack(fill='x', pady=(6, 0))
        ttk.Button(bottom, text='③ 上传并发布', style='Accent.TButton',
                   command=self.start_upload).pack(side='left')
        tk.Label(bottom, text='自动转换 → 上传 GitHub → 等待部署，单篇约 1~2 分钟',
                 bg=self.BASE_BG, fg=self.MUTED,
                 font=(self.FONT, 9)).pack(side='left', padx=14)

    def _build_style_tab(self):
        f = self.tab_style
        c1 = self._card(f, '顶部背景', '4:1 宽幅，自动裁剪并压暗，保证白色标题清晰')
        self.bg_preview = tk.Label(c1, bg='#0d0f14', bd=0)
        self.bg_preview.pack(pady=(0, 12))
        choices = tk.Frame(c1, bg=self.CARD_BG)
        choices.pack(anchor='w')
        for name in list(BG_PRESETS) + ['我的图片…']:
            tk.Radiobutton(choices, text=name, variable=self.bg_choice, value=name,
                           command=self._on_bg_choice, bg=self.CARD_BG, fg=self.TEXT,
                           activebackground=self.CARD_BG, selectcolor='#ffffff',
                           font=(self.FONT, 10)).pack(side='left', padx=(0, 18))

        c2 = self._card(f, '站点信息', '保存后会一起发布到网站')
        self.var_site_title = tk.StringVar()
        self.var_site_sub = tk.StringVar()
        self.var_site_author = tk.StringVar()
        grid = tk.Frame(c2, bg=self.CARD_BG)
        grid.pack(fill='x')
        for r, (label, var) in enumerate([('站点标题', self.var_site_title),
                                          ('副标题', self.var_site_sub),
                                          ('作者', self.var_site_author)]):
            tk.Label(grid, text=label, bg=self.CARD_BG, fg=self.MUTED,
                     font=(self.FONT, 10)).grid(row=r, column=0, sticky='e', padx=(0, 12), pady=5)
            ttk.Entry(grid, textvariable=var).grid(row=r, column=1, sticky='we', pady=5)
        grid.columnconfigure(1, weight=1)

        bottom = tk.Frame(f, bg=self.BASE_BG)
        bottom.pack(fill='x', pady=(6, 0))
        ttk.Button(bottom, text='保存并发布', style='Accent.TButton',
                   command=self.start_style_save).pack(side='left')

    def _build_menu_tab(self):
        f = self.tab_menu
        self.menu_items = []
        self.pending_pages = {}
        c = self._card(f, '顶部导航菜单',
                       '这里改的就是网站最上面那排（Home / Archives / 周报 / 关于）；'
                       '也可以添加自己的页面并顺带创建', expand=True)
        holder, self.menu_list = self._styled_listbox(c, height=7)
        holder.pack(fill='both', expand=True)
        btns = tk.Frame(c, bg=self.CARD_BG)
        btns.pack(fill='x', pady=(10, 0))
        ttk.Button(btns, text='添加菜单', style='Accent.TButton',
                   command=self.menu_add).pack(side='left')
        ttk.Button(btns, text='编辑', style='Ghost.TButton',
                   command=self.menu_edit).pack(side='left', padx=8)
        ttk.Button(btns, text='删除', style='Ghost.TButton',
                   command=self.menu_delete).pack(side='left')
        ttk.Button(btns, text='↑ 上移', style='Ghost.TButton',
                   command=lambda: self.menu_move(-1)).pack(side='left', padx=8)
        ttk.Button(btns, text='↓ 下移', style='Ghost.TButton',
                   command=lambda: self.menu_move(1)).pack(side='left')
        save = tk.Frame(f, bg=self.BASE_BG)
        save.pack(fill='x', pady=(8, 0))
        ttk.Button(save, text='保存并发布', style='Accent.TButton',
                   command=self.menu_save).pack(side='left')
        tk.Label(save, text='保存后自动提交，约 1 分钟网站顶部导航更新',
                 bg=self.BASE_BG, fg=self.MUTED, font=(self.FONT, 9)).pack(side='left', padx=12)

    def _on_tab_changed(self, _event=None):
        try:
            current = str(self.nb.select())
            if current == str(self.tab_menu) and not self.menu_items:
                self.menu_refresh()
            if current == str(self.tab_articles) and not self.articles:
                self.articles_refresh()
        except Exception:
            pass

    def menu_refresh(self):
        api = self.api or get_api(self.cfg)
        if not api:
            return

        def job():
            try:
                text, _ = api.get_text('_config.landscape.yml')
                items, _, _ = parse_menu(text or '')
                self.ui(self._apply_menu, items, text)
            except Exception as e:
                self.log('读取导航菜单失败：%s' % e)

        threading.Thread(target=job, daemon=True).start()

    def _apply_menu(self, items, text=None):
        self.menu_items = items
        self._fill_menu_list()
        self.log('导航菜单：%d 项' % len(items))

    def _fill_menu_list(self):
        self.menu_list.delete(0, 'end')
        for it in self.menu_items:
            self.menu_list.insert('end', '  %s      →      %s' % (it['label'], it['url']))

    def _menu_dialog(self, title='添加菜单', item=None):
        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        win.grab_set()
        win.configure(bg=self.CARD_BG)
        win.resizable(False, False)
        frame = tk.Frame(win, bg=self.CARD_BG)
        frame.pack(fill='both', expand=True, padx=20, pady=16)
        tk.Label(frame, text='显示名称', bg=self.CARD_BG, fg=self.MUTED,
                 font=(self.FONT, 10)).grid(row=0, column=0, sticky='e', pady=5)
        var_label = tk.StringVar(value=(item or {}).get('label', ''))
        ttk.Entry(frame, textvariable=var_label, width=38).grid(row=0, column=1, padx=(10, 0), pady=5)
        tk.Label(frame, text='链接', bg=self.CARD_BG, fg=self.MUTED,
                 font=(self.FONT, 10)).grid(row=1, column=0, sticky='e', pady=5)
        var_url = tk.StringVar(value=(item or {}).get('url', '/'))
        ttk.Entry(frame, textvariable=var_url, width=38).grid(row=1, column=1, padx=(10, 0), pady=5)
        tk.Label(frame, text='站内路径（/notes）或完整网址（https://…）', bg=self.CARD_BG,
                 fg=self.MUTED, font=(self.FONT, 9)).grid(row=2, column=1, sticky='w', padx=(10, 0))

        var_create = tk.BooleanVar(value=False)
        var_page = tk.StringVar(value='')
        chk = tk.Checkbutton(frame, text='同时创建这个页面（生成占位文章，之后可编辑）',
                             variable=var_create, bg=self.CARD_BG, fg=self.TEXT,
                             activebackground=self.CARD_BG, selectcolor='#ffffff',
                             font=(self.FONT, 9), command=lambda: toggle())
        chk.grid(row=3, column=0, columnspan=2, sticky='w', pady=(12, 4))
        tk.Label(frame, text='页面文件', bg=self.CARD_BG, fg=self.MUTED,
                 font=(self.FONT, 10)).grid(row=4, column=0, sticky='e', pady=5)
        page_entry = ttk.Entry(frame, textvariable=var_page, width=38, state='disabled')
        page_entry.grid(row=4, column=1, padx=(10, 0), pady=5)

        def refresh_page_path(*_):
            p = page_path_for(var_url.get())
            via = ''
            if p:
                via = p
            var_page.set(via)
            if p and not var_create.get():
                var_create.set(True)
                toggle()
            if not p and var_create.get():
                var_create.set(False)
                toggle()

        def toggle():
            page_entry.config(state='normal' if var_create.get() else 'disabled')

        var_url.trace_add('write', refresh_page_path)
        refresh_page_path()

        result = {}

        def submit():
            label = var_label.get().strip()
            url = var_url.get().strip()
            if not label or not url:
                messagebox.showwarning('提示', '名称和链接都要填', parent=win)
                return
            result.update(label=label, url=url,
                          create=bool(var_create.get() and var_page.get().strip()),
                          page=var_page.get().strip())
            win.destroy()

        bar = tk.Frame(frame, bg=self.CARD_BG)
        bar.grid(row=5, column=0, columnspan=2, sticky='e', pady=(16, 0))
        ttk.Button(bar, text='确定', style='Accent.TButton', command=submit).pack(side='left')
        ttk.Button(bar, text='取消', style='Ghost.TButton', command=win.destroy).pack(side='left', padx=8)
        win.wait_window()
        return result or None

    def menu_add(self):
        data = self._menu_dialog('添加菜单')
        if not data:
            return
        self.menu_items.append({'label': data['label'], 'url': data['url']})
        if data['create']:
            self.pending_pages[data['page']] = page_markdown(data['label'])
            self.log('将创建页面：%s' % data['page'])
        self._fill_menu_list()

    def menu_edit(self):
        sel = self.menu_list.curselection()
        if not sel:
            return
        idx = sel[0]
        data = self._menu_dialog('编辑菜单', self.menu_items[idx])
        if not data:
            return
        self.menu_items[idx] = {'label': data['label'], 'url': data['url']}
        if data['create']:
            self.pending_pages[data['page']] = page_markdown(data['label'])
        self._fill_menu_list()

    def menu_delete(self):
        sel = self.menu_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if messagebox.askyesno('确认删除', '删除菜单「%s」吗？' % self.menu_items[idx]['label']):
            self.menu_items.pop(idx)
            self._fill_menu_list()

    def menu_move(self, delta):
        sel = self.menu_list.curselection()
        if not sel:
            return
        idx = sel[0]
        new = idx + delta
        if 0 <= new < len(self.menu_items):
            self.menu_items[idx], self.menu_items[new] = self.menu_items[new], self.menu_items[idx]
            self._fill_menu_list()
            self.menu_list.selection_set(new)

    def menu_save(self):
        if not self.menu_items:
            messagebox.showwarning('提示', '菜单不能为空')
            return
        api = self.api or get_api(self.cfg)
        if not api:
            messagebox.showwarning('提示', '先设置 GitHub Token（状态页）')
            return

        def job():
            try:
                text, _ = api.get_text('_config.landscape.yml')
                new_text = replace_menu_block(text or '', self.menu_items)
                files = {'_config.landscape.yml': new_text.encode('utf-8')}
                for path, content in self.pending_pages.items():
                    files[path] = content.encode('utf-8')
                sha = api.commit_files(files, 'nav: 更新顶部导航菜单')
                self.pending_pages.clear()
                (REPO / '_config.landscape.yml').write_text(new_text, encoding='utf-8', newline='\n')
                state = api.run_status(sha, log=self.log)
                self.log('✅ 导航菜单已发布（%s）' % state)
                self.ui(self.menu_refresh)
            except Exception as e:
                self.log('❌ 保存菜单失败：%s' % e)
                self.ui(messagebox.showerror, '保存失败', str(e))

        threading.Thread(target=job, daemon=True).start()

    def _build_articles_tab(self):
        f = self.tab_articles
        self.articles = []
        c = self._card(f, '文章管理',
                       '改分类/标签会同步更新分类页和标签云；也可以删除文章或移动到其它分区',
                       expand=True)
        holder, self.article_list = self._styled_listbox(c, height=9)
        holder.pack(fill='both', expand=True)
        btns = tk.Frame(c, bg=self.CARD_BG)
        btns.pack(fill='x', pady=(10, 0))
        ttk.Button(btns, text='编辑信息', style='Accent.TButton',
                   command=self.article_edit).pack(side='left')
        ttk.Button(btns, text='移动到分区', style='Ghost.TButton',
                   command=self.article_move).pack(side='left', padx=8)
        ttk.Button(btns, text='删除文章', style='Ghost.TButton',
                   command=self.article_delete).pack(side='left')
        ttk.Button(btns, text='刷新', style='Ghost.TButton',
                   command=self.articles_refresh).pack(side='left', padx=8)

    def articles_refresh(self):
        api = self.api or get_api(self.cfg)
        if not api:
            return

        def job():
            try:
                entries = [e for e in api.list_dir('source/_posts')
                           if e['type'] == 'file' and e['name'].lower().endswith('.md')]
                articles = []
                for e in entries:
                    text, _ = api.get_text(e['path'])
                    data, body = parse_front_matter(text or '')
                    data['path'] = e['path']
                    data['body'] = body
                    articles.append(data)
                articles.sort(key=lambda a: str(a.get('date')), reverse=True)
                self.ui(self._apply_articles, articles)
            except Exception as e:
                self.log('读取文章失败：%s' % e)

        threading.Thread(target=job, daemon=True).start()

    def _apply_articles(self, articles):
        self.articles = articles
        self.article_list.delete(0, 'end')
        for a in articles:
            cats = '/'.join(a.get('categories') or []) or '未分类'
            self.article_list.insert('end', '  %s   %s      [%s]'
                                     % (str(a.get('date', ''))[:10], a.get('title', ''), cats))
        self.log('文章：%d 篇' % len(articles))

    def _selected_article(self):
        sel = self.article_list.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx >= len(self.articles):
            return None
        return self.articles[idx]

    def _article_dialog(self, title, article):
        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        win.grab_set()
        win.configure(bg=self.CARD_BG)
        win.resizable(False, False)
        frame = tk.Frame(win, bg=self.CARD_BG)
        frame.pack(fill='both', expand=True, padx=20, pady=16)
        fields = [('标题', 'title'), ('日期', 'date'), ('分类（逗号分隔）', 'categories'),
                  ('标签（逗号分隔）', 'tags'), ('永久链接', 'permalink')]
        vars_ = {}
        for r, (label, key) in enumerate(fields):
            tk.Label(frame, text=label, bg=self.CARD_BG, fg=self.MUTED,
                     font=(self.FONT, 10)).grid(row=r, column=0, sticky='e', padx=(0, 12), pady=5)
            val = article.get(key) or ''
            if isinstance(val, list):
                val = '，'.join(val)
            vars_[key] = tk.StringVar(value=val)
            ttk.Entry(frame, textvariable=vars_[key], width=56).grid(row=r, column=1, pady=5)
        tk.Label(frame, text='分类和标签决定文章出现在哪个分区、分类页、标签云',
                 bg=self.CARD_BG, fg=self.MUTED,
                 font=(self.FONT, 9)).grid(row=len(fields), column=1, sticky='w')
        result = {}

        def submit():
            data = {}
            for key, var in vars_.items():
                v = var.get().strip()
                if key in ('categories', 'tags'):
                    data[key] = [x.strip() for x in re.split(r'[,，]', v) if x.strip()]
                else:
                    data[key] = v
            if not data['title']:
                messagebox.showwarning('提示', '标题不能为空', parent=win)
                return
            result.update(data)
            win.destroy()

        bar = tk.Frame(frame, bg=self.CARD_BG)
        bar.grid(row=len(fields) + 1, column=0, columnspan=2, sticky='e', pady=(14, 0))
        ttk.Button(bar, text='保存', style='Accent.TButton', command=submit).pack(side='left')
        ttk.Button(bar, text='取消', style='Ghost.TButton', command=win.destroy).pack(side='left', padx=8)
        win.wait_window()
        return result or None

    def article_edit(self):
        article = self._selected_article()
        if not article:
            return
        data = self._article_dialog('编辑文章', article)
        if not data:
            return
        api = self.api or get_api(self.cfg)
        path = article['path']
        body = article.get('body', '')
        new_text = build_front_matter(data, body)
        try:
            sha = api.commit_files({path: new_text.encode('utf-8')},
                                   'edit: 更新文章《%s》' % data['title'])
            local = REPO / path
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(new_text, encoding='utf-8', newline='\n')
            state = api.run_status(sha, log=self.log)
            self.log('✅ 文章已更新（%s）' % state)
            self.articles_refresh()
        except Exception as e:
            messagebox.showerror('保存失败', str(e))

    def article_delete(self):
        article = self._selected_article()
        if not article:
            return
        if not messagebox.askyesno('确认删除',
                                   '删除文章《%s》吗？\n（会同时尝试删除它引用的图片）' % article['title']):
            return
        api = self.api or get_api(self.cfg)
        body = article.get('body', '')
        imgs = set(re.findall(r'!\[[^\]]*\]\(/images/([^)\s"]+)', body))
        deletions = [article['path']]
        for i in imgs:
            deletions.append('source/images/' + i)

        def job():
            try:
                sha = api.commit_files({}, 'delete: 删除文章《%s》' % article['title'],
                                       deletions=deletions)
                state = api.run_status(sha, log=self.log)
                self.log('✅ 已删除（%s）' % state)
                self.ui(self.articles_refresh)
            except Exception as e:
                self.log('删除失败：%s' % e)
                self.ui(messagebox.showerror, '删除失败', str(e))

        threading.Thread(target=job, daemon=True).start()

    def article_move(self):
        article = self._selected_article()
        if not article:
            return
        win = tk.Toplevel(self)
        win.title('移动到分区')
        win.transient(self)
        win.grab_set()
        win.configure(bg=self.CARD_BG)
        frame = tk.Frame(win, bg=self.CARD_BG)
        frame.pack(fill='both', expand=True, padx=20, pady=16)
        tk.Label(frame, text='目标分区（例如 周报、Wp、笔记）', bg=self.CARD_BG,
                 fg=self.MUTED, font=(self.FONT, 10)).pack(anchor='w')
        var_target = tk.StringVar(value=(article.get('categories') or [''])[0])
        ttk.Entry(frame, textvariable=var_target, width=32).pack(anchor='w', pady=6)
        var_page = tk.BooleanVar(value=True)
        var_nav = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text='分区页不存在时自动创建（自动列出该分区文章）',
                       variable=var_page, bg=self.CARD_BG, selectcolor='#ffffff',
                       font=(self.FONT, 9)).pack(anchor='w', pady=2)
        tk.Checkbutton(frame, text='同时把分区加到顶部导航菜单',
                       variable=var_nav, bg=self.CARD_BG, selectcolor='#ffffff',
                       font=(self.FONT, 9)).pack(anchor='w', pady=2)
        result = {}

        def submit():
            target = var_target.get().strip().strip('/')
            if not target:
                messagebox.showwarning('提示', '分区名不能为空', parent=win)
                return
            result.update(target=target, page=bool(var_page.get()), nav=bool(var_nav.get()))
            win.destroy()

        bar = tk.Frame(frame, bg=self.CARD_BG)
        bar.pack(anchor='e', pady=(14, 0))
        ttk.Button(bar, text='移动', style='Accent.TButton', command=submit).pack(side='left')
        ttk.Button(bar, text='取消', style='Ghost.TButton', command=win.destroy).pack(side='left', padx=8)
        win.wait_window()
        if not result:
            return
        api = self.api or get_api(self.cfg)
        target = result['target']
        slug = article_slug(article['path'], article.get('permalink'))

        def job():
            try:
                data = {'title': article['title'], 'date': article['date'],
                        'categories': [target], 'tags': [target],
                        'permalink': '%s/%s/' % (target, slug)}
                files = {article['path']: build_front_matter(data, article.get('body', '')).encode('utf-8')}
                if result['page']:
                    page_path = 'source/%s/index.md' % target
                    existing, _ = api.get_file(page_path)
                    if existing is None:
                        files[page_path] = section_page_markdown(target).encode('utf-8')
                        self.log('将创建分区页：' + page_path)
                if result['nav']:
                    text, _ = api.get_text('_config.landscape.yml')
                    items, _, _ = parse_menu(text or '')
                    if not any(it['label'] == target for it in items):
                        items.append({'label': target, 'url': '/' + target})
                        files['_config.landscape.yml'] = replace_menu_block(text or '', items).encode('utf-8')
                        self.log('将分区加入顶部导航')
                sha = api.commit_files(files, 'move: 把《%s》移动到分区 %s' % (article['title'], target))
                state = api.run_status(sha, log=self.log)
                self.log('✅ 已移动（%s）：%s%s/' % (state, self.cfg['site_url'], target))
                self.ui(self.articles_refresh)
                self.ui(self.menu_refresh)
            except Exception as e:
                self.log('移动失败：%s' % e)
                self.ui(messagebox.showerror, '移动失败', str(e))

        threading.Thread(target=job, daemon=True).start()

    def _build_repo_tab(self):
        f = self.tab_repo
        self.repo_info_label = tk.Label(f, text='加载中……', bg=self.BASE_BG, fg=self.MUTED,
                                        font=(self.FONT, 9), anchor='w', justify='left')
        self.repo_info_label.pack(fill='x', pady=(0, 10))

        c1 = self._card(f, '仓库文件', '双击文件夹进入，双击文件直接编辑（保存后自动发布）', expand=True)
        bar = tk.Frame(c1, bg=self.CARD_BG)
        bar.pack(fill='x', pady=(0, 8))
        ttk.Button(bar, text='⬆ 上一级', style='Ghost.TButton', command=self.repo_up).pack(side='left')
        ttk.Button(bar, text='刷新', style='Ghost.TButton', command=self.repo_refresh).pack(side='left', padx=6)
        self.path_var = tk.StringVar(value='/')
        ttk.Entry(bar, textvariable=self.path_var, state='readonly').pack(
            side='left', fill='x', expand=True, padx=(10, 0))
        holder, self.repo_list = self._styled_listbox(c1, height=6)
        holder.pack(fill='both', expand=True)
        self.repo_list.bind('<Double-Button-1>', lambda e: self.repo_open())

        btns = tk.Frame(c1, bg=self.CARD_BG)
        btns.pack(fill='x', pady=(10, 0))
        ttk.Button(btns, text='打开 / 编辑', style='Accent.TButton',
                   command=self.repo_open).pack(side='left')
        ttk.Button(btns, text='上传文件…', style='Ghost.TButton',
                   command=self.repo_upload).pack(side='left', padx=8)
        ttk.Button(btns, text='新建文件…', style='Ghost.TButton',
                   command=self.repo_new_file).pack(side='left')
        ttk.Button(btns, text='删除', style='Ghost.TButton',
                   command=self.repo_delete).pack(side='left', padx=8)

        c2 = self._card(f, '仓库设置', '需要仓库管理员权限（Token 勾选 repo / Administration）')
        grid = tk.Frame(c2, bg=self.CARD_BG)
        grid.pack(fill='x')
        tk.Label(grid, text='仓库简介', bg=self.CARD_BG, fg=self.MUTED,
                 font=(self.FONT, 10)).grid(row=0, column=0, sticky='e', padx=(0, 12), pady=5)
        self.var_desc = tk.StringVar()
        ttk.Entry(grid, textvariable=self.var_desc).grid(row=0, column=1, sticky='we', pady=5)
        ttk.Button(grid, text='保存', style='Ghost.TButton',
                   command=self.save_description).grid(row=0, column=2, padx=(8, 0))
        tk.Label(grid, text='仓库名', bg=self.CARD_BG, fg=self.MUTED,
                 font=(self.FONT, 10)).grid(row=1, column=0, sticky='e', padx=(0, 12), pady=5)
        self.var_rename = tk.StringVar()
        ttk.Entry(grid, textvariable=self.var_rename).grid(row=1, column=1, sticky='we', pady=5)
        ttk.Button(grid, text='重命名', style='Ghost.TButton',
                   command=self.rename_repo).grid(row=1, column=2, padx=(8, 0))
        grid.columnconfigure(1, weight=1)
        ttk.Button(c2, text='重新开启 / 修复 GitHub Pages', style='Ghost.TButton',
                   command=self.fix_pages).pack(anchor='w', pady=(10, 0))

    def _build_status_tab(self):
        f = self.tab_status
        c = self._card(f, '运行状态', '仓库、Token、Pages、最近部署', expand=True)
        self.status_text = tk.Text(c, height=13, bd=0, highlightthickness=0, wrap='word',
                                   bg='#fbfcff', fg=self.TEXT, font=('Consolas', 9),
                                   padx=10, pady=8)
        self.status_text.pack(fill='both', expand=True)
        bar = tk.Frame(c, bg=self.CARD_BG)
        bar.pack(fill='x', pady=(10, 0))
        ttk.Button(bar, text='刷新状态', style='Accent.TButton',
                   command=self.refresh_status).pack(side='left')
        ttk.Button(bar, text='设置 GitHub Token', style='Ghost.TButton',
                   command=self.ask_token).pack(side='left', padx=8)
        ttk.Button(bar, text='打开 Actions', style='Ghost.TButton',
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
            self.ui(self.menu_refresh)
            self.ui(self.articles_refresh)
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
        pages_url = pages.get('html_url') if pages else '未开启'
        run_text = ('%s / %s' % (run['status'], run.get('conclusion'))) if run else '未知'
        self.repo_info_label.config(
            text='仓库 %s   ·   站点 %s   ·   Pages %s   ·   最近部署 %s'
                 % (repo['full_name'], self.cfg['site_url'], pages_url, run_text))
        try:
            self.status_bar.config(text='  %s   ·   %s   ·   Pages %s'
                                    % (repo['full_name'], self.cfg['site_url'], pages_url))
        except Exception:
            pass

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
    app = App()
    for arg in sys.argv[1:]:
        if arg.startswith('--tab='):
            try:
                app.nb.select(int(arg.split('=', 1)[1]))
            except Exception:
                pass
    app.mainloop()


if __name__ == '__main__':
    main()
