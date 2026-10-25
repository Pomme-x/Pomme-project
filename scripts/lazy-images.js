'use strict';

/**
 * 给页面里的图片加上懒加载属性，长文章（比如周报）打开时不会一次性加载所有大图。
 */

hexo.extend.filter.register('after_render:html', function (str) {
  if (!/<img\s/.test(str)) return str;
  return str.replace(/<img\s+([^>]*?)(\/?)>/g, function (m, attrs, slash) {
    if (/\bloading=/.test(attrs)) return m;
    return '<img loading="lazy" decoding="async" ' + attrs + slash + '>';
  });
});
