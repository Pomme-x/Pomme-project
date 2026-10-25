---
title: 周报
date: 2026-10-25 20:00:00
type: page
---

<div id="weekly-report-list">加载中……</div>

<noscript>这个列表需要浏览器 JavaScript；也可以直接看 <a href="https://github.com/xunshichen-2008/Pomme-project/tree/main/source/%E5%91%A8%E6%8A%A5">GitHub 上的 source/周报 目录</a>。</noscript>

<script>
(function () {
  var box = document.getElementById('weekly-report-list');
  if (!box) return;
  var api = 'https://api.github.com/repos/xunshichen-2008/Pomme-project/contents/source/' +
            encodeURIComponent('周报') + '?ref=main';
  fetch(api)
    .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function (files) {
      if (!Array.isArray(files)) throw new Error('unexpected response');
      var pdfs = files.filter(function (f) {
        return f.type === 'file' && /\.pdf$/i.test(f.name);
      });
      if (!pdfs.length) {
        box.innerHTML = '<p>还没有周报。把 PDF 上传到 <code>source/周报/</code> 后，这里会自动列出来。</p>';
        return;
      }
      pdfs.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
      var html = '<ul>';
      pdfs.forEach(function (f) {
        var sitePath = '/Pomme-project/' + encodeURI(f.path.replace(/^source\//, ''));
        var mb = (f.size / 1048576).toFixed(2);
        html += '<li><a href="' + sitePath + '" target="_blank" rel="noopener">' +
                f.name + '</a>（' + mb + ' MB）</li>';
      });
      box.innerHTML = html + '</ul>';
    })
    .catch(function (e) {
      box.innerHTML = '<p>列表加载失败：' + e.message +
        '<br>可以直接看 <a href="https://github.com/xunshichen-2008/Pomme-project/tree/main/source/%E5%91%A8%E6%8A%A5">GitHub 目录</a>。</p>';
    });
})();
</script>
