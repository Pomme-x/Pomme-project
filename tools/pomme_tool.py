# -*- coding: utf-8 -*-
"""Pomme 博客小工具（Windows 图形界面）

功能：
  1. 上传周报 PDF：自动转成和第一篇周报一样的网页文章（文字 + 截图 + 表格 + 代码高亮），
     图片自动压缩，然后自动提交、推送到 GitHub，GitHub Actions 自动部署上线。
  2. 外观设置：换顶部背景（内置粉色星云 / 黑洞 / 自己的图片），改站点标题、副标题、作者。
  3. 状态：查看仓库状态、一键打开网站 / 仓库 / Actions。

依赖：pymupdf、Pillow（本机已装）。运行：双击「启动Pomme工具.bat」
"""

import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

REPO = Path(__file__).resolve().parent.parent
GITHUB_REPO = 'xunshichen-2008/Pomme-project'
SITE_URL = 'https://xunshichen-2008.github.io/Pomme-project/'
BRANCH = 'main'
GIT_ENV = dict(os.environ, GIT_SSL_NO_VERIFY='true', GIT_TERMINAL_PROMPT='0',
               GCM_INTERACTIVE='Never')

BG_PRESETS = {
    '粉色星云（当前）': 'banner-pink.jpg',
    '黑洞': 'banner-blackhole.jpg',
}


def run(cmd, input_text=None, timeout=600):
    p = subprocess.run(cmd, cwd=str(REPO), env=GIT_ENV, input=input_text,
                       capture_output=True, text=True, timeout=timeout,
                       encoding='utf-8', errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def get_token():
    code, out = run(['git', 'credential', 'fill'],
                    input_text='protocol=https\nhost=github.com\n\n', timeout=60)
    for line in out.splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return None


def push_changes(message, log=print):
    """提交当前所有改动并推送到 GitHub，返回短 sha（没有改动则返回 None）。"""
    run(['git', 'add', '-A'])
    code, out = run(['git', 'status', '--porcelain'])
    if not out.strip():
        log('没有需要提交的改动。')
        return None
    run(['git', 'commit', '-m', message])
    code, out = run(['git', 'fetch', 'origin'])
    if code != 0:
        raise RuntimeError('拉取远端失败：' + out[-500:])
    code, out = run(['git', 'rebase', 'origin/' + BRANCH])
    if code != 0:
        run(['git', 'rebase', '--abort'])
        raise RuntimeError('和 GitHub 上的改动冲突了，先手动处理一下：\n' + out[-800:])

    token = get_token()
    if not token:
        raise RuntimeError('没有找到 GitHub 凭据（Windows 凭据管理器里没有 github.com）')
    env_token = dict(GIT_ENV, POMME_TOKEN=token)
    helper = 'credential.helper=!f() { echo username=xunshichen-2008; echo password=$POMME_TOKEN; }; f'
    p = subprocess.run(['git', '-c', 'credential.helper=', '-c', helper,
                        'push', 'origin', BRANCH],
                       cwd=str(REPO), env=env_token, capture_output=True,
                       text=True, timeout=600, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        raise RuntimeError('推送失败：' + (p.stdout + p.stderr)[-800:])
    code, sha = run(['git', 'rev-parse', '--short', 'HEAD'])
    log('已推送到 GitHub：' + sha.strip())
    return sha.strip()


def wait_deploy(sha, log=print, timeout=420):
    """等 GitHub Actions 跑完（返回 success/failure/timeout）。"""
    import json
    import urllib.request
    api = 'https://api.github.com/repos/%s/actions/runs?per_page=15' % GITHUB_REPO
    deadline = time.time() + timeout
    seen = False
    while time.time() < deadline:
        try:
            req = urllib.request.Request(api, headers={'User-Agent': 'pomme-tool'})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode('utf-8'))
            for run_item in data.get('workflow_runs', []):
                if run_item['head_sha'].startswith(sha):
                    seen = True
                    if run_item['status'] == 'completed':
                        return run_item['conclusion'] or 'unknown'
                    log('部署进行中……（%s）' % run_item['status'])
                    break
        except Exception as e:
            log('查询部署状态失败：%s' % e)
        time.sleep(8)
    return 'timeout' if seen else 'not-found'


def site_config():
    """从 _config.yml 读取站点信息。"""
    cfg = dict(title='', subtitle='', author='')
    try:
        text = (REPO / '_config.yml').read_text(encoding='utf-8')
    except Exception:
        return cfg
    for key in cfg:
        m = re.search(r'(?m)^%s:\s*(.*)$' % key, text)
        if m:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in '"\'':
                val = val[1:-1]
            cfg[key] = val
    return cfg


def set_site_config(title=None, subtitle=None, author=None):
    path = REPO / '_config.yml'
    text = path.read_text(encoding='utf-8')

    def yaml_val(v):
        if v is None or v == '':
            return "''"
        return '"%s"' % v.replace('\\', '\\\\').replace('"', '\\"')

    def repl(text, key, value):
        if value is None:
            return text
        line = '%s: %s' % (key, yaml_val(value))
        return re.sub(r'(?m)^%s:.*$' % key, lambda m: line, text, count=1)

    text = repl(text, 'title', title)
    text = repl(text, 'subtitle', subtitle)
    text = repl(text, 'author', author)
    path.write_text(text, encoding='utf-8', newline='\n')


def make_banner(src, dst, bright=0.86, size=(1920, 480)):
    """把任意图片裁成 4:1 横幅并压暗（为了白字清晰）。"""
    from PIL import ImageEnhance
    im = Image.open(src).convert('RGB')
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    nw, nh = max(tw, int(im.width * scale + 0.5)), max(th, int(im.height * scale + 0.5))
    im = im.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    im = im.crop((left, top, left + tw, top + th))
    im = ImageEnhance.Brightness(im).enhance(bright)
    im = ImageEnhance.Color(im).enhance(1.05)
    im.save(dst, 'JPEG', quality=88, optimize=True, progressive=True)


def thumb(path, max_w=460, max_h=150):
    im = Image.open(path).convert('RGB')
    ratio = min(max_w / im.width, max_h / im.height)
    im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))), Image.LANCZOS)
    return ImageTk.PhotoImage(im)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Pomme 博客小工具')
        self.geometry('1000x760')
        self.minsize(900, 680)
        self.log_queue = queue.Queue()
        self.pdfs = []
        self.bg_choice = tk.StringVar(value='粉色星云（当前）')
        self.bg_custom = None
        self.bg_image = None

        self._build_ui()
        self._refresh_banner_preview()
        self._refresh_status()
        self.after(120, self._drain_log)

    # ---------------- UI ----------------
    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use('vista')
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
            ttk.Entry(form, textvariable=var, width=60).grid(row=r, column=1, sticky='we', pady=2, padx=4)
        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(f)
        btns.pack(fill='x', pady=6)
        ttk.Button(btns, text='③ 上传并发布（自动转换、推送、等部署）',
                   command=self.start_upload).pack(side='left')
        ttk.Label(btns, text='   单篇 51 页约 1~2 分钟；大文件会久一点').pack(side='left')

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
        cfg = site_config()
        self.var_site_title.set(cfg['title'])
        self.var_site_sub.set(cfg['subtitle'])
        self.var_site_author.set(cfg['author'])
        for r, (label, var) in enumerate([('站点标题：', self.var_site_title),
                                          ('副标题：', self.var_site_sub),
                                          ('作者：', self.var_site_author)]):
            ttk.Label(info, text=label).grid(row=r, column=0, sticky='e', pady=2)
            ttk.Entry(info, textvariable=var, width=46).grid(row=r, column=1, sticky='we', pady=2, padx=4)
        info.columnconfigure(1, weight=1)

        ttk.Button(f, text='保存并发布', command=self.start_style_save).pack(anchor='w', pady=8)

    def _build_status_tab(self):
        f = self.tab_status
        self.status_text = tk.Text(f, height=18, wrap='word', font=('Consolas', 9))
        self.status_text.pack(fill='both', expand=True)
        bar = ttk.Frame(f)
        bar.pack(fill='x', pady=6)
        ttk.Button(bar, text='刷新状态', command=self._refresh_status).pack(side='left')
        ttk.Button(bar, text='打开 Actions',
                   command=lambda: webbrowser.open('https://github.com/%s/actions' % GITHUB_REPO)).pack(side='left', padx=6)
        ttk.Button(bar, text='打开本地预览（需已启动 hexo server）',
                   command=lambda: webbrowser.open('http://localhost:4000/Pomme-project/')).pack(side='left')

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

    # ---------------- pdf tab ----------------
    def add_pdfs(self):
        files = filedialog.askopenfilenames(title='选择 PDF', filetypes=[('PDF 文件', '*.pdf')])
        for f in files:
            if f and f not in self.pdfs:
                self.pdfs.append(f)
                self.pdf_list.insert('end', Path(f).name)
        if files:
            if not self.var_title.get().strip():
                try:
                    from pdf2post import extract_title, open_doc
                    d = open_doc(files[0])
                    self.var_title.set(extract_title(d, files[0]))
                    d.close()
                except Exception:
                    pass
            self.log('已添加 %d 个 PDF' % len(files))

    def remove_pdf(self):
        sel = list(self.pdf_list.curselection())
        for idx in reversed(sel):
            self.pdf_list.delete(idx)
            self.pdfs.pop(idx)

    def start_upload(self):
        if not self.pdfs:
            messagebox.showwarning('提示', '先添加 PDF 文件')
            return
        title = self.var_title.get().strip()
        date_str = self.var_date.get().strip()
        tags = [t.strip() for t in re.split(r'[,，]', self.var_tags.get()) if t.strip()]
        cats = [t.strip() for t in re.split(r'[,，]', self.var_cat.get()) if t.strip()]
        pdfs = list(self.pdfs)

        def job():
            try:
                from pdf2post import convert_pdf
                for idx, pdf in enumerate(pdfs):
                    self.log('—— 开始转换：%s' % Path(pdf).name)
                    t = title if (len(pdfs) == 1 and title) else None
                    res = convert_pdf(pdf, str(REPO), title=t, date_str=date_str,
                                      tags=tags, categories=cats, log=self.log)
                    self.log('—— 推送到 GitHub……')
                    sha = push_changes('feat: 上传周报《%s》' % res['title'], log=self.log)
                    if sha:
                        state = wait_deploy(sha, log=self.log)
                        if state == 'success':
                            self.log('✅ 已上线：%s （首页/Archives 里能看到新文章）' % SITE_URL)
                        else:
                            self.log('⚠️ 部署状态：%s（去 Actions 看看）' % state)
                    else:
                        self.log('没有内容变化，未推送。')
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
                return
            self.bg_custom = f
        self._refresh_banner_preview()

    def _refresh_banner_preview(self):
        try:
            path = self._selected_bg_source()
            if path and Path(path).exists():
                self.bg_image = thumb(path)
                self.bg_preview.config(image=self.bg_image)
            else:
                self.bg_image = thumb(REPO / 'source' / 'images' / 'banner.jpg')
                self.bg_preview.config(image=self.bg_image)
        except Exception as e:
            self.log('预览失败：%s' % e)

    def _selected_bg_source(self):
        choice = self.bg_choice.get()
        if choice == '我的图片…':
            return self.bg_custom
        name = BG_PRESETS.get(choice)
        if name:
            return REPO / 'source' / 'images' / name
        return None

    def start_style_save(self):
        title = self.var_site_title.get().strip()
        subtitle = self.var_site_sub.get().strip()
        author = self.var_site_author.get().strip()
        bg_src = self._selected_bg_source()

        def job():
            try:
                if bg_src and Path(bg_src).exists():
                    dst = REPO / 'source' / 'images' / 'banner.jpg'
                    make_banner(bg_src, dst)
                    self.log('背景已更新：%s → banner.jpg' % Path(bg_src).name)
                set_site_config(title=title, subtitle=subtitle, author=author)
                self.log('站点信息已更新：%s / %s / %s' % (title, subtitle, author))
                sha = push_changes('style: 更新背景与站点信息', log=self.log)
                if sha:
                    state = wait_deploy(sha, log=self.log)
                    self.log('✅ 已发布（%s）：%s' % (state, SITE_URL))
                self._refresh_banner_preview()
            except Exception as e:
                self.log('❌ 出错：%s' % e)
                messagebox.showerror('出错', str(e))

        threading.Thread(target=job, daemon=True).start()

    # ---------------- status tab ----------------
    def _refresh_status(self):
        lines = ['仓库目录：%s' % REPO, '远端仓库：https://github.com/%s' % GITHUB_REPO,
                 '站点地址：%s' % SITE_URL, '']
        code, out = run(['git', 'log', '--oneline', '-5'])
        lines.append('最近提交：')
        lines.extend(out.strip().splitlines() or ['（无）'])
        lines.append('')
        code, out = run(['git', 'status', '--short'])
        lines.append('工作区改动：')
        lines.extend(out.strip().splitlines() or ['（干净）'])
        cfg = site_config()
        lines.extend(['', '当前站点信息：标题=%s 副标题=%s 作者=%s' % (
            cfg['title'], cfg['subtitle'], cfg['author'])])
        self.status_text.delete('1.0', 'end')
        self.status_text.insert('end', '\n'.join(lines))


def main():
    os.chdir(str(REPO))
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
