/* SpaRV project page: link buttons, tabs, comparison sliders, synced videos. */
(function () {
  'use strict';

  /* ------------------------------------------------------------ links -- */

  // YouTube / Bilibili page URL -> embeddable player URL
  function toEmbed(url) {
    var m = url.match(/(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/);
    if (m) return 'https://www.youtube.com/embed/' + m[1];
    m = url.match(/bilibili\.com\/video\/(BV\w+)/);
    if (m) return 'https://player.bilibili.com/player.html?bvid=' + m[1] + '&autoplay=0&high_quality=1';
    return url;
  }

  function applyLinks() {
    var links = window.SPARV_LINKS || {};
    document.querySelectorAll('[data-link]').forEach(function (a) {
      var key = a.dataset.link, url = links[key];
      if (!url) {
        a.classList.add('is-disabled');
        a.setAttribute('aria-disabled', 'true');
        a.removeAttribute('href');
        a.title = 'Coming soon';
        return;
      }
      a.classList.remove('is-disabled');
      a.removeAttribute('aria-disabled');
      a.removeAttribute('title');
      if (key === 'video') {
        a.href = '#video';
      } else {
        a.href = url;
        a.target = '_blank';
        a.rel = 'noopener';
      }
    });
    var box = document.getElementById('video-embed');
    if (box && links.video) {
      box.textContent = '';
      box.classList.add('has-video');
      var f = document.createElement('iframe');
      f.src = toEmbed(links.video);
      f.title = 'SpaRV overview video';
      f.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen';
      f.allowFullscreen = true;
      box.appendChild(f);
    }
  }

  /* ---------------------------------------------------- video playback -- */

  // A "group" is either one standalone <video> or a .cmp holding several
  // videos that play in sync. Groups load their sources only when near the
  // viewport and pause when they leave it (or when their tab is hidden).

  function groupVideos(g) {
    return g.tagName === 'VIDEO' ? [g] : Array.prototype.slice.call(g.querySelectorAll('video'));
  }

  function leader(g) {
    var vs = groupVideos(g);
    return vs.filter(function (v) { return v.hasAttribute('data-lead'); })[0] || vs[0];
  }

  function autoPause(v) {
    if (!v.paused) { v._autoPause = true; v.pause(); }
  }

  function refreshGroup(g) {
    var vs = groupVideos(g);
    if (!g._visible) { vs.forEach(autoPause); return; }
    vs.forEach(function (v) {
      if (v.dataset.src && v.getAttribute('src') !== v.dataset.src) {
        v.src = v.dataset.src;
        if (v.dataset.poster) v.poster = v.dataset.poster;
      }
    });
    var lead = leader(g);
    if (!lead._userPaused) lead.play().catch(function () {});
  }

  function syncGroup(g) {
    var vs = groupVideos(g), lead = leader(g);
    var rest = vs.filter(function (v) { return v !== lead; });
    vs.forEach(function (v) {
      v.addEventListener('pause', function () {
        if (v._autoPause) { v._autoPause = false; } else if (v === lead) { v._userPaused = true; }
      });
      v.addEventListener('play', function () { if (v === lead) v._userPaused = false; });
    });
    if (!rest.length) return;
    // seek on large offsets (start, loop wrap, user seek); close small drift by
    // nudging the playback rate, since seeking every few frames stutters
    function snap(v) {
      v.playbackRate = 1;
      if (Math.abs(v.currentTime - lead.currentTime) > 0.02) v.currentTime = lead.currentTime;
    }
    function nudge(v) {
      var d = lead.currentTime - v.currentTime;
      if (Math.abs(d) > 0.25) { snap(v); return; }
      v.playbackRate = 1 + Math.max(-0.15, Math.min(0.15, d * 3));
    }
    lead.addEventListener('play', function () {
      rest.forEach(function (v) { snap(v); v.play().catch(function () {}); });
    });
    lead.addEventListener('pause', function () { rest.forEach(autoPause); });
    lead.addEventListener('seeked', function () { rest.forEach(snap); });
    lead.addEventListener('timeupdate', function () { rest.forEach(nudge); });
    rest.forEach(function (v) {
      v.addEventListener('loadeddata', function () {
        snap(v);
        if (!lead.paused) v.play().catch(function () {});
      });
    });
  }

  var observer = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      e.target._visible = e.isIntersecting;
      refreshGroup(e.target);
    });
  }, { rootMargin: '200px 0px' }) : null;

  function initVideos() {
    var groups = [];
    document.querySelectorAll('.cmp').forEach(function (c) {
      if (c.querySelector('video')) groups.push(c);
    });
    document.querySelectorAll('video').forEach(function (v) {
      if (!v.closest('.cmp')) groups.push(v);
    });
    groups.forEach(function (g) {
      syncGroup(g);
      if (observer) {
        observer.observe(g);
      } else {
        g._visible = true;
        refreshGroup(g);
      }
    });
  }

  /* --------------------------------------------------- compare sliders -- */

  // .cmp holds 2 or 3 .cmp-layer children (images or videos) stacked on top of
  // each other, and one .cmp-label per layer. Layer i+1 is revealed to the
  // right of divider i.
  function initCompare(el) {
    var layers = el.querySelectorAll(':scope > .cmp-layer');
    var labels = el.querySelectorAll(':scope > .cmp-label');
    var pos = (el.dataset.split || (layers.length === 3 ? '33.3,66.7' : '50'))
      .split(',').map(Number);

    var handles = pos.map(function (p, i) {
      var h = document.createElement('div');
      h.className = 'cmp-handle';
      h.tabIndex = 0;
      h.setAttribute('role', 'slider');
      h.setAttribute('aria-label', 'Comparison divider');
      h.setAttribute('aria-valuemin', '0');
      h.setAttribute('aria-valuemax', '100');
      h.addEventListener('keydown', function (e) {
        var d = e.key === 'ArrowLeft' ? -2 : e.key === 'ArrowRight' ? 2 : 0;
        if (!d) return;
        e.preventDefault();
        set(i, pos[i] + d);
      });
      el.appendChild(h);
      return h;
    });

    function render() {
      pos.forEach(function (p, i) {
        handles[i].style.left = p + '%';
        handles[i].setAttribute('aria-valuenow', String(Math.round(p)));
        layers[i + 1].style.clipPath = 'inset(0 0 0 ' + p + '%)';
      });
      var edges = [0].concat(pos, [100]);
      Array.prototype.forEach.call(labels, function (lb, i) {
        var a = edges[i], b = edges[i + 1];
        lb.style.left = (a + b) / 2 + '%';
        lb.classList.toggle('hide', b - a < 14);
      });
    }

    function set(i, p) {
      var lo = i > 0 ? pos[i - 1] + 4 : 1;
      var hi = i < pos.length - 1 ? pos[i + 1] - 4 : 99;
      pos[i] = Math.min(hi, Math.max(lo, p));
      render();
    }

    function pct(e) {
      var r = el.getBoundingClientRect();
      return (e.clientX - r.left) / r.width * 100;
    }

    var active = -1;
    el.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      var p = pct(e);
      active = 0;
      pos.forEach(function (q, i) { if (Math.abs(q - p) < Math.abs(pos[active] - p)) active = i; });
      el.setPointerCapture(e.pointerId);
      if (e.pointerType === 'mouse') set(active, p);   // touch moves only on drag
    });
    el.addEventListener('pointermove', function (e) { if (active >= 0) set(active, pct(e)); });
    el.addEventListener('pointerup', function () { active = -1; });
    el.addEventListener('pointercancel', function () { active = -1; });
    render();
  }

  /* ----------------------------------------------------------------- tabs -- */

  // .tabs holds one .seg[data-tabs] of buttons[data-tab] and the matching
  // .pane[data-pane] elements.
  function initTabs(root) {
    var buttons = root.querySelectorAll(':scope > .seg[data-tabs] button');
    var panes = root.querySelectorAll(':scope > .pane');
    Array.prototype.forEach.call(buttons, function (b) {
      b.addEventListener('click', function () {
        Array.prototype.forEach.call(buttons, function (x) {
          x.classList.toggle('active', x === b);
          x.setAttribute('aria-selected', String(x === b));
        });
        Array.prototype.forEach.call(panes, function (p) {
          p.hidden = p.dataset.pane !== b.dataset.tab;
        });
      });
    });
  }

  /* ------------------------------------------------- switchable videos -- */

  // .vswitch fills the sources of its images and videos from templates such as
  // "videos/fastlivo2/{scene}/{base}.mp4"; each .seg[data-var] button group
  // sets one variable ({name} -> data-value of the active button, {name.attr}
  // -> its data-attr, e.g. {base.label}).
  function initSwitch(root) {
    var groups = root.querySelectorAll('.seg[data-var]');
    function fill(tpl) {
      return tpl.replace(/\{(\w+)(?:\.(\w+))?\}/g, function (_, name, attr) {
        var b = root.querySelector('.seg[data-var="' + name + '"] button.active');
        return b ? (b.dataset[attr || 'value'] || '') : '';
      });
    }
    function update() {
      root.querySelectorAll('[data-tpl]').forEach(function (el) {
        var url = fill(el.dataset.tpl);
        if (el.tagName === 'VIDEO') {        // videos load lazily, see refreshGroup
          el.dataset.src = url;
          if (el.dataset.posterTpl) el.dataset.poster = fill(el.dataset.posterTpl);
        } else if (el.getAttribute('src') !== url) {
          el.src = url;
        }
      });
      root.querySelectorAll('[data-text]').forEach(function (t) { t.textContent = fill(t.dataset.text); });
      var g = root.querySelector('.cmp');
      if (g && g._visible) refreshGroup(g);
    }
    Array.prototype.forEach.call(groups, function (seg) {
      seg.querySelectorAll('button').forEach(function (b) {
        b.addEventListener('click', function () {
          seg.querySelectorAll('button').forEach(function (x) { x.classList.toggle('active', x === b); });
          update();
        });
      });
    });
    update();
  }

  /* --------------------------------------------------------------- bibtex -- */

  function initBib() {
    document.querySelectorAll('.bib button').forEach(function (b) {
      b.addEventListener('click', function () {
        var text = b.parentElement.querySelector('pre').textContent;
        navigator.clipboard.writeText(text).then(function () {
          b.textContent = 'Copied';
          setTimeout(function () { b.textContent = 'Copy'; }, 1500);
        });
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyLinks();
    document.querySelectorAll('.cmp').forEach(initCompare);
    document.querySelectorAll('.tabs').forEach(initTabs);
    document.querySelectorAll('.vswitch').forEach(initSwitch);
    initVideos();
    initBib();
  });
})();
