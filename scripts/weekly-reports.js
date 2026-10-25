'use strict';

/**
 * 周报列表生成器：构建时扫描 source/周报/ 下的 PDF，注入到「周报」页面，
 * 不需要前端 JS，也不需要访问 GitHub API。上传 PDF 后重新构建即可看到。
 */

const fs = require('fs');
const path = require('path');

const MARKER = /<div id="weekly-report-list">[\s\S]*?<\/div>/;

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

hexo.extend.filter.register('after_render:html', function (str) {
  if (!MARKER.test(str)) return str;

  const dir = path.join(hexo.base_dir, 'source', '周报');
  const root = hexo.config.root || '/';

  let files = [];
  try {
    files = fs.readdirSync(dir).filter(function (f) {
      return /\.pdf$/i.test(f) && !f.startsWith('.');
    });
  } catch (e) {
    files = [];
  }
  files.sort();

  let html;
  if (!files.length) {
    html = '<p>还没有周报。把 PDF 上传到 <code>source/周报/</code> 后，重新构建就会自动列在这里。</p>';
  } else {
    const items = files.map(function (f) {
      let size = 0;
      try {
        size = fs.statSync(path.join(dir, f)).size;
      } catch (e) { /* ignore */ }
      const url = encodeURI(root + '周报/' + f);
      return '<li><a href="' + esc(url) + '" target="_blank" rel="noopener">' +
        esc(f) + '</a>（' + (size / 1048576).toFixed(2) + ' MB）</li>';
    });
    html = '<ul>' + items.join('') + '</ul>';
  }

  return str.replace(MARKER, '<div id="weekly-report-list">' + html + '</div>');
});
