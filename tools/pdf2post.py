# -*- coding: utf-8 -*-
"""把 PDF 转成 Hexo 文章：文字 + 截图 + 表格，图片自动压缩。

用法（在本工具内部调用，也可以命令行测试）：
    from pdf2post import convert_pdf
    result = convert_pdf(pdf_path, repo_dir, title=None)
"""

import os
import re
from pathlib import Path

try:
    import pymupdf
except ImportError:  # 老版本 PyMuPDF 用 fitz
    import fitz as pymupdf

from PIL import Image

RIGHT_MARGIN = 520.0
LANGS = {'C', 'C++', 'Python', 'Python3', 'Bash', 'Shell', 'Java', 'Text',
         'SQL', 'JavaScript', 'Go', 'Rust', 'HTML', 'JSON', 'YAML', 'C#'}
LANG_MAP = {'Python3': 'python', 'C++': 'cpp', 'C#': 'csharp', 'JavaScript': 'javascript'}
PUNCT_ONLY = set('，,。.、_；;· ')
CJK = re.compile(r'[\u3000-\u9fff\uff00-\uffef]')
IMAGE_URL_PREFIX = '/images/'


def _is_cjk(ch):
    return bool(CJK.match(ch))


def _join_lines(lines):
    out = ''
    for t in lines:
        t = t.strip()
        if not t:
            continue
        if not out:
            out = t
        elif _is_cjk(out[-1]) or _is_cjk(t[0]):
            out += t
        else:
            out += ' ' + t
    return out


def _esc_body(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return s.replace('*', r'\*')


def _clean_cell(v):
    if v is None:
        return ''
    raw = str(v)
    lines = []
    for l in raw.split('\n'):
        l = l.strip()
        if not l:
            continue
        if all(ch in PUNCT_ONLY for ch in l):
            continue
        lines.append(l)
    if not lines:
        lines = [raw.strip()] if raw.strip() else []
    s = _join_lines(lines)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.replace('|', r'\|').replace('*', r'\*')


def _inside(bbox, rect):
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    return rect[0] - 1 <= cx <= rect[2] + 1 and rect[1] - 1 <= cy <= rect[3] + 1


def _slugify(text):
    """只保留 ASCII（文章文件名 / 图片目录用，避免中文路径在网址里出问题）。"""
    s = re.sub(r'[^A-Za-z0-9_-]+', '-', text or '').strip('-')
    return re.sub(r'-{2,}', '-', s)[:40]


def extract_title(doc, pdf_path):
    """取第 1 页字号最大的文字行作为标题。"""
    best = ('', 0.0)
    try:
        for block in doc[0].get_text('dict')['blocks']:
            if block['type'] != 0:
                continue
            for line in block['lines']:
                size = max((s['size'] for s in line['spans']), default=0)
                text = ''.join(s['text'] for s in line['spans']).strip()
                if text and size > best[1]:
                    best = (text, size)
    except Exception:
        pass
    if best[1] < 12:
        best = (Path(pdf_path).stem, 0)
    return best[0]


def open_doc(pdf_path):
    """打开 PDF（给工具界面调用）。"""
    return pymupdf.open(str(pdf_path))


def convert_pdf(pdf_path, repo_dir, title=None, date_str=None, tags=None,
                categories=None, log=print):
    """转换 PDF 为 Markdown 文章，返回 dict(md_path, images, title)。"""
    repo = Path(repo_dir)
    pdf_path = Path(pdf_path)
    doc = pymupdf.open(str(pdf_path))

    title = (title or '').strip() or extract_title(doc, pdf_path)
    import hashlib
    base = _slugify(title)
    if len(base) < 3:
        base = 'weekly'
    slug = '%s-%s' % (base, hashlib.md5(title.encode('utf-8')).hexdigest()[:4])
    if date_str:
        m = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
    else:
        from datetime import datetime
        now = datetime.now()
        y, mo, d = str(now.year), str(now.month).zfill(2), str(now.day).zfill(2)

    images_dir = repo / 'source' / 'images' / slug
    images_dir.mkdir(parents=True, exist_ok=True)
    for old in images_dir.glob('*'):
        if old.is_file():
            old.unlink()

    tables = []
    for pno in range(doc.page_count):
        try:
            found = doc[pno].find_tables()
        except Exception:
            found = None
        if not found:
            continue
        for tb in found.tables:
            raw = tb.extract()
            first_empty = (not raw) or (not any(_clean_cell(c) for c in raw[0]))
            rows = [[_clean_cell(c) for c in row] for row in raw]
            rows = [r for r in rows if any(c for c in r)]
            if not rows:
                continue
            tables.append(dict(page=pno, y=tb.bbox[1], bbox=tb.bbox, rows=rows,
                               first_empty=first_empty,
                               cols=max(len(r) for r in rows), positions=[(pno, tb.bbox)]))

    merged = []
    for t in tables:
        if merged and t['first_empty'] and t['cols'] == merged[-1]['cols']:
            merged[-1]['rows'].extend(t['rows'])
            merged[-1]['positions'].extend(t['positions'])
        else:
            merged.append(t)

    md_parts = []
    img_count = 0
    doc_title = title
    page_count = doc.page_count

    for pno in range(doc.page_count):
        if log and doc.page_count > 12 and pno % 10 == 0:
            log('转换中 %d/%d 页 …' % (pno + 1, doc.page_count))
        page = doc[pno]
        page_bboxes = [b for t in merged for p, b in t['positions'] if p == pno]
        emit_tables = [t for t in merged if t['page'] == pno]
        items = []

        for block in page.get_text('dict')['blocks']:
            if block['type'] == 1:
                continue
            for li, line in enumerate(block['lines']):
                spans = line['spans']
                if not spans:
                    continue
                text = ''.join(s['text'] for s in spans)
                if not text.strip():
                    continue
                size = max(round(s['size'], 1) for s in spans)
                color = spans[0]['color']
                mono_len = sum(len(s['text']) for s in spans if s['font'].startswith('Menlo'))
                mono = mono_len >= 0.5 * max(1, len(text.strip()))
                t = text.strip()
                if color == 0x117cee:
                    continue
                if not mono and t.isdigit() and size <= 10.0:
                    continue
                if mono and re.fullmatch(r'\d+', t):
                    continue
                if any(_inside(line['bbox'], b) for b in page_bboxes):
                    continue
                items.append(dict(y=line['bbox'][1], x=line['bbox'][0], x1=line['bbox'][2],
                                  text=text, size=size, mono=mono, color=color,
                                  block=block['number'], line=li))

        for info in page.get_image_info(xrefs=True):
            x0, y0, x1, y1 = info['bbox']
            w, h = x1 - x0, y1 - y0
            if not ((w >= 100 and h >= 15) or (w >= 40 and h >= 40)):
                continue
            if any(_inside(info['bbox'], b) for b in page_bboxes):
                continue
            items.append(dict(kind='img', y=y0, x=x0, xref=info['xref'], bbox=info['bbox']))

        for tb in emit_tables:
            items.append(dict(kind='table', y=tb['y'], x=0, table=tb))

        items.sort(key=lambda it: (round(it['y'], 1), it['x']))

        def take_code(start):
            lang = None
            j = start
            first = items[j]
            if (first['size'] <= 10.5 and first['x'] > 480
                    and first['text'].strip() in LANGS):
                lang = LANG_MAP.get(first['text'].strip(), first['text'].strip().lower())
                j += 1
            lines = []
            while j < len(items) and items[j].get('kind') is None and items[j]['mono']:
                cur = items[j]
                nxt = items[j + 1] if j + 1 < len(items) else None
                t = cur['text'].rstrip('\n')
                if (cur['x1'] >= RIGHT_MARGIN and nxt is not None
                        and nxt.get('kind') is None and nxt['mono']
                        and abs(nxt['x'] - cur['x']) < 6):
                    t += nxt['text'].rstrip('\n')
                    j += 2
                    continue
                lines.append(t)
                j += 1
            return lines, j, lang

        i = 0
        while i < len(items):
            it = items[i]

            if it.get('kind') == 'img':
                img_count += 1
                try:
                    pix = doc.extract_image(it['xref'])
                    name = 'p%02d_%d.%s' % (pno + 1, img_count, 'jpg')
                    target = images_dir / name
                    im = Image.open(__import__('io').BytesIO(pix['image'])).convert('RGB')
                    if im.width > 1200:
                        ratio = 1200.0 / im.width
                        im = im.resize((1200, max(1, int(im.height * ratio))), Image.LANCZOS)
                    im.save(target, 'JPEG', quality=80, optimize=True, progressive=True)
                    url = '%s%s/%s' % (IMAGE_URL_PREFIX, slug, name)
                    md_parts.append('\n![第%d页截图](%s)\n' % (pno + 1, url))
                except Exception as e:
                    log('图片处理失败 p%d: %s' % (pno + 1, e))
                i += 1
                continue

            if it.get('kind') == 'table':
                tb = it['table']
                rows = tb['rows']
                width = max(len(r) for r in rows)
                rows = [r + [''] * (width - len(r)) for r in rows]
                out = ['| ' + ' | '.join(rows[0]) + ' |',
                       '|' + '|'.join([' --- '] * width) + '|']
                for r in rows[1:]:
                    out.append('| ' + ' | '.join(r) + ' |')
                md_parts.append('\n' + '\n'.join(out) + '\n')
                i += 1
                continue

            txt = it['text'].strip()
            size = it['size']

            if it['mono']:
                lines, i, _ = take_code(i)
                md_parts.append('\n```\n' + '\n'.join(lines) + '\n```\n')
                continue

            if size <= 10.5 and it['x'] > 480 and txt in LANGS:
                lines, j, lang = take_code(i)
                if lines:
                    md_parts.append('\n```' + (lang or '') + '\n' + '\n'.join(lines) + '\n```\n')
                    i = j
                    continue
                i += 1
                continue

            if size >= 13:
                parts = [txt]
                j = i + 1
                while j < len(items):
                    nxt = items[j]
                    if nxt.get('kind') is not None or nxt['mono'] or nxt['size'] < 13:
                        break
                    if abs(nxt['size'] - size) > 0.4:
                        break
                    if abs(nxt['x'] - it['x']) > 2 or nxt['y'] - items[j - 1]['y'] > 30:
                        break
                    parts.append(nxt['text'].strip())
                    j += 1
                heading = _join_lines(parts)
                if size >= 24 and heading == doc_title:
                    md_parts.append('\n')  # 标题已经在 front-matter 里
                elif size >= 24:
                    md_parts.append('\n# ' + _esc_body(heading) + '\n')
                elif size >= 20:
                    md_parts.append('\n## ' + _esc_body(heading) + '\n')
                elif size >= 16:
                    md_parts.append('\n### ' + _esc_body(heading) + '\n')
                else:
                    md_parts.append('\n#### ' + _esc_body(heading) + '\n')
                i = j
                continue

            if txt.startswith('•') or txt.startswith('·'):
                md_parts.append('\n- ' + _esc_body(txt.lstrip('•· ').strip()) + '\n')
                i += 1
                continue

            para = [txt]
            block_id = it['block']
            last_x1 = it['x1']
            j = i + 1
            while j < len(items):
                nxt = items[j]
                if nxt.get('kind') is not None or nxt['mono'] or nxt['size'] >= 13:
                    break
                if abs(nxt['x'] - it['x']) > 100:
                    break
                if nxt['block'] == block_id:
                    para.append(nxt['text'].strip())
                    last_x1 = nxt['x1']
                    j += 1
                    continue
                if last_x1 >= RIGHT_MARGIN and nxt['x'] <= it['x'] + 2:
                    para.append(nxt['text'].strip())
                    last_x1 = nxt['x1']
                    j += 1
                    continue
                break
            md_parts.append('\n' + _esc_body(_join_lines(para).lstrip('，,、')) + '\n')
            i = j

    body = ''.join(md_parts)
    body = re.sub(r'\n{3,}', '\n\n', body).strip('\n')

    tags = tags or ['周报']
    categories = categories or ['周报']

    def q(s):
        return '"%s"' % str(s).replace('\\', '\\\\').replace('"', '\\"')

    fm = ['---', 'title: %s' % q(' '.join(title.split())),
          'date: %s 20:00:00' % ('%s-%s-%s' % (y, mo, d))]
    fm.append('tags:')
    for t in tags:
        fm.append('  - ' + q(t))
    fm.append('categories:')
    for c in categories:
        fm.append('  - ' + q(c))
    section = (categories[0].strip().strip('/') if categories else '周报') or '周报'
    fm.append('permalink: ' + q('%s/%s/' % (section, slug)))
    fm.append('---')
    fm.append('')
    content = '\n'.join(fm) + body + '\n'

    posts_dir = repo / 'source' / '_posts'
    posts_dir.mkdir(parents=True, exist_ok=True)
    md_path = posts_dir / ('%s-%s-%s-%s.md' % (y, mo, d, slug))
    md_path.write_text(content, encoding='utf-8', newline='\n')
    doc.close()

    used = len(list(images_dir.glob('*.jpg')))
    log('转换完成：%d 页，%d 张截图，标题「%s」' % (page_count, used, title))
    log('文章文件：%s' % md_path)
    return dict(md_path=md_path, images=used, title=title, slug=slug,
                image_dir=images_dir, pages=page_count)
