'use strict';

/**
 * 「周报」目录页：构建时自动列出所有分类/标签里带「周报」的文章。
 * 新上传的周报只要分类是「周报」，就会自动出现在 /周报/ 列表里。
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

  weekly.sort(function (a, b) { return b.date.valueOf() - a.date.valueOf(); });

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
