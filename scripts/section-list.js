'use strict';

/**
 * 通用「分区目录页」：页面里放
 *   <div class="section-list" data-section="Wp"></div>
 * 构建时会自动列出所有分类/标签里带该分区名的文章。
 * （「周报」页保持原来的 weekly-report-list 标记，由 weekly-index.js 处理）
 */

hexo.extend.filter.register('after_render:html', function (str) {
  var RE = /<div class="section-list" data-section="([^"]*)"><\/div>/g;
  if (!/section-list/.test(str)) return str;

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

  function postsOf(section) {
    return posts.filter(function (post) {
      var names = [];
      try {
        if (post.categories) names = names.concat(post.categories.toArray().map(function (c) { return c.name; }));
        if (post.tags) names = names.concat(post.tags.toArray().map(function (t) { return t.name; }));
      } catch (e) { /* ignore */ }
      return names.indexOf(section) >= 0;
    }).sort(function (a, b) { return b.date.valueOf() - a.date.valueOf(); });
  }

  return str.replace(RE, function (m, section) {
    var list = postsOf(section);
    var html;
    if (!list.length) {
      html = '<p>这个分区还没有文章。</p>';
    } else {
      var root = hexo.config.root || '/';
      var items = list.map(function (post) {
        var path = root.replace(/\/+$/, '') + '/' + String(post.path).replace(/^\/+/, '');
        return '<li><a href="' + esc(encodeURI(path)) + '">' +
          esc(post.date.format('YYYY-MM-DD')) + '　' + esc(post.title) + '</a></li>';
      });
      html = '<p>共 ' + list.length + ' 篇：</p><ul>' + items.join('') + '</ul>';
    }
    return '<div class="section-list" data-section="' + esc(section) + '">' + html + '</div>';
  });
});
