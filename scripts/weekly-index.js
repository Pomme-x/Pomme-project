'use strict';

/**
 * 「周报」目录页：构建时自动列出所有分类/标签里带「周报」的文章。
 * 排序规则：先按标题里的「第 X 周」从新到旧（第八周 → 第七周 → …），
 * 同一周再按日期从新到旧。
 */

hexo.extend.filter.register('after_render:html', function (str) {
  var MARKER = /<div id="weekly-report-list">[\s\S]*?<\/div>/;
  if (!MARKER.test(str)) return str;

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var CN = { '零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
             '五': 5, '六': 6, '七': 7, '八': 8, '九': 9 };

  function cnToInt(s) {
    if (/^[0-9]+$/.test(s)) return parseInt(s, 10);
    var result = 0, tmp = 0;
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (c === '百') { result += (tmp || 1) * 100; tmp = 0; }
      else if (c === '十') { result += (tmp || 1) * 10; tmp = 0; }
      else if (CN[c] !== undefined) { tmp = CN[c]; }
    }
    result += tmp;
    return result;
  }

  // 取标题里所有「第 X 周」的最大周数（「第五周周末及第六周」算 6）
  function weekRank(title) {
    var re = /第\s*([0-9零〇一二两三四五六七八九十百]+)\s*周/g;
    var m, best = -1;
    while ((m = re.exec(String(title || '')))) {
      var n = cnToInt(m[1]);
      if (n > best) best = n;
    }
    return best;
  }

  var posts = [];
  try {
    posts = hexo.locals.get('posts').toArray();
  } catch (e) {
    posts = [];
  }

  var weekly = posts.filter(function (post) {
    var names = [];
    try {
      if (post.categories) names = names.concat(post.categories.toArray().map(function (c) { return c.name; }));
      if (post.tags) names = names.concat(post.tags.toArray().map(function (t) { return t.name; }));
    } catch (e) { /* ignore */ }
    return names.indexOf('周报') >= 0;
  });

  weekly.sort(function (a, b) {
    var wa = weekRank(a.title), wb = weekRank(b.title);
    if (wa !== wb) return wb - wa;
    return b.date.valueOf() - a.date.valueOf();
  });

  var html;
  if (!weekly.length) {
    html = '<p>还没有周报。用「Pomme 博客小工具」上传 PDF，或把文章分类设为「周报」即可。</p>';
  } else {
    var root = hexo.config.root || '/';
    var items = weekly.map(function (post) {
      var path = (root.replace(/\/+$/, '') + '/' + String(post.path).replace(/^\/+/, ''));
      var url = encodeURI(path);
      var date = post.date.format('YYYY-MM-DD');
      return '<li><a href="' + esc(url) + '">' + esc(date) + '　' + esc(post.title) + '</a></li>';
    });
    html = '<p>共 ' + weekly.length + ' 篇：</p><ul>' + items.join('') + '</ul>';
  }

  return str.replace(MARKER, '<div id="weekly-report-list">' + html + '</div>');
});
