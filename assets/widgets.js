/* Bit by Bit — interactive figures.
   Every element with data-widget="name" is handed to WIDGETS[name](element).
   No dependencies; each widget renders its own markup. */
(function () {
  'use strict';

  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var SVGNS = 'http://www.w3.org/2000/svg';
  var WIDGETS = {};

  // ---------------------------------------------------------------- helpers

  function h(tag, attrs) {
    var node = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'text') node.textContent = attrs[k];
      else if (k === 'html') node.innerHTML = attrs[k];
      else if (k.slice(0, 2) === 'on') node.addEventListener(k.slice(2), attrs[k]);
      else node.setAttribute(k, attrs[k]);
    }
    for (var i = 2; i < arguments.length; i++) {
      var kid = arguments[i];
      if (kid == null) continue;
      node.appendChild(typeof kid === 'string' ? document.createTextNode(kid) : kid);
    }
    return node;
  }

  function s(tag, attrs) {
    var node = document.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) {
      if (k === 'text') node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    }
    for (var i = 2; i < arguments.length; i++) if (arguments[i]) node.appendChild(arguments[i]);
    return node;
  }

  function btn(label, onclick, cls) {
    return h('button', { type: 'button', class: 'btn ' + (cls || ''), onclick: onclick, text: label });
  }

  function frame(el, title, hint) {
    el.classList.add('widget');
    el.innerHTML = '';
    el.appendChild(h('div', { class: 'w-title', text: title }));
    if (hint) el.appendChild(h('p', { class: 'w-hint', html: hint }));
    return el;
  }

  function pad(str, n, c) { str = String(str); while (str.length < n) str = (c || '0') + str; return str; }

  var CODEBOOK5 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ .,?!~'.split('');
  function cbLabel(ch) { return ch === ' ' ? '␣' : ch; }

  // ---------------------------------------------------------------- stepper
  // <figure data-widget="stepper"> with an <svg> whose children carry data-show,
  // and an <ol class="steps"> with one <li> per step.
  //   data-show="3"    visible from step 3 onward
  //   data-show="2-4"  visible for steps 2..4
  //   data-show="=2"   visible only on step 2
  //   combine with commas: "=1,4"

  function parseShow(spec, total) {
    var on = {};
    spec.split(',').forEach(function (part) {
      part = part.trim();
      var m;
      if ((m = /^=(\d+)$/.exec(part))) on[+m[1]] = true;
      else if ((m = /^(\d+)-(\d+)$/.exec(part))) for (var i = +m[1]; i <= +m[2]; i++) on[i] = true;
      else if ((m = /^(\d+)$/.exec(part))) for (var j = +m[1]; j <= total; j++) on[j] = true;
    });
    return on;
  }

  WIDGETS.stepper = function (fig) {
    var items = fig.querySelectorAll('.steps > li');
    var total = items.length;
    if (!total) return;
    var targets = Array.prototype.map.call(fig.querySelectorAll('[data-show]'), function (node) {
      return { node: node, on: parseShow(node.getAttribute('data-show'), total), shown: null };
    });
    var cur = 1;

    var prev = btn('◀ Back', function () { go(cur - 1); }, 'ghost small');
    var next = btn('Next ▶', function () { go(cur + 1); }, 'small');
    var count = h('span', { class: 'count' });
    var dots = h('div', { class: 'step-dots' });
    for (var i = 1; i <= total; i++) (function (n) {
      dots.appendChild(h('button', { type: 'button', 'aria-label': 'Step ' + n, onclick: function () { go(n); } }));
    })(i);
    var controls = h('div', { class: 'step-controls' }, prev, count, next, dots);
    var list = fig.querySelector('.steps');
    list.parentNode.insertBefore(controls, list);

    function go(n) {
      cur = Math.max(1, Math.min(total, n));
      Array.prototype.forEach.call(items, function (li, idx) { li.classList.toggle('current', idx + 1 === cur); });
      targets.forEach(function (t) {
        var visible = !!t.on[cur];
        t.node.classList.toggle('is-hidden', !visible);
        if (visible && t.shown === false && !reduced) {
          Array.prototype.forEach.call(t.node.querySelectorAll('animate, animateMotion, animateTransform'), function (a) {
            if (a.getAttribute('begin') === 'indefinite' && a.beginElement) a.beginElement();
          });
        }
        t.shown = visible;
      });
      // animations that belong to the current step even if their parent was already visible
      Array.prototype.forEach.call(fig.querySelectorAll('[data-play="' + cur + '"]'), function (a) {
        if (!reduced && a.beginElement) a.beginElement();
      });
      count.textContent = 'Step ' + cur + ' of ' + total;
      prev.disabled = cur === 1;
      next.disabled = cur === total;
      next.textContent = cur === total ? 'Done' : 'Next ▶';
      Array.prototype.forEach.call(dots.children, function (d, idx) { d.classList.toggle('on', idx + 1 === cur); });
    }
    fig.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { go(cur + 1); e.preventDefault(); }
      if (e.key === 'ArrowLeft') { go(cur - 1); e.preventDefault(); }
    });
    targets.forEach(function (t) { t.shown = true; });
    go(1);
  };

  // ---------------------------------------------------------------- ch1: mind-reading halving game

  WIDGETS.halving = function (el) {
    frame(el, 'I can guess your letter in five questions',
      'Pick any symbol below and keep it secret. Each time, tell me which half it’s in. ' +
      'Each answer is one bit: <b>left = 0</b>, <b>right = 1</b>.');
    var grid = h('div', { style: 'display:grid;grid-template-columns:repeat(16,1fr);gap:4px;margin:10px 0;' });
    var cells = CODEBOOK5.map(function (ch, i) {
      var c = h('div', { style: 'font-family:var(--slab);font-weight:700;text-align:center;padding:6px 0;border-radius:6px;' +
        'border:1.5px solid var(--line);transition:all .25s;font-size:110%;', text: cbLabel(ch) });
      grid.appendChild(c);
      return c;
    });
    var answers = h('div', { class: 'row', style: 'min-height:34px' });
    var status = h('p', { style: 'margin:6px 0;font-size:105%;' });
    var left = btn('◀ It’s in the LEFT half', function () { answer(0); });
    var right = btn('It’s in the RIGHT half ▶', function () { answer(1); });
    var again = btn('Play again', reset, 'ghost');
    el.appendChild(grid);
    el.appendChild(h('div', { class: 'row' }, left, right, again));
    el.appendChild(status);
    el.appendChild(answers);

    var lo, hi, bits;
    function paint() {
      var mid = (lo + hi) / 2;
      cells.forEach(function (c, i) {
        var inRange = i >= lo && i < hi;
        c.style.opacity = inRange ? '1' : '0.18';
        c.style.background = !inRange ? 'transparent' : (hi - lo > 1 ? (i < mid ? 'var(--tint-red)' : 'var(--tint-green)') : 'var(--yellow)');
        c.style.borderColor = inRange ? 'var(--ink)' : 'var(--line)';
      });
      answers.innerHTML = '';
      bits.forEach(function (b, i) {
        answers.appendChild(h('span', { style: 'display:inline-flex;align-items:center;gap:6px;margin-right:10px;font-family:var(--mono)' },
          h('i', { class: 'dot b' + b, style: 'width:18px;height:18px' }), 'Q' + (i + 1) + ': ' + (b ? 'right → 1' : 'left → 0')));
      });
    }
    function answer(b) {
      if (hi - lo <= 1) return;
      var mid = (lo + hi) / 2;
      if (b) lo = mid; else hi = mid;
      bits.push(b);
      update();
    }
    function update() {
      paint();
      var done = hi - lo === 1;
      left.disabled = right.disabled = done;
      if (done) {
        var code = bits.join('');
        status.innerHTML = 'Your symbol is <b style="font-size:130%">' + cbLabel(CODEBOOK5[lo]) +
          '</b>. Your five answers spell <code>' + code + '</code>, which is the number <b>' + lo + '</b> in binary.';
      } else {
        status.innerHTML = '<b>' + (hi - lo) + '</b> symbols still possible. Question ' + (bits.length + 1) +
          ': is yours in the <span style="color:var(--red)">left (red)</span> or <span style="color:var(--green)">right (green)</span> half?';
      }
    }
    function reset() { lo = 0; hi = 32; bits = []; update(); }
    reset();
  };

  // ---------------------------------------------------------------- ch1/ch6: bit flipper

  WIDGETS.bits = function (el) {
    var n = +(el.getAttribute('data-bits') || 5);
    var mode = el.getAttribute('data-mode') || (n === 5 ? 'codebook' : 'ascii');
    frame(el, n + ' switches, ' + Math.pow(2, n) + ' possibilities',
      'Click the lights to flip bits. Each position is worth twice the one to its right.');
    var values = [];
    for (var i = 0; i < n; i++) values.push(0);
    var row = h('div', { style: 'display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:14px 0;' });
    var lamps = values.map(function (_, i) {
      var weight = Math.pow(2, n - 1 - i);
      var lamp = h('button', {
        type: 'button', 'aria-label': 'bit worth ' + weight,
        style: 'width:52px;height:52px;border-radius:50%;border:3px solid var(--ink);cursor:pointer;font-family:var(--mono);' +
          'font-size:120%;font-weight:700;color:#fff;transition:background .2s, box-shadow .2s;',
        onclick: function () { values[i] = 1 - values[i]; update(); }
      });
      var col = h('div', { style: 'display:flex;flex-direction:column;align-items:center;gap:4px;' },
        h('span', { style: 'font-family:var(--mono);color:var(--muted);font-size:90%', text: String(weight) }), lamp);
      row.appendChild(col);
      return lamp;
    });
    var sum = h('div', { class: 'out', style: 'text-align:center;font-size:110%' });
    var controls = h('div', { class: 'row', style: 'justify-content:center' },
      btn('− 1', function () { set(val() - 1); }, 'ghost small'),
      btn('+ 1', function () { set(val() + 1); }, 'small'),
      btn('Count all the way up', countUp, 'ghost small'),
      btn('Clear', function () { set(0); }, 'ghost small'));
    el.appendChild(row);
    el.appendChild(sum);
    el.appendChild(controls);

    function val() { return values.reduce(function (acc, b) { return acc * 2 + b; }, 0); }
    function set(v) {
      var max = Math.pow(2, n);
      v = ((v % max) + max) % max;
      for (var i = n - 1; i >= 0; i--) { values[i] = v & 1; v = v >> 1; }
      update();
    }
    var timer = null;
    function countUp() {
      if (timer) { clearInterval(timer); timer = null; return; }
      set(0);
      timer = setInterval(function () {
        if (val() === Math.pow(2, n) - 1) { clearInterval(timer); timer = null; return; }
        set(val() + 1);
      }, reduced ? 50 : 350);
    }
    function update() {
      lamps.forEach(function (l, i) {
        l.textContent = values[i];
        l.style.background = values[i] ? 'var(--green)' : 'var(--red)';
        l.style.boxShadow = values[i] ? '0 0 14px var(--green)' : 'none';
      });
      var parts = [];
      values.forEach(function (b, i) { if (b) parts.push(Math.pow(2, n - 1 - i)); });
      var v = val();
      var extra = '';
      if (mode === 'codebook') extra = '   →   symbol <b>' + cbLabel(CODEBOOK5[v]) + '</b>';
      if (mode === 'ascii') {
        var ch = v >= 33 && v < 127 ? String.fromCharCode(v) : (v === 32 ? '␣ (space)' : (v < 32 ? 'control code' : (v === 127 ? 'DEL' : 'beyond ASCII')));
        extra = '   →   hex <b>' + pad(v.toString(16).toUpperCase(), 2) + '</b>   →   ASCII <b>' + ch + '</b>';
      }
      sum.innerHTML = '<b>' + values.join('') + '</b>   =   ' + (parts.length ? parts.join(' + ') : '0') + '   =   <b>' + v + '</b>' + extra;
    }
    update();
  };

  // ---------------------------------------------------------------- ch2: clock drift playground
  // Mirrors labs/ch02/wire.py: build a signal, let Bob sample it with a skewed clock.

  WIDGETS.drift = function (el) {
    var STEPS = 20, TH = 2;
    frame(el, 'Bob’s clock is off. Can he still read Alice?',
      'Drag the slider to make Bob’s clock run fast or slow, and switch between the three ways of sending. ' +
      'Teal ticks landed in the right place; red ticks read the wrong thing.');
    var input = h('input', { type: 'text', value: 'HI BOB', maxlength: '8', size: '10', 'aria-label': 'message' });
    var slider = h('input', { type: 'range', min: '-15', max: '15', step: '0.5', value: '4', 'aria-label': 'clock error' });
    var driftOut = h('b', { style: 'min-width:60px;display:inline-block' });
    var scheme = h('select', { 'aria-label': 'scheme' },
      h('option', { value: 'plain', text: 'Plain: hold each bit' }),
      h('option', { value: 'letters', text: 'Start pulse on every letter' }),
      h('option', { value: 'manchester', text: 'Manchester: flip in every bit' }));
    var holder = h('div');
    var result = h('div', { class: 'out' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Message ', input), h('label', {}, 'Scheme ', scheme)));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Bob’s clock: '), slider, driftOut));
    el.appendChild(holder);
    el.appendChild(result);

    function lvl(b) { return b === '1' ? 5 : -5; }
    function rep(v, n, arr) { for (var i = 0; i < n; i++) arr.push(v); }
    function read(v) { return v > TH ? '1' : (v < -TH ? '0' : '?'); }
    function edge(sig, start) {
      for (var i = start || 0; i < sig.length; i++) if (Math.abs(sig[i]) > TH) return i;
      return -1;
    }
    function build(bits, kind) {
      var sig = []; rep(0, STEPS, sig);
      if (kind === 'plain') { bits.split('').forEach(function (b) { rep(lvl(b), STEPS, sig); }); rep(0, STEPS, sig); }
      if (kind === 'letters') {
        for (var i = 0; i < bits.length; i += 5) {
          rep(5, STEPS, sig);
          bits.slice(i, i + 5).split('').forEach(function (b) { rep(lvl(b), STEPS, sig); });
          rep(0, STEPS, sig);
        }
      }
      if (kind === 'manchester') {
        bits.split('').forEach(function (b) {
          rep(b === '1' ? -5 : 5, STEPS / 2, sig); rep(b === '1' ? 5 : -5, STEPS / 2, sig);
        });
        rep(0, STEPS, sig);
      }
      return sig;
    }
    function receive(sig, kind, drift) {
      var bt = STEPS * (1 + drift / 100), bits = '', samples = [];
      if (kind === 'plain') {
        var t = edge(sig) + bt / 2;
        while (t < sig.length) { samples.push(t | 0); bits += read(sig[t | 0]); t += bt; }
        bits = bits.replace(/\?+$/, '');
        samples = samples.slice(0, bits.length);
      } else if (kind === 'letters') {
        var pos = 0, e;
        while ((e = edge(sig, pos)) >= 0) {
          for (var k = 1; k <= 5; k++) {
            var tt = (e + (k + 0.5) * bt) | 0;
            if (tt >= sig.length) break;
            samples.push(tt); bits += read(sig[tt]);
          }
          pos = (e + 6 * bt) | 0;
          while (pos < sig.length && Math.abs(sig[pos]) > TH) pos++;
        }
      } else {
        var mid = edge(sig) + bt / 2;
        while (mid + bt / 4 < sig.length) {
          var a = (mid - bt / 4) | 0, b = (mid + bt / 4) | 0;
          var x = read(sig[a]), y = read(sig[b]);
          if (x === '?' && y === '?') break;
          samples.push(a, b);
          bits += (x === '0' && y === '1') ? '1' : (x === '1' && y === '0') ? '0' : '?';
          for (var i = a; i < b; i++) if ((sig[i] > 0) !== (sig[i + 1] > 0)) { mid = i + 0.5; break; }
          mid += bt;
        }
      }
      return { bits: bits, samples: samples };
    }
    function toText(bits) {
      var out = '';
      for (var i = 0; i + 5 <= bits.length; i += 5) {
        var c = bits.slice(i, i + 5);
        out += /^[01]{5}$/.test(c) ? CODEBOOK5[parseInt(c, 2)] : '�';
      }
      return out;
    }
    function draw() {
      var text = input.value.toUpperCase().split('').filter(function (c) { return CODEBOOK5.indexOf(c) >= 0; }).join('') || 'HI';
      var bits = text.split('').map(function (c) { return pad(CODEBOOK5.indexOf(c).toString(2), 5); }).join('');
      var kind = scheme.value, drift = +slider.value;
      driftOut.textContent = (drift > 0 ? '+' : '') + drift + '% ' + (drift > 0 ? '(slow)' : drift < 0 ? '(fast)' : '(perfect)');
      var sig = build(bits, kind);
      var rx = receive(sig, kind, drift);
      var W = 700, H = 170, x0 = 10, mid = 80, amp = 34, dx = (W - 2 * x0) / sig.length;
      var svg = s('svg', { class: 'dia', viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'signal and Bob’s samples' });
      svg.appendChild(s('rect', { x: 0, y: 0, width: W, height: H, rx: 8, class: 'f-card' }));
      [-amp, 0, amp].forEach(function (d) {
        svg.appendChild(s('line', { x1: x0, x2: W - x0, y1: mid + d, y2: mid + d, class: 'grid', 'stroke-dasharray': d ? '4 4' : '0' }));
      });
      var d = 'M' + x0 + ',' + (mid - sig[0] / 5 * amp);
      for (var i = 0; i < sig.length; i++) {
        var y = mid - sig[i] / 5 * amp, x = x0 + i * dx;
        d += ' L' + x.toFixed(1) + ',' + y + ' L' + (x + dx).toFixed(1) + ',' + y;
      }
      svg.appendChild(s('path', { d: d, class: 'line s-navy', 'stroke-width': 2.5 }));
      // which samples were right?
      var perBit = kind === 'manchester' ? 2 : 1;
      rx.samples.forEach(function (t, idx) {
        var bitIdx = Math.floor(idx / perBit);
        var ok = rx.bits[bitIdx] === bits[bitIdx];
        var x = x0 + (t + 0.5) * dx;
        var cls = ok ? 's-teal' : 's-red';
        svg.appendChild(s('line', { x1: x, x2: x, y1: 30, y2: 132, class: 'line thin dot-line ' + cls }));
        svg.appendChild(s('path', { d: 'M' + (x - 5) + ',142 L' + (x + 5) + ',142 L' + x + ',134 Z', class: ok ? 'f-teal' : 'f-red' }));
      });
      svg.appendChild(s('text', { x: x0, y: 164, class: 'xs muted', text: '▲ = moments when Bob reads the wire (his clock)' }));
      holder.innerHTML = '';
      holder.appendChild(svg);
      var got = toText(rx.bits);
      var wrong = 0;
      for (var j = 0; j < bits.length; j++) if (rx.bits[j] !== bits[j]) wrong++;
      var shown = '';
      for (var k = 0; k < Math.max(got.length, text.length); k++) {
        var c = got[k] || '·';
        shown += c === text[k] ? c : '<span class="bad">' + c + '</span>';
      }
      result.innerHTML = 'Alice sent <b>' + text + '</b>  →  Bob read <b>' + shown + '</b>   ' +
        (wrong ? '<span class="bad">' + wrong + ' of ' + bits.length + ' bits wrong</span>' : '<span class="good">every bit correct</span>');
    }
    [input, slider, scheme].forEach(function (c) { c.addEventListener('input', draw); });
    draw();
  };

  // ---------------------------------------------------------------- ch3: framing and escaping
  // Mirrors labs/ch03/framing.py.

  function chip(label, kind) {
    var colours = { ctrl: 'var(--tint-red)', esc: 'var(--tint-purple)', data: 'var(--tint-yellow)', bad: 'var(--red)' };
    var border = { ctrl: 'var(--red)', esc: 'var(--purple)', data: 'var(--line)', bad: 'var(--red)' };
    return h('span', {
      text: label,
      style: 'display:inline-block;min-width:22px;text-align:center;padding:4px 5px;margin:2px 1px;border-radius:4px;' +
        'font-family:var(--mono);font-weight:700;background:' + colours[kind] + ';border:1.5px solid ' + border[kind] +
        ';color:' + (kind === 'bad' ? '#fff' : 'var(--ink)')
    });
  }

  function parseFrames(stream) {
    var msgs = [], errs = [], inside = false, cur = '', i = 0;
    while (i < stream.length) {
      var c = stream[i];
      if (c !== '~') { if (inside) cur += c; i++; continue; }
      var code = stream.slice(i, i + 2);
      if (code === '~S') { if (inside) errs.push('a new ~S arrived before ~E; dropped “' + cur + '”'); inside = true; cur = ''; }
      else if (code === '~E' && inside) { msgs.push(cur); inside = false; }
      else if (code === '~~' && inside) cur += '~';
      else { errs.push('unexpected “' + code + '”'); inside = false; }
      i += 2;
    }
    if (inside) errs.push('message never ended: “' + cur + '” is still waiting for ~E');
    return { msgs: msgs, errs: errs };
  }

  WIDGETS.framing = function (el) {
    frame(el, 'Frame it yourself',
      'Type a message and watch it get wrapped in <b>~S</b> … <b>~E</b>. Try putting a <b>~</b> in it, or even “~E”. ' +
      'Then untick “escape” to see what goes wrong without escaping.');
    var input = h('input', { type: 'text', value: 'SEE YOU ~ SOON', size: '28', 'aria-label': 'message' });
    var esc = h('input', { type: 'checkbox', checked: 'checked', id: 'esc-' + Math.random().toString(36).slice(2) });
    var wire = h('div', { style: 'margin:10px 0;line-height:2.2' });
    var bob = h('div', { class: 'out' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Alice types ', input),
      h('label', { for: esc.id }, esc, ' escape ~ as ~~')));
    el.appendChild(h('div', { style: 'font-size:90%;color:var(--muted);margin-top:10px' }, 'On the wire:'));
    el.appendChild(wire);
    el.appendChild(bob);
    function draw() {
      var text = input.value.toUpperCase().split('').filter(function (c) { return CODEBOOK5.indexOf(c) >= 0; }).join('');
      var body = esc.checked ? text.replace(/~/g, '~~') : text;
      var stream = '~S' + body + '~E';
      wire.innerHTML = '';
      wire.appendChild(chip('~S', 'ctrl'));
      for (var i = 0; i < body.length; i++) {
        if (body[i] === '~' && esc.checked) { wire.appendChild(chip('~~', 'esc')); i++; }
        else if (body[i] === '~') wire.appendChild(chip('~', 'bad'));
        else wire.appendChild(chip(body[i] === ' ' ? '␣' : body[i], 'data'));
      }
      wire.appendChild(chip('~E', 'ctrl'));
      var r = parseFrames(stream);
      var ok = r.msgs.length === 1 && r.msgs[0] === text && !r.errs.length;
      bob.innerHTML = 'Bob’s Chatterbox prints: ' + (r.msgs.length ? r.msgs.map(function (m) { return '<b>“' + m + '”</b>'; }).join(', ') : '<i>nothing</i>') +
        (r.errs.length ? '<br><span class="bad">Problems: ' + r.errs.join('; ') + '</span>' : '') +
        '<br>' + (ok ? '<span class="good">Exactly what Alice typed.</span>' : '<span class="bad">That’s not what Alice typed!</span>');
    }
    input.addEventListener('input', draw);
    esc.addEventListener('change', draw);
    draw();
  };

  // ---------------------------------------------------------------- ch4: be the operating system

  WIDGETS.mailroom = function (el) {
    frame(el, 'You are the operating system',
      'Messages are arriving from the wire. Read the <b>TO</b> line and drop each one into the right program’s mailbox. ' +
      'If that program isn’t running, there’s nowhere to put it: throw it away.');
    var ALL = ['CHAT', 'SERVE', 'FETCH#1', 'FETCH#2', 'GAME'];
    var BODIES = {
      CHAT: [['FROM: CHAT', 'ARE YOU THERE?'], ['FROM: CHAT', 'LOL']],
      SERVE: [['FROM: FETCH#7', 'GET', 'REPORT'], ['FROM: STORE#3', 'PUT', 'NOTES', '…']],
      'FETCH#1': [['FROM: SERVE', 'OK', 'SCHEDULE', 'CLASS PRESENTATIONS…'], ['FROM: SERVE', 'NOT FOUND', 'HOMEWORK']],
      'FETCH#2': [['FROM: SERVE', 'OK', 'REPORT', 'BOOK REPORT: TREASURE ISLAND…']],
      GAME: [['FROM: GAME', 'MOVE', 'E2 E4']]
    };
    var running, current, round = 0, score = 0, ROUNDS = 6;
    var status = h('div', { class: 'row', style: 'font-size:95%' });
    var envelope = h('div', { style: 'font-family:var(--mono);background:var(--tint-yellow);border:2px solid var(--ink);' +
      'border-radius:8px;padding:10px 14px;margin:10px 0;min-height:70px;white-space:pre;line-height:1.5;overflow-x:auto' });
    var boxes = h('div', { class: 'row' });
    var feedback = h('p', { style: 'margin:6px 0;min-height:1.5em' });
    el.appendChild(status);
    el.appendChild(envelope);
    el.appendChild(boxes);
    el.appendChild(feedback);

    function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
    function newRound() {
      running = ['CHAT'].concat(ALL.slice(1).filter(function () { return Math.random() < 0.55; }));
      var to = pick(ALL);
      current = { to: to, body: pick(BODIES[to]) };
      envelope.innerHTML = '';
      envelope.appendChild(h('div', { html: '<b style="background:var(--tint-blue);padding:1px 4px;border-radius:3px">TO: ' + to + '</b>' }));
      current.body.forEach(function (l) { envelope.appendChild(h('div', { text: l })); });
      boxes.innerHTML = '';
      ALL.forEach(function (p) {
        var on = running.indexOf(p) >= 0;
        var b = btn('📬 ' + p, function () { choose(p); }, on ? '' : 'ghost');
        if (!on) { b.disabled = true; b.title = p + ' is not running'; b.textContent = '💤 ' + p; }
        boxes.appendChild(b);
      });
      boxes.appendChild(btn('🗑 throw away', function () { choose(null); }, 'ghost'));
      status.innerHTML = 'Round <b>' + (round + 1) + '</b> of ' + ROUNDS + ' · score <b>' + score + '</b> · running right now: <b>' +
        running.join(', ') + '</b>';
    }
    function choose(p) {
      var right = running.indexOf(current.to) >= 0 ? current.to : null;
      if (p === right) {
        score++;
        feedback.innerHTML = '<span class="good">Correct!</span> ' + (right ? 'Delivered to ' + right + '.' :
          current.to + ' isn’t running, so the message is dropped. Whoever sent it will eventually time out.');
      } else {
        feedback.innerHTML = '<span class="bad">Not quite.</span> ' + (right ? 'The TO line says ' + right + ', and it’s running.' :
          current.to + ' isn’t running, so this one had to be thrown away.');
      }
      round++;
      if (round >= ROUNDS) {
        status.innerHTML = 'Final score: <b>' + score + ' / ' + ROUNDS + '</b>';
        envelope.textContent = score === ROUNDS ? 'Perfect. You’d make a fine operating system.' : 'Good effort! Want another shift?';
        boxes.innerHTML = '';
        boxes.appendChild(btn('Play again', function () { round = 0; score = 0; feedback.innerHTML = ''; newRound(); }));
      } else {
        setTimeout(newRound, 250);
      }
    }
    newRound();
  };

  // ---------------------------------------------------------------- ch5: text -> UTF-8 bytes

  WIDGETS.utf8 = function (el) {
    frame(el, 'Text is just bytes',
      'Type anything, in any language, emoji included, and see the bytes your computer actually stores and sends. ' +
      'Plain English letters take one byte each. Everything else takes two, three or four.');
    var input = h('input', { type: 'text', value: 'Hi Bob! café 👋', size: '26', 'aria-label': 'text' });
    var table = h('div', { style: 'display:flex;flex-wrap:wrap;gap:6px;margin-top:12px' });
    var total = h('div', { class: 'out', style: 'margin-top:10px' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Text: ', input)));
    el.appendChild(table);
    el.appendChild(total);
    var enc = window.TextEncoder ? new TextEncoder() : null;
    var colours = ['', 'var(--tint-teal)', 'var(--tint-yellow)', 'var(--tint-orange)', 'var(--tint-red)'];
    function draw() {
      table.innerHTML = '';
      if (!enc) { total.textContent = 'Your browser can’t show UTF-8 bytes.'; return; }
      var all = [];
      Array.from(input.value).forEach(function (ch) {
        var bytes = Array.from(enc.encode(ch));
        all = all.concat(bytes);
        var cp = ch.codePointAt(0);
        table.appendChild(h('div', {
          style: 'border:1.5px solid var(--line);border-radius:8px;padding:6px 8px;text-align:center;background:' + colours[bytes.length] + ';min-width:54px'
        },
          h('div', { style: 'font-size:150%;font-family:var(--slab);font-weight:700', text: ch === ' ' ? '␣' : ch }),
          h('div', { style: 'font-family:var(--mono);font-size:75%;color:var(--muted)', text: 'U+' + pad(cp.toString(16).toUpperCase(), 4) }),
          h('div', { style: 'font-family:var(--mono);font-weight:700', text: bytes.map(function (b) { return pad(b.toString(16).toUpperCase(), 2); }).join(' ') })));
      });
      total.innerHTML = '<b>' + Array.from(input.value).length + '</b> characters → <b>' + all.length + '</b> bytes:  ' +
        all.map(function (b) { return pad(b.toString(16).toUpperCase(), 2); }).join(' ');
    }
    input.addEventListener('input', draw);
    draw();
  };

  // ---------------------------------------------------------------- ch5: pixel editor

  WIDGETS.pixels = function (el) {
    frame(el, 'Draw with bytes',
      'Click squares to paint them. Each row of 8 pixels is exactly one byte: dark = 1, light = 0. ' +
      'Underneath, the same 8 bytes are read as if they were text.');
    var PRESETS = {
      smiley: [0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C],
      heart: [0x00, 0x66, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C, 0x18],
      invader: [0x18, 0x3C, 0x7E, 0xDB, 0xFF, 0x24, 0x5A, 0xA5],
      'HELLO!!!': [0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x21, 0x21, 0x21]
    };
    var rows = PRESETS.smiley.slice();
    var wrap = h('div', { style: 'display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start' });
    var grid = h('div', { style: 'display:grid;grid-template-columns:repeat(8,30px);gap:2px;touch-action:none' });
    var cells = [];
    var painting = null;
    for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++) (function (r, c) {
      var cell = h('div', { style: 'width:30px;height:30px;border-radius:3px;cursor:pointer;border:1px solid var(--line)' });
      cell.addEventListener('pointerdown', function (e) {
        e.preventDefault();
        painting = (rows[r] >> (7 - c)) & 1 ? 0 : 1;
        setPixel(r, c, painting);
      });
      cell.addEventListener('pointerenter', function () { if (painting !== null) setPixel(r, c, painting); });
      grid.appendChild(cell);
      cells.push(cell);
    })(r, c);
    document.addEventListener('pointerup', function () { painting = null; });
    var bytesOut = h('div', { style: 'font-family:var(--mono);line-height:32px;font-size:95%' });
    var textOut = h('div', { class: 'out', style: 'margin-top:12px' });
    wrap.appendChild(grid);
    wrap.appendChild(bytesOut);
    el.appendChild(wrap);
    el.appendChild(textOut);
    var presets = h('div', { class: 'row' });
    Object.keys(PRESETS).forEach(function (k) {
      presets.appendChild(btn(k, function () { rows = PRESETS[k].slice(); draw(); }, 'ghost small'));
    });
    presets.appendChild(btn('clear', function () { rows = [0, 0, 0, 0, 0, 0, 0, 0]; draw(); }, 'ghost small'));
    el.appendChild(presets);

    function setPixel(r, c, v) {
      if (v) rows[r] |= (1 << (7 - c)); else rows[r] &= ~(1 << (7 - c));
      draw();
    }
    function draw() {
      cells.forEach(function (cell, i) {
        var on = (rows[Math.floor(i / 8)] >> (7 - i % 8)) & 1;
        cell.style.background = on ? 'var(--ink)' : 'var(--tint-yellow)';
      });
      bytesOut.innerHTML = rows.map(function (b) {
        return pad(b.toString(2), 8) + '  <b>' + pad(b.toString(16).toUpperCase(), 2) + '</b>';
      }).join('<br>');
      var asText = rows.map(function (b) {
        if (b >= 33 && b < 127) return String.fromCharCode(b);
        if (b === 32) return '␣';
        return '<span style="color:var(--muted)">·</span>';
      }).join('');
      textOut.innerHTML = 'The same 8 bytes, read as ASCII text: <b style="font-size:120%">' + asText + '</b>' +
        '<br><span style="color:var(--muted);font-size:90%">(· = a byte that isn’t a printable character)</span>';
    }
    draw();
  };

  // ---------------------------------------------------------------- ch6: a tiny browser with a request log
  // Same pages as labs/ch06/sites.

  var VOLCANO = [
    '................................', '..............#..#..............', '.............#.##.#.............',
    '..............####..............', '...............##...............', '..............####..............',
    '.............######.............', '............########............', '...........##########...........',
    '..........############..........', '.........##############.........', '........################........',
    '.......##################.......', '......####################......', '.....######################.....',
    '################################'];

  var PAGES = {
    'bob/index.mu': '<title>Bob’s corner of the web</title><h>Welcome to Bob’s computer!</h>Things you can read here:\n' +
      '- my <link to="/report.mu">book report</link> (due Tuesday)\n- the <link to="/schedule.mu">class schedule</link>\n' +
      '- my <link to="/homework.mu">homework notes</link>\n- <link to="ttp://carol/index.mu">Carol’s page</link> has recipes and bees\n' +
      '- <link to="ttp://alice/index.mu">Alice’s page</link>\n<image src="/volcano.png">\n(Volcano by Carol.)',
    'bob/report.mu': '<title>Book report</title><h>Book report: Treasure Island</h>by <b>Bob</b>\n\nJim Hawkins finds a map, a ship full of pirates, and a parrot that will not stop shouting about pieces of eight.\n\n' +
      'See the <link to="schedule.mu">schedule</link> for when we present.\n<link to="/index.mu">Back to Bob’s page</link>',
    'bob/schedule.mu': '<title>Class presentations</title><h>Class presentations</h>Monday: <link to="ttp://alice/volcanoes.mu">Alice (volcanoes)</link>\n' +
      'Tuesday: <link to="/report.mu">Bob (Treasure Island)</link>\nWednesday: <link to="ttp://carol/bees.mu">Carol (how bees talk)</link>',
    'bob/school/homework.mu': '<title>Homework notes</title><h>Homework notes</h>Math: pages 40 to 42. <b>All</b> of them, Bob.\n(This page used to live at /homework.mu.)\n<link to="/index.mu">Back to Bob’s page</link>',
    'carol/index.mu': '<title>Carol’s page</title><h>Hi, I’m Carol!</h>I just moved in down the street. I like drawing, baking and bees.\n' +
      '- <link to="/bees.mu">How bees talk</link>\n- <link to="/recipes.mu">Recipes</link>\n- <link to="/old-drawings.mu">My old drawings</link>\n- <link to="ttp://bob/index.mu">Bob’s page</link>',
    'carol/bees.mu': '<title>How bees talk</title><h>How bees talk</h>A honeybee that finds flowers flies home and does a <b>waggle dance</b>. The angle says which way to fly, and the length of the waggle says how far. It’s a protocol!\n<link to="/index.mu">Back to Carol’s page</link>',
    'carol/recipes.mu': '<title>Recipes</title><h>Emergency treehouse snacks</h>Crackers. Peanut butter. Another cracker. Works every time.\n<link to="/index.mu">Back to Carol’s page</link>',
    'alice/index.mu': '<title>Alice’s page</title><h>Alice’s page</h>Under construction! For now, my <link to="/volcanoes.mu">volcano notes</link>.\n<link to="ttp://bob/index.mu">Bob’s page</link> | <link to="ttp://carol/index.mu">Carol’s page</link>',
    'alice/volcanoes.mu': '<title>Volcano notes</title><h>Volcanoes</h>A volcano is a crack in the Earth’s crust where melted rock comes out. ' +
      'Carol drew one: <link to="ttp://bob/volcano.png">see it on Bob’s computer</link>.\n<link to="/index.mu">Back to Alice’s page</link>'
  };
  var MOVED = { 'bob/homework.mu': '/school/homework.mu' };

  function volcanoSVG(scale) {
    var svg = s('svg', { viewBox: '0 0 32 16', width: 32 * scale, height: 16 * scale, style: 'display:block;image-rendering:pixelated' });
    svg.appendChild(s('rect', { width: 32, height: 16, fill: '#ffd966' }));
    VOLCANO.forEach(function (row, y) {
      row.split('').forEach(function (c, x) { if (c === '#') svg.appendChild(s('rect', { x: x, y: y, width: 1.02, height: 1.02, fill: '#202020' })); });
    });
    return svg;
  }

  WIDGETS.browser = function (el) {
    frame(el, 'A web browser, with the lid off',
      'Click links like you would in any browser. Underneath, you can see every request the browser sends and every reply it gets back.');
    var back = btn('◀', function () { if (hist.length) go(hist.pop(), true); }, 'ghost small');
    var bar = h('input', { type: 'text', size: '34', 'aria-label': 'address', style: 'flex:1;min-width:0' });
    var goBtn = btn('Go', function () { hist.push(cur); go(bar.value.trim(), true); }, 'small');
    bar.addEventListener('keydown', function (e) { if (e.key === 'Enter') goBtn.click(); });
    var page = h('div', { style: 'border:1.5px solid var(--line);border-radius:8px;padding:12px 16px;min-height:200px;margin:8px 0;' +
      'font-family:var(--serif);line-height:1.5;background:var(--bg);white-space:pre-wrap' });
    var logBox = h('div', { class: 'out', style: 'max-height:210px;overflow:auto;font-size:85%;white-space:pre;word-break:normal' });
    el.appendChild(h('div', { class: 'row', style: 'flex-wrap:nowrap' }, back, bar, goBtn));
    el.appendChild(page);
    el.appendChild(h('div', { style: 'font-size:90%;color:var(--muted);margin-top:6px', text: 'Requests for this page:' }));
    el.appendChild(logBox);
    var hist = [], cur = 'ttp://bob/index.mu';

    function split(url) {
      var m = /^ttp:\/\/([^\/]+)(\/.*)?$/.exec(url);
      return m ? { host: m[1], path: m[2] || '/' } : null;
    }
    function resolve(base, link) {
      if (/^ttp:\/\//.test(link)) return link;
      var b = split(base);
      if (link[0] === '/') return 'ttp://' + b.host + link;
      return 'ttp://' + b.host + b.path.replace(/[^\/]*$/, '') + link;
    }
    function request(url, lines) {
      var u = split(url);
      if (!u) { lines.push({ t: 'bad address: ' + url, c: 'bad' }); return { status: 400 }; }
      var key = u.host + (u.path === '/' ? '/index.mu' : u.path);
      lines.push({ t: '→ GET ' + u.path + ' TTP/1   Host: ' + u.host, c: '' });
      if (MOVED[key]) {
        lines.push({ t: '← 301 Moved Permanently   Location: ' + MOVED[key], c: 'warn' });
        return request('ttp://' + u.host + MOVED[key], lines);
      }
      if (key === 'bob/volcano.png') {
        lines.push({ t: '← 200 OK   Type: image/png   Length: 944', c: 'good' });
        return { status: 200, type: 'image/png', url: url };
      }
      if (PAGES[key]) {
        var len = new Blob([PAGES[key]]).size;
        lines.push({ t: '← 200 OK   Type: text/markup   Length: ' + len, c: 'good' });
        return { status: 200, type: 'text/markup', body: PAGES[key], url: url };
      }
      lines.push({ t: '← 404 Not Found', c: 'bad' });
      return { status: 404, url: url, host: u.host, path: u.path };
    }
    function go(url, noPush) {
      var lines = [];
      var r = request(url, lines);
      cur = r.url || url;
      bar.value = cur;
      page.innerHTML = '';
      if (r.status === 404) {
        page.appendChild(h('div', { html: '<b style="font-size:130%">404 Not Found</b>\nThere is no ' + r.path + ' on ' + r.host + '’s computer.' }));
      } else if (r.status !== 200) {
        page.appendChild(h('div', { text: 'Can’t load that address.' }));
      } else if (r.type === 'image/png') {
        page.appendChild(volcanoSVG(8));
      } else {
        render(r.body, lines);
      }
      logBox.innerHTML = '';
      lines.forEach(function (l) {
        logBox.appendChild(h('div', { text: l.t, class: l.c === 'good' ? 'good' : l.c === 'bad' ? 'bad' : '',
          style: l.c === 'warn' ? 'color:var(--orange);font-weight:700' : (l.c ? '' : 'color:var(--ink)') }));
      });
      logBox.appendChild(h('div', { text: lines.filter(function (l) { return l.t[0] === '→'; }).length + ' request(s) in total', style: 'color:var(--muted);margin-top:4px' }));
      back.disabled = !hist.length;
    }
    function render(markup, lines) {
      var title = /<title>(.*?)<\/title>/.exec(markup);
      markup = markup.replace(/<title>.*?<\/title>/, '');
      var parts = markup.split(/(<h>.*?<\/h>|<b>.*?<\/b>|<link to="[^"]*">.*?<\/link>|<image src="[^"]*">)/);
      parts.forEach(function (p) {
        var m;
        if ((m = /^<h>(.*?)<\/h>$/.exec(p))) page.appendChild(h('div', { text: m[1], style: 'font-family:var(--slab);font-weight:700;font-size:140%;margin-bottom:6px' }));
        else if ((m = /^<b>(.*?)<\/b>$/.exec(p))) page.appendChild(h('b', { text: m[1] }));
        else if ((m = /^<link to="([^"]*)">(.*?)<\/link>$/.exec(p))) {
          var target = resolve(cur, m[1]);
          page.appendChild(h('a', { href: '#', text: m[2], title: target, onclick: function (e) { e.preventDefault(); hist.push(cur); go(target); } }));
        } else if ((m = /^<image src="([^"]*)">$/.exec(p))) {
          var r = request(resolve(cur, m[1]), lines);
          page.appendChild(r.status === 200 ? volcanoSVG(5) : h('span', { text: '[broken image]' }));
        } else page.appendChild(document.createTextNode(p));
      });
      if (title) page.insertBefore(h('div', { text: '🗂 ' + title[1], style: 'font-family:var(--sans);font-size:80%;color:var(--muted);margin-bottom:8px' }), page.firstChild);
    }
    go(cur);
  };

  // ---------------------------------------------------------------- ch7: URL dissector + percent-encoding

  WIDGETS.urlparts = function (el) {
    frame(el, 'Take a URL apart',
      'Edit the address and watch it split into pieces. Query parameters come after the <b>?</b>, separated by <b>&amp;</b>. ' +
      'Characters that would confuse things are written as <b>%</b> plus two hex digits.');
    var input = h('input', { type: 'text', value: 'http://carol/guestbook?name=Bob%20the%20Builder&message=Hi+Carol%21&mood=%F0%9F%90%9D', style: 'width:100%', 'aria-label': 'URL' });
    var out = h('div', { style: 'margin-top:10px' });
    var enc = h('input', { type: 'text', value: 'fish & chips = 100%?', size: '24', 'aria-label': 'text to encode' });
    var encOut = h('div', { class: 'out', style: 'margin-top:6px' });
    el.appendChild(input);
    el.appendChild(out);
    el.appendChild(h('div', { class: 'row', style: 'margin-top:16px' }, h('label', {}, 'Encode some text for a URL: ', enc)));
    el.appendChild(encOut);
    function cell(label, value, tint) {
      return h('div', { style: 'display:flex;gap:10px;align-items:baseline;margin:3px 0' },
        h('span', { text: label, style: 'min-width:110px;color:var(--muted);font-size:90%;text-align:right' }),
        h('code', { text: value, style: 'background:' + tint + ';padding:3px 6px;border:0;word-break:break-all' }));
    }
    function decode(s) {
      try { return decodeURIComponent(s.replace(/\+/g, ' ')); } catch (e) { return '⚠ bad encoding: ' + s; }
    }
    function draw() {
      out.innerHTML = '';
      var m = /^([a-z][a-z0-9+.-]*):\/\/([^\/?#]*)([^?#]*)(\?[^#]*)?(#.*)?$/i.exec(input.value.trim());
      if (!m) { out.appendChild(h('p', { class: 'bad', text: 'That doesn’t look like scheme://host/path?query' })); return; }
      out.appendChild(cell('scheme', m[1], 'var(--tint-purple)'));
      out.appendChild(cell('host', m[2], 'var(--tint-blue)'));
      out.appendChild(cell('path', m[3] || '/', 'var(--tint-yellow)'));
      if (m[4]) {
        m[4].slice(1).split('&').filter(Boolean).forEach(function (pair) {
          var kv = pair.split('=');
          var k = decode(kv[0]), v = decode(kv.slice(1).join('='));
          out.appendChild(cell('query', k + '  =  ' + v, 'var(--tint-green)'));
        });
      }
      if (m[5]) out.appendChild(cell('fragment', m[5].slice(1) + '  (never sent to the server)', 'var(--tint-red)'));
    }
    function drawEnc() {
      var e = encodeURIComponent(enc.value);
      encOut.innerHTML = '<b>' + e.replace(/%[0-9A-F]{2}/g, function (x) { return '<span style="color:var(--red)">' + x + '</span>'; }) + '</b>';
    }
    input.addEventListener('input', draw);
    enc.addEventListener('input', drawEnc);
    draw();
    drawEnc();
  };

  // ---------------------------------------------------------------- ch8: shared-wire collision simulator
  // Mirrors labs/ch08/bus_sim.py.

  WIDGETS.bus = function (el) {
    var FRAME = 8, COLS = 96;
    frame(el, 'Rush hour on the shared wire',
      'Each row is one computer; time runs left to right. <span style="color:var(--green);font-weight:700">Green</span> = sending successfully, ' +
      '<span style="color:var(--red);font-weight:700">red</span> = caught in a collision. Change the manners and the traffic, and watch the score.');
    var mode = h('select', { 'aria-label': 'manners' },
      h('option', { value: 'aloha', text: 'Just talk (ALOHA)' }),
      h('option', { value: 'csma', text: 'Listen first (CSMA)' }),
      h('option', { value: 'csmacd', text: 'Listen, detect, back off (CSMA/CD)' }));
    mode.value = 'csmacd';
    var load = h('input', { type: 'range', min: '0.1', max: '1.6', step: '0.1', value: '0.7', 'aria-label': 'traffic' });
    var loadOut = h('b');
    var count = h('select', { 'aria-label': 'computers' });
    [3, 5, 8].forEach(function (n) { count.appendChild(h('option', { value: String(n), text: n + ' computers' })); });
    count.value = '5';
    var run = btn('Pause', function () { running = !running; run.textContent = running ? 'Pause' : 'Run'; }, 'small');
    var stats = h('div', { class: 'out', style: 'margin-top:8px' });
    var holder = h('div', { style: 'margin-top:8px' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Manners: ', mode), count));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Traffic: '), load, loadOut, run));
    el.appendChild(holder);
    el.appendChild(stats);

    var st, rows, t, active, good, delivered, collisions, delays, running = true, rects;
    function reset() {
      var n = +count.value;
      st = []; for (var i = 0; i < n; i++) st.push({ q: [], wait: 0, att: 0, tx: null });
      rows = []; for (var r = 0; r <= n; r++) rows.push([]);
      t = 0; active = []; good = 0; delivered = 0; collisions = 0; delays = [];
      holder.innerHTML = '';
      var cell = 7, gap = 1, W = 84 + COLS * (cell + gap), H = (n + 1) * 18 + 6;
      var svg = s('svg', { class: 'dia', viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'transmissions over time' });
      rects = [];
      for (var rr = 0; rr <= n; rr++) {
        var y = 4 + rr * 18 + (rr === n ? 4 : 0);
        svg.appendChild(s('text', { x: 76, y: y + 11, class: 'end xs' + (rr === n ? ' b' : ''), text: rr === n ? 'the wire' : 'computer ' + String.fromCharCode(65 + rr) }));
        var rowRects = [];
        for (var c = 0; c < COLS; c++) {
          var rect = s('rect', { x: 84 + c * (cell + gap), y: y, width: cell, height: 14, rx: 1.5, fill: 'var(--card)' });
          svg.appendChild(rect); rowRects.push(rect);
        }
        rects.push(rowRects);
      }
      holder.appendChild(svg);
    }
    function backoff(sn) {
      sn.att++;
      if (mode.value === 'csmacd') { var k = Math.min(sn.att, 10); return Math.floor(Math.random() * Math.pow(2, k)); }
      return 1 + Math.floor(Math.random() * 20 * FRAME);
    }
    function step() {
      var n = st.length, L = +load.value, p = L / FRAME / n;
      st.forEach(function (sn) { if (Math.random() < p) sn.q.push(t); });
      var busy = active.some(function (tx) { return tx.start <= t - 1; });
      st.forEach(function (sn) {
        if (sn.tx || !sn.q.length || t < sn.wait) return;
        if (mode.value !== 'aloha' && busy) return;
        var tx = { sn: sn, start: t, end: t + FRAME, col: false };
        sn.tx = tx; active.push(tx);
      });
      if (active.length > 1) active.forEach(function (tx) { tx.col = true; });
      if (mode.value === 'csmacd') active.forEach(function (tx) { if (tx.col && t - tx.start >= 1 && tx.end > t + 1) tx.end = t + 1; });
      st.forEach(function (sn, i) { rows[i].push(sn.tx ? (sn.tx.col ? 2 : 1) : 0); });
      rows[n].push(active.length === 0 ? 0 : (active.length > 1 || active.some(function (x) { return x.col; }) ? 2 : 1));
      active.slice().forEach(function (tx) {
        if (tx.end !== t + 1) return;
        active.splice(active.indexOf(tx), 1);
        var sn = tx.sn; sn.tx = null;
        if (tx.col) { collisions++; if (sn.att >= 15) { sn.q.shift(); sn.att = 0; } else sn.wait = t + 1 + backoff(sn); }
        else { good += FRAME; delivered++; delays.push(t + 1 - sn.q.shift()); sn.att = 0; }
      });
      rows.forEach(function (r) { if (r.length > COLS) r.shift(); });
      t++;
    }
    function paint() {
      var colours = ['var(--card)', 'var(--green)', 'var(--red)'];
      rows.forEach(function (r, ri) {
        for (var c = 0; c < COLS; c++) {
          var v = r[r.length - COLS + c];
          rects[ri][c].setAttribute('fill', v === undefined ? 'var(--card)' : colours[v]);
        }
      });
      var avg = delays.length ? delays.reduce(function (a, b) { return a + b; }, 0) / delays.length : 0;
      stats.innerHTML = 'Useful throughput: <b>' + Math.round(100 * good / Math.max(t, 1)) + '%</b> of the wire · ' +
        'delivered <b>' + delivered + '</b> · collisions <b>' + collisions + '</b> · average wait <b>' + avg.toFixed(0) + '</b> slots';
      loadOut.textContent = Math.round(+load.value * 100) + '% of capacity';
    }
    [mode, count].forEach(function (c) { c.addEventListener('change', function () { reset(); paint(); }); });
    load.addEventListener('input', paint);
    reset();
    for (var i = 0; i < 40; i++) step();
    paint();
    setInterval(function () {
      if (!running || reduced) return;
      if (!el.isConnected) return;
      var r = el.getBoundingClientRect();
      if (r.bottom < 0 || r.top > window.innerHeight) return;   // only animate while visible
      step(); paint();
    }, 70);
    if (reduced) { for (var j = 0; j < 400; j++) step(); paint(); }
  };

  // ---------------------------------------------------------------- ch9: a learning switch you can drive

  function tween(node, from, to, ms, done) {
    if (reduced) { node.setAttribute('cx', to[0]); node.setAttribute('cy', to[1]); if (done) done(); return; }
    var start = null;
    function frameFn(ts) {
      if (start === null) start = ts;
      var k = Math.min(1, (ts - start) / ms);
      node.setAttribute('cx', from[0] + (to[0] - from[0]) * k);
      node.setAttribute('cy', from[1] + (to[1] - from[1]) * k);
      if (k < 1) requestAnimationFrame(frameFn); else if (done) done();
    }
    requestAnimationFrame(frameFn);
  }

  WIDGETS.switchlearn = function (el) {
    frame(el, 'Teach a switch',
      'Pick who sends to whom and press <b>Send</b>. The switch learns from the <b>from</b> address of every frame. ' +
      'When it doesn’t know where the destination is, it floods (orange); once it knows, it sends to just one port (green).');
    var HOSTS = [
      { id: 'alice', name: 'Alice', mac: '0a:11', port: 1, pos: [90, 58], pp: [270, 132] },
      { id: 'bob', name: 'Bob', mac: '0b:22', port: 2, pos: [630, 58], pp: [450, 132] },
      { id: 'carol', name: 'Carol', mac: '0c:33', port: 3, pos: [90, 250], pp: [270, 168] },
      { id: 'dave', name: 'Dave', mac: '0d:44', port: 4, pos: [630, 250], pp: [450, 168] }
    ];
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 324', role: 'img', 'aria-label': 'a switch with four computers' });
    svg.appendChild(s('rect', { width: 720, height: 324, rx: 10, class: 'f-card' }));
    var cables = {};
    HOSTS.forEach(function (hst) {
      var mid = [hst.pos[0] + (hst.pp[0] - hst.pos[0]) * 0.55, hst.pos[1] + 26];
      var d = 'M' + hst.pos[0] + ',' + (hst.pos[1] + 26) + ' L' + mid[0] + ',' + mid[1] + ' L' + hst.pp[0] + ',' + hst.pp[1];
      cables[hst.port] = s('path', { d: d, class: 'wire', 'stroke-width': 4 });
      svg.appendChild(cables[hst.port]);
      hst.route = [[hst.pos[0], hst.pos[1] + 26], mid, hst.pp];
    });
    svg.appendChild(s('rect', { x: 270, y: 116, width: 180, height: 68, rx: 10, fill: '#2b7a73', stroke: '#17423e', 'stroke-width': 2.5 }));
    svg.appendChild(s('text', { x: 360, y: 156, class: 'mid slab b', fill: '#fff', text: 'SWITCH' }));
    HOSTS.forEach(function (hst) {
      svg.appendChild(s('circle', { cx: hst.pp[0], cy: hst.pp[1], r: 7, fill: '#113330', stroke: '#7dffa8', 'stroke-width': 1.5 }));
      svg.appendChild(s('text', { x: hst.pp[0] + (hst.pp[0] < 360 ? 14 : -14), y: hst.pp[1] + 4, class: (hst.pp[0] < 360 ? '' : 'end ') + 'xs b', fill: '#fff', text: String(hst.port) }));
      var u = s('use', { href: '#' + hst.id + '-head', x: hst.pos[0] - 26, y: hst.pos[1] - 30, width: 52, height: 52 });
      svg.appendChild(u);
      svg.appendChild(s('text', { x: hst.pos[0], y: hst.pos[1] + 42, class: 'mid slab b sm', text: hst.name }));
      svg.appendChild(s('text', { x: hst.pos[0], y: hst.pos[1] + 56, class: 'mid mono xs', text: hst.mac }));
    });
    var dotLayer = s('g');
    svg.appendChild(dotLayer);
    var from = h('select', { 'aria-label': 'from' }), to = h('select', { 'aria-label': 'to' });
    HOSTS.forEach(function (hst, i) {
      from.appendChild(h('option', { value: String(i), text: hst.name }));
      to.appendChild(h('option', { value: String(i), text: hst.name }));
    });
    to.appendChild(h('option', { value: 'ff', text: 'everyone (broadcast)' }));
    to.value = '1';
    var sendBtn = btn('Send', send);
    var forget = btn('Switch off and on (forget everything)', function () { table = {}; drawTable(null); say('The switch restarted with an empty table.'); }, 'ghost small');
    var narr = h('div', { class: 'out', style: 'margin-top:8px;min-height:2.6em' });
    var tbl = h('div', { style: 'margin-top:8px' });
    el.appendChild(svg);
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'From ', from), h('label', {}, 'to ', to), sendBtn, forget));
    el.appendChild(narr);
    el.appendChild(tbl);

    var table = {}, busy = false;
    function say(t) { narr.innerHTML = t; }
    function drawTable(fresh) {
      var macs = Object.keys(table).sort();
      tbl.innerHTML = '';
      var t = h('table', { class: 'data', style: 'max-width:360px;margin:0' });
      t.appendChild(h('tr', {}, h('th', { text: 'address' }), h('th', { text: 'port' })));
      if (!macs.length) t.appendChild(h('tr', {}, h('td', { colspan: '2', text: '(empty: the switch knows nobody yet)' })));
      macs.forEach(function (m) {
        t.appendChild(h('tr', { style: m === fresh ? 'background:var(--tint-yellow)' : '' },
          h('td', { html: '<code>' + m + '</code>' + (m === fresh ? ' <b style="color:var(--orange)">new!</b>' : '') }),
          h('td', { text: String(table[m]) })));
      });
      tbl.appendChild(h('div', { style: 'font-family:var(--slab);font-weight:700;margin-bottom:4px', text: 'The switch’s table' }));
      tbl.appendChild(t);
    }
    function path(pts, colour, ms, reverse, done) {
      var seq = reverse ? pts.slice().reverse() : pts;
      var c = s('circle', { r: 9, fill: colour, stroke: 'var(--surface)', 'stroke-width': 2, cx: seq[0][0], cy: seq[0][1] });
      dotLayer.appendChild(c);
      var i = 0;
      (function next() {
        if (i >= seq.length - 1) { setTimeout(function () { c.remove(); }, 450); if (done) done(); return; }
        tween(c, seq[i], seq[i + 1], ms / (seq.length - 1), function () { i++; next(); });
      })();
    }
    function send() {
      if (busy) return;
      var src = HOSTS[+from.value];
      var dst = to.value === 'ff' ? null : HOSTS[+to.value];
      if (dst === src) { say('Sending a frame to yourself doesn’t need the network at all!'); return; }
      busy = true; sendBtn.disabled = true;
      var fresh = table[src.mac] === undefined ? src.mac : null;
      path(src.route, 'var(--blue)', 700, false, function () {
        table[src.mac] = src.port;
        drawTable(fresh);
        var learnt = fresh ? 'Learned: <b>' + src.mac + '</b> lives on port ' + src.port + '. ' : '';
        var outs, colour, why;
        if (!dst) { outs = HOSTS.filter(function (x) { return x !== src; }); colour = 'var(--orange)'; why = 'It’s a broadcast, so flood it out of every other port.'; }
        else if (table[dst.mac] !== undefined) { outs = [dst]; colour = 'var(--green)'; why = 'It knows <b>' + dst.mac + '</b> is on port ' + dst.port + ', so it sends it only there.'; }
        else { outs = HOSTS.filter(function (x) { return x !== src; }); colour = 'var(--orange)'; why = 'It has never heard from <b>' + dst.mac + '</b>, so it floods it out of every other port.'; }
        say(learnt + why);
        var left = outs.length;
        outs.forEach(function (o) {
          path(o.route, colour, 700, true, function () {
            if (--left === 0) { busy = false; sendBtn.disabled = false; }
          });
        });
      });
    }
    drawTable(null);
    say('The switch has just been switched on and knows nobody. Send something!');
  };

  // ---------------------------------------------------------------- ch10: checks, Hamming, packets
  // Mirrors labs/ch10/checks.py and labs/ch10/packets.py.

  var CRC_TABLE = (function () {
    var t = [];
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(bytes) {
    var c = 0xFFFFFFFF;
    for (var i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  function inetsum(bytes) {
    var s = 0;
    for (var i = 0; i < bytes.length; i += 2) {
      s += (bytes[i] << 8) | (i + 1 < bytes.length ? bytes[i + 1] : 0);
      s = (s & 0xFFFF) + (s >>> 16);
    }
    return (~s) & 0xFFFF;
  }
  function ones(x) { var n = 0; while (x) { n += x & 1; x >>= 1; } return n; }

  var CHECKS10 = [
    { name: 'Parity bit', size: '1 bit', fn: function (b) { return String(b.reduce(function (a, x) { return a + ones(x); }, 0) % 2); } },
    { name: '8-bit sum', size: '8 bits', fn: function (b) { return '0x' + pad((b.reduce(function (a, x) { return a + x; }, 0) % 256).toString(16), 2); } },
    { name: 'Internet checksum', size: '16 bits', fn: function (b) { return '0x' + pad(inetsum(b).toString(16), 4); } },
    { name: 'CRC-32', size: '32 bits', fn: function (b) { return '0x' + pad(crc32(b).toString(16), 8); } }
  ];

  WIDGETS.checkplay = function (el) {
    frame(el, 'Damage detector',
      'Alice sends a message, and noise gets at it on the way to Carol. Click any bit of Carol’s copy to flip it, or use the buttons. ' +
      'Which checks notice?');
    var input = h('input', { type: 'text', value: 'HI BOB', maxlength: '12', size: '14', 'aria-label': 'message' });
    var bitsBox = h('div', { style: 'display:flex;flex-wrap:wrap;gap:8px 12px;margin:10px 0;justify-content:center' });
    var said = h('div', { class: 'out' });
    var table = h('table', { class: 'data', style: 'margin:12px 0 0;width:100%' });
    var sent = [], got = [];

    function flip(pos) { got[pos >> 3] ^= 0x80 >> (pos & 7); }
    function fresh() { got = sent.slice(); }
    function flips(n) {
      fresh();
      var total = got.length * 8, picked = {};
      while (Object.keys(picked).length < Math.min(n, total)) picked[Math.floor(Math.random() * total)] = 1;
      Object.keys(picked).forEach(function (p) { flip(+p); });
      draw();
    }
    function swap() {
      fresh();
      var pairs = [];
      for (var i = 0; i < got.length; i++) for (var j = i + 1; j < got.length; j++) if (got[i] !== got[j]) pairs.push([i, j]);
      if (!pairs.length) return flips(2);
      var p = pairs[Math.floor(Math.random() * pairs.length)];
      var t = got[p[0]]; got[p[0]] = got[p[1]]; got[p[1]] = t;
      draw();
    }
    function burst() {
      fresh();
      var total = got.length * 8, len = Math.min(10, total), start = Math.floor(Math.random() * (total - len + 1));
      for (var i = 0; i < len; i++) if (i === 0 || i === len - 1 || Math.random() < 0.5) flip(start + i);
      draw();
    }
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Alice sends ', input)));
    el.appendChild(h('div', { class: 'row' },
      btn('Flip 1 bit', function () { flips(1); }, 'small'),
      btn('Flip 2 bits', function () { flips(2); }, 'small'),
      btn('Swap two letters', swap, 'small'),
      btn('Noise burst', burst, 'small'),
      btn('Undo damage', function () { fresh(); draw(); }, 'ghost small')));
    el.appendChild(h('div', { style: 'font-size:90%;color:var(--muted);margin-top:10px' }, 'Carol receives (click a bit to flip it):'));
    el.appendChild(bitsBox);
    el.appendChild(said);
    el.appendChild(table);

    function show(c) { return c === 32 ? '␣' : (c > 32 && c < 127 ? String.fromCharCode(c) : '·'); }
    function draw() {
      bitsBox.innerHTML = '';
      var damaged = 0;
      got.forEach(function (byte, i) {
        var col = h('div', { style: 'display:flex;flex-direction:column;align-items:center;gap:3px' });
        col.appendChild(h('span', { text: show(byte), style: 'font-family:var(--mono);font-weight:700;font-size:115%;' +
          (byte !== sent[i] ? 'color:var(--red)' : '') }));
        var bits = h('div', { style: 'display:flex;gap:1px' });
        for (var k = 0; k < 8; k++) {
          var v = (byte >> (7 - k)) & 1, bad = v !== ((sent[i] >> (7 - k)) & 1);
          if (bad) damaged++;
          bits.appendChild(h('button', {
            type: 'button', text: String(v), 'aria-label': 'letter ' + (i + 1) + ', bit ' + (k + 1) + (bad ? ', flipped' : ''),
            style: 'width:19px;height:26px;padding:0;border-radius:3px;font-family:var(--mono);font-size:85%;cursor:pointer;' +
              'border:1px solid ' + (bad ? 'var(--red)' : 'var(--line)') + ';background:' + (bad ? 'var(--red)' : 'var(--card)') +
              ';color:' + (bad ? '#fff' : 'var(--ink)'),
            onclick: (function (pos) { return function () { flip(pos); draw(); }; })(i * 8 + k)
          }));
        }
        col.appendChild(bits);
        bitsBox.appendChild(col);
      });
      said.innerHTML = 'Carol reads: <b>“' + got.map(function (c) { return c >= 32 && c < 127 ? String.fromCharCode(c) : '·'; }).join('') + '”</b>' +
        (damaged ? '   <span class="bad">(' + damaged + ' bit' + (damaged > 1 ? 's' : '') + ' changed)</span>' : '   <span class="good">(undamaged)</span>');
      var rows = '<tr><th>Check</th><th>Alice sends</th><th>Carol computes</th><th>Verdict</th></tr>';
      CHECKS10.forEach(function (c) {
        var a = c.fn(sent), b = c.fn(got);
        var verdict = !damaged ? '<span style="color:var(--muted)">match</span>' :
          (a !== b ? '<span class="good">noticed ✓</span>' : '<span class="bad">missed ✗</span>');
        rows += '<tr><td>' + c.name + ' <span style="color:var(--muted);font-size:85%">(' + c.size + ')</span></td><td><code>' + a +
          '</code></td><td><code>' + b + '</code></td><td>' + verdict + '</td></tr>';
      });
      table.innerHTML = rows;
    }
    function encode() {
      sent = [];
      for (var i = 0; i < input.value.length; i++) { var c = input.value.charCodeAt(i); sent.push(c < 128 ? c : 63); }
      if (!sent.length) sent = [32];
      fresh(); draw();
    }
    input.addEventListener('input', encode);
    encode();
  };

  WIDGETS.hamming = function (el) {
    frame(el, 'Three circles that fix mistakes',
      'Choose Alice’s 4 data bits (yellow). The 3 parity bits (teal) are set so that every circle holds an even number of 1s. ' +
      'Now be the noise: click any bit to flip it, and watch the circles find it.');
    var POS = { d1: [360, 88], d2: [298, 196], d3: [422, 196], d4: [360, 154], p1: [230, 100], p2: [490, 100], p3: [360, 284] };
    var CIRCLES = [
      { name: 'p1', c: [300, 122], members: ['d1', 'd2', 'd4'], colour: 'blue', label: [150, 50, 'end'] },
      { name: 'p2', c: [420, 122], members: ['d1', 'd3', 'd4'], colour: 'green', label: [570, 50, 'start'] },
      { name: 'p3', c: [360, 222], members: ['d2', 'd3', 'd4'], colour: 'purple', label: [490, 300, 'start'] }];
    var NAMES = ['d1', 'd2', 'd3', 'd4', 'p1', 'p2', 'p3'];
    var data = [1, 0, 1, 1], sent = {}, got = {};
    function inCircle(name, c) { return name === c.name || c.members.indexOf(name) >= 0; }
    function encode() {
      sent = { d1: data[0], d2: data[1], d3: data[2], d4: data[3] };
      CIRCLES.forEach(function (c) { sent[c.name] = c.members.reduce(function (a, m) { return a + sent[m]; }, 0) % 2; });
      got = {}; NAMES.forEach(function (n) { got[n] = sent[n]; });
    }
    var dataRow = h('div', { class: 'row' }, h('span', { text: 'Alice’s data bits: ' }));
    var dataBtns = data.map(function (_, i) {
      var b = h('button', { type: 'button', class: 'btn small', style: 'font-family:var(--mono);min-width:34px',
        onclick: function () { data[i] = 1 - data[i]; encode(); draw(); } });
      dataRow.appendChild(b);
      return b;
    });
    dataRow.appendChild(btn('Undo noise', function () { encode(); draw(); }, 'ghost small'));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 346', role: 'img', 'aria-label': 'three overlapping parity circles' });
    var status = h('div', { class: 'out', style: 'margin-top:8px;white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(dataRow);
    el.appendChild(svg);
    el.appendChild(status);

    function draw() {
      dataBtns.forEach(function (b, i) { b.textContent = String(data[i]); });
      svg.innerHTML = '';
      var odd = [];
      CIRCLES.forEach(function (c) {
        var sum = NAMES.filter(function (n) { return inCircle(n, c); }).reduce(function (a, n) { return a + got[n]; }, 0);
        c.odd = sum % 2 === 1;
        if (c.odd) odd.push(c);
        svg.appendChild(s('circle', { cx: c.c[0], cy: c.c[1], r: 102,
          fill: c.odd ? 'var(--tint-red)' : 'var(--tint-' + c.colour + ')', 'fill-opacity': c.odd ? 0.55 : 0.4,
          stroke: c.odd ? 'var(--red)' : 'var(--' + c.colour + ')', 'stroke-width': c.odd ? 4 : 2.5,
          'stroke-dasharray': c.odd ? '10 6' : 'none' }));
      });
      CIRCLES.forEach(function (c) {
        var l = c.label;
        svg.appendChild(s('text', { x: l[0], y: l[1], class: 'slab b ' + (l[2] === 'end' ? 'end' : ''), text: 'circle ' + c.name.slice(1) }));
        svg.appendChild(s('text', { x: l[0], y: l[1] + 20, class: 'hand b ' + (l[2] === 'end' ? 'end ' : '') + (c.odd ? 'f-red' : 'f-green'),
          text: c.odd ? 'odd! ✗' : 'even ✓' }));
      });
      NAMES.forEach(function (n) {
        var p = POS[n], flipped = got[n] !== sent[n], isData = n[0] === 'd';
        var g = s('g', { style: 'cursor:pointer', tabindex: '0', role: 'button', 'aria-label': 'bit ' + n + ' is ' + got[n] + (flipped ? ', flipped' : '') });
        g.appendChild(s('circle', { cx: p[0], cy: p[1], r: 22, fill: flipped ? 'var(--red)' : (isData ? 'var(--yellow)' : 'var(--teal)'),
          stroke: 'var(--ink)', 'stroke-width': 2 }));
        g.appendChild(s('text', { x: p[0], y: p[1] + 7, class: 'mid mono b', 'font-size': '20', fill: flipped ? '#fff' : 'var(--navy)', text: String(got[n]) }));
        g.appendChild(s('text', { x: p[0], y: p[1] + 38, class: 'mid mono xs b halo', text: n }));
        var toggle = function () { got[n] = 1 - got[n]; draw(); };
        g.addEventListener('click', toggle);
        g.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
        svg.appendChild(g);
      });
      var flippedCount = NAMES.filter(function (n) { return got[n] !== sent[n]; }).length;
      var word = function (bits) { return ['d1', 'd2', 'd3', 'd4'].map(function (n) { return bits[n]; }).join(''); };
      status.innerHTML = '';
      if (!odd.length) {
        status.innerHTML = flippedCount ?
          'Every circle is even, so Carol thinks nothing is wrong… <span class="bad">but ' + flippedCount + ' bits were flipped!</span> Her data: <b>' + word(got) + '</b>, Alice sent <b>' + word(sent) + '</b>.' :
          'Every circle is even: nothing to fix. Carol reads the data bits: <b>' + word(got) + '</b>.';
        return;
      }
      var suspect = NAMES.filter(function (n) {
        return CIRCLES.every(function (c) { return inCircle(n, c) === c.odd; });
      })[0];
      var names = odd.map(function (c) { return c.name.slice(1); });
      status.appendChild(h('span', { html: 'Circle' + (names.length > 1 ? 's ' : ' ') + names.join(' and ') + (names.length > 1 ? ' are' : ' is') +
        ' odd' + (odd.length < 3 ? ', and the others are even' : '') + '. The only bit inside exactly ' + (names.length > 1 ? 'those circles' : 'that circle') +
        ' is <b>' + suspect + '</b>. ' }));
      status.appendChild(btn('Flip ' + suspect + ' back', function () {
        got[suspect] = 1 - got[suspect];
        draw();
        var ok = word(got) === word(sent);
        status.innerHTML = ok ? '<span class="good">Fixed ✓</span> Carol’s data bits are <b>' + word(got) + '</b>, exactly what Alice sent.' :
          '<span class="bad">Oops ✗</span> Carol “fixed” ' + suspect + ', but that made things worse: her data is <b>' + word(got) +
          '</b>, and Alice sent <b>' + word(sent) + '</b>. With two flips, the circles point at an innocent bit. Hamming codes can fix <em>one</em> error.';
      }, 'small'));
    }
    encode();
    draw();
  };

  WIDGETS.packetizer = function (el) {
    var W = 32, H = 16, S = 10, HDR = 4, MAX_ROUNDS = 30;
    frame(el, 'Send the school play',
      'Bob sends one frame of his video to Carol, over a line where noise damages some pixels. Choose how to chop it up and how noisy the ' +
      'line is, then press Send. A damaged packet fails its check, gets thrown away, and is sent again. Each packet also carries a ' +
      'label and a check, worth ' + HDR + ' pixels.');
    var size = h('select', { 'aria-label': 'packet size' });
    [[1, '1 giant packet'], [8, '8 packets of 64 pixels'], [32, '32 packets of 16'], [128, '128 packets of 4']].forEach(function (o) {
      size.appendChild(h('option', { value: String(o[0]), text: o[1] }));
    });
    size.value = '8';
    var noise = h('input', { type: 'range', min: '0', max: '0.03', step: '0.001', value: '0.005', 'aria-label': 'noise' });
    var noiseOut = h('b');
    var checkId = 'chk-' + Math.random().toString(36).slice(2);
    var checks = h('input', { type: 'checkbox', checked: 'checked', id: checkId });
    var go = btn('Send', start);
    var cBob = h('canvas', { width: W * S, height: H * S, 'aria-label': 'the picture Bob sends',
      style: 'width:100%;image-rendering:pixelated;border-radius:6px;border:1.5px solid var(--line);display:block' });
    var cCarol = h('canvas', { width: W * S, height: H * S, 'aria-label': 'Carol’s copy',
      style: 'width:100%;image-rendering:pixelated;border-radius:6px;border:1.5px solid var(--line);display:block' });
    var stats = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Chop into ', size), h('label', { for: checkId }, checks, ' check each packet')));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Noise: '), noise, noiseOut, go));
    var panel = function (label, canvas) {
      return h('div', { style: 'flex:1 1 240px;min-width:0' }, h('div', { style: 'font-size:90%;color:var(--muted);margin-bottom:4px', text: label }), canvas);
    };
    el.appendChild(h('div', { style: 'display:flex;gap:14px;flex-wrap:wrap;margin:10px 0' }, panel('Bob sends', cBob), panel('Carol’s copy', cCarol)));
    el.appendChild(stats);

    function stage(x, y) {
      var curtain = x % 2 ? '#a82b24' : '#cf4238';
      if (y < 2 || x < 4 || x > 27) return curtain;
      if (y >= 13) return y === 13 ? '#9a6a35' : '#71491f';
      if ((x - 16) * (x - 16) + (y - 4) * (y - 4) < 3.5) return '#f7e39c';                    // the moon
      var stars = ['7,3', '12,6', '21,3', '25,6', '9,9', '24,10', '5,6'];
      if (stars.indexOf(x + ',' + y) >= 0) return '#ffd23f';
      if (y === 7 && (x === 11 || x === 21)) return '#f2c18d';                               // heads
      if (y >= 8 && y <= 10 && x >= 10 && x <= 12) return '#3b82c4';                          // Alice’s costume
      if (y >= 8 && y <= 10 && x >= 20 && x <= 22) return '#2f9e6b';                          // Bob’s costume
      if ((y === 11 || y === 12) && (x === 10 || x === 12 || x === 20 || x === 22)) return '#2b2b2b';
      if (y === 12 && x >= 14 && x <= 18) return '#e9e3cf';                                   // the spotlight on the floor
      return '#1f3550';
    }
    var picture = [];
    for (var yy = 0; yy < H; yy++) for (var xx = 0; xx < W; xx++) picture.push(stage(xx, yy));
    var ctxB = cBob.getContext('2d'), ctxC = cCarol.getContext('2d');
    function css(name) { return getComputedStyle(el).getPropertyValue(name).trim() || '#ccc'; }
    function px(ctx, i, colour) { ctx.fillStyle = colour; ctx.fillRect((i % W) * S, Math.floor(i / W) * S, S, S); }
    function blank(i) { return ((i % W) + Math.floor(i / W)) % 2 ? css('--card') : css('--line'); }
    function noiseColour() { return 'hsl(' + Math.floor(Math.random() * 360) + ',90%,55%)'; }
    function packetRect(p, n) {
      var per = W * H / n, first = p * per;
      if (per >= W) return [0, Math.floor(first / W) * S, W * S, per / W * S];
      return [(first % W) * S, Math.floor(first / W) * S, per * S, S];
    }
    function drawBob() {
      picture.forEach(function (c, i) { px(ctxB, i, c); });
      var n = +size.value;
      ctxB.strokeStyle = 'rgba(255,255,255,0.8)'; ctxB.lineWidth = 1.5;
      for (var p = 0; p < n; p++) { var r = packetRect(p, n); ctxB.strokeRect(r[0] + 0.75, r[1] + 0.75, r[2] - 1.5, r[3] - 1.5); }
    }
    function clearCarol() { for (var i = 0; i < W * H; i++) px(ctxC, i, blank(i)); }

    var timer = null, have, round, sentPx, resent, glitched, n, per;
    function stop() { if (timer) { clearInterval(timer); clearTimeout(timer); timer = null; } }
    function start() {
      stop();
      n = +size.value; per = W * H / n;
      have = []; for (var p = 0; p < n; p++) have.push(false);
      round = 0; sentPx = 0; resent = 0; glitched = 0;
      clearCarol();
      nextRound();
    }
    function nextRound() {
      var todo = [];
      have.forEach(function (ok, p) { if (!ok) todo.push(p); });
      if (!todo.length) return finish(true);
      if (round >= MAX_ROUNDS) return finish(false);
      round++;
      var i = 0, perTick = Math.max(1, Math.ceil(todo.length / 16));
      timer = setInterval(function () {
        for (var k = 0; k < perTick && i < todo.length; k++, i++) deliver(todo[i]);
        report();
        if (i >= todo.length) { clearInterval(timer); timer = setTimeout(nextRound, reduced ? 0 : 500); }
      }, reduced ? 0 : 45);
    }
    function deliver(p) {
      var q = +noise.value, first = p * per, hits = [], headerHit = false;
      sentPx += per + HDR;
      if (round > 1) resent++;
      for (var j = 0; j < per; j++) if (Math.random() < q) hits.push(first + j);
      for (var k = 0; k < HDR; k++) if (Math.random() < q) headerHit = true;
      var damaged = hits.length > 0 || headerHit;
      for (var m = 0; m < per; m++) px(ctxC, first + m, hits.indexOf(first + m) >= 0 ? noiseColour() : picture[first + m]);
      if (!damaged || !checks.checked) {
        have[p] = true;
        if (damaged) glitched++;
        return;
      }
      var r = packetRect(p, n);
      ctxC.strokeStyle = '#e03131'; ctxC.lineWidth = 3;
      ctxC.strokeRect(r[0] + 1.5, r[1] + 1.5, r[2] - 3, r[3] - 3);
      setTimeout(function () {
        if (have[p]) return;
        for (var m = 0; m < per; m++) px(ctxC, first + m, blank(first + m));
      }, reduced ? 0 : 280);
    }
    function report(done) {
      var total = W * H;
      var line = 'Round <b>' + round + '</b> · sent <b>' + sentPx.toLocaleString() + '</b> pixels’ worth for a ' + total + '-pixel picture (<b>' +
        (sentPx / total).toFixed(2) + '×</b>) · resent <b>' + resent + '</b> packet' + (resent === 1 ? '' : 's');
      stats.innerHTML = line + (done || '');
    }
    function finish(ok) {
      stop();
      if (!ok) return report('<br><span class="bad">Bob gives up after ' + MAX_ROUNDS + ' rounds. With one giant packet, almost every try gets hit somewhere.</span>');
      if (glitched) return report('<br><span class="bad">Carol has the whole picture, but ' + glitched + ' damaged packet' + (glitched > 1 ? 's' : '') +
        ' slipped through, and she has no idea. That’s what happens without checks.</span>');
      report('<br><span class="good">Carol has a perfect copy ✓</span>');
    }
    function showNoise() { noiseOut.textContent = (+noise.value * 100).toFixed(1) + '% of pixels'; }
    size.addEventListener('change', function () { stop(); drawBob(); clearCarol(); stats.textContent = 'Press Send.'; });
    noise.addEventListener('input', showNoise);
    showNoise();
    drawBob();
    clearCarol();
    stats.textContent = 'Press Send.';
  };

  // ---------------------------------------------------------------- ch11: routers sharing tables
  // Mirrors labs/ch11/routing_sim.py: four networks, four routers in a ring, distance-vector sharing.

  WIDGETS.routing = function (el) {
    var FAR = 16;
    frame(el, 'Routers that talk to each other',
      'Each router starts out knowing only its own network. Press <b>Share tables</b> to let every router tell its neighbors what it knows. ' +
      'Then send a packet. Click a cable to cut it (or mend it), and share again.');
    var NETS = {
      1: { name: 'Our street', who: 'Alice 1.1 · Bob 1.2 · …', box: [14, 12, 210, 84], plug: [224, 70] },
      2: { name: 'The school', who: 'Teacher 2.1', box: [496, 12, 210, 84], plug: [496, 70] },
      3: { name: 'The library', who: 'Library 3.1', box: [496, 272, 210, 84], plug: [496, 298] },
      4: { name: 'Grandpa Otto’s town', who: 'Otto 4.2', box: [14, 272, 210, 84], plug: [224, 298] }
    };
    var POS = { R1: [292, 118], R2: [428, 118], R3: [428, 250], R4: [292, 250] };
    var HOME = { R1: 1, R2: 2, R3: 3, R4: 4 };
    var CABLES = [['R1', 'R2'], ['R2', 'R3'], ['R3', 'R4'], ['R4', 'R1']];
    var tables, cut, rounds, busy = false, lastChanged = {};

    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 368', role: 'img', 'aria-label': 'four networks joined by four routers in a ring' });
    var tablesBox = h('div', { style: 'display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:8px' });
    var dest = h('select', { 'aria-label': 'destination' },
      h('option', { value: '2', text: 'to the school (2.1)' }),
      h('option', { value: '3', text: 'to the library (3.1)' }),
      h('option', { value: '4', text: 'to Grandpa Otto (4.2)' }));
    dest.value = '4';
    var status = h('div', { class: 'out', style: 'margin-top:8px;white-space:normal;word-break:normal;font-family:var(--sans)' });
    var shareBtn = btn('Share tables', function () { share(); }, 'small');
    el.appendChild(h('div', { class: 'row' }, shareBtn,
      btn('Share until nothing changes', function () { var n = 0; while (share(true) && n++ < 10); say('Shared until the tables stopped changing (' + rounds + ' round' + (rounds === 1 ? '' : 's') + ' so far).'); }, 'ghost small'),
      btn('Start over', reset, 'ghost small')));
    el.appendChild(h('div', { class: 'row' }, h('span', { text: 'Send a packet from Alice ' }), dest, btn('Send', send, 'small')));
    el.appendChild(svg);
    el.appendChild(status);
    el.appendChild(tablesBox);

    function say(html) { status.innerHTML = html; }
    function key(a, b) { return [a, b].sort().join('-'); }
    function neighbors(r) {
      var out = [];
      CABLES.forEach(function (c) {
        if (cut[key(c[0], c[1])]) return;
        if (c[0] === r) out.push(c[1]);
        if (c[1] === r) out.push(c[0]);
      });
      return out;
    }
    function reset() {
      tables = {}; cut = {}; rounds = 0; lastChanged = {};
      Object.keys(HOME).forEach(function (r) { tables[r] = {}; tables[r][HOME[r]] = { via: null, hops: 0 }; });
      draw();
      say('Each router only knows the network it’s plugged into. Try sending a packet to Grandpa Otto now, then share some tables.');
    }
    function share(quiet) {
      var snap = JSON.parse(JSON.stringify(tables)), changed = false;
      lastChanged = {};
      Object.keys(tables).forEach(function (r) {
        neighbors(r).forEach(function (n) {
          Object.keys(snap[n]).forEach(function (net) {
            var offer = Math.min(snap[n][net].hops + 1, FAR);
            var cur = tables[r][net] || { via: null, hops: FAR };
            if (offer < cur.hops || (cur.via === n && offer !== cur.hops)) {
              tables[r][net] = { via: n, hops: offer };
              lastChanged[r + ':' + net] = true;
              changed = true;
            }
          });
        });
      });
      rounds++;
      draw();
      if (!quiet) say(changed ? 'Round ' + rounds + ': every router told its neighbors everything it knows. Changes are highlighted.' :
        'Round ' + rounds + ': nothing changed. The routers agree on a way to every network they can reach.');
      return changed;
    }
    function toggleCable(a, b) {
      if (busy) return;
      var k = key(a, b);
      cut[k] = !cut[k];
      lastChanged = {};
      if (cut[k]) {
        [[a, b], [b, a]].forEach(function (p) {
          Object.keys(tables[p[0]]).forEach(function (net) {
            if (tables[p[0]][net].via === p[1]) { tables[p[0]][net] = { via: p[1], hops: FAR }; lastChanged[p[0] + ':' + net] = true; }
          });
        });
        say('✂ The cable between ' + a + ' and ' + b + ' is cut. They notice the silence and cross out every route that went through each other. ' +
          'Share tables to find new ways around.');
      } else {
        say('The cable between ' + a + ' and ' + b + ' is mended. Share tables so the routers can use it again.');
      }
      draw();
    }
    function draw() {
      svg.innerHTML = '';
      CABLES.forEach(function (c) {
        var p = POS[c[0]], q = POS[c[1]], isCut = cut[key(c[0], c[1])];
        svg.appendChild(s('line', { x1: p[0], y1: p[1], x2: q[0], y2: q[1], stroke: isCut ? 'var(--red)' : 'var(--copper)',
          'stroke-width': 6, 'stroke-dasharray': isCut ? '10 8' : 'none', 'stroke-linecap': 'round' }));
        var mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2;
        if (isCut) svg.appendChild(s('path', { d: 'M' + (mx - 11) + ',' + (my - 11) + ' l22,22 M' + (mx + 11) + ',' + (my - 11) + ' l-22,22',
          stroke: 'var(--red)', 'stroke-width': 5, 'stroke-linecap': 'round' }));
        var hit = s('line', { x1: p[0], y1: p[1], x2: q[0], y2: q[1], stroke: 'transparent', 'stroke-width': 26, style: 'cursor:pointer',
          tabindex: '0', role: 'button', 'aria-label': (isCut ? 'mend' : 'cut') + ' the cable between ' + c[0] + ' and ' + c[1] });
        hit.appendChild(s('title', { text: (isCut ? 'Mend' : 'Cut') + ' this cable' }));
        hit.addEventListener('click', function () { toggleCable(c[0], c[1]); });
        hit.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleCable(c[0], c[1]); } });
        svg.appendChild(hit);
      });
      Object.keys(NETS).forEach(function (n) {
        var net = NETS[n], b = net.box, r = 'R' + n;
        svg.appendChild(s('line', { x1: net.plug[0], y1: net.plug[1], x2: POS[r][0], y2: POS[r][1], stroke: 'var(--copper)', 'stroke-width': 3.5 }));
        svg.appendChild(s('rect', { x: b[0], y: b[1], width: b[2], height: b[3], rx: 14, fill: 'var(--tint-teal)', stroke: 'var(--teal)', 'stroke-width': 2 }));
        svg.appendChild(s('text', { x: b[0] + b[2] / 2, y: b[1] + 30, class: 'mid slab b', text: net.name }));
        svg.appendChild(s('text', { x: b[0] + b[2] / 2, y: b[1] + 52, class: 'mid xs muted', text: 'network ' + n }));
        svg.appendChild(s('text', { x: b[0] + b[2] / 2, y: b[1] + 72, class: 'mid mono xs', text: net.who }));
      });
      Object.keys(POS).forEach(function (r) {
        var p = POS[r];
        svg.appendChild(s('use', { href: '#router', x: p[0] - 36, y: p[1] - 24, width: 72, height: 48 }));
        svg.appendChild(s('text', { x: p[0], y: p[1] + (p[1] < 180 ? -30 : 42), class: 'mid slab b halo', text: r }));
      });
      tablesBox.innerHTML = '';
      Object.keys(tables).forEach(function (r) {
        var rows = '';
        [1, 2, 3, 4].forEach(function (net) {
          var e = tables[r][net], hl = lastChanged[r + ':' + net] ? 'background:var(--tint-yellow);' : '';
          var txt = !e || e.hops >= FAR ? '<span style="color:var(--muted)">' + (e ? 'lost ✗' : '?') + '</span>' :
            (e.via === null ? '<b>right here</b>' : 'via ' + e.via + ' · ' + e.hops + ' hop' + (e.hops > 1 ? 's' : ''));
          rows += '<tr style="' + hl + '"><td style="padding:2px 6px">net ' + net + '</td><td style="padding:2px 6px">' + txt + '</td></tr>';
        });
        tablesBox.appendChild(h('div', { style: 'border:1.5px solid var(--line);border-radius:8px;padding:6px;background:var(--card);font-size:88%' },
          h('div', { class: 'slab', style: 'font-weight:700;margin-bottom:2px', text: r + '’s table' }),
          h('table', { style: 'border-collapse:collapse;width:100%', html: rows })));
      });
    }
    function send() {
      if (busy) return;
      var target = +dest.value, route = [NETS[1].plug, POS.R1], at = 'R1', steps = 0, verdict;
      while (true) {
        var e = tables[at][target];
        if (!e || e.hops >= FAR) { verdict = '<span class="bad">' + at + ' has no route to network ' + target + ', so it drops the packet ✗</span>'; break; }
        if (e.via === null) { route.push(NETS[target].plug); verdict = '<span class="good">Delivered ✓</span> The packet went through ' + (steps + 1) + ' router' + (steps ? 's' : '') + '.'; break; }
        at = e.via; route.push(POS[at]); steps++;
        if (steps > 8) { verdict = '<span class="bad">The packet is going round in circles ✗</span>'; break; }
      }
      busy = true;
      var dot = s('circle', { cx: route[0][0], cy: route[0][1], r: 10, fill: 'var(--blue)', stroke: 'var(--surface)', 'stroke-width': 3 });
      svg.appendChild(dot);
      var i = 0;
      (function hop() {
        if (i + 1 >= route.length) {
          busy = false;
          say(verdict);
          setTimeout(function () { if (dot.parentNode) dot.parentNode.removeChild(dot); }, 900);
          return;
        }
        tween(dot, route[i], route[i + 1], 450, function () { i++; hop(); });
      })();
    }
    reset();
  };

  // ---------------------------------------------------------------- ch12: ports
  // Mirrors labs/ch12/otto.py: the OS hands each datagram to the program that owns its port.

  WIDGETS.portmail = function (el) {
    frame(el, 'Otto’s mailroom',
      'Pick who sends, and which port on Otto’s computer (4.2) to send to. Watch the operating system sort each datagram, ' +
      'and notice how the chess program keeps the games apart. Then switch chess off.');
    var SENDERS = [
      { id: 'a1', who: 'Alice', head: 'alice', addr: '1.1', port: 51234, y: 70, label: 'Alice’s chess' },
      { id: 'a2', who: 'Alice', head: 'alice', addr: '1.1', port: 51240, y: 150, label: 'Alice’s 2nd window' },
      { id: 'b1', who: 'Bob', head: 'bob', addr: '1.2', port: 50999, y: 230, label: 'Bob’s chess' }];
    var PROGS = { 7: { name: 'chat', y: 62, colour: 'var(--blue)' }, 64: { name: 'chess', y: 146, colour: 'var(--green)' },
      123: { name: 'clock', y: 230, colour: 'var(--purple)' } };
    var MOVES = ['e5', 'Nc6', 'Bc5', 'Nf6', 'd6', 'O-O'];
    var games = [], chessOn = true, busy = false;
    var from = h('select', { 'aria-label': 'sender' });
    SENDERS.forEach(function (sd, i) { from.appendChild(h('option', { value: String(i), text: sd.label + ' (' + sd.addr + ', port ' + sd.port + ')' })); });
    var to = h('select', { 'aria-label': 'destination port' },
      h('option', { value: '64', text: 'port 64 (chess)' }), h('option', { value: '7', text: 'port 7 (chat)' }),
      h('option', { value: '123', text: 'port 123 (clock)' }), h('option', { value: '99', text: 'port 99' }));
    var msg = h('input', { type: 'text', value: 'e4', size: '10', 'aria-label': 'message' });
    var chessId = 'chess-' + Math.random().toString(36).slice(2);
    var chessBox = h('input', { type: 'checkbox', checked: 'checked', id: chessId });
    var sendBtn = btn('Send', send, 'small');
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'From ', from)));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'to Otto’s ', to), msg, sendBtn,
      h('label', { for: chessId }, chessBox, ' chess is running')));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 300', role: 'img', 'aria-label': 'senders on the left, Otto’s computer with its ports on the right' });
    var log = h('div', { class: 'out', style: 'margin-top:8px;white-space:normal;word-break:normal;font-family:var(--sans);min-height:3em' });
    el.appendChild(svg);
    el.appendChild(log);

    var gamesText;
    function draw() {
      svg.innerHTML = '';
      svg.appendChild(s('rect', { x: 330, y: 14, width: 376, height: 272, rx: 16, fill: 'var(--card)', stroke: 'var(--ink)', 'stroke-width': 2 }));
      svg.appendChild(s('text', { x: 518, y: 36, class: 'mid slab b', text: 'Otto’s computer, 4.2' }));
      svg.appendChild(s('rect', { x: 346, y: 50, width: 86, height: 222, rx: 10, fill: 'var(--tint-teal)', stroke: 'var(--teal)', 'stroke-width': 2 }));
      svg.appendChild(s('text', { x: 389, y: 156, class: 'mid xs b', text: 'operating' }));
      svg.appendChild(s('text', { x: 389, y: 172, class: 'mid xs b', text: 'system' }));
      Object.keys(PROGS).forEach(function (port) {
        var p = PROGS[port], off = port === '64' && !chessOn;
        svg.appendChild(s('rect', { x: 446, y: p.y - 2, width: 44, height: 30, rx: 6, fill: 'var(--surface)', stroke: 'var(--ink)', 'stroke-width': 2 }));
        svg.appendChild(s('text', { x: 468, y: p.y + 18, class: 'mid mono sm b', text: port }));
        svg.appendChild(s('rect', { x: 500, y: p.y - 14, width: 192, height: port === '64' ? 76 : 54, rx: 8, fill: off ? 'var(--card)' : 'var(--surface)',
          stroke: off ? 'var(--muted)' : p.colour, 'stroke-width': 2.5, 'stroke-dasharray': off ? '6 5' : 'none' }));
        svg.appendChild(s('text', { x: 512, y: p.y + 6, class: 'slab b', text: p.name + (off ? ' (switched off)' : '') }));
      });
      gamesText = s('text', { x: 512, y: 172, class: 'mono xs' });
      svg.appendChild(gamesText);
      drawGames();
      SENDERS.forEach(function (sd) {
        svg.appendChild(s('use', { href: '#' + sd.head + '-head', x: 10, y: sd.y - 24, width: 46, height: 46 }));
        svg.appendChild(s('text', { x: 62, y: sd.y - 4, class: 'sm b', text: sd.label }));
        svg.appendChild(s('text', { x: 62, y: sd.y + 14, class: 'mono xs', text: sd.addr + ' port ' + sd.port }));
      });
    }
    function drawGames() {
      if (!gamesText) return;
      gamesText.innerHTML = '';
      if (!chessOn) return;
      if (!games.length) { gamesText.appendChild(s('tspan', { x: 512, dy: 0, text: 'no games yet' })); return; }
      games.slice(-3).forEach(function (g, i) {
        gamesText.appendChild(s('tspan', { x: 512, dy: i ? 14 : 0, text: '#' + g.n + ' vs ' + g.key + ' (' + g.moves + ')' }));
      });
    }
    function fly(points, colour, done) {
      var dot = s('circle', { cx: points[0][0], cy: points[0][1], r: 9, fill: colour, stroke: 'var(--surface)', 'stroke-width': 3 });
      svg.appendChild(dot);
      var i = 0;
      (function next() {
        if (i + 1 >= points.length) { svg.removeChild(dot); done(); return; }
        tween(dot, points[i], points[i + 1], 380, function () { i++; next(); });
      })();
    }
    function send() {
      if (busy) return;
      var sd = SENDERS[+from.value], port = +to.value, text = msg.value.trim() || '(empty)';
      var start = [230, sd.y], os = [389, 110 + (sd.y - 70) * 0.4];
      var head = '<b>' + sd.addr + ':' + sd.port + '</b> → <b>4.2:' + port + '</b> “' + text.replace(/</g, '&lt;') + '”. ';
      busy = true; sendBtn.disabled = true;
      var prog = PROGS[port], home = prog && !(port === 64 && !chessOn);
      if (!home) {
        fly([start, os], 'var(--red)', function () {
          log.innerHTML = head + 'The operating system finds no program using port ' + port + '. <span class="bad">Nobody home:</span> it drops the datagram and sends back a note saying so.';
          fly([os, start], 'var(--red)', finish);
        });
        return;
      }
      var inbox = [446, prog.y + 13];
      fly([start, os, inbox], 'var(--blue)', function () {
        var reply = null, note = '';
        if (port === 7) note = 'Port 7 belongs to chat, which prints the message. Chat never replies, so the sender just has to hope it arrived.';
        if (port === 123) { reply = 'It’s ' + new Date().toTimeString().slice(0, 8) + ' at Otto’s.'; note = 'Port 123 belongs to the clock. It replies to <b>' + sd.addr + ':' + sd.port + '</b>, the address and port the datagram came <em>from</em>.'; }
        if (port === 64) {
          var key = sd.addr + ':' + sd.port, g = games.filter(function (x) { return x.key === key; })[0];
          if (!g) { g = { key: key, n: games.length + 1, moves: 0 }; games.push(g); note = 'Port 64 belongs to chess. It has never heard from <b>' + key + '</b> before, so this is a <em>new game</em>, #' + g.n + '. '; }
          else note = 'Port 64 belongs to chess. It knows <b>' + key + '</b>: that’s game #' + g.n + '. ';
          g.moves++;
          reply = 'game #' + g.n + ', move ' + g.moves + ': I play ' + MOVES[(g.moves - 1) % MOVES.length];
          drawGames();
        }
        log.innerHTML = head + note + (reply ? '<br>Reply to ' + sd.addr + ':' + sd.port + ': “' + reply + '”' : '');
        if (reply) fly([inbox, os, start], 'var(--green)', finish); else finish();
      });
    }
    function finish() { busy = false; sendBtn.disabled = false; }
    chessBox.addEventListener('change', function () { chessOn = chessBox.checked; if (!chessOn) games = []; draw(); });
    to.addEventListener('change', function () {
      msg.value = { 64: 'e4', 7: 'hello grandpa!', 123: 'what time is it?', 99: 'anyone there?' }[to.value];
    });
    draw();
    log.innerHTML = 'Try sending a chess move from Alice, then one from Alice’s second window, then one from Bob.';
  };

  // ---------------------------------------------------------------- ch13: sliding window
  // Mirrors labs/ch13/reliable.py: cumulative ACKs, go-back-N or selective repeat, timeouts.

  WIDGETS.slidingwindow = function (el) {
    var N = 16, TRAVEL = 28, TIMEOUT = 2 * TRAVEL + 14, COL = 40, X0 = 40, SY = 44, RY = 266;
    frame(el, 'The sliding window',
      'Alice (top) sends 16 datagrams to Otto (bottom), and Otto’s acknowledgments fly back up. Press <b>Run</b>. ' +
      '<b>Click a flying datagram to destroy it</b>, and watch how each method recovers.');
    var win = h('select', { 'aria-label': 'window size' });
    [1, 2, 4, 8].forEach(function (w) { win.appendChild(h('option', { value: String(w), text: w === 1 ? 'window 1 (stop-and-wait)' : 'window ' + w })); });
    win.value = '4';
    var mode = h('select', { 'aria-label': 'method' },
      h('option', { value: 'gbn', text: 'go back N' }), h('option', { value: 'sr', text: 'selective repeat' }));
    var loss = h('input', { type: 'range', min: '0', max: '0.4', step: '0.05', value: '0', 'aria-label': 'random loss' });
    var lossOut = h('b');
    var runBtn = btn('Run', function () { running = !running; runBtn.textContent = running ? 'Pause' : 'Run'; }, 'small');
    el.appendChild(h('div', { class: 'row' }, win, mode, runBtn, btn('Start over', reset, 'ghost small')));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Random loss: '), loss, lossOut));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 316', role: 'img', 'aria-label': 'datagrams travelling from sender to receiver' });
    var stats = h('div', { class: 'out', style: 'margin-top:8px;white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(svg);
    el.appendChild(stats);

    var st, running = false, sBoxes, rBoxes, bracket;
    function colX(i) { return X0 + i * COL; }
    function reset() {
      st = { tick: 0, base: 0, next: 0, sentAt: [], sacked: {}, expected: 0, got: {}, flights: [], sent: 0, resent: 0, done: false };
      running = false; runBtn.textContent = 'Run';
      svg.innerHTML = '';
      svg.appendChild(s('text', { x: 8, y: SY + 20, class: 'sm b', text: 'Alice' }));
      svg.appendChild(s('text', { x: 8, y: RY + 20, class: 'sm b', text: 'Otto' }));
      bracket = s('rect', { y: SY - 8, height: 46, rx: 8, fill: 'none', stroke: 'var(--red)', 'stroke-width': 3 });
      svg.appendChild(bracket);
      sBoxes = []; rBoxes = [];
      for (var i = 0; i < N; i++) {
        var x = colX(i) + 44;
        sBoxes.push(s('rect', { x: x, y: SY, width: COL - 6, height: 30, rx: 5, 'stroke-width': 2 }));
        rBoxes.push(s('rect', { x: x, y: RY, width: COL - 6, height: 30, rx: 5, 'stroke-width': 2 }));
        svg.appendChild(sBoxes[i]); svg.appendChild(rBoxes[i]);
        svg.appendChild(s('text', { x: x + (COL - 6) / 2, y: SY + 20, class: 'mid mono xs b', text: String(i) }));
        svg.appendChild(s('text', { x: x + (COL - 6) / 2, y: RY + 20, class: 'mid mono xs b', text: String(i) }));
      }
      paint();
    }
    function launch(kind, seq, extra) {
      var f = { kind: kind, seq: seq, born: st.tick, lost: Math.random() < +loss.value, dead: false };
      if (extra) for (var k in extra) f[k] = extra[k];
      var x = colX(seq) + 44 + (COL - 6) / 2;
      if (kind === 'data') {
        f.el = s('g', { style: 'cursor:crosshair' });
        f.el.appendChild(s('rect', { x: x - 11, y: -9, width: 22, height: 18, rx: 3, fill: 'var(--blue)', stroke: 'var(--surface)', 'stroke-width': 1.5 }));
        f.el.appendChild(s('text', { x: x, y: 4, class: 'mid mono xs b', fill: '#fff', text: String(seq) }));
      } else {
        f.el = s('g', { style: 'cursor:crosshair' });
        f.el.appendChild(s('circle', { cx: x, cy: 0, r: 11, fill: 'var(--green)', stroke: 'var(--surface)', 'stroke-width': 1.5 }));
        f.el.appendChild(s('text', { x: x, y: 4, class: 'mid mono xs b', fill: '#fff', text: 'A' + f.ack }));
      }
      f.el.addEventListener('click', function () { f.lost = true; f.killAt = st.tick; });
      svg.appendChild(f.el);
      st.flights.push(f);
    }
    function sendData(seq, again) {
      st.sentAt[seq] = st.tick; st.sent++;
      if (again) st.resent++;
      launch('data', seq);
    }
    function step() {
      if (st.done) return;
      var W = +win.value, sr = mode.value === 'sr';
      while (st.next < N && st.next < st.base + W) { sendData(st.next, false); st.next++; }
      st.flights.slice().forEach(function (f) {
        var p = (st.tick - f.born) / TRAVEL;
        if (f.lost && (f.killAt !== undefined || p >= 0.5)) {
          if (!f.dead) { f.dead = true; f.deadAt = st.tick; f.el.setAttribute('opacity', '0.35'); f.el.appendChild(s('text', { x: colX(f.seq) + 44 + 17, y: 6, class: 'mid b', fill: 'var(--red)', 'font-size': '22', text: '✗' })); }
          if (st.tick - f.deadAt > 6) remove(f);
          return;
        }
        if (p >= 1) { remove(f); arrive(f, sr); return; }
        var y = f.kind === 'data' ? SY + 38 + p * (RY - SY - 50) : RY - 12 - p * (RY - SY - 50);
        f.el.setAttribute('transform', 'translate(0,' + y + ')');
      });
      if (st.base < st.next) {
        var late = [];
        if (sr) { for (var s2 = st.base; s2 < st.next; s2++) if (!st.sacked[s2] && st.tick - st.sentAt[s2] > TIMEOUT) late.push(s2); }
        else if (st.tick - st.sentAt[st.base] > TIMEOUT) { for (var s3 = st.base; s3 < st.next; s3++) late.push(s3); }
        late.forEach(function (q) { sendData(q, true); });
      }
      st.tick++;
      if (st.base >= N) { st.done = true; running = false; runBtn.textContent = 'Run'; }
      paint();
    }
    function remove(f) { var i = st.flights.indexOf(f); if (i >= 0) st.flights.splice(i, 1); if (f.el.parentNode) f.el.parentNode.removeChild(f.el); }
    function arrive(f, sr) {
      if (f.kind === 'data') {
        if (f.seq === st.expected || (sr && f.seq > st.expected)) st.got[f.seq] = true;
        while (st.got[st.expected]) st.expected++;
        var sack = [];
        if (sr) for (var k in st.got) if (+k >= st.expected) sack.push(+k);
        launch('ack', f.seq, { ack: st.expected, sack: sack });
      } else {
        if (f.ack > st.base) st.base = f.ack;
        (f.sack || []).forEach(function (q) { st.sacked[q] = true; });
      }
    }
    function paint() {
      var W = +win.value;
      for (var i = 0; i < N; i++) {
        var acked = i < st.base || st.sacked[i], sent = st.sentAt[i] !== undefined;
        sBoxes[i].setAttribute('fill', acked ? 'var(--tint-green)' : sent ? 'var(--tint-yellow)' : 'var(--card)');
        sBoxes[i].setAttribute('stroke', acked ? 'var(--green)' : sent ? 'var(--yellow)' : 'var(--line)');
        var inOrder = i < st.expected, early = st.got[i] && !inOrder;
        rBoxes[i].setAttribute('fill', inOrder ? 'var(--tint-green)' : early ? 'var(--tint-yellow)' : 'var(--card)');
        rBoxes[i].setAttribute('stroke', inOrder ? 'var(--green)' : early ? 'var(--yellow)' : 'var(--line)');
      }
      var b = Math.min(st.base, N), e = Math.min(st.base + W, N);
      bracket.setAttribute('x', colX(b) + 44 - 5);
      bracket.setAttribute('width', Math.max(0, (e - b) * COL + 4));
      bracket.setAttribute('opacity', b < N ? 1 : 0);
      var rt = (st.tick / (2 * TRAVEL)).toFixed(1);
      stats.innerHTML = (st.done ? '<span class="good">All 16 delivered ✓</span> ' : '') + 'Time: <b>' + rt + '</b> round trips · sent <b>' + st.sent +
        '</b> datagrams, <b>' + st.resent + '</b> of them resends · Otto has everything up to #<b>' + (st.expected - 1) + '</b>' +
        '<br><span style="color:var(--muted);font-size:90%">Top row: green = acknowledged, yellow = sent and waiting. Bottom row: green = received in order, ' +
        'yellow = arrived early (kept only in selective repeat). Red box: the window.</span>';
      lossOut.textContent = Math.round(+loss.value * 100) + '%';
    }
    [win, mode].forEach(function (c) { c.addEventListener('change', reset); });
    loss.addEventListener('input', paint);
    setInterval(function () {
      if (!running || !el.isConnected) return;
      var r = el.getBoundingClientRect();
      if (r.bottom < 0 || r.top > window.innerHeight) return;
      step();
    }, reduced ? 15 : 45);
    reset();
  };

  // ---------------------------------------------------------------- ch14: names, resolvers, memory
  // Mirrors labs/ch14/names.py: a root, three zones, and a caching resolver.

  WIDGETS.dnscache = function (el) {
    var ANSWER_TTL = 60, REFERRAL_TTL = 2 * 24 * 60;          // minutes
    frame(el, 'The resolver’s memory',
      'Look up names as Alice or Bob, and watch who the resolver has to ask. Then let time pass, or move Grandpa Otto to a new address, and look him up again.');
    var POS = { Alice: [52, 86], Bob: [52, 214], resolver: [250, 150], root: [450, 58],
      school: [640, 74], library: [640, 150], seaside: [640, 226] };
    var zones, cache, now, asked, busy = false;
    var who = h('select', { 'aria-label': 'who asks' }, h('option', { value: 'Alice', text: 'Alice asks for' }), h('option', { value: 'Bob', text: 'Bob asks for' }));
    var name = h('select', { 'aria-label': 'name' });
    ['otto.seaside', 'harbor.seaside', 'newsletter.school', 'catalog.library', 'ghost.seaside'].forEach(function (n) { name.appendChild(h('option', { value: n, text: n })); });
    var goBtn = btn('Look it up', lookup, 'small');
    var moveBtn = btn('Otto moves to 4.9', function () { zones.seaside.otto = zones.seaside.otto === '4.2' ? '4.9' : '4.2'; moveBtn.textContent = 'Otto moves to ' + (zones.seaside.otto === '4.2' ? '4.9' : '4.2'); say('Otto’s town has updated its name server: otto.seaside is now <b>' + zones.seaside.otto + '</b>. Nobody else has been told.'); paint(); }, 'ghost small');
    el.appendChild(h('div', { class: 'row' }, who, name, goBtn));
    el.appendChild(h('div', { class: 'row' }, btn('Wait 15 minutes', function () { tick(15); }, 'ghost small'),
      btn('Wait 2 days', function () { tick(2 * 24 * 60); }, 'ghost small'), moveBtn, btn('Start over', reset, 'ghost small')));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 290', role: 'img', 'aria-label': 'Alice and Bob, the resolver, the root and three name servers' });
    var status = h('div', { class: 'out', style: 'margin-top:8px;white-space:normal;word-break:normal;font-family:var(--sans)' });
    var memory = h('div', { style: 'margin-top:8px' });
    el.appendChild(svg); el.appendChild(status); el.appendChild(memory);

    function say(html) { status.innerHTML = html; }
    function clock() { var d = Math.floor(now / 1440) + 1, m = now % 1440; return 'day ' + d + ', ' + pad(Math.floor(m / 60), 2) + ':' + pad(m % 60, 2); }
    function reset() {
      zones = { seaside: { otto: '4.2', harbor: '4.8' }, school: { newsletter: '2.7' }, library: { catalog: '3.1' } };
      cache = {}; now = 9 * 60; asked = { root: 0, school: 0, library: 0, seaside: 0 };
      moveBtn.textContent = 'Otto moves to 4.9';
      draw(); paint();
      say('The resolver has just started up, and remembers nothing. Look something up.');
    }
    function tick(mins) {
      now += mins;
      Object.keys(cache).forEach(function (k) { if (cache[k].until <= now) delete cache[k]; });
      paint();
      say('Time passes: it’s now ' + clock() + '. Anything the resolver remembered past its expiry time has been forgotten.');
    }
    function draw() {
      svg.innerHTML = '';
      ['root', 'school', 'library', 'seaside'].forEach(function (n) {
        svg.appendChild(s('line', { x1: POS.resolver[0], y1: POS.resolver[1], x2: POS[n][0], y2: POS[n][1], stroke: 'var(--line)', 'stroke-width': 2, 'stroke-dasharray': '5 5' }));
      });
      ['Alice', 'Bob'].forEach(function (n) {
        svg.appendChild(s('line', { x1: POS[n][0], y1: POS[n][1], x2: POS.resolver[0], y2: POS.resolver[1], stroke: 'var(--line)', 'stroke-width': 2, 'stroke-dasharray': '5 5' }));
        svg.appendChild(s('use', { href: '#' + n.toLowerCase() + '-head', x: POS[n][0] - 24, y: POS[n][1] - 24, width: 48, height: 48 }));
        svg.appendChild(s('text', { x: POS[n][0], y: POS[n][1] + 40, class: 'mid sm b', text: n }));
      });
      [['resolver', 'resolver (our street)'], ['root', 'the root'], ['school', 'school’s server'], ['library', 'library’s server'], ['seaside', 'seaside’s server']].forEach(function (p) {
        var xy = POS[p[0]];
        svg.appendChild(s('use', { href: '#server', x: xy[0] - 14, y: xy[1] - 22, width: 28, height: 44 }));
        svg.appendChild(s('text', { x: xy[0] + (p[0] === 'root' || p[0] === 'resolver' ? 0 : -24), y: xy[1] + (p[0] === 'root' ? -30 : p[0] === 'resolver' ? 40 : 4),
          class: (p[0] === 'root' || p[0] === 'resolver' ? 'mid' : 'end') + ' xs b halo', text: p[1] }));
        if (p[0] !== 'resolver') {
          var c = s('text', { x: xy[0] + (p[0] === 'root' ? 22 : -24), y: xy[1] + (p[0] === 'root' ? 4 : 20), class: (p[0] === 'root' ? '' : 'end ') + 'xs muted halo' });
          c.setAttribute('data-count', p[0]);
          svg.appendChild(c);
        }
      });
    }
    function paint() {
      Array.prototype.forEach.call(svg.querySelectorAll('[data-count]'), function (t) {
        var n = t.getAttribute('data-count');
        t.textContent = 'asked ' + asked[n] + ' time' + (asked[n] === 1 ? '' : 's');
      });
      var keys = Object.keys(cache);
      var rows = keys.length ? keys.map(function (k) {
        var e = cache[k], left = e.until - now;
        var real = e.kind === 'A' ? zones[k.split('.')[1]][k.split('.')[0]] : null;
        var stale = e.kind === 'A' && real !== e.value;
        var leftText = left >= 1440 ? Math.round(left / 1440 * 10) / 10 + ' days' : left + ' min';
        return '<tr><td><code>' + k + '</code></td><td>' + (e.kind === 'A' ? '<b' + (stale ? ' class="bad"' : '') + '>' + e.value + '</b>' + (stale ? ' <span class="bad">(out of date!)</span>' : '') :
          'ask ' + e.value + '’s server') + '</td><td>' + leftText + '</td></tr>';
      }).join('') : '<tr><td colspan="3" style="color:var(--muted)">(nothing remembered)</td></tr>';
      memory.innerHTML = '<div class="slab" style="font-weight:700;margin-bottom:2px">The resolver remembers · ' + clock() + '</div>' +
        '<table class="data" style="margin:0"><tr><th>Name</th><th>Answer</th><th>Forget in</th></tr>' + rows + '</table>';
    }
    function fly(legs, done) {
      var i = 0;
      (function next() {
        if (i >= legs.length) { done(); return; }
        var leg = legs[i], dot = s('circle', { cx: POS[leg[0]][0], cy: POS[leg[0]][1], r: 9, fill: leg[2], stroke: 'var(--surface)', 'stroke-width': 3 });
        svg.appendChild(dot);
        tween(dot, POS[leg[0]], POS[leg[1]], 420, function () { svg.removeChild(dot); i++; next(); });
      })();
    }
    function lookup() {
      if (busy) return;
      busy = true; goBtn.disabled = true;
      var asker = who.value, n = name.value, host = n.split('.')[0], zone = n.split('.')[1];
      var legs = [[asker, 'resolver', 'var(--blue)']], msg;
      var hit = cache[n];
      if (hit) {
        var real = zones[zone][host];
        msg = 'The resolver <b>remembered</b> ' + n + ' = <b>' + hit.value + '</b> (' + (hit.until - now) + ' minutes left). Nobody else was asked.' +
          (real !== hit.value ? ' <span class="bad">But Otto has moved to ' + real + '! Until this memory expires, everyone who asks is sent to the old address.</span>' : '');
        legs.push(['resolver', asker, 'var(--green)']);
      } else {
        var steps = [];
        if (!cache[zone]) {
          legs.push(['resolver', 'root', 'var(--blue)'], ['root', 'resolver', 'var(--orange)']);
          asked.root++;
          cache[zone] = { kind: 'R', value: zone, until: now + REFERRAL_TTL };
          steps.push('asked the root, which said “ask ' + zone + '’s server” (remembered for 2 days)');
        } else steps.push('already knew to ask ' + zone + '’s server, so skipped the root');
        legs.push(['resolver', zone, 'var(--blue)'], [zone, 'resolver', 'var(--green)']);
        asked[zone]++;
        var addr = zones[zone][host];
        if (addr) {
          cache[n] = { kind: 'A', value: addr, until: now + ANSWER_TTL };
          steps.push('asked ' + zone + '’s server: <b>' + addr + '</b>, good for 1 hour');
          msg = 'The resolver ' + steps.join(', then ') + '. ' + asker + ' gets <b>' + addr + '</b>.';
        } else {
          steps.push('asked ' + zone + '’s server, which has never heard of ' + host);
          msg = 'The resolver ' + steps.join(', then ') + '. ' + asker + ' is told: <span class="bad">no such name</span>.';
        }
        legs.push(['resolver', asker, addr ? 'var(--green)' : 'var(--red)']);
      }
      fly(legs, function () { busy = false; goBtn.disabled = false; paint(); say(msg); });
    }
    reset();
  };

  // ---------------------------------------------------------------- ch15: peel a real packet
  // The bytes are packet 8 of labs/ch15/sample.pcap: Alice's "GET /" to grandpa-otto.example.

  WIDGETS.onion = function (el) {
    var HEX = '14c35e400b32e25fb13c770a08004500007b0004400040063ca3c0a80103cb00712acb200050000003e9000013895018ffffe8c80000' +
      '474554202f20485454502f312e310d0a486f73743a206772616e6470612d6f74746f2e6578616d706c650d0a557365722d4167656e743a2' +
      '06375726c2f382e372e310d0a4163636570743a202a2f2a0d0a0d0a';
    var bytes = [];
    for (var i = 0; i < HEX.length; i += 2) bytes.push(parseInt(HEX.slice(i, i + 2), 16));
    var LAYERS = {
      frame: { name: 'Frame (Ethernet)', colour: 'var(--tint-blue)', edge: 'var(--blue)' },
      packet: { name: 'Packet (IP)', colour: 'var(--tint-yellow)', edge: 'var(--yellow)' },
      conn: { name: 'Connection (TCP)', colour: 'var(--tint-green)', edge: 'var(--green)' },
      data: { name: 'Data (HTTP)', colour: 'var(--tint-purple)', edge: 'var(--purple)' } };
    function num(a, b) { var v = 0; for (var k = a; k <= b; k++) v = v * 256 + bytes[k]; return v; }
    function macAt(a) { return bytes.slice(a, a + 6).map(function (x) { return pad(x.toString(16), 2); }).join(':'); }
    function ipAt(a) { return bytes.slice(a, a + 4).join('.'); }
    var FIELDS = [
      [0, 5, 'frame', 'To (card address)', macAt(0) + ': the router’s card. The frame only has to get across Alice’s own network. (Chapter 8)'],
      [6, 11, 'frame', 'From (card address)', macAt(6) + ': Alice’s laptop. Her “private” Wi-Fi address, in fact. (Chapter 8)'],
      [12, 13, 'frame', 'What’s inside', '0x0800 means “an IP packet”. 0x0806 would mean a “who has?” message. (Chapter 8)'],
      [14, 14, 'packet', 'Version and header size', '0x45: version 4, and the header is 5 × 4 = 20 bytes long.'],
      [15, 15, 'packet', 'Priority', '0: nothing special. Routers can use this to give some packets priority.'],
      [16, 17, 'packet', 'Total length', num(16, 17) + ' bytes: this packet, headers and all. A length at the front, like Chapter 5.'],
      [18, 19, 'packet', 'Identification', num(18, 19) + ': a number for this packet, used if a router has to chop it into smaller pieces.'],
      [20, 21, 'packet', 'Flags', '0x4000: “don’t chop me up”. The same bit you set with <code>ping -D</code> to find the MTU. (Chapter 10)'],
      [22, 22, 'packet', 'Hops left (TTL)', num(22, 22) + ': every router takes one off, and drops the packet at zero. (Chapter 11)'],
      [23, 23, 'packet', 'What’s inside', '6 means TCP. 17 would mean UDP. (Chapters 12 and 13)'],
      [24, 25, 'packet', 'Header check', '0x' + HEX.slice(48, 52) + ': the Internet checksum of this header. (Chapter 10)'],
      [26, 29, 'packet', 'From (network address)', ipAt(26) + ': Alice’s laptop. Network 192.168.1, host 3. (Chapter 11)'],
      [30, 33, 'packet', 'To (network address)', ipAt(30) + ': grandpa-otto.example, as the name lookup said. It stays the same all the way. (Chapters 11 and 14)'],
      [34, 35, 'conn', 'From port', num(34, 35) + ': a port Alice’s operating system picked for this connection. (Chapter 12)'],
      [36, 37, 'conn', 'To port', num(36, 37) + ': port 80, the well-known port for web servers. (Chapter 12)'],
      [38, 41, 'conn', 'Sequence number', num(38, 41) + ': the number of the first byte of data in here. Alice started counting at a random 1000. (Chapter 13)'],
      [42, 45, 'conn', 'Acknowledgment', num(42, 45) + ': “I’ve got everything you sent before byte 5001.” (Chapter 13)'],
      [46, 46, 'conn', 'Header size', '0x50: the header is 5 × 4 = 20 bytes.'],
      [47, 47, 'conn', 'Flags', '0x18: PSH + ACK. “Here’s some data, and here’s an acknowledgment.” (Chapter 13)'],
      [48, 49, 'conn', 'Room left (window)', num(48, 49) + ' bytes: how much Alice can receive right now. Flow control. (Chapter 13)'],
      [50, 51, 'conn', 'Check', '0x' + HEX.slice(100, 104) + ': the Internet checksum of the whole segment. (Chapter 10)'],
      [52, 53, 'conn', 'Urgent', '0: an old feature that almost nothing uses.'],
      [54, bytes.length - 1, 'data', 'The request itself', 'Plain text: <code>GET / HTTP/1.1</code>, then the Host header, then a blank line. Exactly Chapter 6’s protocol.']];
    var fieldOf = [];
    FIELDS.forEach(function (f, i) { for (var k = f[0]; k <= f[1]; k++) fieldOf[k] = i; });

    frame(el, 'Peel a real packet',
      'These are all 137 bytes of one real frame: a laptop asking a web server for its home page. Click any byte to find out what it’s for.');
    var legend = h('div', { class: 'row' });
    Object.keys(LAYERS).forEach(function (k) {
      legend.appendChild(h('span', { style: 'display:inline-flex;align-items:center;gap:6px;font-size:90%', html:
        '<i style="display:inline-block;width:14px;height:14px;border-radius:3px;background:' + LAYERS[k].colour + ';border:1.5px solid ' + LAYERS[k].edge + '"></i>' + LAYERS[k].name }));
    });
    var grid = h('div', { style: 'display:grid;grid-template-columns:repeat(16, minmax(0, 1fr));gap:2px;margin:10px 0;font-family:var(--mono);font-size:85%' });
    var info = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:4.2em' });
    el.appendChild(legend); el.appendChild(grid); el.appendChild(info);
    var cells = bytes.map(function (b, i) {
      var f = FIELDS[fieldOf[i]], L = LAYERS[f[2]];
      var c = h('button', { type: 'button', text: pad(b.toString(16), 2), 'aria-label': 'byte ' + i + ', ' + f[3],
        style: 'padding:3px 0;border-radius:3px;cursor:pointer;font-family:inherit;font-size:inherit;color:var(--ink);background:' + L.colour +
          ';border:1.5px solid transparent', onclick: function () { pick(fieldOf[i]); } });
      grid.appendChild(c);
      return c;
    });
    function pick(n) {
      var f = FIELDS[n];
      cells.forEach(function (c, i) {
        var mine = fieldOf[i] === n;
        c.style.borderColor = mine ? LAYERS[f[2]].edge : 'transparent';
        c.style.fontWeight = mine ? '700' : '400';
      });
      var shown = f[1] - f[0] < 8 ? ' <code>' + HEX.slice(f[0] * 2, (f[1] + 1) * 2).replace(/(..)/g, '$1 ').trim() + '</code>' : '';
      info.innerHTML = '<b>' + LAYERS[f[2]].name + ' · ' + f[3] + '</b> (byte' + (f[1] > f[0] ? 's ' + f[0] + '–' + f[1] : ' ' + f[0]) + ')' + shown + '<br>' + f[4];
    }
    pick(8);
  };

  // ---------------------------------------------------------------- ch16: capture filters, compiled and run
  // Mirrors labs/ch16/minidump.py: the same parser, compiler and virtual machine, on the same 29 packets.

  var BPF = (function () {
    var NAMES = { tcpflags: 13, 'tcp-fin': 1, 'tcp-syn': 2, 'tcp-rst': 4, 'tcp-push': 8, 'tcp-ack': 16, 'tcp-urg': 32,
      icmptype: 0, icmpcode: 1, 'icmp-echoreply': 0, 'icmp-unreach': 3, 'icmp-echo': 8, 'icmp-timxceed': 11,
      ssh: 22, domain: 53, bootps: 67, bootpc: 68, http: 80, ntp: 123, https: 443, mdns: 5353 };
    var PROTOS = { tcp: 6, udp: 17, icmp: 1 };
    var ACCEPT = 262144;
    function fail(msg) { var e = new Error(msg); e.filter = true; throw e; }
    function tokenize(text) {
      var re = /\s*(\(|\)|\[|\]|!=|==|<=|>=|&&|\|\||[=<>!&|]|[A-Za-z0-9_.:\/\-]+)/y, out = [], m;
      text = text.trim(); re.lastIndex = 0;
      while (re.lastIndex < text.length) {
        m = re.exec(text);
        if (!m) fail('don’t understand “' + text.slice(re.lastIndex).trim() + '”');
        out.push(m[1]);
      }
      return out;
    }
    function num(w) {
      w = w in NAMES ? String(NAMES[w]) : w;
      if (!/^(0x[0-9a-f]+|\d+)$/i.test(w)) fail('expected a number, got “' + w + '”');
      return parseInt(w);
    }
    function ipv4(w) {
      var p = w.split('.');
      if (p.length !== 4 || !p.every(function (x) { return /^\d+$/.test(x) && +x < 256; })) fail('“' + w + '” isn’t an IPv4 address');
      return ((+p[0] << 24) >>> 0) + (+p[1] << 16) + (+p[2] << 8) + +p[3];
    }
    function macBytes(w) {
      var p = w.split(':');
      if (p.length !== 6 || !p.every(function (x) { return /^[0-9a-f]{1,2}$/i.test(x); })) fail('“' + w + '” isn’t a card (MAC) address');
      return p.map(function (x) { return parseInt(x, 16); });
    }
    function parse(text) {
      var toks = tokenize(text), i = 0;
      function peek() { return toks[i]; }
      function take(want) {
        var t = toks[i];
        if (t === undefined) fail('the filter stops too soon' + (want ? ' (expected “' + want + '”)' : ''));
        if (want && t !== want) fail('expected “' + want + '”, got “' + t + '”');
        i++; return t;
      }
      function expr() {
        var left = unary();
        while (['and', '&&', 'or', '||'].indexOf(peek()) >= 0) {
          var t = take(), op = (t === 'and' || t === '&&') ? 'and' : 'or';
          left = [op, left, unary()];
        }
        return left;
      }
      function unary() {
        var t = peek();
        if (t === 'not' || t === '!') { take(); return ['not', unary()]; }
        if (t === '(') { take(); var inner = expr(); take(')'); return inner; }
        return primitive();
      }
      function primitive() {
        var t = take();
        if (t === 'greater' || t === 'less') return ['len', t, num(take())];
        if (t === 'broadcast') return ['ether', 'dst', [255, 255, 255, 255, 255, 255]];
        if (t === 'multicast') return ['multicast'];
        var proto = null;
        if (['ether', 'ip', 'arp', 'ip6', 'tcp', 'udp', 'icmp'].indexOf(t) >= 0) {
          proto = t;
          if (peek() === '[') return comparison(proto);
          if (['src', 'dst', 'host', 'net', 'port', 'portrange', 'broadcast'].indexOf(peek()) < 0) return ['proto', proto];
          t = take();
        }
        if (proto === 'ether' && t === 'broadcast') return ['ether', 'dst', [255, 255, 255, 255, 255, 255]];
        var dir = null;
        if (t === 'src' || t === 'dst') { dir = t; t = take(); }
        if (['host', 'net', 'port', 'portrange'].indexOf(t) < 0) { i--; t = 'host'; }
        var v = take();
        if (proto === 'ether') return ['ether', dir, macBytes(v)];
        if (t === 'host') return ['host', dir, ipv4(v), null, proto];
        if (t === 'net') {
          var parts = v.split('/'), bits = parts[1] ? +parts[1] : 24;
          var mask = bits === 0 ? 0 : (0xFFFFFFFF << (32 - bits)) >>> 0;
          return ['net', dir, (ipv4(parts[0]) & mask) >>> 0, mask, proto];
        }
        var lo = v, hi = v;
        if (t === 'portrange') { var r = v.split('-'); lo = r[0]; hi = r[1] || r[0]; }
        return ['port', dir, num(lo), num(hi), proto];
      }
      function comparison(proto) {
        take('[');
        var where = take().split(':');
        take(']');
        var mask = null;
        if (peek() === '&') { take(); mask = num(take()); }
        var op = take();
        if (['=', '==', '!=', '<', '<=', '>', '>='].indexOf(op) < 0) fail('expected a comparison like = or !=, got “' + op + '”');
        return ['cmp', proto, num(where[0]), where[1] ? +where[1] : 1, mask, op === '==' ? '=' : op, num(take())];
      }
      var tree = expr();
      if (peek() !== undefined) fail('unexpected “' + peek() + '”');
      return tree;
    }
    function compile(text) {
      var code = [];
      function Label() { this.at = null; }
      function emit(op, arg, jt, jf) { code.push([op, arg, jt === undefined ? null : jt, jf === undefined ? null : jf]); }
      function place(l) { l.at = code.length; }
      function ipv4hdr(protos, no) {
        emit('ldh', 12); emit('jeq', 0x800, null, no);
        if (protos.length) {
          emit('ldb', 23);
          var found = new Label();
          protos.forEach(function (p, n) {
            var last = n === protos.length - 1;
            emit('jeq', p, last ? null : found, last ? no : null);
          });
          place(found);
        }
        emit('ldh', 20); emit('jset', 0x1fff, no, null); emit('ldxb', 14);
      }
      function gen(node, yes, no) {
        var k = node[0], mid, spots, n;
        if (k === 'and') { mid = new Label(); gen(node[1], mid, no); place(mid); gen(node[2], yes, no); }
        else if (k === 'or') { mid = new Label(); gen(node[1], yes, mid); place(mid); gen(node[2], yes, no); }
        else if (k === 'not') gen(node[1], no, yes);
        else if (k === 'proto') {
          emit('ldh', 12);
          if (PROTOS[node[1]]) { emit('jeq', 0x800, null, no); emit('ldb', 23); emit('jeq', PROTOS[node[1]], yes, no); }
          else emit('jeq', { ip: 0x800, arp: 0x806, ip6: 0x86dd, ether: 0x800 }[node[1]], yes, no);
        } else if (k === 'host' || k === 'net') {
          var dir = node[1], value = node[2], mask = node[3], proto = node[4], places = [];
          if (!proto || proto === 'ip') places.push([0x800, 26, 30]);
          if (!proto || proto === 'arp') places.push([0x806, 28, 38]);
          emit('ldh', 12);
          places.forEach(function (pl, m) {
            var other = m === places.length - 1 ? no : new Label();
            emit('jeq', pl[0], null, other);
            var sp = dir === 'src' ? [pl[1]] : dir === 'dst' ? [pl[2]] : [pl[1], pl[2]];
            sp.forEach(function (off, j) {
              emit('ld', off);
              if (mask !== null) emit('and', mask);
              emit('jeq', value, yes, j === sp.length - 1 ? other : null);
            });
            if (other !== no) place(other);
          });
        } else if (k === 'port') {
          ipv4hdr(node[4] ? [PROTOS[node[4]]] : [6, 17], no);
          spots = node[1] === 'src' ? [14] : node[1] === 'dst' ? [16] : [14, 16];
          spots.forEach(function (off, j) {
            var miss = j === spots.length - 1 ? no : new Label();
            emit('ldh', ['x', off]);
            if (node[2] === node[3]) emit('jeq', node[2], yes, miss);
            else { emit('jge', node[2], null, miss); emit('jgt', node[3], miss, yes); }
            if (miss !== no) place(miss);
          });
        } else if (k === 'ether') {
          var b = node[2], first = ((b[0] << 24) >>> 0) + (b[1] << 16) + (b[2] << 8) + b[3], last2 = (b[4] << 8) + b[5];
          spots = node[1] === 'src' ? [6] : node[1] === 'dst' ? [0] : [6, 0];
          spots.forEach(function (off, j) {
            var miss = j === spots.length - 1 ? no : new Label();
            emit('ld', off); emit('jeq', first, null, miss); emit('ldh', off + 4); emit('jeq', last2, yes, miss);
            if (miss !== no) place(miss);
          });
        } else if (k === 'multicast') { emit('ldb', 0); emit('jset', 1, yes, no); }
        else if (k === 'len') {
          emit('ld', 'len');
          if (node[1] === 'greater') emit('jge', node[2], yes, no); else emit('jgt', node[2], no, yes);
        } else if (k === 'cmp') {
          var load = { 1: 'ldb', 2: 'ldh', 4: 'ld' }[node[3]];
          if (!load) fail('a size must be 1, 2 or 4 bytes');
          if (node[1] === 'ether') emit(load, node[2]);
          else if (node[1] === 'ip') { emit('ldh', 12); emit('jeq', 0x800, null, no); emit(load, 14 + node[2]); }
          else if (PROTOS[node[1]]) { ipv4hdr([PROTOS[node[1]]], no); emit(load, ['x', 14 + node[2]]); }
          else fail('can’t look inside ' + node[1] + '[…] here');
          var cmask = node[4], op = node[5], v = node[6];
          if (cmask !== null && op === '!=' && v === 0) { emit('jset', cmask, yes, no); return; }
          if (cmask !== null) emit('and', cmask);
          var j = { '=': ['jeq', yes, no], '!=': ['jeq', no, yes], '>': ['jgt', yes, no], '>=': ['jge', yes, no],
            '<': ['jge', no, yes], '<=': ['jgt', no, yes] }[op];
          emit(j[0], v, j[1], j[2]);
        }
      }
      var yes = new Label(), no = new Label();
      if (text.trim()) gen(parse(text), yes, no);
      place(yes); emit('ret', ACCEPT); place(no); emit('ret', 0);
      code.forEach(function (ins) { for (var q = 2; q < 4; q++) if (ins[q] instanceof Label) ins[q] = ins[q].at; });
      return code;
    }
    function run(prog, pkt, trace) {
      var A = 0, X = 0, pc = 0;
      for (var guard = 0; guard < 1000; guard++) {
        var ins = prog[pc], op = ins[0], arg = ins[1];
        if (trace) trace.push([pc, A, X]);
        if (op === 'ret') return arg;
        if (op === 'ldb' || op === 'ldh' || op === 'ld' || op === 'ldxb') {
          if (arg === 'len') A = pkt.length;
          else {
            var at = Array.isArray(arg) ? X + arg[1] : arg, size = { ldb: 1, ldh: 2, ld: 4, ldxb: 1 }[op];
            if (at + size > pkt.length) { if (trace) trace.push([-1, A, X]); return 0; }
            var v = 0;
            for (var b = 0; b < size; b++) v = v * 256 + pkt[at + b];
            if (op === 'ldxb') X = 4 * (v & 15); else A = v;
          }
          pc++;
        } else if (op === 'and') { A = (A & arg) >>> 0; pc++; }
        else {
          var ok = op === 'jeq' ? A === arg : op === 'jgt' ? A > arg : op === 'jge' ? A >= arg : (A & arg) !== 0;
          var target = ok ? ins[2] : ins[3];
          pc = target === null ? pc + 1 : target;
        }
      }
      return 0;
    }
    function show(prog) {
      return prog.map(function (ins, n) {
        var op = ins[0], arg = ins[1], t;
        if (op === 'ldxb') t = '4*([' + arg + ']&0xf)';
        else if (arg === 'len') t = '#pktlen';
        else if (op === 'ldb' || op === 'ldh' || op === 'ld') t = Array.isArray(arg) ? '[x + ' + arg[1] + ']' : '[' + arg + ']';
        else t = op === 'ret' ? '#' + arg : '#0x' + arg.toString(16);
        var line = '(' + pad(n, 3) + ') ' + (op + '        ').slice(0, 8) + ' ' + t;
        if (op.charAt(0) === 'j') {
          while (line.length < 32) line += ' ';
          line += 'jt ' + (ins[2] === null ? n + 1 : ins[2]) + '  jf ' + (ins[3] === null ? n + 1 : ins[3]);
        }
        return line;
      });
    }
    return { compile: compile, run: run, show: show };
  })();

  WIDGETS.bpfplay = function (el) {
    var PACKETS = [
      ["IP 192.168.1.4.58417 > 192.168.1.1.53: 36514+ question: info.cern.ch? (30)", '14c35e400b322ccf675e10c208004500003aed9040004011c9ccc0a80104c0a80101e43100350026e6348ea20100000100000000000004696e666f046365726e0263680000010001'],
      ["IP 192.168.1.4.58417 > 192.168.1.1.53: 51373+ question: info.cern.ch? (30)", '14c35e400b322ccf675e10c208004500003aed9140004011c9cbc0a80104c0a80101e43100350026ac0ec8ad0100000100000000000004696e666f046365726e02636800001c0001'],
      ["IP 192.168.1.1.53 > 192.168.1.4.58417: 36514 answer for info.cern.ch, 2 record(s) (77)", '2ccf675e10c214c35e400b32080045000069baaf40004011fc7ec0a80101c0a801040035e4310055870e8ea28180000100020000000004696e666f046365726e0263680000010001c00c0005000100000373001309776562616673393032046365726e02636800c02a00010001000001030004bcb8437f'],
      ["IP 192.168.1.1.53 > 192.168.1.4.58417: 51373 answer for info.cern.ch, 2 record(s) (89)", '2ccf675e10c214c35e400b32080045000075bab040004011fc71c0a80101c0a801040035e43100614e94c8ad8180000100020000000004696e666f046365726e02636800001c0001c00c0005000100000373001309776562616673393032046365726e02636800c02a001c000100000374001020011458020100a400000000010001a0'],
      ["IP 192.168.1.4.57426 > 188.184.67.127.80: Flags [S], seq 3208982406, win 64240, length 0", '14c35e400b322ccf675e10c208004500003c71c5400040060713c0a80104bcb8437fe0520050bf452f8600000000a002faf0391b0000020405b40402080ab160d13d000000000103030a'],
      ["IP 188.184.67.127.80 > 192.168.1.4.57426: Flags [S.], seq 3577108115, ack 3208982407, win 28960, length 0", '2ccf675e10c214c35e400b3208004500003c000040003c067cd8bcb8437fc0a801040050e052d5365693bf452f87a0127120f2690000020405ac0402080a416f6340b160d13d01030309'],
      ["IP 192.168.1.4.57426 > 188.184.67.127.80: Flags [.], seq 3208982407, ack 3577108116, win 63, length 0", '14c35e400b322ccf675e10c208004500003471c640004006071ac0a80104bcb8437fe0520050bf452f87d53656948010003f917500000101080ab160d1d9416f6340'],
      ["IP 192.168.1.4.57426 > 188.184.67.127.80: Flags [P.], seq 3208982407, ack 3577108116, win 63, length 76: HTTP: GET / HTTP/1.1", '14c35e400b322ccf675e10c208004500008071c74000400606cdc0a80104bcb8437fe0520050bf452f87d53656948018003f45d300000101080ab160d1d9416f6340474554202f20485454502f312e310d0a486f73743a20696e666f2e6365726e2e63680d0a557365722d4167656e743a206375726c2f382e31342e310d0a4163636570743a202a2f2a0d0a0d0a'],
      ["IP 188.184.67.127.80 > 192.168.1.4.57426: Flags [.], seq 3577108116, ack 3208982483, win 57, length 0", '2ccf675e10c214c35e400b3208004500003435d540003c06470bbcb8437fc0a801040050e052d5365694bf452fd380100039912e00000101080a416f6341b160d1d9'],
      ["IP 188.184.67.127.80 > 192.168.1.4.57426: Flags [P.], seq 3577108116, ack 3208982483, win 57, length 878: HTTP: HTTP/1.1 200 OK", '2ccf675e10c214c35e400b320800450003a235d640003c06439cbcb8437fc0a801040050e052d5365694bf452fd380180039088b00000101080a416f6350b160d1d9485454502f312e3120323030204f4b0d0a446174653a2053756e2c2032372053657020323032362031373a33343a313820474d540d0a5365727665723a204170616368650d0a4c6173742d4d6f6469666965643a205765642c2030352046656220323031342031363a30303a333120474d540d0a455461673a20223238362d34663161616462333130356330220d0a4163636570742d52616e6765733a2062797465730d0a436f6e74656e742d4c656e6774683a203634360d0a436f6e6e656374696f6e3a20636c6f73650d0a436f6e74656e742d547970653a20746578742f68746d6c0d0a0d0a3c68746d6c3e3c686561643e3c2f686561643e3c626f64793e3c6865616465723e0a3c7469746c653e687474703a2f2f696e666f2e6365726e2e63683c2f7469746c653e0a3c2f6865616465723e0a0a3c68313e687474703a2f2f696e666f2e6365726e2e6368202d20686f6d65206f662074686520666972737420776562736974653c2f68313e0a3c703e46726f6d206865726520796f752063616e3a3c2f703e0a3c756c3e0a3c6c693e3c6120687265663d22687474703a2f2f696e666f2e6365726e2e63682f6879706572746578742f5757572f54686550726f6a6563742e68746d6c223e42726f7773652074686520666972737420776562736974653c2f613e3c2f6c693e0a3c6c693e3c6120687265663d22687474703a2f2f6c696e652d6d6f64652e6365726e2e63682f7777772f6879706572746578742f5757572f54686550726f6a6563742e68746d6c223e42726f777365207468652066697273742077656273697465207573696e6720746865206c696e652d6d6f64652062726f777365722073696d756c61746f723c2f613e3c2f6c693e0a3c6c693e3c6120687265663d22687474703a2f2f686f6d652e7765622e6365726e2e63682f746f706963732f62697274682d776562223e4c6561726e2061626f757420746865206269727468206f6620746865207765623c2f613e3c2f6c693e0a3c6c693e3c6120687265663d22687474703a2f2f686f6d652e7765622e6365726e2e63682f61626f7574223e4c6561726e2061626f7574204345524e2c207468652070687973696373206c61626f7261746f727920776865726520746865207765622077617320626f726e3c2f613e3c2f6c693e0a3c2f756c3e0a3c2f626f64793e3c2f68746d6c3e0a'],
      ["IP 192.168.1.4.57426 > 188.184.67.127.80: Flags [.], seq 3208982483, ack 3577108994, win 63, length 0", '14c35e400b322ccf675e10c208004500003471c8400040060718c0a80104bcb8437fe0520050bf452fd3d5365a028010003f8d0c00000101080ab160d278416f6350'],
      ["IP 188.184.67.127.80 > 192.168.1.4.57426: Flags [F.], seq 3577108994, ack 3208982483, win 57, length 0", '2ccf675e10c214c35e400b3208004500003435d740003c064709bcb8437fc0a801040050e052d5365a02bf452fd3801100398db000000101080a416f6350b160d1d9'],
      ["IP 192.168.1.4.57426 > 188.184.67.127.80: Flags [F.], seq 3208982483, ack 3577108995, win 63, length 0", '14c35e400b322ccf675e10c208004500003471c9400040060717c0a80104bcb8437fe0520050bf452fd3d5365a038011003f8d0a00000101080ab160d278416f6350'],
      ["IP 192.168.1.4 > 1.1.1.1: ICMP echo request, id 15080, seq 1, length 64", '14c35e400b322ccf675e10c208004500005449c3400040012d38c0a8010401010101080015a63ae800019a53b96a0000000088df0c0000000000101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031323334353637'],
      ["IP 188.184.67.127.80 > 192.168.1.4.57426: Flags [.], seq 3577108995, ack 3208982484, win 57, length 0", '2ccf675e10c214c35e400b3208004500003435d840003c064708bcb8437fc0a801040050e052d5365a03bf452fd4801000398d0f00000101080a416f6351b160d278'],
      ["IP 1.1.1.1 > 192.168.1.4: ICMP echo reply, id 15080, seq 1, length 64", '2ccf675e10c214c35e400b32080045000054343e00003a0188bd01010101c0a8010400001da63ae800019a53b96a0000000088df0c0000000000101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031323334353637'],
      ["IP 192.168.1.4 > 1.1.1.1: ICMP echo request, id 15080, seq 2, length 64", '14c35e400b322ccf675e10c20800450000544a26400040012cd5c0a801040101010108006c9e3ae800029b53b96a0000000030e60c0000000000101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031323334353637'],
      ["IP 1.1.1.1 > 192.168.1.4: ICMP echo reply, id 15080, seq 2, length 64", '2ccf675e10c214c35e400b32080045000054901800003a012ce301010101c0a801040000749e3ae800029b53b96a0000000030e60c0000000000101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031323334353637'],
      ["ARP, Request who-has 192.168.1.1 tell 192.168.1.4", 'ffffffffffff2ccf675e10c2080600010800060400012ccf675e10c2c0a80104000000000000c0a80101'],
      ["ARP, Reply 192.168.1.1 is-at 14:c3:5e:40:0b:32", '2ccf675e10c214c35e400b320806000108000604000214c35e400b32c0a801012ccf675e10c2c0a80104'],
      ["IP 192.168.1.4 > 1.1.1.1: ICMP echo request, id 15081, seq 1, length 64", '14c35e400b322ccf675e10c2080045000054ad8d40000101086ec0a80104010101010800d62e3ae900011554b96a000000004b550e0000000000101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031323334353637'],
      ["IP 192.168.1.1 > 192.168.1.4: ICMP time exceeded in-transit, length 92", '2ccf675e10c214c35e400b32080045c00070adae0000400148c9c0a80101c0a801040b00f4ff0000000045000054ad8d40000101086ec0a80104010101010800d62e3ae900011554b96a000000004b550e0000000000101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031323334353637'],
      ["IP 192.168.1.4.56429 > 192.168.1.1.53: 14839+ question: example.org? (29)", '14c35e400b322ccf675e10c2080045000039174340004011a01bc0a80104c0a80101dc6d00350025934039f701000001000000000000076578616d706c65036f72670000010001'],
      ["IP 192.168.1.4.56429 > 192.168.1.1.53: 48011+ question: example.org? (29)", '14c35e400b322ccf675e10c2080045000039174440004011a01ac0a80104c0a80101dc6d00350025f6abbb8b01000001000000000000076578616d706c65036f726700001c0001'],
      ["IP 192.168.1.1.53 > 192.168.1.4.56429: 14839 answer for example.org, 2 record(s) (61)", '2ccf675e10c214c35e400b32080045000059e1fe40004011d53fc0a80101c0a801040035dc6d0045d83039f781800001000200000000076578616d706c65036f72670000010001c00c00010001000000240004ac429dedc00c0001000100000024000468141a88'],
      ["IP 192.168.1.1.53 > 192.168.1.4.56429: 48011 answer for example.org, 2 record(s) (85)", '2ccf675e10c214c35e400b32080045000071e20240004011d523c0a80101c0a801040035dc6d005db08fbb8b81800001000200000000076578616d706c65036f726700001c0001c00c001c00010000012c001026064700001000000000000068141a88c00c001c00010000012c0010260647000010000000000000ac429ded'],
      ["IP 192.168.1.4.58798 > 172.66.157.237.443: Flags [S], seq 1912436191, win 64240, length 0", '14c35e400b322ccf675e10c208004500003c67c940004006c716c0a80104ac429dede5ae01bb71fd75df00000000a002faf095100000020405b40402080a1e1dbebb000000000103030a'],
      ["IP 172.66.157.237.443 > 192.168.1.4.58798: Flags [S.], seq 3510948663, ack 1912436192, win 65535, length 0", '2ccf675e10c214c35e400b3208004500003c00004000380636e0ac429dedc0a8010401bbe5aed144d33771fd75e0a012ffff75bd0000020405780402080a69e80c071e1dbebb0103030d'],
      ["IP 192.168.1.4.58798 > 172.66.157.237.443: Flags [.], seq 1912436192, ack 3510948664, win 63, length 0", '14c35e400b322ccf675e10c208004500003467ca40004006c71dc0a80104ac429dede5ae01bb71fd75e0d144d3388010003fa3f600000101080a1e1dbed969e80c07'],
    ];
    var pkts = PACKETS.map(function (p) {
      var b = [];
      for (var i = 0; i < p[1].length; i += 2) b.push(parseInt(p[1].slice(i, i + 2), 16));
      return { text: p[0], bytes: b };
    });
    frame(el, 'Filter lab',
      'These are 29 real packets, captured on a Raspberry Pi. Type a capture filter: it’s compiled into a little program, ' +
      'which runs on every packet, as it would in the kernel. Click a packet to follow its trip through the program.');
    var input = h('input', { type: 'text', value: 'tcp port 80', 'aria-label': 'capture filter', spellcheck: 'false',
      autocapitalize: 'off', style: 'flex:1 1 16em;min-width:0;font-family:var(--mono)' });
    var presets = h('div', { class: 'row', style: 'gap:6px' });
    ['tcp port 80', 'icmp or arp', 'host 192.168.1.1', 'udp port 53 and src host 192.168.1.1',
      'tcp[tcpflags] & tcp-syn != 0', 'broadcast', 'greater 500', 'not tcp and not udp'].forEach(function (f) {
      presets.appendChild(btn(f, function () { input.value = f; update(); }, 'small ghost'));
    });
    var status = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    var list = h('div', { style: 'max-height:19em;overflow:auto;border:1px solid var(--line);border-radius:6px;margin-top:8px;' +
      'font-family:var(--mono);font-size:78%;background:var(--surface)' });
    var prog = h('pre', { style: 'margin:8px 0 0;padding:8px 10px;background:var(--code-bg);border-radius:6px;overflow:auto;' +
      'font-size:78%;line-height:1.5;max-height:22em' });
    var traceNote = h('p', { class: 'w-hint', style: 'margin:8px 0 0' });
    el.appendChild(h('div', { class: 'row' }, h('label', { style: 'flex:1 1 100%' }, 'Filter: ', input)));
    el.appendChild(presets);
    el.appendChild(status);
    el.appendChild(list);
    el.appendChild(traceNote);
    el.appendChild(prog);
    var rows = pkts.map(function (p, i) {
      var r = h('div', { role: 'button', tabindex: '0', style: 'padding:2px 8px;white-space:pre;cursor:pointer;border-left:4px solid transparent',
        onclick: function () { selected = i; paint(); },
        onkeydown: function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selected = i; paint(); } } },
        pad(i + 1, 2, ' ') + '  ' + p.text);
      list.appendChild(r);
      return r;
    });
    var program = null, selected = 4, lines = [];
    function update() {
      try {
        program = BPF.compile(input.value);
        lines = BPF.show(program);
        input.style.borderColor = '';
      } catch (err) {
        if (!err.filter) throw err;
        program = null;
        input.style.borderColor = 'var(--red)';
        status.innerHTML = '<span class="bad">Filter problem:</span> ' + err.message;
      }
      paint();
    }
    function paint() {
      if (!program) {
        rows.forEach(function (r) { r.style.opacity = '0.45'; r.style.background = ''; r.style.borderLeftColor = 'transparent'; });
        prog.textContent = ''; traceNote.textContent = '';
        return;
      }
      var hits = 0;
      pkts.forEach(function (p, i) {
        var ok = BPF.run(program, p.bytes) !== 0;
        if (ok) hits++;
        rows[i].style.opacity = ok ? '1' : '0.42';
        rows[i].style.fontWeight = ok ? '700' : '400';
        rows[i].style.background = i === selected ? 'var(--tint-yellow)' : ok ? 'var(--tint-green)' : '';
        rows[i].style.borderLeftColor = i === selected ? 'var(--yellow)' : ok ? 'var(--green)' : 'transparent';
      });
      status.innerHTML = '<b>' + hits + '</b> of ' + pkts.length + ' packets match. The program has <b>' + program.length +
        '</b> instructions' + (input.value.trim() ? '' : ' (an empty filter accepts everything)') + '.';
      var trace = [];
      var verdict = BPF.run(program, pkts[selected].bytes, trace);
      var seen = {};
      trace.forEach(function (t) { seen[t[0]] = t; });
      prog.innerHTML = '';
      lines.forEach(function (line, n) {
        var t = seen[n], span = h('span', { style: 'display:block;' + (t ? 'font-weight:700' : 'opacity:0.45') });
        span.textContent = line;
        if (t && program[n][0] !== 'ret') {
          var after = trace[trace.indexOf(t) + 1] || t;
          span.appendChild(h('span', { style: 'color:var(--teal-ink);font-weight:400', text: '   ← A=0x' + after[1].toString(16) + ', X=' + after[2] }));
        }
        if (t && program[n][0] === 'ret') span.style.color = verdict ? 'var(--green)' : 'var(--red)';
        prog.appendChild(span);
      });
      var steps = trace.filter(function (t) { return t[0] >= 0; }).length;
      traceNote.innerHTML = 'Packet <b>' + (selected + 1) + '</b> ran ' + steps + ' instructions and was ' +
        (verdict ? '<span class="good">accepted</span>' : '<span class="bad">rejected</span>') +
        '. Bold lines are the ones it went through; A and X show the two registers just after each step.';
    }
    input.addEventListener('input', update);
    update();
  };

  // ---------------------------------------------------------------- ch17: constellations in the noise
  // Mirrors labs/ch17/signals.py (qam_errors).

  WIDGETS.qam = function (el) {
    frame(el, 'Dots in the fog',
      'Each symbol is one dot on a grid: its position is set by the wave’s strength and timing. Noise smudges where the dot lands, ' +
      'and the receiver picks the nearest grid point. <span style="color:var(--red);font-weight:700">Red</span> dots were misread.');
    var mod = h('select', { 'aria-label': 'modulation' });
    [[4, 'QPSK (2 bits)'], [16, '16-QAM (4 bits)'], [64, '64-QAM (6 bits)'], [256, '256-QAM (8 bits)'], [1024, '1024-QAM (10 bits)']].forEach(function (m) {
      mod.appendChild(h('option', { value: String(m[0]), text: m[1] }));
    });
    mod.value = '64';
    var snr = h('input', { type: 'range', min: '0', max: '55', step: '1', value: '25', 'aria-label': 'signal to noise ratio' });
    var snrOut = h('b');
    var presets = h('div', { class: 'row', style: 'gap:6px' });
    [['Pi by the router', 55], ['Bob’s laptop', 37], ['through two walls', 22], ['in the garden', 12]].forEach(function (p) {
      presets.appendChild(btn(p[0] + ' (' + p[1] + ' dB)', function () { snr.value = String(p[1]); draw(); }, 'small ghost'));
    });
    var holder = h('div', { style: 'max-width:340px;margin:10px auto 0' });
    var stats = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Constellation: ', mod), h('label', {}, 'Signal-to-noise: ', snr, snrOut)));
    el.appendChild(presets);
    el.appendChild(holder);
    el.appendChild(stats);
    function gauss() {
      var u = 1 - Math.random(), v = Math.random();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    }
    function draw() {
      var M = +mod.value, side = Math.round(Math.sqrt(M)), db = +snr.value;
      var axis = [];
      for (var i = 0; i < side; i++) axis.push(2 * i - (side - 1));
      var scale = Math.sqrt(2 * axis.reduce(function (a, v) { return a + v * v; }, 0) / side);
      var sigma = Math.sqrt(1 / (2 * Math.pow(10, db / 10))) * scale;
      var S = 320, pad = 18, span = (side - 1) + 2, k = (S - 2 * pad) / (2 * span);
      function px(v) { return S / 2 + v * k; }
      var svg = s('svg', { class: 'dia', viewBox: '0 0 ' + S + ' ' + S, role: 'img', 'aria-label': M + '-point constellation with noise' });
      svg.appendChild(s('rect', { x: 1, y: 1, width: S - 2, height: S - 2, rx: 8, fill: 'var(--card)', stroke: 'var(--line)' }));
      svg.appendChild(s('line', { x1: S / 2, y1: 6, x2: S / 2, y2: S - 6, class: 'grid' }));
      svg.appendChild(s('line', { x1: 6, y1: S / 2, x2: S - 6, y2: S / 2, class: 'grid' }));
      var n = M >= 256 ? 2500 : 1200, wrong = 0, dots = [];
      for (var t = 0; t < n; t++) {
        var x = axis[Math.floor(Math.random() * side)], y = axis[Math.floor(Math.random() * side)];
        var hx = x + gauss() * sigma, hy = y + gauss() * sigma;
        var gx = Math.max(-(side - 1), Math.min(side - 1, 2 * Math.round((hx + side - 1) / 2) - (side - 1)));
        var gy = Math.max(-(side - 1), Math.min(side - 1, 2 * Math.round((hy + side - 1) / 2) - (side - 1)));
        var bad = gx !== x || gy !== y;
        if (bad) wrong++;
        dots.push([hx, hy, bad]);
      }
      var r = M >= 256 ? 1.3 : 2;
      dots.forEach(function (d) {
        if (Math.abs(d[0]) > span || Math.abs(d[1]) > span) return;
        svg.appendChild(s('circle', { cx: px(d[0]).toFixed(1), cy: px(-d[1]).toFixed(1), r: d[2] ? r + 0.6 : r,
          fill: d[2] ? 'var(--red)' : 'var(--blue)', 'fill-opacity': d[2] ? 0.9 : 0.35 }));
      });
      axis.forEach(function (ax) {
        axis.forEach(function (ay) {
          svg.appendChild(s('circle', { cx: px(ax), cy: px(ay), r: M >= 256 ? 1.4 : 2.6, fill: 'var(--ink)' }));
        });
      });
      holder.innerHTML = '';
      holder.appendChild(svg);
      snrOut.textContent = db + ' dB';
      var rate = wrong / n, bits = Math.log2(M);
      var verdict = rate < 0.01 ? '<span class="good">usable</span>: error-correcting codes can fix the few mistakes'
        : rate < 0.1 ? '<span class="bad">too many mistakes</span>: Wi-Fi would step down to fewer dots'
          : '<span class="bad">hopeless</span>';
      stats.innerHTML = '<b>' + bits + '</b> bits per symbol · <b>' + (100 * rate).toFixed(1) + '%</b> of symbols misread · ' + verdict + '.';
    }
    mod.addEventListener('change', draw);
    snr.addEventListener('input', draw);
    draw();
  };

  // ---------------------------------------------------------------- ch18: build a real frame
  // Mirrors labs/ch18/frames.py (ethernet_frame). Uses Chapter 10's crc32().

  WIDGETS.framebuild = function (el) {
    frame(el, 'Build a frame',
      'Choose where it goes and what’s in it. Every byte appears below, colored by its job, with the padding and the CRC-32 check added exactly as a network card would.');
    var PI = [0x2c, 0xcf, 0x67, 0x5e, 0x10, 0xc2];
    var DST = { router: [0x14, 0xc3, 0x5e, 0x40, 0x0b, 0x32], everyone: [255, 255, 255, 255, 255, 255], laptop: [0xe2, 0x5f, 0xb1, 0x3c, 0x77, 0x0a] };
    var dst = h('select', { 'aria-label': 'destination' },
      h('option', { value: 'router', text: 'the router' }), h('option', { value: 'everyone', text: 'everyone (broadcast)' }),
      h('option', { value: 'laptop', text: 'Bob’s laptop' }));
    var type = h('select', { 'aria-label': 'type' },
      h('option', { value: '88b5', text: '0x88B5: an experiment' }), h('option', { value: '0800', text: '0x0800: IPv4' }),
      h('option', { value: '0806', text: '0x0806: ARP' }), h('option', { value: '86dd', text: '0x86DD: IPv6' }));
    var vlan = h('input', { type: 'checkbox', 'aria-label': 'add a VLAN tag' });
    var vid = h('input', { type: 'number', min: '1', max: '4094', value: '20', style: 'width:5em', 'aria-label': 'VLAN number' });
    var msg = h('input', { type: 'text', value: 'hi, router!', 'aria-label': 'message', style: 'flex:1 1 12em;min-width:0' });
    var size = h('input', { type: 'range', min: '0', max: '1500', step: '1', value: '11', 'aria-label': 'data size' });
    var grid = h('div', { style: 'display:grid;grid-template-columns:repeat(16, minmax(0, 1fr));gap:2px;margin:10px 0;font-family:var(--mono);font-size:80%' });
    var more = h('p', { class: 'w-hint', style: 'margin:0' });
    var stats = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'To: ', dst), h('label', {}, 'Type: ', type)));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, vlan, ' VLAN tag, number ', vid)));
    el.appendChild(h('div', { class: 'row' }, h('label', { style: 'flex:1 1 100%' }, 'Data: ', msg)));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'or just make it ', size, ' bytes long')));
    el.appendChild(grid); el.appendChild(more); el.appendChild(stats);
    var COLORS = { to: 'var(--tint-blue)', from: 'var(--tint-blue)', tag: 'var(--tint-orange)', type: 'var(--tint-blue)',
      data: 'var(--tint-yellow)', pad: 'var(--card)', check: 'var(--tint-red)' };
    function draw(fromSlider) {
      var data = [];
      if (fromSlider) { data = new Array(+size.value).fill(0x2e); msg.value = '(' + size.value + ' bytes of dots)'; }
      else {
        data = Array.from(new TextEncoder().encode(msg.value));
        if (data.length > 1500) data = data.slice(0, 1500);
        size.value = String(data.length);
      }
      var parts = [['to', DST[dst.value]], ['from', PI]];
      if (vlan.checked) { var v = Math.max(1, Math.min(4094, +vid.value || 1)); parts.push(['tag', [0x81, 0x00, v >> 8, v & 255]]); }
      var t = parseInt(type.value, 16);
      parts.push(['type', [t >> 8, t & 255]]);
      parts.push(['data', data]);
      var pad = Math.max(0, 46 - data.length);
      parts.push(['pad', new Array(pad).fill(0)]);
      var body = [];
      parts.forEach(function (p) { body = body.concat(p[1]); });
      var c = crc32(body);
      var fcs = [c & 255, (c >>> 8) & 255, (c >>> 16) & 255, (c >>> 24) & 255];
      parts.push(['check', fcs]);
      grid.innerHTML = '';
      var shown = 0, LIMIT = 160;
      parts.forEach(function (p) {
        p[1].forEach(function (byte, i) {
          if (p[0] === 'data' && data.length > LIMIT && i === 64) {
            grid.appendChild(h('span', { style: 'grid-column:span 16;text-align:center;color:var(--muted);font-family:var(--sans)',
              text: '… ' + (data.length - 128).toLocaleString() + ' more data bytes …' }));
          }
          if (p[0] === 'data' && data.length > LIMIT && i >= 64 && i < data.length - 64) return;
          grid.appendChild(h('span', { title: p[0], style: 'text-align:center;padding:2px 0;border-radius:3px;background:' + COLORS[p[0]] +
            (p[0] === 'pad' ? ';color:var(--muted)' : ''), text: pad2(byte) }));
          shown++;
        });
      });
      var len = body.length + 4, wire = len + 8 + 12;
      more.innerHTML = '<span style="background:var(--tint-blue);padding:0 4px">addresses and type</span> ' +
        (vlan.checked ? '<span style="background:var(--tint-orange);padding:0 4px">VLAN tag</span> ' : '') +
        '<span style="background:var(--tint-yellow);padding:0 4px">your data</span> ' +
        (pad ? '<span style="background:var(--card);padding:0 4px">padding</span> ' : '') +
        '<span style="background:var(--tint-red);padding:0 4px">CRC-32 check</span>';
      stats.innerHTML = 'Frame: <b>' + len + '</b> bytes' + (pad ? ', including <b>' + pad + '</b> bytes of padding' : '') +
        '. On the cable, with the preamble and the gap: <b>' + wire + '</b> bytes, of which <b>' +
        (100 * data.length / wire).toFixed(1) + '%</b> is your data. At 1 Gb/s it takes <b>' + (wire * 8 / 1000).toFixed(3) + ' µs</b>.';
    }
    function pad2(n) { return pad(n.toString(16), 2); }
    [dst, type, vlan, vid].forEach(function (c) { c.addEventListener('change', function () { draw(false); }); });
    vid.addEventListener('input', function () { draw(false); });
    msg.addEventListener('input', function () { draw(false); });
    size.addEventListener('input', function () { draw(true); });
    draw(false);
  };

  // ---------------------------------------------------------------- ch18: a switch with VLANs
  // Mirrors labs/ch18/frames.py (Switch).

  WIDGETS.vlanswitch = function (el) {
    frame(el, 'One switch, two networks',
      'Put each port in a VLAN, then send. A switch only floods a broadcast to ports in the <em>same</em> VLAN, and only learns addresses within a VLAN. ' +
      'Port 6 is a trunk to the router: it carries both, with tags.');
    var DEV = [
      { name: 'laptop', port: 1, pos: [70, 60], vlan: 10 }, { name: 'TV', port: 2, pos: [70, 150], vlan: 10 },
      { name: 'gaming PC', port: 3, pos: [70, 240], vlan: 10 }, { name: 'doorbell', port: 4, pos: [650, 60], vlan: 20 },
      { name: 'thermostat', port: 5, pos: [650, 150], vlan: 20 }, { name: 'router', port: 6, pos: [650, 240], trunk: true }];
    var VCOL = { 10: 'var(--blue)', 20: 'var(--orange)' };
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 300', role: 'img', 'aria-label': 'a switch with six ports and two VLANs' });
    svg.appendChild(s('rect', { width: 720, height: 300, rx: 10, class: 'f-card' }));
    var sw = { x: 270, y: 100, w: 180, h: 100 };
    DEV.forEach(function (d, i) {
      var left = d.pos[0] < 360;
      d.pp = [left ? sw.x : sw.x + sw.w, sw.y + 22 + (i % 3) * 28];
      d.route = [[d.pos[0] + (left ? 40 : -40), d.pos[1]], [d.pos[0] + (left ? 90 : -90), d.pos[1]], d.pp];
      d.cable = s('path', { d: 'M' + d.route.map(function (p) { return p.join(','); }).join(' L'), class: 'wire', 'stroke-width': d.trunk ? 6 : 4 });
      svg.appendChild(d.cable);
    });
    svg.appendChild(s('rect', { x: sw.x, y: sw.y, width: sw.w, height: sw.h, rx: 10, fill: '#2b7a73', stroke: '#17423e', 'stroke-width': 2.5 }));
    svg.appendChild(s('text', { x: 360, y: 156, class: 'mid slab b', fill: '#fff', text: 'SWITCH' }));
    DEV.forEach(function (d) {
      var left = d.pos[0] < 360;
      d.dot = s('circle', { cx: d.pp[0], cy: d.pp[1], r: 8, 'stroke-width': 2, stroke: '#fff' });
      svg.appendChild(d.dot);
      svg.appendChild(s('text', { x: d.pp[0] + (left ? 14 : -14), y: d.pp[1] + 4, class: (left ? '' : 'end ') + 'xs b', fill: '#fff', text: String(d.port) }));
      svg.appendChild(s('use', { href: d.trunk ? '#router' : '#computer', x: d.pos[0] - 30, y: d.pos[1] - 26, width: 60, height: d.trunk ? 40 : 52 }));
      d.label = s('text', { x: d.pos[0], y: d.pos[1] + 42, class: 'mid xs b' });
      svg.appendChild(d.label);
    });
    var dotLayer = s('g');
    svg.appendChild(dotLayer);
    el.appendChild(svg);
    var controls = h('div', { class: 'row' });
    DEV.forEach(function (d) {
      if (d.trunk) return;
      var sel = h('select', { 'aria-label': d.name + ' VLAN' }, h('option', { value: '10', text: 'VLAN 10' }), h('option', { value: '20', text: 'VLAN 20' }));
      sel.value = String(d.vlan);
      sel.addEventListener('change', function () { d.vlan = +sel.value; table = {}; paint(); say('Port ' + d.port + ' moved to VLAN ' + d.vlan + '. The switch forgot its table.'); });
      controls.appendChild(h('label', {}, d.name + ': ', sel));
    });
    var from = h('select', { 'aria-label': 'from' }), to = h('select', { 'aria-label': 'to' });
    DEV.forEach(function (d, i) {
      if (!d.trunk) from.appendChild(h('option', { value: String(i), text: d.name }));
      to.appendChild(h('option', { value: String(i), text: d.name }));
    });
    to.appendChild(h('option', { value: 'ff', text: 'everyone (broadcast)' }));
    from.value = '3'; to.value = 'ff';
    var sendBtn = btn('Send', send);
    var narr = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:2.6em' });
    el.appendChild(controls);
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Send from ', from), h('label', {}, 'to ', to), sendBtn));
    el.appendChild(narr);
    var table = {}, busy = false;
    function say(t) { narr.innerHTML = t; }
    function paint() {
      DEV.forEach(function (d) {
        d.dot.setAttribute('fill', d.trunk ? 'var(--purple)' : VCOL[d.vlan]);
        d.label.textContent = d.trunk ? 'router (trunk: 10 and 20)' : d.name + ' · VLAN ' + d.vlan;
        d.label.setAttribute('fill', d.trunk ? 'var(--purple)' : VCOL[d.vlan]);
      });
    }
    function path(pts, colour, reverse, done) {
      var seq = reverse ? pts.slice().reverse() : pts;
      var c = s('circle', { r: 9, fill: colour, stroke: 'var(--surface)', 'stroke-width': 2, cx: seq[0][0], cy: seq[0][1] });
      dotLayer.appendChild(c);
      var i = 0;
      (function next() {
        if (i >= seq.length - 1) { setTimeout(function () { c.remove(); }, 400); if (done) done(); return; }
        tween(c, seq[i], seq[i + 1], 260, function () { i++; next(); });
      })();
    }
    function send() {
      if (busy) return;
      var src = DEV[+from.value], dst = to.value === 'ff' ? null : DEV[+to.value];
      if (dst === src) { say('That’s the same device!'); return; }
      busy = true; sendBtn.disabled = true;
      var v = src.vlan, key = v + '/' + src.name;
      path(src.route, VCOL[v], false, function () {
        table[key] = src.port;
        var members = DEV.filter(function (d) { return d !== src && (d.trunk || d.vlan === v); });
        var outs, why;
        if (dst && !dst.trunk && dst.vlan !== v) {
          outs = members;
          why = 'The switch has never seen <b>' + dst.name + '</b> in VLAN ' + v + ' (it’s in VLAN ' + dst.vlan + '), so it floods to VLAN ' + v +
            ' only. The ' + dst.name + ' never hears it. To cross between VLANs, frames have to go through the router, which can refuse them.';
        } else if (dst && table[v + '/' + dst.name] !== undefined) {
          outs = [dst]; why = 'The switch learned where <b>' + dst.name + '</b> is (in VLAN ' + v + '), so only that port gets it.';
        } else {
          outs = members;
          why = (dst ? 'Not learned yet, so it’s flooded' : 'A broadcast is flooded') + ', but only to ports in <b>VLAN ' + v + '</b>' +
            (members.some(function (d) { return d.trunk; }) ? ', and up the trunk to the router with a tag saying “VLAN ' + v + '”' : '') + '.';
        }
        if (dst && table[v + '/' + dst.name] === undefined && (dst.trunk || dst.vlan === v)) table[v + '/' + dst.name] = dst.port;
        var heard = outs.map(function (d) { return d.name; });
        say(why + ' Heard by: <b>' + (heard.join(', ') || 'nobody') + '</b>.');
        var left = outs.length;
        if (!left) { busy = false; sendBtn.disabled = false; }
        outs.forEach(function (o) { path(o.route, VCOL[v], true, function () { if (--left === 0) { busy = false; sendBtn.disabled = false; } }); });
      });
    }
    paint();
    say('Two families of devices share one switch. Send a broadcast from the doorbell, then from the laptop.');
  };

  // ---------------------------------------------------------------- ch19: sharing the air (CSMA/CA)
  // Mirrors labs/ch19/wifi_sim.py.

  WIDGETS.airtime = function (el) {
    var DIFS = 4, FRAME = 20, RTS = 3, CWMIN = 15, CWMAX = 1023, COLS = 110;
    frame(el, 'Rush hour in the air',
      'Each row is one device, and every device always has something to send. Time runs left to right, one 9 µs slot per square. ' +
      '<span style="color:var(--green);font-weight:700">Green</span>: a frame that got through. <span style="color:var(--red);font-weight:700">Red</span>: a collision. ' +
      '<span style="color:var(--purple);font-weight:700">Purple</span>: asking permission (RTS/CTS).');
    var count = h('select', { 'aria-label': 'devices' });
    [2, 4, 8].forEach(function (n) { count.appendChild(h('option', { value: String(n), text: n + ' devices' })); });
    count.value = '4';
    var hid = h('input', { type: 'checkbox', 'aria-label': 'hidden stations' });
    var rts = h('input', { type: 'checkbox', 'aria-label': 'RTS/CTS' });
    var slow = h('input', { type: 'checkbox', 'aria-label': 'one slow device' });
    var run = btn('Pause', function () { running = !running; run.textContent = running ? 'Pause' : 'Run'; }, 'small');
    var holder = h('div', { style: 'margin-top:8px' });
    var stats = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);margin-top:8px' });
    el.appendChild(h('div', { class: 'row' }, count, h('label', {}, hid, ' odd and even rows can’t hear each other'), run));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, rts, ' ask first (RTS/CTS)'), h('label', {}, slow, ' device A is far away (8× slower)')));
    el.appendChild(holder);
    el.appendChild(stats);
    var st, rows, rects, t, nav, running = true;
    function rnd(n) { return Math.floor(Math.random() * (n + 1)); }
    function reset() {
      var n = +count.value;
      st = [];
      for (var i = 0; i < n; i++) st.push({ name: String.fromCharCode(65 + i), group: i % 2, slow: slow.checked && i === 0, cw: CWMIN, backoff: rnd(CWMIN),
        quiet: 0, sending: 0, clean: true, asking: false, tries: 0, delivered: 0, collided: 0, airtime: 0 });
      rows = st.map(function () { return []; });
      t = 0; nav = 0;
      holder.innerHTML = '';
      var cell = 5, gap = 1, W = 70 + COLS * (cell + gap), H = n * 16 + 4;
      var svg = s('svg', { class: 'dia', viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'transmissions over time' });
      rects = [];
      st.forEach(function (sn, r) {
        var y = 2 + r * 16;
        svg.appendChild(s('text', { x: 62, y: y + 10, class: 'end xs', text: 'device ' + sn.name + (sn.slow ? ' (far)' : '') }));
        var rr = [];
        for (var c = 0; c < COLS; c++) {
          var rect = s('rect', { x: 70 + c * (cell + gap), y: y, width: cell, height: 12, rx: 1, fill: 'var(--card)' });
          svg.appendChild(rect); rr.push(rect);
        }
        rects.push(rr);
      });
      holder.appendChild(svg);
    }
    function dur(sn) { return FRAME * (sn.slow ? 8 : 1); }
    function finish(sn) {
      if (sn.clean && sn.asking) { sn.asking = false; sn.sending = dur(sn); nav = dur(sn); return; }
      if (sn.clean) { sn.delivered++; sn.cw = CWMIN; sn.tries = 0; }
      else { sn.collided++; sn.tries++; sn.cw = Math.min(2 * sn.cw + 1, CWMAX); if (sn.tries > 7) { sn.cw = CWMIN; sn.tries = 0; } }
      sn.backoff = rnd(sn.cw); sn.asking = false;
    }
    function step() {
      var talking = st.filter(function (x) { return x.sending; });
      if (talking.length > 1) talking.forEach(function (x) { x.clean = false; });
      st.forEach(function (sn, i) {
        var hears = talking.some(function (o) { return o !== sn && (!hid.checked || o.group === sn.group); });
        var mark = 0;
        if (sn.sending) {
          mark = sn.asking ? 3 : sn.clean ? 1 : 2;
          sn.sending--; sn.airtime++;
          if (!sn.sending) finish(sn);
        } else if (nav || hears) sn.quiet = 0;
        else {
          sn.quiet++;
          if (sn.quiet > DIFS) {
            if (sn.backoff === 0) { sn.asking = rts.checked; sn.sending = rts.checked ? RTS : dur(sn); sn.clean = true; }
            else sn.backoff--;
          }
        }
        rows[i].push(mark);
        if (rows[i].length > COLS) rows[i].shift();
      });
      nav = Math.max(0, nav - 1);
      t++;
    }
    function paint() {
      var colours = ['var(--card)', 'var(--green)', 'var(--red)', 'var(--purple)'];
      rows.forEach(function (r, ri) {
        for (var c = 0; c < COLS; c++) {
          var v = r[r.length - COLS + c];
          rects[ri][c].setAttribute('fill', v === undefined ? 'var(--card)' : colours[v]);
        }
      });
      var useful = st.reduce(function (a, x) { return a + x.delivered * FRAME; }, 0);
      var frames = st.reduce(function (a, x) { return a + x.delivered; }, 0);
      var tries = frames + st.reduce(function (a, x) { return a + x.collided; }, 0);
      var air = st.reduce(function (a, x) { return a + x.airtime; }, 0) || 1;
      var txt = 'Air used for data that got through: <b>' + Math.round(100 * useful / Math.max(t, 1)) + '%</b> · attempts that collided: <b>' +
        Math.round(100 * (tries - frames) / Math.max(tries, 1)) + '%</b>';
      if (slow.checked) txt += ' · device A delivered ' + st[0].delivered + ' frames (the others about ' +
        Math.round((frames - st[0].delivered) / Math.max(st.length - 1, 1)) + ' each), but used <b>' + Math.round(100 * st[0].airtime / air) + '%</b> of the airtime';
      stats.innerHTML = txt + '.';
    }
    [count, hid, rts, slow].forEach(function (c) { c.addEventListener('change', function () { reset(); for (var i = 0; i < 400; i++) step(); paint(); }); });
    reset();
    for (var i = 0; i < 400; i++) step();
    paint();
    setInterval(function () {
      if (!running || reduced || !el.isConnected) return;
      var r = el.getBoundingClientRect();
      if (r.bottom < 0 || r.top > window.innerHeight) return;
      for (var k = 0; k < 2; k++) step();
      paint();
    }, 60);
    if (reduced) { for (var j = 0; j < 4000; j++) step(); paint(); }
  };

  // ---------------------------------------------------------------- ch20: subnets, bit by bit
  // Mirrors labs/ch20/ipcalc.py.

  WIDGETS.subnet = function (el) {
    frame(el, 'Slide the slash',
      'The prefix length says how many of the 32 bits name the network. Everything after it names one computer on that network. ' +
      'Drag the slider, or type any address.');
    var addr = h('input', { type: 'text', value: '192.168.1.3', spellcheck: 'false', 'aria-label': 'address', style: 'width:10em;font-family:var(--mono)' });
    var pre = h('input', { type: 'range', min: '0', max: '32', step: '1', value: '24', 'aria-label': 'prefix length' });
    var preOut = h('b', { style: 'font-family:var(--mono)' });
    var other = h('input', { type: 'text', value: '192.168.1.4', spellcheck: 'false', 'aria-label': 'another address', style: 'width:10em;font-family:var(--mono)' });
    var bitsBox = h('div', { style: 'display:grid;grid-template-columns:repeat(35, minmax(0, 1fr));gap:1px;margin:10px 0 4px;font-family:var(--mono);font-size:78%' });
    var table = h('div', { style: 'overflow-x:auto' });
    var verdict = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Address ', addr), h('label', {}, 'prefix ', pre, preOut)));
    el.appendChild(bitsBox);
    el.appendChild(table);
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Where does a packet to ', other, ' go?')));
    el.appendChild(verdict);
    function parse(t) {
      var p = t.trim().split('.');
      if (p.length !== 4 || !p.every(function (x) { return /^\d+$/.test(x) && +x < 256; })) return null;
      return ((+p[0] << 24) >>> 0) + (+p[1] << 16) + (+p[2] << 8) + +p[3];
    }
    function txt(n) { return [24, 16, 8, 0].map(function (s) { return (n >>> s) & 255; }).join('.'); }
    function maskOf(p) { return p === 0 ? 0 : (0xFFFFFFFF << (32 - p)) >>> 0; }
    var SPECIAL = [['10.0.0.0', 8, 'private: for homes and offices'], ['100.64.0.0', 10, 'shared by internet providers (carrier-grade NAT)'],
      ['127.0.0.0', 8, 'loopback: this computer itself'], ['169.254.0.0', 16, 'link-local: made up when nothing else worked'],
      ['172.16.0.0', 12, 'private: for homes and offices'], ['192.168.0.0', 16, 'private: for homes and offices'],
      ['192.0.2.0', 24, 'for documentation'], ['198.51.100.0', 24, 'for documentation'], ['203.0.113.0', 24, 'for documentation'],
      ['224.0.0.0', 4, 'multicast: a group of listeners'], ['240.0.0.0', 4, 'reserved'], ['0.0.0.0', 8, '“this network”']];
    function kind(n) {
      for (var i = 0; i < SPECIAL.length; i++) if (((n & maskOf(SPECIAL[i][1])) >>> 0) === parse(SPECIAL[i][0])) return SPECIAL[i][2];
      return 'public: unique on the whole internet';
    }
    function draw() {
      var n = parse(addr.value), p = +pre.value;
      preOut.textContent = '/' + p;
      addr.style.borderColor = n === null ? 'var(--red)' : '';
      if (n === null) return;
      var mask = maskOf(p), net = (n & mask) >>> 0, bc = (net | (~mask >>> 0)) >>> 0;
      bitsBox.innerHTML = '';
      for (var i = 0; i < 32; i++) {
        if (i && i % 8 === 0) bitsBox.appendChild(h('span', { style: 'text-align:center;color:var(--muted)', text: '.' }));
        var bit = (n >>> (31 - i)) & 1, isNet = i < p;
        bitsBox.appendChild(h('span', { title: isNet ? 'network bit' : 'host bit', style: 'text-align:center;padding:3px 0;border-radius:3px;font-weight:700;' +
          'background:' + (isNet ? 'var(--tint-yellow)' : 'var(--tint-green)') + ';border-bottom:3px solid ' + (isNet ? 'var(--yellow)' : 'var(--green)'), text: String(bit) }));
      }
      var size = Math.pow(2, 32 - p);
      var rows = [['netmask', txt(mask), p + ' ones, then ' + (32 - p) + ' zeros'], ['network', txt(net), 'the address with every host bit set to 0']];
      if (p <= 30) {
        rows.push(['broadcast', txt(bc), 'every host bit set to 1: “everyone on this network”']);
        rows.push(['computers', txt(net + 1) + ' to ' + txt(bc - 1), (size - 2).toLocaleString() + ' usable addresses']);
      } else rows.push(['computers', size + (size === 1 ? ' address' : ' addresses'), p === 32 ? 'just this one computer' : 'a link between two routers']);
      rows.push(['kind', '', kind(n)]);
      table.innerHTML = '';
      var t = h('table', { class: 'data', style: 'margin:0;font-size:92%' });
      rows.forEach(function (r) {
        t.appendChild(h('tr', {}, h('th', { text: r[0] }), h('td', { html: r[1] ? r[1].split(' to ').map(function (x) { return '<code style="white-space:nowrap">' + x + '</code>'; }).join(' to ') : '' }), h('td', { text: r[2] })));
      });
      table.appendChild(t);
      var o = parse(other.value);
      other.style.borderColor = o === null ? 'var(--red)' : '';
      if (o === null) { verdict.textContent = ''; return; }
      var same = ((o & mask) >>> 0) === net;
      verdict.innerHTML = '<code>' + other.value.trim() + '</code> AND <code>' + txt(mask) + '</code> = <code>' + txt((o & mask) >>> 0) + '</code>, ' +
        (same ? 'the same network as this computer, so it’s sent <span class="good">straight there</span> (after a “who has?”, Chapter 21).'
          : 'a different network, so it’s sent <span class="bad">to the router</span>, whose job is to find the way (Chapter 11).');
    }
    [addr, pre, other].forEach(function (c) { c.addEventListener('input', draw); });
    draw();
  };

  // ---------------------------------------------------------------- ch21: who has?, and who's lying
  // Mirrors labs/ch21/arpwatch.py (the attack it watches for).

  WIDGETS.arpspoof = function (el) {
    frame(el, 'Who has?, and who’s lying',
      'Each computer keeps a small memory of which card has which IP address. Press the buttons in order, and watch the two memories below. ' +
      'Nothing in ARP checks that an answer is true.');
    var N = {
      bob: { name: 'Bob’s laptop', ip: '192.168.1.3', mac: 'e2:5f:…:77:0a', pos: [100, 56], sprite: '#computer' },
      pi: { name: 'Grandpa’s Pi', ip: '192.168.1.4', mac: '2c:cf:…:10:c2', pos: [100, 214], sprite: '#computer' },
      router: { name: 'router', ip: '192.168.1.1', mac: '14:c3:…:0b:32', pos: [610, 56], sprite: '#router' },
      eve: { name: 'Eve’s laptop', ip: '192.168.1.66', mac: '3c:7c:…:55:66', pos: [610, 214], sprite: '#computer' } };
    var HUB = [360, 145];
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 300', role: 'img', 'aria-label': 'four computers on one network' });
    svg.appendChild(s('rect', { width: 720, height: 300, rx: 10, class: 'f-card' }));
    Object.keys(N).forEach(function (k) {
      var n = N[k];
      svg.appendChild(s('line', { x1: n.pos[0], y1: n.pos[1], x2: HUB[0], y2: HUB[1], class: 'wire', 'stroke-width': 4 }));
    });
    svg.appendChild(s('use', { href: '#switch', x: HUB[0] - 60, y: HUB[1] - 18, width: 120, height: 37 }));
    Object.keys(N).forEach(function (k) {
      var n = N[k];
      svg.appendChild(s('use', { href: n.sprite, x: n.pos[0] - 30, y: n.pos[1] - 26, width: 60, height: k === 'router' ? 40 : 52 }));
      svg.appendChild(s('text', { x: n.pos[0], y: n.pos[1] + 40, class: 'mid xs b', text: n.name + (k === 'eve' ? ' 😈' : '') }));
      svg.appendChild(s('text', { x: n.pos[0], y: n.pos[1] + 54, class: 'mid mono xs', text: n.ip }));
      svg.appendChild(s('text', { x: n.pos[0], y: n.pos[1] + 67, class: 'mid mono xs muted', text: n.mac }));
    });
    svg.appendChild(s('use', { href: '#cloud', x: 640, y: 0, width: 76, height: 44 }));
    var dots = s('g');
    svg.appendChild(dots);
    el.appendChild(svg);
    var b1 = btn('1. Bob: “who has 192.168.1.1?”', ask, 'small');
    var b2 = btn('2. Eve lies to both', lie, 'small');
    var b3 = btn('3. Bob sends a packet to the internet', sendOut, 'small');
    var fwd = h('input', { type: 'checkbox', checked: 'checked', 'aria-label': 'Eve forwards' });
    var b4 = btn('Start again', reset, 'small ghost');
    el.appendChild(h('div', { class: 'row', style: 'gap:6px' }, b1, b2, b3, b4));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, fwd, ' Eve quietly passes things on (so nobody notices)')));
    var narr = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:2.6em' });
    var tables = h('div', { style: 'display:flex;gap:16px;flex-wrap:wrap;margin-top:8px' });
    el.appendChild(narr); el.appendChild(tables);
    var cache, busy;
    function say(t) { narr.innerHTML = t; }
    function draw(fresh) {
      tables.innerHTML = '';
      [['bob', 'Bob’s laptop remembers'], ['router', 'The router remembers']].forEach(function (pair) {
        var t = h('table', { class: 'data', style: 'margin:0;font-size:88%' });
        t.appendChild(h('tr', {}, h('th', { text: 'IP address' }), h('th', { text: 'card' })));
        var c = cache[pair[0]], keys = Object.keys(c);
        if (!keys.length) t.appendChild(h('tr', {}, h('td', { colspan: '2', text: '(nothing yet)' })));
        keys.forEach(function (ip) {
          var bad = c[ip] === N.eve.mac;
          t.appendChild(h('tr', { style: bad ? 'background:var(--tint-red)' : fresh === pair[0] + ip ? 'background:var(--tint-yellow)' : '' },
            h('td', { html: '<code>' + ip + '</code>' }), h('td', { html: '<code>' + c[ip] + '</code>' + (bad ? ' <b style="color:var(--red)">Eve!</b>' : '') })));
        });
        tables.appendChild(h('div', {}, h('div', { style: 'font-family:var(--slab);font-weight:700;margin-bottom:4px', text: pair[1] }), t));
      });
    }
    function reset() { cache = { bob: {}, router: {} }; busy = false; dots.innerHTML = ''; draw(); say('A quiet network. Bob wants to send something to the internet, which means handing it to the router.'); }
    function hop(from, to, colour, done) {
      var c = s('circle', { r: 9, fill: colour, stroke: 'var(--surface)', 'stroke-width': 2, cx: from[0], cy: from[1] });
      dots.appendChild(c);
      tween(c, from, HUB, 380, function () { tween(c, HUB, to, 380, function () { setTimeout(function () { c.remove(); }, 250); if (done) done(); }); });
    }
    function lock(f) { return function () { if (busy) return; busy = true; f(function () { busy = false; }); }; }
    function ask(done) {
      if (typeof done !== 'function') return lock(ask)();
      say('Bob broadcasts “who has 192.168.1.1? Tell 192.168.1.3”. Every card hears it…');
      var left = 3;
      ['pi', 'router', 'eve'].forEach(function (k) {
        hop(N.bob.pos, N[k].pos, 'var(--orange)', function () {
          if (--left) return;
          cache.router[N.bob.ip] = N.bob.mac;
          draw('router' + N.bob.ip);
          hop(N.router.pos, N.bob.pos, 'var(--green)', function () {
            cache.bob[N.router.ip] = N.router.mac;
            draw('bob' + N.router.ip);
            say('…and the router answers: “192.168.1.1 is at 14:c3:…:0b:32”. Both now remember each other (the router learned Bob from his question).');
            done();
          });
        });
      });
    }
    function lie(done) {
      if (typeof done !== 'function') return lock(lie)();
      say('Nobody asked Eve anything. She sends answers anyway: to Bob, “192.168.1.1 is at <b>3c:7c:…:55:66</b>”, and to the router, “192.168.1.3 is at <b>3c:7c:…:55:66</b>”.');
      var left = 2;
      [['bob', N.router.ip], ['router', N.bob.ip]].forEach(function (p) {
        hop(N.eve.pos, N[p[0]].pos, 'var(--red)', function () {
          cache[p[0]][p[1]] = N.eve.mac;
          draw();
          if (--left === 0) { say('Both believed her: an ARP reply overwrites what they remembered, even an answer to a question nobody asked. This is <b>ARP spoofing</b>.'); done(); }
        });
      });
    }
    function sendOut(done) {
      if (typeof done !== 'function') return lock(sendOut)();
      var mac = cache.bob[N.router.ip];
      if (!mac) {
        say('Bob doesn’t know the router’s card address yet, so first he has to ask (button 1).');
        return done();
      }
      if (mac === N.router.mac) {
        hop(N.bob.pos, N.router.pos, 'var(--blue)', function () { say('The frame goes to the router’s card, and out to the internet. All is well.'); done(); });
        return;
      }
      hop(N.bob.pos, N.eve.pos, 'var(--blue)', function () {
        if (!fwd.checked) { say('Bob’s frame went to <b>Eve’s</b> card. She keeps it, and Bob’s internet simply stops working.'); return done(); }
        hop(N.eve.pos, N.router.pos, 'var(--blue)', function () {
          say('Bob’s frame went to <b>Eve</b>. She read it, copied it, and passed it on to the router. The router’s replies to Bob will go to her too. Bob’s internet works perfectly, and he has no idea. She’s a <b>man in the middle</b>.');
          done();
        });
      });
    }
    reset();
  };

  // ---------------------------------------------------------------- ch22: inside a NAT
  // Mirrors labs/ch22/nat_sim.py (the Nat class).

  WIDGETS.natbox = function (el) {
    var PUBLIC = '203.0.113.77', TIMEOUT = 120;
    frame(el, 'Many devices, one address',
      'Everything inside uses a private address. Watch the router rewrite each packet on its way out, remember what it did in its table, ' +
      'and undo it for the answers. Then see what happens to packets nobody asked for.');
    var IN = { laptop: { name: 'Bob’s laptop', ip: '192.168.1.3', y: 60 }, pi: { name: 'Grandpa’s Pi', ip: '192.168.1.4', y: 150 },
      pc: { name: 'gaming PC', ip: '192.168.1.20', y: 240 } };
    var OUT = { cern: { name: 'info.cern.ch', addr: ['188.184.67.127', 80], y: 60 }, dns: { name: '1.1.1.1', addr: ['1.1.1.1', 53], y: 150 },
      stranger: { name: 'a stranger', addr: ['198.51.100.66', 4444], y: 240 } };
    var NATX = 360, LX = 110, RX = 610;
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 300', role: 'img', 'aria-label': 'a NAT router between private devices and the internet' });
    svg.appendChild(s('rect', { width: 720, height: 300, rx: 10, class: 'f-card' }));
    svg.appendChild(s('rect', { x: 8, y: 8, width: 250, height: 284, rx: 10, fill: 'var(--tint-green)', 'fill-opacity': 0.5 }));
    svg.appendChild(s('text', { x: 20, y: 28, class: 'xs b', fill: 'var(--green)', text: 'inside: 192.168.1.0/24 (private)' }));
    svg.appendChild(s('text', { x: 706, y: 28, class: 'end xs b', fill: 'var(--blue)', text: 'the internet' }));
    Object.keys(IN).forEach(function (k) {
      var d = IN[k];
      svg.appendChild(s('line', { x1: LX, y1: d.y, x2: NATX, y2: 150, class: 'wire', 'stroke-width': 3 }));
    });
    Object.keys(OUT).forEach(function (k) {
      var d = OUT[k];
      svg.appendChild(s('line', { x1: RX, y1: d.y, x2: NATX, y2: 150, class: 'line s-muted dash', 'stroke-width': 2 }));
    });
    Object.keys(IN).forEach(function (k) {
      var d = IN[k];
      svg.appendChild(s('use', { href: '#computer', x: LX - 60, y: d.y - 22, width: 50, height: 45 }));
      svg.appendChild(s('text', { x: LX - 35, y: d.y + 36, class: 'mid xs b', text: d.name }));
      svg.appendChild(s('text', { x: LX - 35, y: d.y + 49, class: 'mid mono xs', text: d.ip }));
    });
    Object.keys(OUT).forEach(function (k) {
      var d = OUT[k];
      svg.appendChild(s('use', { href: k === 'stranger' ? '#eve-head' : '#server', x: RX + 12, y: d.y - 24, width: 40, height: 48 }));
      svg.appendChild(s('text', { x: RX + 32, y: d.y + 38, class: 'mid xs b', text: d.name }));
      svg.appendChild(s('text', { x: RX + 32, y: d.y + 51, class: 'mid mono xs', text: d.addr[0] }));
    });
    svg.appendChild(s('use', { href: '#router', x: NATX - 40, y: 124, width: 80, height: 52 }));
    svg.appendChild(s('text', { x: NATX, y: 196, class: 'mid xs b', text: 'home router (NAT)' }));
    svg.appendChild(s('text', { x: NATX, y: 209, class: 'mid mono xs', text: 'outside: ' + PUBLIC }));
    var layer = s('g');
    svg.appendChild(layer);
    el.appendChild(svg);
    var actions = [
      ['Laptop → CERN', function (d) { out('laptop', 52000, 'cern', d); }],
      ['Pi → 1.1.1.1, same port!', function (d) { out('pi', 52000, 'dns', d); }],
      ['CERN answers', function (d) { inn('cern', 52000, d); }],
      ['1.1.1.1 answers', function (d) { inn('dns', map[k2('pi', 52000)] || 52000, d); }],
      ['A stranger knocks', function (d) { inn('stranger', 52000, d); }],
      ['A stranger tries port 25565', function (d) { inn('stranger', 25565, d); }],
      ['Wait 5 minutes', function (d) { now += 300; expire(); say('Five quiet minutes pass. Mappings that haven’t been used are forgotten.'); draw(); d(); }]];
    var row = h('div', { class: 'row', style: 'gap:6px' });
    actions.forEach(function (a) { row.appendChild(btn(a[0], function () { if (busy) return; busy = true; a[1](function () { busy = false; }); }, 'small')); });
    var fwd = h('input', { type: 'checkbox', 'aria-label': 'port forwarding' });
    fwd.addEventListener('change', function () { draw(); say(fwd.checked ? 'Rule added: anything arriving at port 25565 goes to the gaming PC (192.168.1.20:25565).' : 'Port forwarding rule removed.'); });
    el.appendChild(row);
    el.appendChild(h('div', { class: 'row' }, h('label', {}, fwd, ' forward port 25565 to the gaming PC (for Bob’s game server)'), btn('Start again', reset, 'small ghost')));
    var narr = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:2.6em' });
    var tbl = h('div', { style: 'overflow-x:auto;margin-top:8px' });
    el.appendChild(narr); el.appendChild(tbl);
    var map, back, now, busy, fresh;
    function k2(who, port) { return IN[who].ip + ':' + port; }
    function say(t) { narr.innerHTML = t; }
    function reset() { map = {}; back = {}; now = 0; busy = false; fresh = null; fwd.checked = false; layer.innerHTML = ''; draw(); say('The router’s table is empty. Send something from inside.'); }
    function expire() { Object.keys(back).forEach(function (p) { if (now - back[p].last > TIMEOUT) { delete map[back[p].inside]; delete back[p]; } }); }
    function freePort() { var p = 1024; while (back[p] || p === 25565) p++; return p; }
    function draw() {
      tbl.innerHTML = '';
      var t = h('table', { class: 'data', style: 'margin:0;font-size:88%' });
      t.appendChild(h('tr', {}, h('th', { text: 'outside' }), h('th', { text: 'inside' }), h('th', { text: 'may hear from' })));
      var ports = Object.keys(back);
      ports.forEach(function (p) {
        var e = back[p];
        t.appendChild(h('tr', { style: String(p) === String(fresh) ? 'background:var(--tint-yellow)' : '' },
          h('td', { html: '<code>' + PUBLIC + ':' + p + '</code>' }), h('td', { html: '<code>' + e.inside + '</code>' }),
          h('td', { html: e.remotes.map(function (r) { return '<code>' + r + '</code>'; }).join(' ') })));
      });
      if (fwd.checked) t.appendChild(h('tr', {}, h('td', { html: '<code>' + PUBLIC + ':25565</code>' }), h('td', { html: '<code>192.168.1.20:25565</code>' }), h('td', { text: 'anyone (forwarded)' })));
      if (!ports.length && !fwd.checked) t.appendChild(h('tr', {}, h('td', { colspan: '3', text: '(empty)' })));
      tbl.appendChild(h('div', { style: 'font-family:var(--slab);font-weight:700;margin-bottom:4px', text: 'The router’s NAT table' }));
      tbl.appendChild(t);
    }
    function packet(x, y, label, colour) {
      var g = s('g');
      g.appendChild(s('circle', { r: 8, fill: colour, stroke: 'var(--surface)', 'stroke-width': 2 }));
      var tx = s('text', { y: -13, class: 'mid mono xs b halo', text: label });
      g.appendChild(tx);
      g.setAttribute('transform', 'translate(' + x + ',' + y + ')');
      layer.appendChild(g);
      return { g: g, label: tx, at: [x, y] };
    }
    function move(p, to, ms, done) {
      var from = p.at.slice(), start = null;
      if (reduced) { p.at = to; p.g.setAttribute('transform', 'translate(' + to[0] + ',' + to[1] + ')'); return done(); }
      (function frameFn(ts) {
        if (start === null) start = ts;
        var k = Math.min(1, (ts - start) / ms);
        p.at = [from[0] + (to[0] - from[0]) * k, from[1] + (to[1] - from[1]) * k];
        p.g.setAttribute('transform', 'translate(' + p.at[0] + ',' + p.at[1] + ')');
        if (k < 1) requestAnimationFrame(frameFn); else done();
      })(performance.now());
    }
    function out(who, port, dest, done) {
      var src = k2(who, port), D = OUT[dest], dst = D.addr.join(':');
      var p = packet(LX, IN[who].y, 'from ' + src, 'var(--green)');
      move(p, [NATX, 150], 650, function () {
        var o = map[src], note;
        if (o === undefined || !back[o]) {
          o = (!back[port] && port !== 25565) ? port : freePort();
          map[src] = o; back[o] = { inside: src, remotes: [], last: now };
          note = 'New entry in the table' + (o === port ? ', keeping the port number.' : ': port ' + port + ' is already taken by someone else inside, so this one gets ' + o + '.');
        } else note = 'It already had an entry for this.';
        if (back[o].remotes.indexOf(dst) < 0) back[o].remotes.push(dst);
        back[o].last = now; fresh = o; draw();
        p.label.textContent = 'from ' + PUBLIC + ':' + o;
        p.g.firstChild.setAttribute('fill', 'var(--blue)');
        say('The router swaps the private source <code>' + src + '</code> for its own address, <code>' + PUBLIC + ':' + o + '</code>. ' + note);
        move(p, [RX, D.y], 650, function () { setTimeout(function () { p.g.remove(); }, 300); done(); });
      });
    }
    function inn(from, port, done) {
      var D = OUT[from], src = D.addr.join(':');
      var p = packet(RX, D.y, 'to ' + PUBLIC + ':' + port, from === 'stranger' ? 'var(--red)' : 'var(--blue)');
      move(p, [NATX, 150], 650, function () {
        expire();
        var e = back[port], target = null, why;
        if (fwd.checked && port === 25565) { target = '192.168.1.20:25565'; why = 'A port forwarding rule sends it to the gaming PC, whoever it’s from.'; }
        else if (!e) why = 'There’s no entry for port ' + port + ': nobody inside started this conversation. <b>Dropped.</b>';
        else if (e.remotes.indexOf(src) < 0) why = e.inside + ' never sent anything to <code>' + src + '</code>, so this isn’t an answer. <b>Dropped.</b>';
        else { target = e.inside; e.last = now; why = 'It’s an answer to something sent from inside, so the router swaps the destination back to <code>' + e.inside + '</code>.'; }
        say(why);
        draw();
        if (!target) {
          p.g.firstChild.setAttribute('fill', 'var(--red)');
          p.label.textContent = '✗ dropped';
          setTimeout(function () { p.g.remove(); done(); }, 900);
          return;
        }
        p.label.textContent = 'to ' + target;
        p.g.firstChild.setAttribute('fill', 'var(--green)');
        var who = Object.keys(IN).filter(function (k) { return target.indexOf(IN[k].ip + ':') === 0; })[0];
        move(p, [LX, IN[who].y], 650, function () { setTimeout(function () { p.g.remove(); }, 300); done(); });
      });
    }
    reset();
  };

  // ---------------------------------------------------------------- ch23: longest-prefix match
  // Mirrors labs/ch23/lpm.py.

  function ip4parse(t) {
    var p = String(t).trim().split('.');
    if (p.length !== 4 || !p.every(function (x) { return /^\d+$/.test(x) && +x < 256; })) return null;
    return ((+p[0] << 24) >>> 0) + (+p[1] << 16) + (+p[2] << 8) + +p[3];
  }
  function ip4text(n) { return [24, 16, 8, 0].map(function (k) { return (n >>> k) & 255; }).join('.'); }
  function ip4mask(p) { return p === 0 ? 0 : (0xFFFFFFFF << (32 - p)) >>> 0; }

  WIDGETS.lpmtable = function (el) {
    frame(el, 'Which route wins?',
      'This is the main building’s routing table. Type an address, or pick one. Every route whose prefix matches is a candidate, and the longest one wins. ' +
      'Untick a route to see what happens without it, or add your own.');
    var routes = [['0.0.0.0/0', 'the internet provider'], ['10.0.0.0/8', 'drop it: private, and not ours'],
      ['10.1.0.0/16', 'the lab building'], ['10.1.1.0/24', 'the library'], ['10.1.3.0/24', 'this building'],
      ['10.1.3.99/32', 'the library (one server moved)']].map(function (r) { return { prefix: r[0], where: r[1], on: true }; });
    var addr = h('input', { type: 'text', value: '10.1.3.99', spellcheck: 'false', 'aria-label': 'address to look up', style: 'width:10em;font-family:var(--mono)' });
    var picks = h('span', { style: 'display:inline-flex;gap:4px;flex-wrap:wrap' });
    ['10.1.3.99', '10.1.3.7', '10.1.1.20', '10.1.2.5', '10.9.9.9', '188.184.67.127'].forEach(function (a) {
      picks.appendChild(btn(a, function () { addr.value = a; draw(); }, 'small ghost'));
    });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Look up ', addr), picks));
    var box = h('div', { style: 'overflow-x:auto' });
    el.appendChild(box);
    var newP = h('input', { type: 'text', placeholder: '10.1.2.0/24', spellcheck: 'false', 'aria-label': 'new prefix', style: 'width:9em;font-family:var(--mono)' });
    var newW = h('input', { type: 'text', placeholder: 'the lab (directly)', 'aria-label': 'where it goes', style: 'width:12em' });
    el.appendChild(h('div', { class: 'row' }, h('span', { text: 'Add a route:' }), newP, newW, btn('Add', add, 'small')));
    var verdict = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(verdict);
    function parsePrefix(t) {
      var m = /^\s*([\d.]+)\/(\d+)\s*$/.exec(t);
      if (!m || +m[2] > 32) return null;
      var n = ip4parse(m[1]);
      if (n === null) return null;
      return { net: (n & ip4mask(+m[2])) >>> 0, len: +m[2] };
    }
    function add() {
      var p = parsePrefix(newP.value);
      if (!p) { newP.style.borderColor = 'var(--red)'; return; }
      newP.style.borderColor = '';
      routes.push({ prefix: ip4text(p.net) + '/' + p.len, where: newW.value.trim() || 'somewhere new', on: true });
      newP.value = ''; newW.value = '';
      draw();
    }
    function draw() {
      var a = ip4parse(addr.value);
      addr.style.borderColor = a === null ? 'var(--red)' : '';
      var best = -1;
      routes.forEach(function (r, i) {
        var p = parsePrefix(r.prefix);
        r.len = p.len; r.net = p.net;
        r.match = a !== null && ((a & ip4mask(p.len)) >>> 0) === p.net;
        r.miss = -1;
        if (a !== null && !r.match) for (var k = 0; k < p.len; k++) if (((a >>> (31 - k)) & 1) !== ((p.net >>> (31 - k)) & 1)) { r.miss = k; break; }
        if (r.on && r.match && (best < 0 || r.len > routes[best].len)) best = i;
      });
      var t = h('table', { class: 'data', style: 'margin:6px 0;font-size:90%' });
      t.appendChild(h('tr', {}, h('th', { text: 'use' }), h('th', { text: 'route' }), h('th', { text: 'prefix bits vs. the address' }), h('th', { text: 'goes to' })));
      routes.forEach(function (r, i) {
        var cb = h('input', { type: 'checkbox', 'aria-label': 'use ' + r.prefix });
        cb.checked = r.on;
        cb.addEventListener('change', function () { r.on = cb.checked; draw(); });
        var bar = h('span', { style: 'display:inline-grid;grid-template-columns:repeat(32,7px);gap:1px;vertical-align:middle' });
        for (var k = 0; k < 32; k++) {
          var col = 'var(--line)';
          if (k < r.len) col = r.miss === k ? 'var(--red)' : (r.miss >= 0 && k > r.miss) ? 'var(--tint-red)' : 'var(--green)';
          if (a === null && k < r.len) col = 'var(--muted)';
          bar.appendChild(h('i', { style: 'display:block;height:12px;border-radius:2px;background:' + col + (k % 8 === 7 && k < 31 ? ';margin-right:3px' : '') }));
        }
        var win = i === best;
        t.appendChild(h('tr', { style: win ? 'background:var(--tint-green)' : !r.on ? 'opacity:0.45' : '' },
          h('td', {}, cb), h('td', { html: '<code>' + r.prefix + '</code>' }), h('td', {}, bar),
          h('td', { html: (win ? '<b>★ ' : '') + r.where + (win ? '</b>' : '') })));
      });
      box.innerHTML = '';
      box.appendChild(t);
      if (a === null) { verdict.textContent = 'That isn’t an IPv4 address.'; return; }
      var ms = routes.filter(function (r) { return r.on && r.match; });
      if (best < 0) {
        verdict.innerHTML = 'No route matches <code>' + ip4text(a) + '</code>, not even a default route. The router drops the packet and sends back an ICMP “network unreachable” (Chapter 21).';
        return;
      }
      verdict.innerHTML = '<code>' + ip4text(a) + '</code> matches ' + ms.length + ' route' + (ms.length === 1 ? '' : 's') + ' (' +
        ms.map(function (r) { return '/' + r.len; }).join(', ') + '). The longest is <code>' + routes[best].prefix + '</code>, so it goes to <span class="good">' + routes[best].where + '</span>.';
    }
    addr.addEventListener('input', draw);
    draw();
  };

  // ---------------------------------------------------------------- ch23: Dijkstra's shortest paths
  // Mirrors labs/ch23/linkstate.py (dijkstra).

  WIDGETS.spf = function (el) {
    frame(el, 'Shortest paths, one step at a time',
      'Every router has this same map. Click a router to work out paths from it, then press <b>Step</b> to watch Dijkstra’s algorithm settle one router at a time. ' +
      'Click a cable to cut it (or mend it), and the paths change.');
    var POS = { gateway: [70, 150], main: [220, 150], library: [390, 70], lab: [390, 230], dorms: [580, 70], sports: [580, 230] };
    var LINKS = [['gateway', 'main', 1], ['main', 'library', 10], ['main', 'lab', 10], ['library', 'lab', 10],
      ['library', 'dorms', 10], ['lab', 'sports', 100], ['dorms', 'sports', 10]].map(function (l) { return { a: l[0], b: l[1], cost: l[2], cut: false }; });
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 290', role: 'img', 'aria-label': 'campus network of six routers' });
    svg.appendChild(s('rect', { width: 720, height: 290, rx: 10, class: 'f-card' }));
    var gLinks = s('g'), gNodes = s('g');
    svg.appendChild(gLinks); svg.appendChild(gNodes);
    el.appendChild(svg);
    var bStep = btn('Step ▶', step, 'small'), bAll = btn('Run to the end', function () { while (step()) {} }, 'small ghost');
    var bReset = btn('Start again', function () { start(src); }, 'small ghost');
    el.appendChild(h('div', { class: 'row', style: 'gap:6px' }, bStep, bAll, bReset));
    var narr = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:2.6em' });
    var tbl = h('div');
    el.appendChild(narr); el.appendChild(tbl);
    var src = 'main', st;
    function nbrs(r) {
      var out = [];
      LINKS.forEach(function (l) {
        if (l.cut) return;
        if (l.a === r) out.push([l.b, l.cost, l]);
        else if (l.b === r) out.push([l.a, l.cost, l]);
      });
      return out;
    }
    function start(r) {
      src = r;
      st = { dist: {}, first: {}, via: {}, done: {}, order: [] };
      Object.keys(POS).forEach(function (k) { st.dist[k] = Infinity; });
      st.dist[r] = 0;
      narr.innerHTML = 'Working out paths from <b>' + r + '</b>. It knows the cost to itself (0) and nothing else yet. Press <b>Step</b>.';
      draw();
    }
    function step() {
      var pick = null;
      Object.keys(POS).forEach(function (k) {
        if (!st.done[k] && st.dist[k] < Infinity && (pick === null || st.dist[k] < st.dist[pick])) pick = k;
      });
      if (pick === null) {
        var left = Object.keys(POS).filter(function (k) { return !st.done[k]; });
        narr.innerHTML = left.length ? 'Nothing else can be reached: <b>' + left.join(', ') + '</b> ' + (left.length === 1 ? 'is' : 'are') + ' cut off. Their routes are withdrawn.'
          : 'Done: every router is settled. The green cables form a <b>shortest-path tree</b>, and the table below is ' + src + '’s forwarding table.';
        draw();
        return false;
      }
      st.done[pick] = true;
      st.order.push(pick);
      var notes = [];
      nbrs(pick).forEach(function (n) {
        var k = n[0], c = st.dist[pick] + n[1];
        if (st.done[k]) return;
        if (c < st.dist[k]) {
          notes.push(k + ' for ' + c + (st.dist[k] < Infinity ? ' (better than ' + st.dist[k] + ')' : ''));
          st.dist[k] = c; st.via[k] = n[2]; st.first[k] = pick === src ? k : st.first[pick];
        }
      });
      narr.innerHTML = 'The cheapest unsettled router is <b>' + pick + '</b>, at cost ' + st.dist[pick] + '. Nothing can reach it more cheaply now, so it’s settled. ' +
        (notes.length ? 'Through it, we can reach ' + notes.join(', ') + '.' : 'It doesn’t improve anything.');
      var more = Object.keys(POS).some(function (k) { return !st.done[k] && st.dist[k] < Infinity; });
      if (!more) {
        var cutoff = Object.keys(POS).filter(function (k) { return !st.done[k]; });
        narr.innerHTML += ' <br>' + (cutoff.length ? 'Nothing else can be reached: <b>' + cutoff.join(', ') + '</b> ' + (cutoff.length === 1 ? 'is' : 'are') + ' cut off.'
          : '<b>Done.</b> The green cables form a <b>shortest-path tree</b>, and the table below is ' + src + '’s forwarding table.');
      }
      draw();
      return more;
    }
    function draw() {
      gLinks.innerHTML = ''; gNodes.innerHTML = '';
      LINKS.forEach(function (l) {
        var p = POS[l.a], q = POS[l.b];
        var inTree = Object.keys(st.via).some(function (k) { return st.via[k] === l && st.done[k]; });
        var g = s('g', { style: 'cursor:pointer' });
        g.appendChild(s('line', { x1: p[0], y1: p[1], x2: q[0], y2: q[1], stroke: 'transparent', 'stroke-width': 22 }));
        g.appendChild(s('line', { x1: p[0], y1: p[1], x2: q[0], y2: q[1], class: 'line ' + (l.cut ? 's-red dash' : inTree ? 's-green' : 's-line'), 'stroke-width': inTree ? 7 : 5 }));
        var mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2;
        g.appendChild(s('rect', { x: mx - 15, y: my - 10, width: 30, height: 19, rx: 4, class: 'f-surface', stroke: l.cut ? 'var(--red)' : 'var(--line)' }));
        g.appendChild(s('text', { x: mx, y: my + 4, class: 'mid mono xs b' + (l.cut ? ' f-red' : ''), text: l.cut ? '✂' : String(l.cost) }));
        g.addEventListener('click', function () { l.cut = !l.cut; start(src); narr.innerHTML = 'The ' + l.a + '–' + l.b + ' cable is ' + (l.cut ? '<b>cut</b>. Both ends flood new advertisements, and every router starts again from scratch.' : '<b>mended</b>.') + ' Press <b>Step</b>.'; });
        gLinks.appendChild(g);
      });
      Object.keys(POS).forEach(function (k) {
        var p = POS[k], g = s('g', { style: 'cursor:pointer' });
        var ring = st.done[k] ? 'var(--green)' : st.dist[k] < Infinity ? 'var(--orange)' : 'var(--line)';
        g.appendChild(s('circle', { cx: p[0], cy: p[1], r: 30, fill: st.done[k] ? 'var(--tint-green)' : st.dist[k] < Infinity ? 'var(--tint-orange)' : 'var(--surface)', stroke: ring, 'stroke-width': k === src ? 5 : 2.5 }));
        g.appendChild(s('use', { href: '#router', x: p[0] - 22, y: p[1] - 14, width: 44, height: 28 }));
        g.appendChild(s('text', { x: p[0], y: p[1] + 46, class: 'mid xs b halo', text: k + (k === src ? ' (start)' : '') }));
        var d = st.dist[k];
        g.appendChild(s('text', { x: p[0] + 34, y: p[1] - 22, class: 'mono sm b halo', fill: ring, text: d === Infinity ? '∞' : String(d) }));
        g.addEventListener('click', function () { start(k); });
        gNodes.appendChild(g);
      });
      var t = h('table', { class: 'data', style: 'margin:6px 0 0;font-size:90%' });
      t.appendChild(h('tr', {}, h('th', { text: 'to' }), h('th', { text: 'send to' }), h('th', { text: 'total cost' })));
      var any = false;
      st.order.forEach(function (k) {
        if (k === src) return;
        any = true;
        t.appendChild(h('tr', {}, h('td', { text: k }), h('td', { html: '<b>' + st.first[k] + '</b>' }), h('td', { text: String(st.dist[k]) })));
      });
      if (!any) t.appendChild(h('tr', {}, h('td', { colspan: '3', text: '(nothing settled yet)' })));
      tbl.innerHTML = '';
      tbl.appendChild(h('div', { style: 'font-family:var(--slab);font-weight:700;margin-top:6px', text: src + '’s forwarding table' }));
      tbl.appendChild(t);
      bStep.disabled = !Object.keys(POS).some(function (k) { return !st.done[k] && st.dist[k] < Infinity; });
    }
    start('main');
  };

  // ---------------------------------------------------------------- ch24: BGP between autonomous systems
  // Mirrors labs/ch24/bgp_sim.py.

  WIDGETS.bgpworld = function (el) {
    frame(el, 'Ten networks, one announcement',
      'Each box is an autonomous system. Solid lines go from a provider down to a customer, who pays; dashed lines join peers, who don’t. ' +
      'Pick a situation, and each network’s arrow shows where it sends traffic for the address below. Click any network to see every route it heard, and why it chose the one it did.');
    var AS = {
      'Tier1-West': [190, 42, 64500], 'Tier1-East': [530, 42, 64501], 'SmallCo': [360, 108, 65077],
      'Southnet': [90, 180, 64530], 'Northnet': [300, 180, 64510], 'ResearchNet': [560, 180, 64520],
      'Eve': [54, 296, 65066], 'Shop': [154, 296, 65088], 'Bob’s ISP': [256, 296, 65002], 'University': [450, 296, 65001] };
    var LINKS = [['Tier1-West', 'Tier1-East', 'peer'], ['Tier1-West', 'SmallCo', 'cust'], ['Tier1-East', 'SmallCo', 'cust'],
      ['Tier1-West', 'Southnet', 'cust'], ['Tier1-West', 'Northnet', 'cust'], ['Tier1-East', 'Northnet', 'cust'],
      ['Tier1-East', 'ResearchNet', 'cust'], ['Northnet', 'ResearchNet', 'peer'], ['Southnet', 'Eve', 'cust'],
      ['Southnet', 'Shop', 'cust'], ['Southnet', 'Bob’s ISP', 'cust'], ['Northnet', 'Bob’s ISP', 'cust'],
      ['Northnet', 'University', 'cust'], ['ResearchNet', 'University', 'cust']];
    var RANK = { self: 4, cust: 3, peer: 2, prov: 1 }, HOW = { self: 'its own', cust: 'a customer', peer: 'a peer', prov: 'a provider' };
    var REL = {};
    Object.keys(AS).forEach(function (a) { REL[a] = {}; });
    LINKS.forEach(function (l) {
      if (l[2] === 'cust') { REL[l[0]][l[1]] = 'cust'; REL[l[1]][l[0]] = 'prov'; }
      else { REL[l[0]][l[1]] = 'peer'; REL[l[1]][l[0]] = 'peer'; }
    });
    var ROV = ['Tier1-West', 'Tier1-East', 'Northnet'];

    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 336', role: 'img', 'aria-label': 'ten autonomous systems and the routes between them' });
    svg.appendChild(s('rect', { width: 720, height: 336, rx: 10, class: 'f-card' }));
    var gL = s('g'), gA = s('g'), gN = s('g');
    svg.appendChild(gL); svg.appendChild(gA); svg.appendChild(gN);
    el.appendChild(svg);
    var mode = h('select', { 'aria-label': 'situation' });
    [['normal', 'The university announces 10.1.0.0/16'], ['hijack', 'Eve also announces 10.1.1.0/24'], ['leak', 'The shop announces 10.8.0.0/16, and SmallCo leaks it']].forEach(function (o) {
      mode.appendChild(h('option', { value: o[0], text: o[1] }));
    });
    var prep = h('select', { 'aria-label': 'prepending' });
    ['no prepending', 'prepend 1× towards Northnet', 'prepend 2× towards Northnet', 'prepend 3× towards Northnet'].forEach(function (t, i) { prep.appendChild(h('option', { value: String(i), text: t })); });
    var rov = h('input', { type: 'checkbox', 'aria-label': 'route origin validation' });
    el.appendChild(h('div', { class: 'row' }, mode, prep));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, rov, ' The tier-1s and Northnet check route origins (RPKI)'), btn('Replay the announcements', replay, 'small ghost')));
    var narr = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:2.6em' });
    var panel = h('div');
    el.appendChild(narr); el.appendChild(panel);
    var picked = 'Tier1-East', timer = null;

    function valid(prefix, origin) {
      if (prefix === '10.1.0.0/16') return origin === 65001;
      if (prefix === '10.1.1.0/24') return false;     // covered by the ROA for 10.1.0.0/16, max /16
      return true;
    }
    function announcements() {
      if (mode.value === 'leak') return { '10.8.0.0/16': 'Shop' };
      var a = { '10.1.0.0/16': 'University' };
      if (mode.value === 'hijack') a['10.1.1.0/24'] = 'Eve';
      return a;
    }
    function choose(me, prefix, heard, ann) {
      if (ann[prefix] === me) return { path: [], from: null, rel: 'self' };
      var best = null;
      Object.keys(heard[me][prefix]).forEach(function (n) {
        var p = heard[me][prefix][n];
        if (!p) return;
        var o = { path: p, from: n, rel: REL[me][n] };
        if (!best || RANK[o.rel] > RANK[best.rel] || (RANK[o.rel] === RANK[best.rel] && (o.path.length < best.path.length ||
          (o.path.length === best.path.length && AS[o.from][2] < AS[best.from][2])))) best = o;
      });
      return best;
    }
    // synchronous rounds, so we can replay them: snapshot after each round
    function run() {
      var ann = announcements(), prefixes = Object.keys(ann), leaker = mode.value === 'leak' ? 'SmallCo' : null;
      var heard = {}, snaps = [];
      Object.keys(AS).forEach(function (a) { heard[a] = {}; prefixes.forEach(function (p) { heard[a][p] = {}; }); });
      for (var round = 0; round < 30; round++) {
        var best = {}, changed = false, next = JSON.parse(JSON.stringify(heard));
        Object.keys(AS).forEach(function (me) { best[me] = {}; prefixes.forEach(function (p) { best[me][p] = choose(me, p, heard, ann); }); });
        snaps.push(best);
        Object.keys(AS).forEach(function (me) {
          prefixes.forEach(function (p) {
            var r = best[me][p];
            Object.keys(REL[me]).forEach(function (nbr) {
              var kind = REL[me][nbr], offer = null;
              if (r && (r.rel === 'self' || r.rel === 'cust' || kind === 'cust' || me === leaker)) {
                var copies = 1 + (r.rel === 'self' && nbr === 'Northnet' && mode.value !== 'leak' ? +prep.value : 0);
                offer = [];
                for (var i = 0; i < copies; i++) offer.push(AS[me][2]);
                offer = offer.concat(r.path);
                if (offer.indexOf(AS[nbr][2]) >= 0) offer = null;
                else if (rov.checked && ROV.indexOf(nbr) >= 0 && !valid(p, offer[offer.length - 1])) offer = null;
              }
              var old = heard[nbr][p][me] || null;
              if (JSON.stringify(old) !== JSON.stringify(offer)) { next[nbr][p][me] = offer; changed = true; }
            });
          });
        });
        heard = next;
        if (!changed) break;
      }
      return { ann: ann, heard: heard, snaps: snaps };
    }
    function target(ann) { return mode.value === 'leak' ? '10.8.0.1' : '10.1.1.1'; }
    function fwd(best, me, ann) {   // longest-prefix match over what this AS chose
      var hit = null;
      Object.keys(best[me]).forEach(function (p) {
        var r = best[me][p];
        if (!r) return;
        var matches = mode.value === 'leak' ? p === '10.8.0.0/16' : (p === '10.1.0.0/16' || p === '10.1.1.0/24');
        if (matches && (!hit || +p.split('/')[1] > +hit.p.split('/')[1])) hit = { p: p, r: r };
      });
      return hit;
    }
    function draw(best, ann, heard) {
      gL.innerHTML = ''; gA.innerHTML = ''; gN.innerHTML = '';
      LINKS.forEach(function (l) {
        var p = AS[l[0]], q = AS[l[1]];
        gL.appendChild(s('line', { x1: p[0], y1: p[1], x2: q[0], y2: q[1], class: 'line s-line' + (l[2] === 'peer' ? ' dash' : ''), 'stroke-width': 3 }));
      });
      var dests = {};
      Object.keys(AS).forEach(function (me) {
        var hit = fwd(best, me, ann);
        dests[me] = hit ? ann[hit.p] : null;
        if (hit && hit.r.from) {
          var p = AS[me], q = AS[hit.r.from];
          var dx = q[0] - p[0], dy = q[1] - p[1], len = Math.sqrt(dx * dx + dy * dy), k0 = 30 / len, k1 = 1 - 34 / len;
          var col = dests[me] === 'Eve' ? 'red' : (mode.value === 'leak' && hit.r.path.indexOf(65077) >= 0) ? 'orange' : 'green';
          gA.appendChild(s('line', { x1: p[0] + dx * k0, y1: p[1] + dy * k0, x2: p[0] + dx * k1, y2: p[1] + dy * k1,
            class: 'line s-' + col, 'stroke-width': 4.5, 'marker-end': 'url(#ah-' + col + ')' }));
        }
      });
      Object.keys(AS).forEach(function (k) {
        var a = AS[k], d = dests[k], g = s('g', { style: 'cursor:pointer' });
        var fill = d === 'Eve' ? 'var(--tint-red)' : d ? 'var(--tint-green)' : 'var(--surface)';
        var stroke = k === picked ? 'var(--ink)' : d === 'Eve' ? 'var(--red)' : d ? 'var(--green)' : 'var(--line)';
        g.appendChild(s('rect', { x: a[0] - 46, y: a[1] - 18, width: 92, height: 36, rx: 8, fill: fill, stroke: stroke, 'stroke-width': k === picked ? 3 : 1.5 }));
        g.appendChild(s('text', { x: a[0], y: a[1] - 2, class: 'mid xs b', text: k }));
        g.appendChild(s('text', { x: a[0], y: a[1] + 12, class: 'mid mono xs muted', text: 'AS' + a[2] + (ROV.indexOf(k) >= 0 && rov.checked ? ' ✓' : '') }));
        g.addEventListener('click', function () { picked = k; draw(best, ann, heard); });
        gN.appendChild(g);
      });
      // the panel: everything the picked AS heard
      panel.innerHTML = '';
      if (!heard) return;
      Object.keys(ann).forEach(function (p) {
        var b = best[picked][p];
        var t = h('table', { class: 'data', style: 'margin:4px 0 8px;font-size:88%' });
        t.appendChild(h('tr', {}, h('th', { text: 'heard from' }), h('th', { text: 'who they are' }), h('th', { text: 'AS path' }), h('th', { text: '' })));
        var any = false;
        Object.keys(heard[picked][p]).forEach(function (n) {
          var path = heard[picked][p][n];
          if (!path) return;
          any = true;
          var win = b && b.from === n;
          t.appendChild(h('tr', { style: win ? 'background:var(--tint-green)' : '' }, h('td', { text: n }), h('td', { text: HOW[REL[picked][n]] }),
            h('td', { html: '<code>' + path.join(' ') + '</code>' }), h('td', { html: win ? '<b>★ best</b>' : '' })));
        });
        if (ann[p] === picked) t.appendChild(h('tr', {}, h('td', { colspan: '4', text: 'This is its own prefix: it announces it.' })));
        else if (!any) t.appendChild(h('tr', {}, h('td', { colspan: '4', text: 'It heard no routes to this prefix.' })));
        panel.appendChild(h('div', { style: 'font-family:var(--slab);font-weight:700;margin-top:6px', html: picked + ' (AS' + AS[picked][2] + '): routes to <code>' + p + '</code>' }));
        panel.appendChild(t);
      });
    }
    function explain(res) {
      var best = res.snaps[res.snaps.length - 1], t = target(res.ann), bad = [];
      Object.keys(AS).forEach(function (me) { var hit = fwd(best, me, res.ann); if (me !== 'Eve' && hit && res.ann[hit.p] === 'Eve') bad.push(me); });
      if (mode.value === 'hijack') {
        narr.innerHTML = bad.length ? '<b class="bad">' + bad.length + ' of the 9 other networks</b> now send traffic for <code>' + t + '</code> to Eve: her /24 is more specific than the university’s /16, and longest-prefix match believes it. ' +
          (rov.checked ? 'The networks that check origins threw her route away, and so are safe, along with everyone who reaches the university through them. But Southnet doesn’t check, so its customers are still fooled.' : 'Tick the RPKI box.')
          : 'Nobody believes Eve: every network that would have heard her route either checks origins, or only hears from networks that do.';
      } else if (mode.value === 'leak') {
        narr.innerHTML = 'Tier1-East used to reach the shop through its peer, Tier1-West. Now SmallCo, one of its <em>customers</em>, offers a route, and customers’ routes win, even though this one is longer. Orange arrows go through SmallCo, whose little connections were never meant to carry that much.';
      } else {
        var te = best['Tier1-East']['10.1.0.0/16'];
        narr.innerHTML = 'Everyone can reach <code>' + t + '</code>. ' + (+prep.value ? 'With ' + prep.value + ' extra cop' + (+prep.value === 1 ? 'y' : 'ies') + ' of 65001 on the way to Northnet, Tier1-East now goes through ' + (te && te.from) + '. But Tier1-West still uses Northnet: its only customer route is through Northnet, and money beats path length.'
          : 'Tier1-East hears the university from two customers, Northnet and ResearchNet, with equally long paths, and picks the lower AS number. Try prepending.');
      }
    }
    function show() {
      if (timer) { clearInterval(timer); timer = null; }
      var res = run();
      draw(res.snaps[res.snaps.length - 1], res.ann, res.heard);
      explain(res);
    }
    function replay() {
      if (timer) clearInterval(timer);
      var res = run(), i = 0;
      narr.innerHTML = 'Round 1: only the origin knows.';
      draw(res.snaps[0], res.ann, null);
      timer = setInterval(function () {
        i++;
        if (i >= res.snaps.length) { clearInterval(timer); timer = null; draw(res.snaps[res.snaps.length - 1], res.ann, res.heard); explain(res); return; }
        narr.innerHTML = 'Round ' + (i + 1) + ': each network tells its neighbours its current best route (if the rules allow).';
        draw(res.snaps[i], res.ann, null);
      }, reduced ? 0 : 900);
    }
    [mode, prep, rov].forEach(function (c) { c.addEventListener('change', show); });
    show();
  };

  // ---------------------------------------------------------------- ch25: IPv6 addresses taken apart
  // Mirrors labs/ch25/v6.py.

  function parse6(t) {
    t = String(t).trim().replace(/%.*$/, '');
    if (!/^[0-9a-fA-F:.]+$/.test(t) || (t.match(/::/g) || []).length > 1) return null;
    var tail = [];
    var m = /(\d+\.\d+\.\d+\.\d+)$/.exec(t);
    if (m) {
      var v4 = ip4parse(m[1]);
      if (v4 === null) return null;
      tail = [v4 >>> 16, v4 & 0xFFFF];
      t = t.slice(0, t.length - m[1].length) + (t.slice(-m[1].length - 1, -m[1].length) === ':' ? '' : '');
      if (/[^:]$/.test(t) && t.length) return null;
      if (t.slice(-2) !== '::' && t.slice(-1) === ':') t = t.slice(0, -1);
    }
    var halves = t.split('::'), left = [], right = [];
    function groups(s) {
      if (s === '') return [];
      return s.split(':').map(function (g) { return /^[0-9a-fA-F]{1,4}$/.test(g) ? parseInt(g, 16) : NaN; });
    }
    left = groups(halves[0]);
    right = halves.length > 1 ? groups(halves[1]) : [];
    right = right.concat(tail);
    if (halves.length === 1) left = left.concat(tail);
    if (left.concat(right).some(isNaN)) return null;
    var missing = 8 - left.length - (halves.length > 1 ? right.length : 0);
    if (halves.length === 1) return left.length === 8 ? left : null;
    if (missing < 1) return null;
    var zeros = [];
    for (var i = 0; i < missing; i++) zeros.push(0);
    return left.concat(zeros, right);
  }
  function short6(g) {
    var best = -1, bestLen = 1, start = -1;
    for (var i = 0; i <= 8; i++) {
      if (i < 8 && g[i] === 0) { if (start < 0) start = i; }
      else if (start >= 0) { if (i - start > bestLen) { best = start; bestLen = i - start; } start = -1; }
    }
    var hex = g.map(function (x) { return x.toString(16); });
    if (best < 0) return hex.join(':');
    return hex.slice(0, best).join(':') + '::' + hex.slice(best + bestLen).join(':');
  }
  function in6(g, prefix, len) {
    var p = parse6(prefix);
    for (var bit = 0; bit < len; bit++) {
      var gi = bit >> 4, sh = 15 - (bit & 15);
      if (((g[gi] >> sh) & 1) !== ((p[gi] >> sh) & 1)) return false;
    }
    return true;
  }
  var KINDS6 = [['::1', 128, 'loopback: this computer itself'], ['::', 128, 'unspecified: “I don’t have an address yet”'],
    ['::ffff:0:0', 96, 'an IPv4 address, dressed up as IPv6'], ['64:ff9b::', 96, 'NAT64: an IPv4 address, reached through a translator'],
    ['2001:db8::', 32, 'documentation: for examples in books'], ['fe80::', 10, 'link-local: only works on this one network'],
    ['fc00::', 7, 'unique local: private, like 192.168.x.x'], ['ff00::', 8, 'multicast: a group of listeners'],
    ['2000::', 3, 'global unicast: unique on the whole internet']];

  WIDGETS.v6play = function (el) {
    frame(el, 'Take an IPv6 address apart',
      'Type any IPv6 address, in any form, or pick one. The colours show which part says <em>which network</em> and which says <em>which computer</em>. ' +
      'Below, turn a card address into the second half of an IPv6 address.');
    var input = h('input', { type: 'text', value: '2001:1458:201:a4::100:1a0', spellcheck: 'false', 'aria-label': 'IPv6 address', style: 'width:100%;max-width:26em;font-family:var(--mono)' });
    var picks = h('div', { class: 'row', style: 'gap:4px' });
    [['CERN', '2001:1458:201:a4::100:1a0'], ['Cloudflare DNS', '2606:4700:4700::1111'], ['Bob’s router', 'fe80::16c3:5eff:fe40:b32'],
      ['all nodes', 'ff02::1'], ['loopback', '::1'], ['NAT64', '64:ff9b::cb00:7150'], ['IPv4 inside', '::ffff:192.168.1.3']].forEach(function (p) {
      picks.appendChild(btn(p[0], function () { input.value = p[1]; draw(); }, 'small ghost'));
    });
    el.appendChild(h('div', { class: 'row' }, input));
    el.appendChild(picks);
    var cells = h('div', { style: 'display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:4px;margin:10px 0 4px;font-family:var(--mono);font-size:88%' });
    var info = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(cells); el.appendChild(info);
    var mac = h('input', { type: 'text', value: '14:c3:5e:40:0b:32', spellcheck: 'false', 'aria-label': 'MAC address', style: 'width:11em;font-family:var(--mono)' });
    var eui = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(h('div', { class: 'row', style: 'margin-top:14px' }, h('label', {}, 'Card address ', mac)));
    el.appendChild(eui);
    function hex4(x) { return pad(x.toString(16), 4); }
    function draw() {
      var g = parse6(input.value);
      input.style.borderColor = g ? '' : 'var(--red)';
      cells.innerHTML = '';
      if (!g) { info.textContent = 'That isn’t an IPv6 address (yet). Remember: at most one ::, and groups of up to four hex digits.'; return; }
      var kind = 'reserved';
      for (var i = 0; i < KINDS6.length; i++) if (in6(g, KINDS6[i][0], KINDS6[i][1])) { kind = KINDS6[i][2] + ' (' + KINDS6[i][0] + '/' + KINDS6[i][1] + ')'; break; }
      var unicast = in6(g, '2000::', 3) || in6(g, 'fc00::', 7) || in6(g, 'fe80::', 10);
      g.forEach(function (x, idx) {
        var part = !unicast ? 'none' : in6(g, 'fe80::', 10) ? (idx < 4 ? 'link' : 'iid') : (idx < 3 ? 'global' : idx < 4 ? 'subnet' : 'iid');
        var col = { global: ['var(--tint-blue)', 'var(--blue)'], subnet: ['var(--tint-yellow)', 'var(--yellow)'], link: ['var(--tint-purple)', 'var(--purple)'],
          iid: ['var(--tint-green)', 'var(--green)'], none: ['var(--card)', 'var(--line)'] }[part];
        cells.appendChild(h('div', { style: 'text-align:center;padding:6px 0;border-radius:5px;font-weight:700;background:' + col[0] + ';border:1.5px solid ' + col[1], text: hex4(x) }));
      });
      var lines = ['<b>In full:</b> <code>' + g.map(hex4).join(':') + '</code>', '<b>Shortest:</b> <code>' + short6(g) + '</code>', '<b>Kind:</b> ' + kind];
      if (unicast) {
        lines.push(in6(g, 'fe80::', 10) ? '<span style="color:var(--purple)">■</span> fe80::/64, the link-local network, and <span style="color:var(--green)">■</span> the interface ID: which computer.'
          : '<span style="color:var(--blue)">■</span> the routing prefix (usually 48 bits), <span style="color:var(--yellow)">■</span> the subnet, and <span style="color:var(--green)">■</span> the interface ID: which computer on it.');
        if ((g[5] & 0xFF) === 0xFF && (g[6] >> 8) === 0xFE) {
          var bytes = [g[4] >> 8 ^ 0x02, g[4] & 255, g[5] >> 8, g[6] & 255, g[7] >> 8, g[7] & 255];
          lines.push('<b>Hidden card address:</b> <code>' + bytes.map(function (b) { return pad(b.toString(16), 2); }).join(':') + '</code> (it has ff:fe in the middle)');
        }
        var sn = [0xff02, 0, 0, 0, 0, 1, 0xff00 | (g[6] & 255), g[7]];
        lines.push('<b>To find it on the network, ask:</b> <code>' + short6(sn) + '</code>, its solicited-node group');
      }
      if (in6(g, '::ffff:0:0', 96) || in6(g, '64:ff9b::', 96)) lines.push('<b>The IPv4 address inside:</b> <code>' + ip4text(((g[6] << 16) >>> 0) + g[7]) + '</code>');
      info.innerHTML = lines.join('<br>');
    }
    function drawEui() {
      var m = mac.value.trim().split(/[:-]/);
      if (m.length !== 6 || !m.every(function (x) { return /^[0-9a-fA-F]{1,2}$/.test(x); })) { mac.style.borderColor = 'var(--red)'; eui.textContent = 'Six bytes, like 14:c3:5e:40:0b:32.'; return; }
      mac.style.borderColor = '';
      var b = m.map(function (x) { return parseInt(x, 16); });
      var flipped = b[0] ^ 0x02;
      var id = [(flipped << 8) | b[1], (b[2] << 8) | 0xff, 0xfe00 | b[3], (b[4] << 8) | b[5]];
      var nc = '<code style="white-space:nowrap">';
      eui.innerHTML = 'Split it, put <b>ff:fe</b> in the middle, and flip the “chosen by software” bit: ' + nc + pad(b[0].toString(16), 2) + '</code> → ' + nc + pad(flipped.toString(16), 2) + '</code>. ' +
        'Link-local address: ' + nc + short6([0xfe80, 0, 0, 0].concat(id)) + '</code>. On the university’s network, the same card would be ' + nc + short6([0x2001, 0xdb8, 0x4c1, 0x12].concat(id)) +
        '</code>, and anyone could recognise it anywhere. That’s why modern computers use random interface IDs instead.';
    }
    input.addEventListener('input', draw);
    mac.addEventListener('input', drawEui);
    draw(); drawEui();
  };

  // ---------------------------------------------------------------- ch26: a socket's receive buffer
  // Mirrors labs/ch26/udp_lab.py (flood).

  WIDGETS.udpbuffer = function (el) {
    frame(el, 'A fast sender, a slow reader',
      'Datagrams arrive whenever the sender likes. The kernel keeps them in the socket’s receive buffer until the program reads them. ' +
      'Make the sender faster than the reader, and watch what UDP does when the buffer is full.');
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 170', role: 'img', 'aria-label': 'a sender, a receive buffer and a reading program' });
    svg.appendChild(s('rect', { width: 720, height: 170, rx: 10, class: 'f-card' }));
    svg.appendChild(s('use', { href: '#computer', x: 18, y: 50, width: 70, height: 62 }));
    svg.appendChild(s('text', { x: 53, y: 132, class: 'mid xs b', text: 'sender' }));
    svg.appendChild(s('rect', { x: 150, y: 58, width: 440, height: 50, rx: 8, class: 'f-surface', stroke: 'var(--line)' }));
    svg.appendChild(s('text', { x: 370, y: 48, class: 'mid xs b muted', text: 'the socket’s receive buffer (in the kernel)' }));
    svg.appendChild(s('use', { href: '#computer', x: 632, y: 50, width: 70, height: 62 }));
    svg.appendChild(s('text', { x: 667, y: 132, class: 'mid xs b', text: 'program' }));
    var slotsG = s('g'), flyG = s('g');
    svg.appendChild(slotsG); svg.appendChild(flyG);
    el.appendChild(svg);
    var send = h('input', { type: 'range', min: '1', max: '40', value: '8', 'aria-label': 'send rate' });
    var read = h('input', { type: 'range', min: '1', max: '40', value: '6', 'aria-label': 'read rate' });
    var size = h('input', { type: 'range', min: '2', max: '16', value: '8', 'aria-label': 'buffer size' });
    var sendOut = h('b'), readOut = h('b'), sizeOut = h('b');
    var tcp = h('input', { type: 'checkbox', 'aria-label': 'flow control' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'sender ', send, sendOut), h('label', {}, 'reader ', read, readOut)));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'buffer ', size, sizeOut), h('label', {}, tcp, ' the sender waits when the buffer is full (like TCP)'),
      btn('Burst of 20', function () { burst += 20; }, 'small ghost'), btn('Reset', reset, 'small ghost')));
    var stats = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(stats);
    var queue, sent, got, dropped, waited, burst, nextId, accS, accR, last;
    function reset() { queue = []; sent = got = dropped = waited = burst = 0; nextId = 0; accS = accR = 0; flyG.innerHTML = ''; }
    function flash(x, y, colour, label) {
      var g = s('g');
      g.appendChild(s('rect', { x: x - 14, y: y - 12, width: 28, height: 24, rx: 4, fill: colour }));
      if (label) g.appendChild(s('text', { x: x, y: y + 5, class: 'mid mono xs b', fill: '#fff', text: label }));
      flyG.appendChild(g);
      var t0 = null;
      function step(ts) {
        if (t0 === null) t0 = ts;
        var k = (ts - t0) / 500;
        g.setAttribute('opacity', String(Math.max(0, 1 - k)));
        g.setAttribute('transform', 'translate(0,' + (-k * 20) + ')');
        if (k < 1) requestAnimationFrame(step); else g.remove();
      }
      if (reduced) setTimeout(function () { g.remove(); }, 300); else requestAnimationFrame(step);
    }
    function draw() {
      var n = +size.value;
      sendOut.textContent = ' ' + send.value + '/s'; readOut.textContent = ' ' + read.value + '/s'; sizeOut.textContent = ' ' + n + ' datagrams';
      slotsG.innerHTML = '';
      var w = 430 / n;
      for (var i = 0; i < n; i++) {
        var item = queue[i];
        var x = 585 - (i + 1) * w;
        slotsG.appendChild(s('rect', { x: x + 2, y: 62, width: w - 4, height: 42, rx: 4, fill: item !== undefined ? 'var(--tint-green)' : 'var(--card)', stroke: item !== undefined ? 'var(--green)' : 'var(--line)' }));
        if (item !== undefined && w > 22) slotsG.appendChild(s('text', { x: x + w / 2, y: 88, class: 'mid mono xs b', text: String(item % 1000) }));
      }
      var lossPct = sent ? Math.round(100 * dropped / sent) : 0;
      stats.innerHTML = 'sent <b>' + sent + '</b> · read by the program <b>' + got + '</b> · <span class="' + (dropped ? 'bad' : '') + '">dropped: ' + dropped + (sent ? ' (' + lossPct + '%)' : '') + '</span>' +
        (tcp.checked ? ' · the sender had to wait <b>' + waited + '</b> times' : '') +
        '<br>' + (tcp.checked ? 'With flow control, nothing is lost: the sender simply goes at the reader’s speed. That’s Chapter 28.'
          : dropped ? 'The buffer was full, so the kernel threw the new datagrams away, and told nobody. The sender never knew. UDP leaves it to the program to notice (and to slow down, if it cares).'
            : 'Everything fits so far. Try making the sender faster than the reader.');
    }
    var visible = true;
    if (window.IntersectionObserver) new IntersectionObserver(function (e) { visible = e[0].isIntersecting; }).observe(el);
    function tick(ts) {
      if (last === undefined) last = ts;
      var dt = Math.min(0.2, (ts - last) / 1000);
      last = ts;
      if (!visible) { requestAnimationFrame(tick); return; }      // don't burn battery when nobody's looking
      accS += dt * +send.value; accR += dt * +read.value;
      while (accS >= 1 || burst > 0) {
        if (burst > 0) burst--; else accS -= 1;
        if (queue.length >= +size.value) {
          if (tcp.checked) { waited++; accS = 0; burst = 0; break; }
          sent++; dropped++;
          flash(135, 83, 'var(--red)', '✗');
        } else {
          sent++;
          queue.push(nextId++);
          flash(120, 83, 'var(--blue)', '');
        }
      }
      while (accR >= 1) {
        accR -= 1;
        if (queue.length) { queue.shift(); got++; flash(612, 83, 'var(--green)', ''); }
      }
      draw();
      requestAnimationFrame(tick);
    }
    [send, read, size, tcp].forEach(function (c) { c.addEventListener('input', draw); });
    reset();
    draw();
    requestAnimationFrame(tick);
  };

  // ---------------------------------------------------------------- ch27: replay a real TCP connection
  // The segments of labs/ch27/example-org.pcap, as labs/ch27/tcpflow.py reads them.

  WIDGETS.tcpreplay = function (el) {
    frame(el, 'Replay a real connection',
      'Every segment of Grandpa Otto’s Pi fetching example.org over HTTPS, as captured on the Pi. The bars are the two byte streams: ' +
      'what’s been sent, what’s been acknowledged, and what’s missing. Step through it, or press play.');
    // [ms, direction (0 = Pi→server, 1 = server→Pi), flags, relative seq, length, relative ack, SACK blocks]
    var P = [[0.0,0,"S",0,0,null,[]],[30.2,1,"SA",0,0,1,[]],[30.2,0,"A",1,0,1,[]],[33.5,0,"A",1,1388,1,[]],[33.5,0,"AP",1389,183,1,[]],[98.3,0,"AP",1389,183,1,[]],[113.2,1,"A",1,0,1572,[]],[116.5,1,"A",1,1440,1572,[]],[116.5,0,"A",1572,0,1441,[]],[120.4,1,"A",1441,1440,1572,[]],[120.4,0,"A",1572,0,2881,[]],[120.4,1,"A",2881,1440,1572,[]],[120.4,0,"A",1572,0,4321,[]],[120.4,1,"AP",4321,761,1572,[]],[120.4,0,"A",1572,0,5082,[]],[125.4,0,"AP",1572,80,5082,[]],[126.1,0,"AP",1652,123,5082,[]],[189.0,1,"A",5082,0,1572,[[1389,1572]]],[192.8,1,"AP",4321,761,1572,[]],[192.8,0,"A",1775,0,5082,[[4321,5082]]],[202.3,0,"AP",1652,123,5082,[]],[205.9,1,"A",5082,0,1652,[]],[206.6,1,"AP",5082,544,1652,[]],[206.6,0,"A",1775,0,5626,[]],[206.6,1,"AP",5626,31,1775,[]],[206.6,0,"A",1775,0,5657,[]],[206.7,0,"AP",1775,31,5657,[]],[210.7,1,"AP",5828,590,1775,[]],[210.8,0,"A",1806,0,5657,[[5828,6418]]],[282.3,1,"A",6449,0,1775,[[1652,1775]]],[284.7,1,"A",6449,0,1806,[]],[300.8,1,"AP",5657,171,1806,[]],[300.8,0,"A",1806,0,6418,[]],[300.9,0,"AP",1806,48,6418,[]],[381.3,1,"AP",6418,31,1806,[]],[381.4,0,"AP",1854,48,6449,[]],[381.4,0,"AP",1902,24,6449,[]],[382.9,0,"AF",1926,0,6449,[]],[414.5,1,"A",6449,0,1854,[]],[459.9,1,"A",6449,0,1902,[]],[459.9,1,"A",6449,0,1926,[]],[459.9,1,"AF",6449,0,1926,[]],[459.9,0,"A",1927,0,6450,[]],[460.0,1,"A",6450,0,1927,[]]];
    var NOTE = {
      0: 'SYN: the Pi asks to connect, and says what it can do (MSS 1460, SACK, timestamps, window scale 10).',
      1: 'SYN-ACK: the server agrees, with its own options. It came back 30.2 ms after the SYN: one round trip.',
      2: 'The Pi’s ACK completes the handshake. The connection is established.',
      3: 'The first 1,388 bytes of the TLS hello (Chapter 32): the most one segment can carry, since the server said MSS 1400.',
      4: 'The last 183 bytes of the hello. PSH means “hand this to the program straight away”.',
      5: '65 ms and no acknowledgement: the Pi resends its <b>last</b> segment, a tail loss probe, to provoke one.',
      6: 'The server acknowledges everything up to byte 1572. It had it all along: its ACK was just slow.',
      7: 'The server’s answer starts arriving, in full segments of 1,440 bytes. The Pi acknowledges each as it comes.',
      17: 'A D-SACK: the server says it received bytes 1389–1572 twice. The Pi’s probe wasn’t needed.',
      18: 'Now the server sends a tail loss probe of its own, resending its last segment.',
      19: 'And the Pi answers with a D-SACK: “I already had 4321–5082”.',
      20: 'The Pi resends 1652–1775, its last segment again. Another probe, another unnecessary one.',
      27: 'Bytes 5828–6418 arrive, but 5657–5828 never did. There’s a hole.',
      28: 'The Pi still acknowledges 5657 (the first byte it’s missing), and adds a SACK block: “but I have 5828–6418”.',
      31: 'The server resends just the missing 171 bytes. The hole is filled…',
      32: '…and the Pi acknowledges everything up to 6418 at once.',
      37: 'FIN: the Pi has finished sending (it has read the whole page).',
      41: 'The server sends its own FIN.',
      42: 'The Pi acknowledges the server’s FIN. It will now wait in TIME_WAIT for a minute, in case this ACK was lost.',
      43: 'The last ACK. The connection is over, 460 ms and 44 segments after it began.' };
    var TOTAL = [1927, 6450];
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 190', role: 'img', 'aria-label': 'two byte streams of a TCP connection' });
    svg.appendChild(s('rect', { width: 720, height: 190, rx: 10, class: 'f-card' }));
    var g = s('g');
    svg.appendChild(g);
    el.appendChild(svg);
    var prev = btn('◀', function () { go(cur - 1); }, 'small ghost'), next = btn('▶', function () { go(cur + 1); }, 'small');
    var play = btn('Play', toggle, 'small ghost');
    var pos = h('span', { style: 'font-family:var(--mono);font-size:90%' });
    el.appendChild(h('div', { class: 'row', style: 'gap:6px' }, prev, next, play, pos));
    var narr = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:2.6em' });
    el.appendChild(narr);
    var list = h('div', { style: 'max-height:210px;overflow:auto;margin-top:8px;border:1px solid var(--line);border-radius:6px' });
    el.appendChild(list);
    var table = h('table', { class: 'data', style: 'margin:0;font-size:82%;font-family:var(--mono)' });
    list.appendChild(table);
    var rows = [];
    P.forEach(function (p, i) {
      var tr = h('tr', { style: 'cursor:pointer' }, h('td', { text: p[0].toFixed(1) + ' ms' }), h('td', { text: p[1] ? 'server → Pi' : 'Pi → server' }),
        h('td', { text: p[2].split('').map(function (c) { return { S: 'SYN', A: 'ACK', P: 'PSH', F: 'FIN', R: 'RST' }[c]; }).join(',') }),
        h('td', { text: p[4] ? p[3] + ':' + (p[3] + p[4]) : String(p[3]) }), h('td', { text: p[5] === null ? '' : 'ack ' + p[5] }),
        h('td', { text: p[6].map(function (b) { return 'sack ' + b[0] + '-' + b[1]; }).join(' ') }));
      tr.addEventListener('click', function () { go(i); });
      rows.push(tr); table.appendChild(tr);
    });
    var cur = 0, timer = null;
    function state(upto) {   // what each side has sent, what has been acknowledged, and the SACK picture, after packet `upto`
      var st = [{ sent: [], acked: 0, sack: [], retx: [] }, { sent: [], acked: 0, sack: [], retx: [] }];
      for (var i = 0; i <= upto; i++) {
        var p = P[i], me = st[p[1]], them = st[1 - p[1]];
        if (p[4]) {
          var a = p[3], b = p[3] + p[4];
          if (me.sent.some(function (r) { return r[0] <= a && b <= r[1]; })) me.retx.push([a, b]);
          me.sent.push([a, b]);
        }
        if (p[5] !== null) { them.acked = Math.max(them.acked, p[5]); them.sack = p[6].filter(function (x) { return x[1] > p[5]; }); }
      }
      return st;
    }
    function lane(y, label, st, total, dir) {
      var X = 30, W = 660, sc = W / total;
      g.appendChild(s('text', { x: X, y: y - 8, class: 'xs b', text: label }));
      g.appendChild(s('rect', { x: X, y: y, width: W, height: 26, rx: 4, class: 'f-surface', stroke: 'var(--line)' }));
      st.sent.forEach(function (r) { g.appendChild(s('rect', { x: X + r[0] * sc, y: y + 2, width: Math.max(1, (r[1] - r[0]) * sc), height: 22, fill: 'var(--tint-blue)', stroke: 'var(--blue)', 'stroke-width': 0.6 })); });
      if (st.acked > 0) g.appendChild(s('rect', { x: X, y: y + 2, width: Math.min(W, st.acked * sc), height: 22, fill: 'var(--tint-green)', stroke: 'var(--green)' }));
      st.sack.forEach(function (r) {
        g.appendChild(s('rect', { x: X + r[0] * sc, y: y + 2, width: (r[1] - r[0]) * sc, height: 22, fill: 'var(--tint-teal)', stroke: 'var(--teal)', 'stroke-width': 1.5 }));
        g.appendChild(s('rect', { x: X + st.acked * sc, y: y + 2, width: Math.max(1, (r[0] - st.acked) * sc), height: 22, fill: 'var(--tint-red)', stroke: 'var(--red)', 'stroke-width': 1.5 }));
      });
      st.retx.forEach(function (r) { g.appendChild(s('rect', { x: X + r[0] * sc, y: y - 3, width: Math.max(2, (r[1] - r[0]) * sc), height: 4, fill: 'var(--orange)' })); });
      var p = P[cur];
      if (p[1] === dir && p[4]) g.appendChild(s('rect', { x: X + p[3] * sc, y: y, width: Math.max(2, p[4] * sc), height: 26, fill: 'none', stroke: 'var(--ink)', 'stroke-width': 2.5 }));
      if (p[1] !== dir && p[5] !== null) g.appendChild(s('path', { d: 'M' + (X + p[5] * sc) + ',' + (y + 34) + ' l-6,9 l12,0 z', fill: 'var(--ink)' }));
      g.appendChild(s('text', { x: X + W, y: y - 8, class: 'end xs muted', text: total - 1 + ' bytes' }));
    }
    function go(n) {
      cur = Math.max(0, Math.min(P.length - 1, n));
      var st = state(cur), p = P[cur];
      g.innerHTML = '';
      lane(34, 'Pi → server: the TLS handshake and the HTTP request', st[0], TOTAL[0], 0);
      lane(114, 'server → Pi: certificates, and the web page', st[1], TOTAL[1], 1);
      var key = [['var(--tint-blue)', 'sent'], ['var(--tint-green)', 'acknowledged'], ['var(--tint-teal)', 'SACKed'], ['var(--tint-red)', 'missing'], ['var(--orange)', 'sent again']];
      key.forEach(function (k, i) {
        g.appendChild(s('rect', { x: 30 + i * 130, y: 172, width: 12, height: 10, fill: k[0], stroke: 'var(--line)' }));
        g.appendChild(s('text', { x: 46 + i * 130, y: 181, class: 'xs', text: k[1] }));
      });
      rows.forEach(function (r, i) { r.style.background = i === cur ? 'var(--tint-yellow)' : ''; r.style.fontWeight = i === cur ? '700' : ''; });
      var top = rows[cur].offsetTop - rows[0].offsetTop - list.clientHeight / 2 + 14;
      list.scrollTop = Math.max(0, top);
      pos.textContent = 'segment ' + (cur + 1) + ' of ' + P.length + ' · ' + p[0].toFixed(1) + ' ms';
      var who = p[1] ? 'The server' : 'The Pi';
      narr.innerHTML = NOTE[cur] || (p[4] ? who + ' sends bytes ' + p[3] + '–' + (p[3] + p[4]) + ' (' + p[4] + ' bytes).' : who + ' acknowledges everything up to byte ' + p[5] + '.');
      prev.disabled = cur === 0; next.disabled = cur === P.length - 1;
    }
    function toggle() {
      if (timer) { clearInterval(timer); timer = null; play.textContent = 'Play'; return; }
      if (cur === P.length - 1) go(0);
      play.textContent = 'Pause';
      timer = setInterval(function () { if (cur >= P.length - 1) { toggle(); return; } go(cur + 1); }, reduced ? 400 : 1100);
    }
    go(0);
  };

  // ---------------------------------------------------------------- ch28: congestion control, simulated
  // Mirrors labs/ch28/ccsim.py.

  WIDGETS.ccsim = function (el) {
    frame(el, 'Congestion control, one round trip at a time',
      'A link that carries 120 packets per round trip, and a router that can queue some more. Choose an algorithm and a buffer size. ' +
      'The blue line is the congestion window; the green dashes are what the link can carry, the orange ones that plus the queue. Above the orange line, packets are dropped.');
    var algo = h('select', { 'aria-label': 'algorithm' });
    [['reno', 'Reno (AIMD)'], ['cubic', 'CUBIC'], ['bbr', 'BBR']].forEach(function (o) { algo.appendChild(h('option', { value: o[0], text: o[1] })); });
    var buf = h('input', { type: 'range', min: '10', max: '400', step: '10', value: '60', 'aria-label': 'router buffer' });
    var bufOut = h('b');
    var two = h('input', { type: 'checkbox', 'aria-label': 'second connection' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Algorithm ', algo), h('label', {}, 'router buffer ', buf, bufOut),
      h('label', {}, two, ' a second connection joins at round 40')));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 300', role: 'img', 'aria-label': 'congestion window and round-trip time over time' });
    el.appendChild(svg);
    var stats = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(stats);
    var RATE = 10, RTT0 = 12, BDP = RATE * RTT0, ROUNDS = 200;
    function Reno() { this.cwnd = 10; this.ssthresh = Infinity; }
    Reno.prototype.round = function (lost) {
      if (lost) { this.ssthresh = Math.max(2, Math.floor(this.cwnd / 2)); this.cwnd = this.ssthresh; }
      else if (this.cwnd < this.ssthresh) this.cwnd *= 2;
      else this.cwnd += 1;
    };
    function Cubic() { this.cwnd = 10; this.ssthresh = Infinity; this.wmax = 0; this.t = 0; }
    Cubic.prototype.round = function (lost, rtt) {
      if (lost) { this.wmax = this.cwnd; this.cwnd = this.ssthresh = Math.max(2, this.cwnd * 0.7); this.t = 0; }
      else if (this.cwnd < this.ssthresh) this.cwnd *= 2;
      else {
        this.t += rtt / 1000;
        var k = Math.cbrt(this.wmax * 0.3 / 0.4);
        var cub = 0.4 * Math.pow(this.t - k, 3) + this.wmax;
        var reno = this.wmax * 0.7 + 3 * 0.3 / 1.7 * this.t * 1000 / rtt;
        this.cwnd = Math.max(cub, reno);
      }
    };
    var GAINS = [1.25, 0.75, 1, 1, 1, 1, 1, 1];
    function BBR() { this.cwnd = 10; this.btlbw = 0; this.minrtt = Infinity; this.n = 0; this.startup = true; }
    BBR.prototype.round = function (lost, rtt, delivered) {
      this.n++;
      this.minrtt = Math.min(this.minrtt, rtt);
      var rate = delivered / rtt;
      if (this.startup && rate < this.btlbw * 1.25) this.startup = false;
      this.btlbw = Math.max(this.btlbw, rate);
      var bdp = this.btlbw * this.minrtt;
      this.cwnd = Math.max(4, (this.startup ? 2 : GAINS[this.n % 8]) * bdp);
    };
    function make() { return new ({ reno: Reno, cubic: Cubic, bbr: BBR }[algo.value])(); }
    function run() {
      var B = +buf.value, flows = [make()], hist = [];
      for (var r = 0; r < ROUNDS; r++) {
        if (two.checked && r === 40) flows.push(make());
        var want = flows.reduce(function (a, f) { return a + f.cwnd; }, 0);
        var q = Math.max(0, want - BDP), lost = q > B;
        q = Math.min(q, B);
        var rtt = RTT0 + q / RATE, delivered = Math.min(want, BDP + B);
        var cw = flows.map(function (f) { return f.cwnd; });
        flows.forEach(function (f) {
          var share = want ? f.cwnd / want : 0;
          f.round(lost && (share >= 1 / flows.length || flows.length === 1), rtt, delivered * share);
        });
        hist.push({ cw: cw, q: q, rtt: rtt, lost: lost, util: Math.min(1, want / BDP) });
      }
      return hist;
    }
    function draw() {
      var B = +buf.value;
      bufOut.textContent = ' ' + B + ' packets';
      var hist = run();
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 300, rx: 10, class: 'f-card' }));
      var X0 = 50, X1 = 700, TOP = 20, H = 170, ymax = Math.max(BDP + B, 60) * 1.25;
      function X(r) { return X0 + (X1 - X0) * r / ROUNDS; }
      function Y(v) { return TOP + H - H * Math.min(v, ymax) / ymax; }
      [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
        var v = Math.round(ymax * f);
        svg.appendChild(s('line', { x1: X0, y1: Y(v), x2: X1, y2: Y(v), class: 'grid' }));
        svg.appendChild(s('text', { x: X0 - 6, y: Y(v) + 4, class: 'end xs muted', text: String(v) }));
      });
      svg.appendChild(s('line', { x1: X0, y1: Y(BDP), x2: X1, y2: Y(BDP), class: 'line s-green dash', 'stroke-width': 1.5 }));
      svg.appendChild(s('line', { x1: X0, y1: Y(BDP + B), x2: X1, y2: Y(BDP + B), class: 'line s-orange dash', 'stroke-width': 1.5 }));
      svg.appendChild(s('text', { x: X1, y: Y(BDP) + 14, class: 'end xs b f-green', text: 'the link: ' + BDP }));
      svg.appendChild(s('text', { x: X1, y: Y(BDP + B) - 5, class: 'end xs b f-orange', text: 'link + queue: ' + (BDP + B) }));
      for (var f = 0; f < (two.checked ? 2 : 1); f++) {
        var pts = [];
        hist.forEach(function (hh, r) { if (hh.cw[f] !== undefined) pts.push(X(r).toFixed(1) + ',' + Y(hh.cw[f]).toFixed(1)); });
        svg.appendChild(s('polyline', { points: pts.join(' '), fill: 'none', class: 'line ' + (f ? 's-purple' : 's-blue'), 'stroke-width': 2.2 }));
      }
      hist.forEach(function (hh, r) { if (hh.lost) svg.appendChild(s('text', { x: X(r), y: TOP + 10, class: 'mid xs b f-red', text: '✗' })); });
      // RTT strip
      var RT = 230, RH = 50, rmax = Math.max(RTT0 + B / RATE, 20);
      svg.appendChild(s('text', { x: X0, y: RT - 8, class: 'xs b muted', text: 'round-trip time (' + RTT0 + ' ms when the queue is empty, up to ' + (RTT0 + B / RATE).toFixed(0) + ' ms when it’s full)' }));
      svg.appendChild(s('line', { x1: X0, y1: RT + RH, x2: X1, y2: RT + RH, class: 'grid' }));
      var rp = hist.map(function (hh, r) { return X(r).toFixed(1) + ',' + (RT + RH - RH * hh.rtt / rmax).toFixed(1); });
      svg.appendChild(s('polyline', { points: rp.join(' '), fill: 'none', class: 'line s-red', 'stroke-width': 1.8 }));
      svg.appendChild(s('text', { x: X1, y: RT + RH + 16, class: 'end xs muted', text: ROUNDS + ' round trips' }));
      var tail = hist.slice(100);
      var util = 100 * tail.reduce(function (a, hh) { return a + hh.util; }, 0) / tail.length;
      var rtt = tail.reduce(function (a, hh) { return a + hh.rtt; }, 0) / tail.length;
      var losses = hist.filter(function (hh) { return hh.lost; }).length;
      var share = '';
      if (two.checked) {
        var last = hist[hist.length - 1].cw;
        share = ' · at the end, the two connections have <b>' + Math.round(last[0]) + '</b> and <b>' + Math.round(last[1]) + '</b>';
      }
      stats.innerHTML = 'Second half: link busy <b>' + util.toFixed(0) + '%</b> of the time · average round trip <b>' + rtt.toFixed(1) + ' ms</b> · ' +
        losses + ' round trips with losses' + share + '<br>' +
        (algo.value === 'bbr' ? 'BBR measures the link’s speed and the empty round trip, and keeps just enough in flight: a full link, and almost no queue.'
          : B >= 300 ? 'A huge buffer: the link never goes idle, but the queue is always full, and every packet waits. That’s bufferbloat.'
            : algo.value === 'cubic' ? 'CUBIC only cuts to 70%, and grows back fast, then slowly near where the last loss happened.'
              : 'Reno halves its window at every loss, then adds one packet per round trip: the sawtooth.');
    }
    [algo, buf, two].forEach(function (c) { c.addEventListener('input', draw); c.addEventListener('change', draw); });
    draw();
  };

  // ---------------------------------------------------------------- ch29: a real DNS answer, byte by byte
  // Bytes from `python3 dig.py info.cern.ch @8.8.8.8`; fields from labs/ch29/dnswire.py fields().

  WIDGETS.dnsbytes = function (el) {
    frame(el, 'A real DNS answer, byte by byte',
      'Google’s public resolver answering “what’s the address of info.cern.ch?”: all 81 bytes. Point at (or tap) any byte to see which field it belongs to. ' +
      'Pointers are the clever bit: they say “the rest of this name is somewhere earlier”, and light up where.');
    var HEX = '2d1f8180000100020000000104696e666f046365726e0263680000010001c00c000500010000027e000c09776562616673393032c011c02a00010001000003840004bcb8437f0000290200000000000000';
    var F = [[0,2,"ID","11551: the answer must carry the same number"],[2,4,"flags","qr, rd, ra; rcode NOERROR"],[4,6,"questions","1"],[6,8,"answers","2"],[8,10,"authority","0"],[10,12,"additional","1"],[12,17,"question name: label","length 4, then “info”"],[17,22,"question name: label","length 4, then “cern”"],[22,25,"question name: label","length 2, then “ch”"],[25,26,"question name: end","a zero length: the end of the name"],[26,28,"question type","1 = A"],[28,30,"question class","1 = IN, the internet"],[30,32,"answer name: pointer","the rest of the name is at byte 12: “info.cern.ch.”"],[32,34,"answer type","5 = CNAME"],[34,36,"answer class","1 = IN"],[36,40,"answer TTL","638 seconds: how long it may be remembered"],[40,42,"data length","12 bytes"],[42,52,"answer data: label","length 9, then “webafs902”"],[52,54,"answer data: pointer","the rest of the name is at byte 17: “cern.ch.”"],[54,56,"answer name: pointer","the rest of the name is at byte 42: “webafs902.cern.ch.”"],[56,58,"answer type","1 = A"],[58,60,"answer class","1 = IN"],[60,64,"answer TTL","900 seconds: how long it may be remembered"],[64,66,"data length","4 bytes"],[66,70,"answer data","188.184.67.127"],[70,71,"additional name: end","a zero length: the end of the name"],[71,73,"OPT","41 = OPT: not a record, but EDNS settings"],[73,75,"UDP size","512: the biggest UDP answer I can take"],[75,79,"EDNS flags","none"],[79,81,"data length","0 bytes"]];
    var bytes = [];
    for (var i = 0; i < HEX.length; i += 2) bytes.push(HEX.substr(i, 2));
    function section(name) {
      if (/^question/.test(name)) return 'q';
      if (/^answer/.test(name) || name === 'data length') return 'a';
      if (/^additional|^OPT|^UDP|^EDNS/.test(name)) return 'x';
      return 'h';
    }
    var COL = { h: ['var(--tint-purple)', 'var(--purple)'], q: ['var(--tint-yellow)', 'var(--yellow)'], a: ['var(--tint-green)', 'var(--green)'], x: ['var(--tint-blue)', 'var(--blue)'] };
    var owner = [];
    F.forEach(function (f, idx) { for (var b = f[0]; b < f[1]; b++) owner[b] = idx; });
    // "data length" belongs to whichever record it's in: colour it like its neighbours
    var grid = h('div', { style: 'display:grid;grid-template-columns:repeat(16,minmax(0,1fr));gap:3px;font-family:var(--mono);font-size:85%;margin:8px 0' });
    var cells = bytes.map(function (bt, b) {
      var f = F[owner[b]], sec = section(f[2]);
      if (f[2] === 'data length') sec = b > 70 ? 'x' : 'a';
      var c = h('div', { tabindex: '0', style: 'text-align:center;padding:5px 0;border-radius:4px;cursor:pointer;background:' + COL[sec][0] + ';border:1.5px solid ' + COL[sec][1], text: bt, title: 'byte ' + b });
      c.addEventListener('mouseenter', function () { pick(b); });
      c.addEventListener('focus', function () { pick(b); });
      c.addEventListener('click', function () { pick(b); });
      grid.appendChild(c);
      return c;
    });
    el.appendChild(grid);
    var legend = h('div', { class: 'row', style: 'gap:14px;font-size:88%' });
    [['h', 'header'], ['q', 'the question'], ['a', 'the answers'], ['x', 'EDNS (the OPT record)']].forEach(function (l) {
      legend.appendChild(h('span', { html: '<i style="display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;background:' + COL[l[0]][0] + ';border:1.5px solid ' + COL[l[0]][1] + '"></i> ' + l[1] }));
    });
    el.appendChild(legend);
    var info = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:3.4em' });
    el.appendChild(info);
    function pick(b) {
      var f = F[owner[b]];
      cells.forEach(function (c) { c.style.outline = ''; c.style.fontWeight = ''; c.style.boxShadow = ''; });
      for (var i = f[0]; i < f[1]; i++) { cells[i].style.outline = '2.5px solid var(--ink)'; cells[i].style.fontWeight = '700'; }
      var extra = '';
      var m = /at byte (\d+)/.exec(f[3]);
      if (m) {
        var t = +m[1];
        var end = t;
        while (end < bytes.length && bytes[end] !== '00' && parseInt(bytes[end], 16) < 0xc0) end += parseInt(bytes[end], 16) + 1;
        if (end < bytes.length && parseInt(bytes[end], 16) >= 0xc0) end += 2; else end += 1;
        for (var k = t; k < end && k < bytes.length; k++) cells[k].style.boxShadow = '0 0 0 3px var(--orange)';
        extra = ' <span style="color:var(--orange);font-weight:700">(lit up in orange)</span>. The pointer is 2 bytes: the first starts with the bits 11, which a length can’t (labels are at most 63 bytes long), and the other 14 bits are the position.';
      }
      info.innerHTML = '<b>Bytes ' + f[0] + (f[1] - f[0] > 1 ? '–' + (f[1] - 1) : '') + ': ' + f[2] + '.</b> ' + f[3] + extra;
    }
    pick(30);
  };

  // ---------------------------------------------------------------- ch30: a browser cache, and a clock
  // Mirrors labs/ch30/cacheproxy.py (freshness, then revalidation).

  WIDGETS.httpcache = function (el) {
    frame(el, 'Be the browser’s cache',
      'Grandpa Otto’s garden page shows a 2.4 MB photo. Choose what the server says about caching it, then load the page, move the clock on, and load it again. ' +
      'Each load either goes to the server or doesn’t, and the log says why.');
    var policy = h('select', { 'aria-label': 'cache policy' });
    [['max-age=60', 'Cache-Control: max-age=60 (fresh for a minute)'], ['max-age=86400', 'Cache-Control: max-age=86400 (a day)'],
      ['no-cache', 'Cache-Control: no-cache (always check first)'], ['no-store', 'Cache-Control: no-store (never keep it)']].forEach(function (o) {
      policy.appendChild(h('option', { value: o[0], text: o[1] }));
    });
    el.appendChild(h('div', { class: 'row' }, policy));
    var clockOut = h('b', { style: 'font-family:var(--mono)' });
    el.appendChild(h('div', { class: 'row', style: 'gap:6px' }, btn('Load the page', load, 'small'),
      btn('+10 s', function () { tick(10); }, 'small ghost'), btn('+1 min', function () { tick(60); }, 'small ghost'),
      btn('+1 day', function () { tick(86400); }, 'small ghost'), btn('Grandpa uploads a new photo', change, 'small ghost'),
      btn('Start again', reset, 'small ghost'), h('span', {}, 'clock: ', clockOut)));
    var state = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    var log = h('div', { style: 'max-height:220px;overflow:auto;margin-top:8px' });
    el.appendChild(state); el.appendChild(log);
    var now, version, entry, totals;
    function fmt(t) { return t >= 86400 ? Math.floor(t / 86400) + ' d ' + fmt(t % 86400) : t >= 60 ? Math.floor(t / 60) + ' min ' + (t % 60) + ' s' : t + ' s'; }
    function maxAge() { var m = /max-age=(\d+)/.exec(policy.value); return policy.value === 'no-cache' ? 0 : m ? +m[1] : null; }
    function reset() { now = 0; version = 1; entry = null; totals = { bytes: 0, loads: 0 }; log.innerHTML = ''; draw(); }
    function tick(s) { now += s; draw(); }
    function change() { version++; add('var(--muted)', 'Grandpa uploads a new photo. The server’s copy is now version ' + version + ' (ETag <code>"v' + version + '"</code>). Your cached copy doesn’t know yet.'); draw(); }
    function add(col, html) {
      log.insertBefore(h('div', { style: 'border-left:4px solid ' + col + ';padding:4px 10px;margin:4px 0;background:var(--card);border-radius:0 6px 6px 0;font-size:92%', html: '<b>' + fmt(now) + '</b> · ' + html }), log.firstChild);
    }
    function load() {
      totals.loads++;
      var age = maxAge();
      if (entry && now - entry.stored < entry.fresh) {
        add('var(--green)', '<b>From the cache.</b> The copy is ' + fmt(now - entry.stored) + ' old, and fresh for ' + fmt(entry.fresh) + '. No request at all: 0 bytes, 0 ms.' +
          (entry.version !== version ? ' <span class="bad">(It’s out of date! The server has a newer photo, but the cache was told it could keep this one.)</span>' : ''));
      } else if (entry) {
        if (entry.version === version) {
          entry.stored = now; entry.fresh = age || 0;
          totals.bytes += 300;
          add('var(--orange)', '<b>Revalidated.</b> The copy is stale, so the browser asks: <code>If-None-Match: "v' + version + '"</code>. The server answers <code>304 Not Modified</code>, with no body: about 300 bytes and one round trip, instead of 2.4 MB.');
        } else {
          totals.bytes += 2400000;
          entry = { version: version, stored: now, fresh: age || 0 };
          add('var(--blue)', '<b>Changed.</b> The browser asks <code>If-None-Match</code> with its old ETag; the server’s file has changed, so it answers <code>200 OK</code> with the new photo: 2.4 MB.');
        }
      } else {
        totals.bytes += 2400000;
        if (age === null) add('var(--red)', '<b>Downloaded, and forgotten.</b> <code>200 OK</code>, 2.4 MB. The server said <code>no-store</code>, so the browser keeps nothing, and will download it all again next time.');
        else { entry = { version: version, stored: now, fresh: age }; add('var(--blue)', '<b>Downloaded.</b> Nothing in the cache, so: <code>200 OK</code>, 2.4 MB, with <code>Cache-Control: ' + policy.value + '</code> and <code>ETag: "v' + version + '"</code>. The browser keeps a copy.'); }
      }
      draw();
    }
    function draw() {
      clockOut.textContent = fmt(now);
      var fresh = entry && now - entry.stored < entry.fresh;
      state.innerHTML = (entry ? 'In the cache: version ' + entry.version + ', stored at ' + fmt(entry.stored) + ', <b>' + (fresh ? 'fresh' : 'stale') + '</b>' + (fresh ? ' for another ' + fmt(entry.fresh - (now - entry.stored)) : '') + '.'
        : 'The cache is empty.') + ' Loads: ' + totals.loads + ', bytes downloaded: <b>' + (totals.bytes / 1e6).toFixed(2) + ' MB</b>.';
    }
    policy.addEventListener('change', function () { entry = null; add('var(--muted)', 'The server now says <code>Cache-Control: ' + policy.value + '</code>. (The cache is cleared, to start fresh.)'); draw(); });
    reset();
  };

  // ---------------------------------------------------------------- ch31: fingerprints and the avalanche
  // Mirrors labs/ch31/crypto_lab.py hash. Uses the browser's own SHA-256.

  WIDGETS.hashplay = function (el) {
    frame(el, 'Change one letter, change everything',
      'Two messages and their SHA-256 fingerprints, drawn as 256 squares, one per bit. Squares where the two fingerprints differ are orange. ' +
      'Change one character, and about half of them change.');
    var a = h('input', { type: 'text', value: 'Meet me at noon', 'aria-label': 'first message', style: 'width:100%;max-width:22em' });
    var b = h('input', { type: 'text', value: 'Meet me at noon.', 'aria-label': 'second message', style: 'width:100%;max-width:22em' });
    var ha = h('div', { class: 'out', style: 'font-size:82%' }), hb = h('div', { class: 'out', style: 'font-size:82%' });
    var grid = h('div', { style: 'display:grid;grid-template-columns:repeat(32,minmax(0,1fr));gap:2px;margin:10px 0' });
    var verdict = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(h('div', { class: 'row' }, h('label', { style: 'flex:1' }, 'A ', a)));
    el.appendChild(ha);
    el.appendChild(h('div', { class: 'row' }, h('label', { style: 'flex:1' }, 'B ', b)));
    el.appendChild(hb);
    el.appendChild(grid); el.appendChild(verdict);
    var cells = [];
    for (var i = 0; i < 256; i++) { var c = h('i', { style: 'display:block;aspect-ratio:1;border-radius:2px' }); cells.push(c); grid.appendChild(c); }
    function sha(t) {
      if (!(window.crypto && crypto.subtle)) return Promise.resolve(null);
      return crypto.subtle.digest('SHA-256', new TextEncoder().encode(t)).then(function (buf) { return new Uint8Array(buf); });
    }
    function hex(u) { return Array.prototype.map.call(u, function (x) { return pad(x.toString(16), 2); }).join(''); }
    var ticket = 0;
    function draw() {
      var mine = ++ticket;
      Promise.all([sha(a.value), sha(b.value)]).then(function (r) {
        if (mine !== ticket) return;
        if (!r[0]) { verdict.textContent = 'This browser can’t compute SHA-256 here (it needs a secure page, like https or localhost).'; return; }
        ha.textContent = hex(r[0]); hb.textContent = hex(r[1]);
        var diff = 0;
        for (var i = 0; i < 256; i++) {
          var ba = (r[0][i >> 3] >> (7 - (i & 7))) & 1, bb = (r[1][i >> 3] >> (7 - (i & 7))) & 1;
          if (ba !== bb) diff++;
          cells[i].style.background = ba !== bb ? 'var(--orange)' : ba ? 'var(--ink)' : 'var(--line)';
        }
        verdict.innerHTML = a.value === b.value ? 'The same message always gives the same fingerprint.' :
          '<b>' + diff + ' of 256 bits differ</b>. There’s no way to steer the fingerprint: you can’t find a message that gives a chosen one, except by trying about 2<sup>256</sup> of them.';
      });
    }
    a.addEventListener('input', draw); b.addEventListener('input', draw);
    draw();
  };

  // ---------------------------------------------------------------- ch31: Diffie-Hellman, with paint and numbers
  // Mirrors labs/ch31/crypto_lab.py dh.

  WIDGETS.dhplay = function (el) {
    frame(el, 'Agree on a secret, in public',
      'Everyone, including Eve, can see the public numbers. Alice and Bob each keep one number to themselves. ' +
      'Change the secrets, and watch Alice and Bob still end up with the same answer, which Eve never sees.');
    var PRIMES = [23, 101, 1009, 10007, 100003, 1000003];
    var p = h('select', { 'aria-label': 'prime' });
    PRIMES.forEach(function (x) { p.appendChild(h('option', { value: String(x), text: String(x) })); });
    var g = h('input', { type: 'number', value: '5', min: '2', 'aria-label': 'g', style: 'width:5em' });
    var sa = h('input', { type: 'number', value: '6', min: '1', 'aria-label': 'Alice secret', style: 'width:7em' });
    var sb = h('input', { type: 'number', value: '15', min: '1', 'aria-label': 'Bob secret', style: 'width:7em' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'public prime p ', p), h('label', {}, 'public g ', g)));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'Alice’s secret a ', sa), h('label', {}, 'Bob’s secret b ', sb)));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 250', role: 'img', 'aria-label': 'Diffie-Hellman exchange' });
    el.appendChild(svg);
    var eveBtn = btn('Eve tries every possible secret', eve, 'small ghost');
    el.appendChild(h('div', { class: 'row' }, eveBtn));
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);
    function mp(base, e, m) {   // modular exponentiation with BigInt
      var r = 1n, bb = BigInt(base) % BigInt(m), ee = BigInt(e), mm = BigInt(m);
      while (ee > 0n) { if (ee & 1n) r = r * bb % mm; bb = bb * bb % mm; ee >>= 1n; }
      return Number(r);
    }
    function colour(n, P) { var hue = Math.round(360 * n / P); return 'hsl(' + hue + ',70%,55%)'; }
    function blob(x, y, n, P, label, sub) {
      svg.appendChild(s('circle', { cx: x, cy: y, r: 24, fill: colour(n, P), stroke: 'var(--ink)', 'stroke-width': 1.5 }));
      svg.appendChild(s('text', { x: x, y: y + 44, class: 'mid mono sm b', text: String(n) }));
      svg.appendChild(s('text', { x: x, y: y + 58, class: 'mid xs muted', text: label }));
      if (sub) svg.appendChild(s('text', { x: x, y: y - 32, class: 'mid xs b', text: sub }));
    }
    function draw() {
      var P = +p.value, G = Math.max(2, +g.value), a = Math.max(1, +sa.value), b = Math.max(1, +sb.value);
      var A = mp(G, a, P), B = mp(G, b, P), KA = mp(B, a, P), KB = mp(A, b, P);
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 250, rx: 10, class: 'f-card' }));
      svg.appendChild(s('rect', { x: 250, y: 12, width: 220, height: 226, rx: 10, class: 't-red', opacity: 0.5 }));
      svg.appendChild(s('text', { x: 360, y: 32, class: 'mid xs b f-red', text: 'in public: Eve sees all of this' }));
      svg.appendChild(s('text', { x: 90, y: 32, class: 'mid sm b', text: 'Alice' }));
      svg.appendChild(s('text', { x: 630, y: 32, class: 'mid sm b', text: 'Bob' }));
      blob(90, 90, a, P, 'secret a', '');
      blob(630, 90, b, P, 'secret b', '');
      blob(310, 90, A, P, 'A = g^a mod p', 'from Alice');
      blob(410, 90, B, P, 'B = g^b mod p', 'from Bob');
      svg.appendChild(s('path', { d: 'M116,90 L284,90', class: 'line s-blue', 'stroke-width': 2, 'marker-end': 'url(#ah-blue)' }));
      svg.appendChild(s('path', { d: 'M604,90 L436,90', class: 'line s-purple', 'stroke-width': 2, 'marker-end': 'url(#ah-purple)' }));
      blob(90, 190, KA, P, 'B^a mod p', '');
      blob(630, 190, KB, P, 'A^b mod p', '');
      svg.appendChild(s('text', { x: 360, y: 196, class: 'mid sm b', text: 'g = ' + G + ', p = ' + P }));
      out.innerHTML = 'Alice gets <b>' + KA + '</b>, Bob gets <b>' + KB + '</b>' + (KA === KB ? ': the same, because both are g<sup>ab</sup> mod p.' : '.') +
        ' Eve has A = ' + A + ' and B = ' + B + ', but to get the secret she needs a or b.';
    }
    function eve() {
      var P = +p.value, G = Math.max(2, +g.value), a = Math.max(1, +sa.value);
      var A = mp(G, a, P), t0 = performance.now(), tries = 0, found = null;
      for (var x = 1, cur = G % P; x < P; x++, cur = cur * G % P) { tries++; if (cur === A) { found = x; break; } }   // g^1, g^2, g^3…
      var ms = performance.now() - t0;
      var perTry = ms / Math.max(1, tries);
      var years = perTry / 1000 * Math.pow(2, 255) / (3600 * 24 * 365);
      out.innerHTML = found !== null ? 'Eve tried ' + tries.toLocaleString() + ' numbers in ' + ms.toFixed(1) + ' ms and found a number that works: <b>' + found + '</b>. ' +
        'With p = ' + P + ', that’s easy. With the 255-bit numbers real TLS uses, the same search would take her about <b>10<sup>' + Math.round(Math.log10(years)) + '</b> years</b>.'
        : 'Eve didn’t find it (g may not reach every number for this p).';
    }
    [p, g, sa, sb].forEach(function (c) { c.addEventListener('input', draw); c.addEventListener('change', draw); });
    draw();
  };

  // ---------------------------------------------------------------- ch32: a real ClientHello and ServerHello, byte by byte
  // Bytes from labs/ch32/tls13.py talking to example.org; field descriptions generated from the same bytes.

  WIDGETS.tlshello = function (el) {
    frame(el, 'The two hellos, byte by byte',
      'The first two messages of a real TLS 1.3 handshake between this chapter’s lab and example.org: the only two that aren’t encrypted. ' +
      'Point at (or tap) any byte to see what it’s for. Everything here is visible to Eve.');
    var MSGS = {"ch": ["16030100bf010000bb030326d09e9fda6a0cb56c00f3dd32341c9e1944999ded5ab2660c4695861568cda220ce1e9793f651dd0089d0faa20822151f3258385459825d0e57263a3ad1f52c85000213030100007000000010000e00000b6578616d706c652e6f7267000a00040002001d000d0010000e0403050308040805080704010501002b0003020304003300260024001d0020f35b65024260cff2a011310012299b328544507b244f1104bbe6815c0536a8180010000b000908687474702f312e31", [[0, 1, "r", "record type", "22 = handshake"], [1, 3, "r", "record version", "0x0301: “TLS 1.0”, a fib kept for old middleboxes"], [3, 5, "r", "record length", "191 bytes follow"], [5, 6, "h", "handshake type", "1 = ClientHello"], [6, 9, "h", "handshake length", "187 bytes"], [9, 11, "h", "legacy version", "0x0303, “TLS 1.2”: the real version is in an extension, because old servers choked on anything else"], [11, 43, "h", "random", "32 random bytes, mixed into the keys"], [43, 44, "h", "session ID length", "32"], [44, 76, "h", "legacy session ID", "random, and meaningless in TLS 1.3: it makes the hello look like TLS 1.2 resuming a session, which middleboxes let through"], [76, 78, "h", "cipher suites length", "2 bytes: one suite"], [78, 80, "h", "cipher suite", "0x1303 = TLS_CHACHA20_POLY1305_SHA256, Chapter 31’s cipher. Browsers offer three or more"], [80, 81, "h", "compression methods length", "1"], [81, 82, "h", "compression", "0 = none: compressing before encrypting leaked secrets (an attack called CRIME), so TLS 1.3 forbids it"], [82, 84, "h", "extensions length", "112 bytes of extensions"], [84, 86, "x", "extension type", "0 = server_name (SNI)"], [86, 88, "x", "extension length", "16 bytes"], [88, 90, "x", "SNI: list length", "14"], [90, 91, "x", "SNI: name type", "0 = a host name"], [91, 93, "x", "SNI: name length", "11"], [93, 104, "s", "SNI: the name", "“example.org”, in plain text: which of the thousands of sites on this server Bob wants. Eve can read it"], [104, 106, "x", "extension type", "10 = supported_groups"], [106, 108, "x", "extension length", "4 bytes"], [108, 110, "x", "groups: list length", "2"], [110, 112, "x", "group", "0x001d = x25519"], [112, 114, "x", "extension type", "13 = signature_algorithms"], [114, 116, "x", "extension length", "16 bytes"], [116, 118, "x", "signatures: list length", "14 bytes: 7 kinds"], [118, 120, "x", "signature algorithm", "0x0403 = ECDSA P-256 + SHA-256: a kind of signature the lab can check"], [120, 122, "x", "signature algorithm", "0x0503 = ECDSA P-384 + SHA-384: a kind of signature the lab can check"], [122, 124, "x", "signature algorithm", "0x0804 = RSA-PSS + SHA-256: a kind of signature the lab can check"], [124, 126, "x", "signature algorithm", "0x0805 = RSA-PSS + SHA-384: a kind of signature the lab can check"], [126, 128, "x", "signature algorithm", "0x0807 = Ed25519: a kind of signature the lab can check"], [128, 130, "x", "signature algorithm", "0x0401 = RSA PKCS#1 + SHA-256 (for certificates): a kind of signature the lab can check"], [130, 132, "x", "signature algorithm", "0x0501 = RSA PKCS#1 + SHA-384 (for certificates): a kind of signature the lab can check"], [132, 134, "x", "extension type", "43 = supported_versions"], [134, 136, "x", "extension length", "3 bytes"], [136, 137, "x", "versions: list length", "2"], [137, 139, "x", "version", "0x0304 = TLS 1.3: the real version"], [139, 141, "x", "extension type", "51 = key_share"], [141, 143, "x", "extension length", "38 bytes"], [143, 145, "x", "key shares: list length", "36"], [145, 147, "x", "key share: group", "0x001d = x25519"], [147, 149, "x", "key share: length", "32"], [149, 181, "k", "key share: public key", "Bob’s X25519 public key, made fresh for this one connection. The private half never leaves his laptop"], [181, 183, "x", "extension type", "16 = ALPN"], [183, 185, "x", "extension length", "11 bytes"], [185, 187, "x", "ALPN: list length", "9"], [187, 188, "x", "ALPN: length", "8"], [188, 196, "s", "ALPN: protocol", "“http/1.1”: what we’ll speak inside. Browsers offer “h2” too (Chapter 33)"]]], "sh": ["160303007a020000760303ff9cde9880ff9db14e67c25020a2d34cd3eb6327b1ab5115f0d1f8fd49b4717320ce1e9793f651dd0089d0faa20822151f3258385459825d0e57263a3ad1f52c85130300002e00330024001d00209c64f6cc225d79dfcf60ae97ab8b50caaf48c213b26ae819bd34a2e00124c70f002b00020304", [[0, 1, "r", "record type", "22 = handshake"], [1, 3, "r", "record version", "0x0303: “TLS 1.2”, a fib kept for old middleboxes"], [3, 5, "r", "record length", "122 bytes follow"], [5, 6, "h", "handshake type", "2 = ServerHello"], [6, 9, "h", "handshake length", "118 bytes"], [9, 11, "h", "legacy version", "0x0303, “TLS 1.2”: the real version is in an extension, because old servers choked on anything else"], [11, 43, "h", "random", "32 random bytes from the server"], [43, 44, "h", "session ID length", "32"], [44, 76, "h", "legacy session ID", "the server echoes the client’s"], [76, 78, "h", "cipher suite", "0x1303: the server picks ChaCha20-Poly1305, the only one offered"], [78, 79, "h", "compression", "0 = none"], [79, 81, "h", "extensions length", "46 bytes of extensions"], [81, 83, "x", "extension type", "51 = key_share"], [83, 85, "x", "extension length", "36 bytes"], [85, 87, "x", "key share: group", "0x001d = x25519"], [87, 89, "x", "key share: length", "32"], [89, 121, "k", "key share: public key", "the server’s X25519 public key. With it and his own private key, Bob gets the shared secret"], [121, 123, "x", "extension type", "43 = supported_versions"], [123, 125, "x", "extension length", "2 bytes"], [125, 127, "x", "selected version", "0x0304 = TLS 1.3"]]]};
    var COL = { r: ['var(--tint-blue)', 'var(--blue)'], h: ['var(--tint-purple)', 'var(--purple)'], x: ['var(--tint-yellow)', 'var(--yellow)'],
      s: ['var(--tint-orange)', 'var(--orange)'], k: ['var(--tint-green)', 'var(--green)'] };
    var which = 'ch';
    var tabs = h('div', { class: 'row' });
    var bCH = btn('ClientHello (Bob → server)', function () { show('ch'); }, 'small');
    var bSH = btn('ServerHello (server → Bob)', function () { show('sh'); }, 'small ghost');
    tabs.appendChild(bCH); tabs.appendChild(bSH);
    el.appendChild(tabs);
    var grid = h('div', { style: 'display:grid;grid-template-columns:repeat(16,minmax(0,1fr));gap:3px;font-family:var(--mono);font-size:82%;margin:8px 0' });
    el.appendChild(grid);
    var legend = h('div', { class: 'row', style: 'gap:14px;font-size:88%' });
    [['r', 'record header'], ['h', 'the hello itself'], ['x', 'extensions'], ['s', 'readable text'], ['k', 'the key share']].forEach(function (l) {
      legend.appendChild(h('span', { html: '<i style="display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;background:' + COL[l[0]][0] + ';border:1.5px solid ' + COL[l[0]][1] + '"></i> ' + l[1] }));
    });
    el.appendChild(legend);
    var info = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:3.4em' });
    el.appendChild(info);
    var cells = [], owner = [];
    function show(w) {
      which = w;
      bCH.className = 'btn small' + (w === 'ch' ? '' : ' ghost');
      bSH.className = 'btn small' + (w === 'sh' ? '' : ' ghost');
      var hex = MSGS[w][0], F = MSGS[w][1];
      grid.innerHTML = ''; cells = []; owner = [];
      F.forEach(function (f, idx) { for (var b = f[0]; b < f[1]; b++) owner[b] = idx; });
      for (var b = 0; b < hex.length / 2; b++) {
        (function (b) {
          var f = F[owner[b]], col = COL[f[2]];
          var c = h('div', { tabindex: '0', style: 'text-align:center;padding:4px 0;border-radius:4px;cursor:pointer;background:' + col[0] + ';border:1.5px solid ' + col[1], text: hex.substr(2 * b, 2), title: 'byte ' + b });
          c.addEventListener('mouseenter', function () { pick(b); });
          c.addEventListener('focus', function () { pick(b); });
          c.addEventListener('click', function () { pick(b); });
          grid.appendChild(c); cells.push(c);
        })(b);
      }
      pick(w === 'ch' ? F.filter(function (f) { return /SNI: the name/.test(f[3]); })[0][0] : F.filter(function (f) { return /public key/.test(f[3]); })[0][0]);
    }
    function pick(b) {
      var F = MSGS[which][1], f = F[owner[b]];
      cells.forEach(function (c) { c.style.outline = ''; c.style.fontWeight = ''; });
      for (var i = f[0]; i < f[1]; i++) { cells[i].style.outline = '2.5px solid var(--ink)'; cells[i].style.fontWeight = '700'; }
      info.innerHTML = '<b>Byte' + (f[1] - f[0] > 1 ? 's ' + f[0] + '–' + (f[1] - 1) : ' ' + f[0]) + ': ' + f[3] + '.</b> ' + f[4] + '.';
    }
    show('ch');
  };

  // ---------------------------------------------------------------- ch33: head-of-line blocking, four ways
  // A toy model: RTT = 4 time slots of 25 ms; each response is 4 packets; one packet can be lost,
  // and its resend arrives 5 slots later. TCP hands data over strictly in order; QUIC per stream.

  WIDGETS.holblock = function (el) {
    frame(el, 'One lost packet, four ways',
      'Grandpa’s page, its stylesheet and a photo, each 4 packets, fetched over a link with a 100 ms round trip. ' +
      '<b>Click any packet to lose it</b> (click again for no loss), and switch protocols. Solid boxes are when a packet arrives; ' +
      'the pale bar after one is time it spends <em>waiting</em> in the receiver, unusable, because something in front of it is missing.');
    var MODES = [
      { id: 'h1', label: 'HTTP/1.1, one connection' },
      { id: 'h1x3', label: 'HTTP/1.1, three connections' },
      { id: 'h2', label: 'HTTP/2 (one TCP connection)' },
      { id: 'h3', label: 'HTTP/3 (QUIC)' }];
    var RES = [{ name: 'page', col: 'blue' }, { name: 'style', col: 'orange' }, { name: 'photo', col: 'green' }];
    var RTT = 4, SLOT = 25, N = 4, SLOTS = 36;
    var mode = 'h2', lost = { r: 0, k: 1 };
    var bar = h('div', { class: 'row' });
    var buttons = MODES.map(function (m) {
      var b = btn(m.label, function () { mode = m.id; draw(); }, 'small');
      bar.appendChild(b); return b;
    });
    el.appendChild(bar);
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 250', role: 'img', 'aria-label': 'Timeline of packets for three responses' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);

    function schedule() {
      // returns {hs: [[from,to,label,cls]], pk: [{r,k,arrive,orig,lost,deliver}], done: [t,t,t]}
      var hs = [], pk = [];
      var tcpStart = 2 * RTT, quicStart = RTT;
      function isLost(r, k) { return lost && lost.r === r && lost.k === k; }
      function add(r, k, t) {
        var p = { r: r, k: k, orig: t, lost: isLost(r, k) };
        p.arrive = p.lost ? t + RTT + 1 : t;
        pk.push(p); return p;
      }
      if (mode === 'h1') {
        hs.push([0, RTT, 'TCP', 'blue'], [RTT, 2 * RTT, 'TLS', 'purple']);
        var t = tcpStart + RTT, prevDone = 0;
        RES.forEach(function (_, r) {
          if (r > 0) t = prevDone + RTT;            // the next request goes when the last response is complete
          var ps = [];
          for (var k = 0; k < N; k++) ps.push(add(r, k, t + k));
          var d = 0; ps.forEach(function (p) { d = Math.max(d, p.arrive); p.deliver = d; });
          prevDone = d;
        });
      } else {
        var start = mode === 'h3' ? quicStart + RTT : tcpStart + RTT;
        if (mode === 'h3') hs.push([0, RTT, 'QUIC + TLS', 'orange']);
        else if (mode === 'h1x3') hs.push([0, RTT, 'TCP ×3', 'blue'], [RTT, 2 * RTT, 'TLS ×3', 'purple']);
        else hs.push([0, RTT, 'TCP', 'blue'], [RTT, 2 * RTT, 'TLS', 'purple']);
        var order = [];
        for (var k2 = 0; k2 < N; k2++) for (var r2 = 0; r2 < RES.length; r2++) order.push(add(r2, k2, start + order.length));
        if (mode === 'h2') {                         // one byte stream: strictly in sending order
          var d2 = 0; order.forEach(function (p) { d2 = Math.max(d2, p.arrive); p.deliver = d2; });
        } else {                                     // each stream (or connection) on its own
          RES.forEach(function (_, r) {
            var d3 = 0; order.filter(function (p) { return p.r === r; }).forEach(function (p) { d3 = Math.max(d3, p.arrive); p.deliver = d3; });
          });
        }
      }
      var done = RES.map(function (_, r) { return Math.max.apply(null, pk.filter(function (p) { return p.r === r; }).map(function (p) { return p.deliver; })) + 1; });
      return { hs: hs, pk: pk, done: done };
    }

    function draw() {
      buttons.forEach(function (b, i) { b.className = 'btn small' + (MODES[i].id === mode ? '' : ' ghost'); });
      var S = schedule();
      var X0 = 80, W = (706 - X0) / SLOTS;
      function X(t) { return X0 + t * W; }
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 250, rx: 10, class: 'f-card' }));
      for (var t = 0; t < SLOTS; t += 4) {
        svg.appendChild(s('line', { x1: X(t), y1: 28, x2: X(t), y2: 205, class: 'grid' }));
        svg.appendChild(s('text', { x: X(t), y: 222, class: 'mid xs muted', text: (t * SLOT) + ' ms' }));
      }
      svg.appendChild(s('text', { x: 14, y: 44, class: 'xs b', text: 'handshakes' }));
      S.hs.forEach(function (hh) {
        svg.appendChild(s('rect', { x: X(hh[0]) + 1, y: 30, width: (hh[1] - hh[0]) * W - 2, height: 20, rx: 4, class: 't-' + hh[3], stroke: 'var(--' + hh[3] + ')' }));
        svg.appendChild(s('text', { x: X((hh[0] + hh[1]) / 2), y: 44, class: 'mid xs b', text: hh[2] }));
      });
      RES.forEach(function (res, r) {
        var y = 66 + r * 46;
        svg.appendChild(s('text', { x: 14, y: y + 16, class: 'xs b', text: res.name }));
        S.pk.filter(function (p) { return p.r === r; }).forEach(function (p) {
          if (p.lost) {
            var xo = X(p.orig) + W / 2;
            svg.appendChild(s('path', { d: 'M' + (xo - 6) + ',' + (y + 4) + ' l12,14 M' + (xo + 6) + ',' + (y + 4) + ' l-12,14', class: 'line s-red', 'stroke-width': 3 }));
          }
          if (p.deliver > p.arrive) {
            svg.appendChild(s('rect', { x: X(p.arrive) + W - 1, y: y + 6, width: (p.deliver - p.arrive) * W, height: 12, rx: 2, fill: 'var(--red)', opacity: 0.3 }));
          }
          var g = s('rect', { x: X(p.arrive) + 1, y: y, width: W - 2, height: 24, rx: 3, fill: 'var(--' + res.col + ')', 'fill-opacity': 0.75, stroke: p.lost ? 'var(--red)' : 'var(--' + res.col + ')', 'stroke-width': p.lost ? 3 : 1.2, style: 'cursor:pointer' });
          g.addEventListener('click', function () { lost = (lost && lost.r === p.r && lost.k === p.k) ? null : { r: p.r, k: p.k }; draw(); });
          svg.appendChild(g);
          if (p.lost) svg.appendChild(s('text', { x: X(p.arrive) + W / 2, y: y + 38, class: 'mid xs b f-red', text: 'resent' }));
        });
        var dx = X(S.done[r]);
        svg.appendChild(s('text', { x: Math.min(dx + 4, 652), y: y + 16, class: 'xs b f-green halo', text: '✓ ' + (S.done[r] * SLOT) + ' ms' }));
      });
      svg.appendChild(s('text', { x: 14, y: 244, class: 'xs muted', text: 'time →' }));
      var total = Math.max.apply(null, S.done) * SLOT;
      var waits = S.pk.filter(function (p) { return p.deliver > p.arrive && !p.lost; });
      var victims = {}; waits.forEach(function (p) { victims[RES[p.r].name] = 1; });
      var msg = 'Everything is ready at <b>' + total + ' ms</b>. ';
      if (!lost) msg += 'With no loss, the differences are the handshakes, and HTTP/1.1’s one-at-a-time requests.';
      else if (mode === 'h2') msg += 'TCP must hand over bytes in order, so everything sent after the lost packet waits for it, including the ' +
        Object.keys(victims).filter(function (n) { return n !== RES[lost.r].name; }).join(' and ') + ', which lost nothing. That’s <b>head-of-line blocking</b>, moved down from HTTP to TCP.';
      else if (mode === 'h3') msg += 'QUIC knows which stream each packet belongs to, so only the ' + RES[lost.r].name + ' waits for its resent packet. The others carry on.';
      else if (mode === 'h1x3') msg += 'Separate connections don’t block each other either, but each needed its own handshakes, and browsers only open six per site.';
      else msg += 'Each request waits for the previous response to finish, so one loss delays everything after it.';
      out.innerHTML = msg;
    }
    draw();
  };

  // ---------------------------------------------------------------- ch34: a load balancer, live
  // Mirrors labs/ch34/balancer.py: round robin, least connections, hashing; health checks; 502s.
  // A queue model: each server handles one request at a time; requests arrive at random.

  WIDGETS.lbsim = function (el) {
    frame(el, 'Be the load balancer',
      'Requests arrive at random and the balancer hands each to one of three servers. Each server works on one at a time; the rest wait in its queue (the squares). ' +
      'Make one server slow, or crash it, and see which strategy copes.');
    var strat = h('select', { 'aria-label': 'strategy' });
    [['rr', 'round robin: take turns'], ['lc', 'least connections: the least busy'], ['hash', 'hash: same visitor, same server'], ['random', 'at random']].forEach(function (o) {
      strat.appendChild(h('option', { value: o[0], text: o[1] }));
    });
    var rate = h('input', { type: 'range', min: '10', max: '90', value: '45', 'aria-label': 'requests per second' });
    var rateOut = h('span', { class: 'mono' });
    var health = h('input', { type: 'checkbox', checked: 'checked' });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'strategy ', strat), h('label', {}, 'load ', rate, rateOut)));
    var SERVERS = [{ name: 'bean-1', ms: 20 }, { name: 'bean-2', ms: 20 }, { name: 'bean-3', ms: 20 }];
    var ctl = h('div', { class: 'row' });
    SERVERS.forEach(function (sv, i) {
      sv.speed = h('select', { 'aria-label': sv.name + ' speed' });
      [['20', 'fast (20 ms)'], ['120', 'slow (120 ms)'], ['down', 'crashed']].forEach(function (o) { sv.speed.appendChild(h('option', { value: o[0], text: o[1] })); });
      ctl.appendChild(h('label', {}, sv.name + ' ', sv.speed));
    });
    el.appendChild(ctl);
    el.appendChild(h('div', { class: 'row' }, h('label', {}, health, ' health checks (every second)'), btn('Reset the numbers', reset, 'small ghost')));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 200', role: 'img', 'aria-label': 'Three servers with their queues' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);

    var now = 0, rr = 0, done = [], errors = 0, total = 0, timer = null;
    SERVERS.forEach(function (sv) { sv.queue = []; sv.busyUntil = 0; sv.inRotation = true; sv.served = 0; });
    function reset() { done = []; errors = 0; total = 0; SERVERS.forEach(function (sv) { sv.served = 0; }); }
    function rnd() { return Math.random(); }
    function pick(visitor) {
      var live = SERVERS.filter(function (sv) { return sv.inRotation; });
      if (!live.length) return null;
      var v = strat.value;
      if (v === 'rr') { rr = (rr + 1) % live.length; return live[rr]; }
      if (v === 'lc') return live.reduce(function (a, b) { return (b.queue.length < a.queue.length) ? b : a; });
      if (v === 'hash') return live[visitor % live.length];
      return live[Math.floor(rnd() * live.length)];
    }
    var lastCheck = 0;
    function step(dt) {                        // advance the simulation by dt milliseconds
      var end = now + dt;
      var perMs = +rate.value / 1000;
      while (true) {
        var next = now - Math.log(1 - rnd()) / perMs;   // exponential gaps: random arrivals
        if (next > end) break;
        now = next;
        total++;
        var visitor = Math.floor(rnd() * 12);          // a dozen regular visitors
        var sv = pick(visitor);
        if (!sv) { errors++; continue; }
        if (sv.speed.value === 'down') { errors++; continue; }   // refused: the balancer answers 502
        sv.queue.push(now);
      }
      now = end;
      SERVERS.forEach(function (sv) {
        if (sv.speed.value === 'down') { sv.queue = []; return; }
        var ms = +sv.speed.value;
        while (sv.queue.length) {
          var start = Math.max(sv.busyUntil, sv.queue[0]);
          if (start + ms > now) break;
          var arrived = sv.queue.shift();
          sv.busyUntil = start + ms;
          sv.served++;
          done.push(sv.busyUntil - arrived);
          if (done.length > 400) done.shift();
        }
      });
      if (now - lastCheck > 1000) {                    // health checks
        lastCheck = now;
        SERVERS.forEach(function (sv) { sv.inRotation = !health.checked || sv.speed.value !== 'down'; });
      }
    }
    function draw() {
      rateOut.textContent = ' ' + rate.value + ' requests a second';
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 200, rx: 10, class: 'f-card' }));
      svg.appendChild(s('rect', { x: 20, y: 70, width: 110, height: 50, rx: 8, class: 't-orange', stroke: 'var(--orange)' }));
      svg.appendChild(s('text', { x: 75, y: 99, class: 'mid sm b', text: 'balancer' }));
      SERVERS.forEach(function (sv, i) {
        var y = 20 + i * 58;
        var down = sv.speed.value === 'down';
        svg.appendChild(s('path', { d: 'M132,95 L200,' + (y + 20), class: 'line ' + (sv.inRotation ? 's-muted' : 's-red dash'), 'stroke-width': 1.6 }));
        svg.appendChild(s('rect', { x: 200, y: y, width: 90, height: 40, rx: 6, class: down ? 't-red' : 't-green', stroke: down ? 'var(--red)' : 'var(--green)' }));
        svg.appendChild(s('text', { x: 245, y: y + 17, class: 'mid xs b', text: sv.name }));
        svg.appendChild(s('text', { x: 245, y: y + 31, class: 'mid xs muted', text: down ? 'crashed' : (sv.inRotation ? '' : 'out of rotation') || (sv.speed.value + ' ms each') }));
        var n = sv.queue.length;
        for (var k = 0; k < Math.min(n, 22); k++) {
          svg.appendChild(s('rect', { x: 300 + k * 11, y: y + 12, width: 9, height: 16, rx: 2, fill: n > 12 ? 'var(--red)' : 'var(--blue)', 'fill-opacity': 0.7 }));
        }
        svg.appendChild(s('text', { x: 700, y: y + 25, class: 'end xs b', text: (n ? n + ' waiting · ' : '') + 'served ' + sv.served }));
      });
      var sorted = done.slice().sort(function (a, b) { return a - b; });
      var avg = sorted.length ? sorted.reduce(function (a, b) { return a + b; }, 0) / sorted.length : 0;
      var p95 = sorted.length ? sorted[Math.floor(sorted.length * 0.95)] : 0;
      out.innerHTML = 'Recent requests: average <b>' + avg.toFixed(0) + ' ms</b>, slowest 5% over <b>' + p95.toFixed(0) + ' ms</b>. ' +
        'Errors (502s) so far: <b>' + errors + '</b> of ' + total + '. ' +
        (SERVERS.some(function (sv) { return sv.speed.value === 'down'; }) && !health.checked ? 'Without health checks, the balancer keeps sending requests to the crashed server, and every one of them fails.' :
          SERVERS.some(function (sv) { return sv.speed.value === '120'; }) && strat.value !== 'lc' ? 'The slow server’s queue grows, and everyone sent to it waits. Least connections notices, and sends it less.' : '');
    }
    function tick() { step(100); draw(); }
    function start() { if (!timer) timer = setInterval(tick, 100); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { es.forEach(function (e) { e.isIntersecting ? start() : stop(); }); }).observe(el);
    } else start();
    [strat, rate, health].concat(SERVERS.map(function (sv) { return sv.speed; })).forEach(function (c) { c.addEventListener('change', function () { reset(); draw(); }); });
    rate.addEventListener('input', draw);
    SERVERS[1].speed.value = '120';
    draw();
  };

  // ---------------------------------------------------------------- ch35: wrapping packets, and what it costs
  // Overheads for an IPv4 outer header. WireGuard also pads to 16 bytes; ESP to 4.

  WIDGETS.encap = function (el) {
    frame(el, 'Wrap it up',
      'Pick a tunnel (or two, one inside the other) and a link. The coloured bar is one full-size packet on the wire, drawn to scale. ' +
      'Every tunnel eats into the room left for the packet inside, and anything bigger has to be split, or dropped.');
    var TUNNELS = {
      none: { label: 'no tunnel', layers: [] },
      ipip: { label: 'IP in IP', layers: [['outer IP', 20, 'blue']] },
      gre: { label: 'GRE', layers: [['outer IP', 20, 'blue'], ['GRE', 4, 'orange']] },
      vxlan: { label: 'VXLAN', layers: [['outer IP', 20, 'blue'], ['UDP', 8, 'blue'], ['VXLAN', 8, 'orange'], ['inner Ethernet', 14, 'teal']] },
      wg: { label: 'WireGuard', layers: [['outer IP', 20, 'blue'], ['UDP', 8, 'blue'], ['WireGuard header', 16, 'purple'], ['tag', 16, 'purple', 1]] },
      wg6: { label: 'WireGuard, over IPv6', layers: [['outer IPv6', 40, 'blue'], ['UDP', 8, 'blue'], ['WireGuard header', 16, 'purple'], ['tag', 16, 'purple', 1]] },
      esp: { label: 'IPsec ESP, tunnel mode', layers: [['outer IP', 20, 'blue'], ['ESP header', 8, 'purple'], ['IV', 8, 'purple'], ['trailer', 2, 'purple', 1], ['ICV', 16, 'purple', 1]] },
      espnat: { label: 'IPsec ESP through a NAT', layers: [['outer IP', 20, 'blue'], ['UDP 4500', 8, 'orange'], ['ESP header', 8, 'purple'], ['IV', 8, 'purple'], ['trailer', 2, 'purple', 1], ['ICV', 16, 'purple', 1]] }
    };
    var outer = h('select', { 'aria-label': 'tunnel' }), inner = h('select', { 'aria-label': 'second tunnel' });
    Object.keys(TUNNELS).forEach(function (k) {
      outer.appendChild(h('option', { value: k, text: TUNNELS[k].label }));
      inner.appendChild(h('option', { value: k, text: TUNNELS[k].label }));
    });
    outer.value = 'wg';
    var link = h('select', { 'aria-label': 'link' });
    [['1500', 'Ethernet or Wi-Fi: 1,500 bytes'], ['1492', 'Bob’s internet (PPPoE): 1,492'], ['1280', 'the smallest IPv6 allows: 1,280']].forEach(function (o) {
      link.appendChild(h('option', { value: o[0], text: o[1] }));
    });
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'tunnel ', outer), h('label', {}, 'inside it ', inner)));
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'the link ', link)));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 150', role: 'img', 'aria-label': 'One packet with its tunnel headers, to scale' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);
    function draw() {
      var mtu = +link.value;
      var layers = TUNNELS[outer.value].layers.concat(TUNNELS[inner.value].layers);
      var overhead = layers.reduce(function (a, l) { return a + l[1]; }, 0);
      var room = mtu - overhead;
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 150, rx: 10, class: 'f-card' }));
      var X0 = 20, W = 680, scale = W / 1500, x = X0;
      svg.appendChild(s('text', { x: X0, y: 24, class: 'xs b', text: 'one ' + mtu + '-byte packet, drawn to scale (a full-width bar would be 1,500 bytes)' }));
      function put(l) {
        var w = Math.max(l[1] * scale, 3);
        svg.appendChild(s('rect', { x: x, y: 36, width: w, height: 40, fill: 'var(--' + l[2] + ')', 'fill-opacity': 0.8 }));
        x += w;
      }
      layers.filter(function (l) { return !l[3]; }).forEach(put);          // headers in front…
      var iw = Math.max(0, room) * scale;
      svg.appendChild(s('rect', { x: x, y: 36, width: iw, height: 40, class: 't-green', stroke: 'var(--green)' }));
      svg.appendChild(s('text', { x: x + iw / 2, y: 60, class: 'mid sm b', text: 'the packet inside: at most ' + room + ' bytes' }));
      x += iw;
      var tail = function (k) { return TUNNELS[k].layers.filter(function (l) { return l[3]; }); };
      tail(inner.value).concat(tail(outer.value)).forEach(put);              // …tags and trailers behind, the inner tunnel's first
      var lx = X0;
      layers.forEach(function (l, i) {
        svg.appendChild(s('rect', { x: lx, y: 96, width: 10, height: 10, fill: 'var(--' + l[2] + ')', 'fill-opacity': 0.8 }));
        svg.appendChild(s('text', { x: lx + 14, y: 105, class: 'xs', text: l[0] + ' ' + l[1] }));
        lx += 30 + 6.2 * (l[0].length + String(l[1]).length);
        if (lx > 620 && i < layers.length - 1) { lx = X0; }
      });
      svg.appendChild(s('text', { x: X0, y: 136, class: 'xs b', text: layers.length ? 'the tunnels add ' + overhead + ' bytes to every packet' : 'no tunnel: the whole packet is yours' }));
      var mss = room - 40;
      out.innerHTML = 'Inside the tunnel, the biggest packet is <b>' + room + ' bytes</b>, so TCP can carry at most <b>' + mss + ' bytes</b> of data per segment (Chapter 27’s MSS). ' +
        'That’s ' + (100 * overhead / mtu).toFixed(1) + '% of every full packet spent on wrapping. ' +
        (outer.value === 'wg' && inner.value === 'none' && mtu === 1500 ? 'WireGuard sets its interface to 1,420, not 1,440, to leave room for an IPv6 outer header too.' :
          inner.value !== 'none' && outer.value !== 'none' ? 'Tunnels inside tunnels are common: a data centre’s VXLAN, inside a company’s VPN, over a home connection.' :
            'A program that sends a bigger packet into the tunnel gets it split into fragments or, if fragmenting isn’t allowed, dropped, with an ICMP “too big” message that firewalls sometimes throw away. Chapter 38 hunts that problem down.');
    }
    [outer, inner, link].forEach(function (c) { c.addEventListener('change', draw); });
    draw();
  };

  // ---------------------------------------------------------------- ch36: follow a packet through container networking
  // The addresses are box.sh's (labs/ch36), and the NAT entries are the ones conntrack showed.

  WIDGETS.podnet = function (el) {
    frame(el, 'Follow the packet',
      'Pick a journey, then step through it. At each hop, the packet’s addresses are shown as they are at that moment; ' +
      '<b style="color:var(--orange)">orange</b> means something just rewrote them.');
    var PUB = '203.0.113.77';
    var TRIPS = {
      boxbox: { label: 'db → web (box to box)', hops: [
        ['inside db', 'db’s program connects to 10.36.0.2:80. Its routing table says 10.36.0.0/24 is on eth0, so no router is needed: it ARPs for web’s MAC address.', '10.36.0.3:40112', '10.36.0.2:80'],
        ['eth0 → veth-db', 'Out of db’s end of the virtual cable, in at the host’s end, veth-db.', '10.36.0.3:40112', '10.36.0.2:80'],
        ['br36', 'The bridge is a switch: it looks up web’s MAC address in its table (bridge fdb), and sends the frame out of veth-web only.', '10.36.0.3:40112', '10.36.0.2:80'],
        ['inside web', 'Delivered to the web server’s socket on port 80. Nothing was rewritten: to web, db is just another computer on its network.', '10.36.0.3:40112', '10.36.0.2:80']] },
      out: { label: 'bot → example.org (out to the internet)', hops: [
        ['inside bot', 'bot connects to 104.20.26.136:443. That isn’t on its network, so it sends the packet to its default gateway, 10.36.0.1: the host.', '10.36.0.4:36680', '104.20.26.136:443'],
        ['br36 → the host', 'The host receives it on br36, and because ip_forward is switched on, routes it: towards the default route, out of wlan0.', '10.36.0.4:36680', '104.20.26.136:443'],
        ['nftables: postrouting', 'On the way out, the masquerade rule replaces the private source address with the host’s own, and conntrack remembers the swap so replies can be turned back.', '192.168.1.4:36680', '104.20.26.136:443', 'src'],
        ['wlan0 → the home router', 'Now it’s an ordinary packet from the Pi. The home router does its own NAT (Chapter 22): a second rewrite, to the house’s public address.', PUB + ':36680', '104.20.26.136:443', 'src'],
        ['example.org', 'The server sees a connection from the house. It has no idea there’s a Pi, let alone a box inside it. Replies go back through both NATs, each undoing its own rewrite.', PUB + ':36680', '104.20.26.136:443']] },
      pub: { label: 'the Mac → Pi:8036 (a published port)', hops: [
        ['the Mac', 'Bob runs curl http://192.168.1.4:8036/: an ordinary connection to the Pi.', '192.168.1.3:62004', '192.168.1.4:8036'],
        ['wlan0 → nftables: prerouting', 'Before the host decides where the packet goes, the DNAT rule rewrites its destination: port 8036 on the host becomes web’s port 80.', '192.168.1.3:62004', '10.36.0.2:80', 'dst'],
        ['routing → br36 → veth-web', '10.36.0.2 is on br36, so the host forwards it there, and the bridge delivers it to web.', '192.168.1.3:62004', '10.36.0.2:80'],
        ['inside web', 'web answers the Mac directly, from 10.36.0.2:80…', '10.36.0.2:80', '192.168.1.3:62004'],
        ['the reply, leaving the host', '…and conntrack turns the reply’s source back into 192.168.1.4:8036, so the Mac sees an answer from the address it asked. This is what docker run -p 8036:80 sets up.', '192.168.1.4:8036', '192.168.1.3:62004', 'src']] }
    };
    var trip = 'out', step = 0;
    var bar = h('div', { class: 'row' });
    var buttons = Object.keys(TRIPS).map(function (k) {
      var b = btn(TRIPS[k].label, function () { trip = k; step = 0; draw(); }, 'small');
      bar.appendChild(b); return b;
    });
    el.appendChild(bar);
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 170', role: 'img', 'aria-label': 'The hops of the packet and its addresses' });
    el.appendChild(svg);
    var nav = h('div', { class: 'row' });
    var back = btn('◀ Back', function () { if (step > 0) { step--; draw(); } }, 'small ghost');
    var next = btn('Next ▶', function () { if (step < TRIPS[trip].hops.length - 1) { step++; draw(); } }, 'small');
    var where = h('span', { class: 'xs muted' });
    nav.appendChild(back); nav.appendChild(next); nav.appendChild(where);
    el.appendChild(nav);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:3.6em' });
    el.appendChild(out);
    function draw() {
      buttons.forEach(function (b, i) { b.className = 'btn small' + (Object.keys(TRIPS)[i] === trip ? '' : ' ghost'); });
      var hops = TRIPS[trip].hops, hp = hops[step];
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 170, rx: 10, class: 'f-card' }));
      var n = hops.length, W = 680 / n;
      hops.forEach(function (x, i) {
        var cx = 20 + W * i + W / 2;
        if (i < n - 1) svg.appendChild(s('path', { d: 'M' + (cx + 14) + ',40 L' + (cx + W - 14) + ',40', class: 'line ' + (i < step ? 's-ink' : 's-muted'), 'stroke-width': 2, 'marker-end': 'url(#ah-' + (i < step ? 'ink' : 'muted') + ')' }));
        svg.appendChild(s('circle', { cx: cx, cy: 40, r: i === step ? 11 : 8, class: i === step ? 'f-orange' : i < step ? 'f-ink' : 'f-line' }));
        svg.appendChild(s('text', { x: cx, y: 72, class: 'mid xs' + (i === step ? ' b' : ' muted'), text: x[0].length > 22 ? x[0].slice(0, 21) + '…' : x[0] }));
      });
      function field(x, label, value, changed) {
        svg.appendChild(s('rect', { x: x, y: 96, width: 300, height: 52, rx: 8, class: changed ? 't-orange' : 't-blue', stroke: changed ? 'var(--orange)' : 'var(--blue)', 'stroke-width': changed ? 2.5 : 1.4 }));
        svg.appendChild(s('text', { x: x + 150, y: 116, class: 'mid xs b', text: label }));
        svg.appendChild(s('text', { x: x + 150, y: 137, class: 'mid sm mono b', text: value }));
      }
      field(40, 'source', hp[2], hp[4] === 'src');
      field(380, 'destination', hp[3], hp[4] === 'dst');
      svg.appendChild(s('text', { x: 360, y: 128, class: 'mid lg b', text: '→' }));
      where.textContent = '  hop ' + (step + 1) + ' of ' + n;
      out.innerHTML = '<b>' + hp[0] + '.</b> ' + hp[1];
    }
    draw();
  };

  // ---------------------------------------------------------------- ch37: replay a real page load, layer by layer
  // Events from the Pi's decrypted capture of `curl https://example.org/` (Chapter 37). Times in ms from the first packet.

  WIDGETS.replay = function (el) {
    frame(el, 'Replay the page load',
      'The packets from the real capture (leaving out bare acknowledgements), on a time line. Press play, or pick any packet: the stack shows which layers it used, ' +
      'and which chapter explains them. Blue arrows go from the Pi; purple ones come back.');
    // [ms, out?, summary, bytes, layers, chapters, explanation]
    var EV = [
      [0.0, 1, 'ARP: who has 192.168.1.1?', 42, 'L', '21', 'The ARP cache was empty, so before the first real packet, the Pi shouts for the router’s MAC address. Broadcast, link layer only: no IP at all.'],
      [5.1, 0, 'ARP: 192.168.1.1 is at 14:c3:5e:40:0b:32', 42, 'L', '21', 'The router answers, to the Pi alone.'],
      [5.1, 1, 'DNS: A? example.org   AAAA? example.org', 71, 'LIUD', '29, 26', 'Two questions at once, in two UDP datagrams, to the DNS server DHCP named: the router.'],
      [42.5, 0, 'DNS: AAAA 2606:4700:10::ac42:9ded …   A 172.66.157.237, 104.20.26.136', 103, 'LIUD', '29, 25', 'The router didn’t have the answers cached, and had to ask upstream: 37 ms. Both IPv6 and IPv4 addresses, but the Pi has no global IPv6 address, so it will use IPv4.'],
      [42.7, 1, 'TCP SYN → 172.66.157.237:443', 74, 'LIT', '27', 'A new TCP connection: MSS 1460, SACK, timestamps, window scaling (Chapter 27’s options). The nearest Cloudflare site, thanks to anycast (Chapter 34).'],
      [80.6, 0, 'TCP SYN, ACK', 74, 'LIT', '27, 28', 'One round trip: 38 ms. The server offers MSS 1400, and a window scale of 8192.'],
      [80.6, 1, 'TCP ACK', 66, 'LIT', '27', 'Established. The Pi can send data at once.'],
      [83.1, 1, 'TLS ClientHello (1,388 + 183 bytes, two segments)', 1571, 'LITS', '32, 42', 'Too big for one segment: besides an X25519 key share, curl offers a post-quantum one (X25519MLKEM768), over a kilobyte by itself. The SNI says example.org.'],
      [124.9, 0, 'TLS ServerHello, change_cipher_spec, 🔒 …', 1506, 'LITS', '32', 'The server’s key share: from here on, everything is encrypted. The certificate chain follows in the next segments.'],
      [127.9, 0, '🔒 EncryptedExtensions, Certificate, CertificateVerify, Finished', 826, 'LITS', '31, 32', 'ALPN says h2. The chain leads to a trusted root; the signature covers the whole handshake; the Finished MAC matches.'],
      [131.4, 1, '🔒 change_cipher_spec, Finished', 146, 'LITS', '32', 'The Pi’s half of the handshake is done…'],
      [131.9, 1, '🔒 HTTP/2 preface, SETTINGS, WINDOW_UPDATE, HEADERS: GET /', 189, 'LITSH', '33', '…and the request goes straight after it: 189 bytes on the wire, headers compressed from 127 bytes to 28.'],
      [171.0, 0, '🔒 SETTINGS, WINDOW_UPDATE, SETTINGS', 619, 'LITSH', '33', 'The server’s HTTP/2 settings, and its acknowledgement of curl’s.'],
      [174.4, 0, '🔒 HEADERS[1]: 200 OK', 247, 'LITSH', '30, 33, 34', 'The response: 200 OK, from Cloudflare’s cache.'],
      [174.6, 0, '🔒 DATA[1]: 713 bytes of HTML', 810, 'LITSH', '30, 33', 'The page itself, and an empty DATA frame with END_STREAM.'],
      [174.7, 1, '🔒 GOAWAY, close_notify, TCP FIN', 114, 'LITSH', '27, 32, 33', 'curl wanted one page, so it says goodbye at every layer: HTTP/2, then TLS, then TCP.'],
      [211.7, 0, 'TCP FIN, ACK', 66, 'LIT', '27', 'The server closes its side too. The page arrived 175 ms after the first packet.']];
    var LAYERS = [['H', 'HTTP/2', 'green'], ['D', 'DNS', 'green'], ['S', 'TLS', 'purple'], ['T', 'TCP', 'blue'], ['U', 'UDP', 'blue'], ['I', 'IP', 'yellow'], ['L', 'Wi-Fi / Ethernet', 'teal']];
    var cur = 0, timer = null;
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 250', role: 'img', 'aria-label': 'Packets of the page load on a time line, and the protocol layers of the chosen one' });
    el.appendChild(svg);
    var bar = h('div', { class: 'row' });
    var play = btn('▶ Play', toggle, 'small');
    bar.appendChild(btn('◀', function () { stop(); cur = Math.max(0, cur - 1); draw(); }, 'small ghost'));
    bar.appendChild(play);
    bar.appendChild(btn('▶', function () { stop(); cur = Math.min(EV.length - 1, cur + 1); draw(); }, 'small ghost'));
    el.appendChild(bar);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:4.2em' });
    el.appendChild(out);
    function X(t) { return 30 + t / 215 * 660; }
    function draw() {
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 250, rx: 10, class: 'f-card' }));
      [0, 50, 100, 150, 200].forEach(function (t) {
        svg.appendChild(s('line', { x1: X(t), y1: 20, x2: X(t), y2: 96, class: 'grid' }));
        svg.appendChild(s('text', { x: X(t), y: 110, class: 'mid xs muted', text: t + ' ms' }));
      });
      svg.appendChild(s('line', { x1: 30, y1: 58, x2: 690, y2: 58, class: 'line s-muted', 'stroke-width': 1 }));
      EV.forEach(function (e, i) {
        var up = e[1], y1 = up ? 58 : 58, y2 = up ? 26 : 90;
        var col = up ? 'blue' : 'purple';
        var line = s('line', { x1: X(e[0]), y1: y1, x2: X(e[0]), y2: y2, class: 'line s-' + col, 'stroke-width': i === cur ? 4 : 2, opacity: i <= cur ? 1 : 0.3 });
        var dot = s('circle', { cx: X(e[0]), cy: y2, r: i === cur ? 7 : 4.5, fill: 'var(--' + col + ')', opacity: i <= cur ? 1 : 0.3, style: 'cursor:pointer' });
        dot.addEventListener('click', function () { stop(); cur = i; draw(); });
        svg.appendChild(line); svg.appendChild(dot);
      });
      svg.appendChild(s('text', { x: 30, y: 16, class: 'xs muted', text: 'the Pi sends ↑' }));
      svg.appendChild(s('text', { x: 690, y: 104, class: 'end xs muted', text: 'arrives at the Pi ↓' }));
      var e = EV[cur];
      LAYERS.forEach(function (L, k) {
        var on = e[4].indexOf(L[0]) >= 0;
        var y = 124 + k * 17;
        svg.appendChild(s('rect', { x: 30, y: y, width: 200, height: 15, rx: 3, class: on ? 't-' + L[2] : 'f-surface', stroke: on ? 'var(--' + L[2] + ')' : 'var(--line)', opacity: on ? 1 : 0.5 }));
        svg.appendChild(s('text', { x: 130, y: y + 11.5, class: 'mid xs' + (on ? ' b' : ' muted'), text: L[1] }));
      });
      svg.appendChild(s('text', { x: 250, y: 140, class: 'sm b', text: (e[1] ? '↑ ' : '↓ ') + e[2].slice(0, 62) }));
      svg.appendChild(s('text', { x: 250, y: 162, class: 'xs', text: 'at ' + e[0].toFixed(1) + ' ms · ' + e[3].toLocaleString() + ' bytes on the wire' }));
      svg.appendChild(s('text', { x: 250, y: 184, class: 'xs muted', text: 'chapters ' + e[5] }));
      out.innerHTML = '<b>Packet ' + (cur + 1) + ' of ' + EV.length + '.</b> ' + e[6];
      play.textContent = timer ? '❚❚ Pause' : '▶ Play';
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function toggle() {
      if (timer) { stop(); draw(); return; }
      if (cur >= EV.length - 1) cur = 0;
      timer = setInterval(function () { if (cur >= EV.length - 1) { stop(); } else { cur++; } draw(); }, reduced ? 2400 : 1400);
      draw();
    }
    draw();
  };

  // ---------------------------------------------------------------- ch38: be the network detective
  // Every output here is real: from labs/ch38/breakit.sh's broken networks on the Pi, and (case 4) Bob's own home network.

  WIDGETS.detective = function (el) {
    frame(el, 'Be the detective',
      'Pick a case. Run whichever tests you like (each shows its real output), then name the culprit. ' +
      'A good detective needs few tests: start at the bottom, and let each answer choose the next question.');
    var PING_GW = '$ ping -c 2 10.38.0.1\n64 bytes from 10.38.0.1: icmp_seq=1 ttl=64 time=0.053 ms\n64 bytes from 10.38.0.1: icmp_seq=2 ttl=64 time=0.027 ms\n2 packets transmitted, 2 received, 0% packet loss';
    var PING_IP = '$ ping -c 2 1.1.1.1\n64 bytes from 1.1.1.1: icmp_seq=1 ttl=55 time=11.5 ms\n64 bytes from 1.1.1.1: icmp_seq=2 ttl=55 time=10.9 ms\n2 packets transmitted, 2 received, 0% packet loss';
    var ROUTE_OK = '$ ip route\ndefault via 10.38.0.1 dev eth0\n10.38.0.0/24 dev eth0 proto kernel scope link src 10.38.0.2';
    var DIG1 = '$ dig +short example.org @1.1.1.1\n172.66.157.237\n104.20.26.136';
    var CASES = [
      { title: 'Nothing loads', symptom: 'Grandpa’s laptop: every website says “server not found”. The Wi-Fi icon looks fine.',
        tools: [['ping the router', PING_GW], ['ping 1.1.1.1', PING_IP], ['look at the routes', ROUTE_OK],
          ['dig example.org', '$ dig example.org\n;; communications error to 10.38.0.53#53: timed out\n;; no servers could be reached'],
          ['dig @1.1.1.1', DIG1],
          ['curl https://example.org/', '$ curl https://example.org/\ncurl: (6) Could not resolve host: example.org']],
        options: [['The Wi-Fi is broken', 0, 'The router answers ping, so the Wi-Fi and the first hop are fine.'],
          ['There’s no route to the internet', 0, '1.1.1.1 answers ping: packets get out and back.'],
          ['The DNS server it was given doesn’t work', 1, 'Right. The internet works by address, 1.1.1.1 answers DNS questions, but the configured server, 10.38.0.53, doesn’t. Fix the DNS setting (it usually comes from DHCP, Chapter 22).'],
          ['example.org is down', 0, 'dig @1.1.1.1 found its address, and every site fails the same way: the problem is on this side.']] },
      { title: 'No internet at all', symptom: 'The laptop is on the network, but nothing outside works, not even by address.',
        tools: [['ping the router', PING_GW], ['ping 1.1.1.1', '$ ping -c 2 1.1.1.1\nping: connect: Network is unreachable'],
          ['look at the routes', '$ ip route\n10.38.0.0/24 dev eth0 proto kernel scope link src 10.38.0.2'],
          ['dig @1.1.1.1', '$ dig example.org @1.1.1.1\n;; UDP setup with 1.1.1.1#53(1.1.1.1) for example.org failed: network unreachable.\n;; no servers could be reached']],
        options: [['The router is broken', 0, 'The router answers ping, instantly.'],
          ['The laptop has no default route', 1, 'Right. “Network is unreachable” comes from the laptop itself, before any packet is sent: its routing table only knows its own subnet. A gateway missing from DHCP, or a VPN that deleted the route, does this (Chapter 20).'],
          ['DNS is broken', 0, 'Even pinging an address fails, so it’s below DNS.'],
          ['The internet provider is down', 0, 'Then the error would be silence (timeouts), not “unreachable” from our own computer.']] },
      { title: 'Big things hang', symptom: 'Small pages and chat messages work. Big downloads stall at 0 bytes, and some secure websites never finish connecting.',
        tools: [['ping the router', PING_GW], ['ping 1.1.1.1', PING_IP], ['dig @1.1.1.1', DIG1],
          ['curl https://example.org/', '$ curl -m 6 https://example.org/\ncurl: (28) Connection timed out after 6002 milliseconds'],
          ['curl a small file', '$ curl http://10.38.2.2:8038/small.txt\nHTTP 200, 6 bytes in 0.005448 s'],
          ['curl a big file', '$ curl -m 6 http://10.38.2.2:8038/big.bin\ncurl: (28) Operation timed out after 6002 milliseconds with 0 out of 2000000 bytes received'],
          ['ping with a big packet, DF set', '$ ping -c 1 -M do -s 1472 10.38.2.2\nPING 10.38.2.2 (10.38.2.2) 1472(1500) bytes of data.\n1 packets transmitted, 0 received, 100% packet loss'],
          ['ping with a smaller one', '$ ping -c 1 -M do -s 1372 10.38.2.2\nPING 10.38.2.2 (10.38.2.2) 1372(1400) bytes of data.\n1380 bytes from 10.38.2.2: icmp_seq=1 ttl=62 time=0.093 ms\n1 packets transmitted, 1 received, 0% packet loss']],
        options: [['The Wi-Fi is too slow', 0, 'Small things are instant, and big ones don’t get slow: they stop dead.'],
          ['DNS is broken', 0, 'Names resolve fine, and connections open.'],
          ['A path MTU black hole', 1, 'Right. Packets up to 1,400 bytes get through, bigger ones vanish, and nobody sends back the ICMP “too big” message that would tell the sender to shrink them. TLS certificates and file downloads need full-size packets; ACKs and small pages don’t.'],
          ['The server is overloaded', 0, 'An overloaded server is slow for small requests too.']] },
      { title: 'One site never loads', symptom: 'On Bob’s home network, example.com never opens. example.org, and everything else, is fine.',
        tools: [['dig example.com', '$ dig +time=2 +tries=1 example.com @8.8.8.8\n;; communications error to 8.8.8.8#53: timed out'],
          ['dig example.org', '$ dig +short example.org @8.8.8.8\n104.20.26.136'],
          ['dig example.com over TCP', '$ dig +tcp +short example.com @8.8.8.8\n104.20.23.154'],
          ['dig with other servers', '$ dig example.com @1.1.1.1      (timed out)\n$ dig example.com @192.168.1.1  (timed out)\n$ dig example.net @8.8.8.8      172.66.175.59\n$ dig myexample.com @8.8.8.8    (timed out)\n$ dig example.com.au @8.8.8.8   198.202.211.1'],
          ['DNS traceroute: example.org', '$ python3 dnstrace.py example.org 8.8.8.8\n  ttl  1: expired at 192.168.1.1\n  ttl  2: silence\n  ttl  3: expired at 203.0.113.9\n  …\n  ttl  8: an ANSWER from 8.8.8.8, 36.0 ms'],
          ['DNS traceroute: example.com', '$ python3 dnstrace.py example.com 8.8.8.8\n  ttl  1: expired at 192.168.1.1\n  ttl  2: silence\n  ttl  3: silence\n  … silence all the way to ttl 20']],
        options: [['example.com is down', 0, 'Over TCP, it resolves at once, and the site itself works.'],
          ['Google’s DNS is broken', 0, 'Every resolver fails the same way, even the router, and only for this name.'],
          ['Something near the house drops UDP DNS questions for names ending in example.com', 1, 'Right. Only UDP, only that name (and anything ending in it), whatever the server; and the question never gets past the second hop. So it’s the home router or the provider’s first box, filtering. The workaround is DNS over TCP or HTTPS; the fix is to find the filter.'],
          ['The Wi-Fi drops big packets', 0, 'These questions are tiny, and example.org’s are the same size.']] },
      { title: 'The server is down!', symptom: 'Bob pings Grandpa’s new server, 10.38.0.2, and gets nothing back. “It’s dead,” says Bob.',
        tools: [['ping 10.38.0.2', '$ ping -c 2 10.38.0.2\n2 packets transmitted, 0 received, 100% packet loss'],
          ['curl http://10.38.0.2/', '$ curl http://10.38.0.2/\nHTTP 200'],
          ['nc -vz 10.38.0.2 80', '$ nc -vz 10.38.0.2 80\nConnection to 10.38.0.2 80 port [tcp/http] succeeded!']],
        options: [['It’s dead', 0, 'It served a web page.'],
          ['It’s alive, and its firewall drops ping', 1, 'Right. Ping is just one kind of packet (ICMP echo, Chapter 21), and many firewalls drop it. Test the thing you care about: here, a TCP connection to port 80.'],
          ['The network between is broken', 0, 'Then the web page wouldn’t have arrived either.']] }];
    var ci = 0, used = {}, answered = false;
    var picker = h('div', { class: 'row' });
    var pbtns = CASES.map(function (c, i) { var b = btn((i + 1) + '. ' + c.title, function () { ci = i; used = {}; answered = false; draw(); }, 'small'); picker.appendChild(b); return b; });
    el.appendChild(picker);
    var sym = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);font-size:105%' });
    var tools = h('div', { class: 'row', style: 'gap:6px' });
    var term = h('pre', { class: 'out', style: 'white-space:pre-wrap;word-break:normal;overflow-wrap:anywhere;min-height:5em;font-size:85%' });
    var ask = h('div', { style: 'margin-top:8px' });
    var verdict = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    [sym, h('div', { class: 'w-hint', html: '<b>Tests</b>' }), tools, term, h('div', { class: 'w-hint', html: '<b>Your diagnosis</b>' }), ask, verdict].forEach(function (x) { el.appendChild(x); });
    function draw() {
      var c = CASES[ci];
      pbtns.forEach(function (b, i) { b.className = 'btn small' + (i === ci ? '' : ' ghost'); });
      sym.innerHTML = '<b>The case:</b> ' + c.symptom;
      tools.innerHTML = ''; ask.innerHTML = ''; verdict.innerHTML = '';
      term.textContent = 'Pick a test.';
      c.tools.forEach(function (t, i) {
        tools.appendChild(btn(t[0], function () { used[i] = 1; term.textContent = t[1]; draw2(); }, 'small' + (used[i] ? '' : ' ghost')));
      });
      c.options.forEach(function (o) {
        ask.appendChild(btn(o[0], function () {
          answered = true;
          var n = Object.keys(used).length;
          verdict.innerHTML = (o[1] ? '✓ ' : '✗ ') + o[2] + (o[1] ? ' <span class="muted">(' + n + ' test' + (n === 1 ? '' : 's') + ' used.)</span>' : ' Try another test, or another answer.');
        }, 'small ghost'));
      });
    }
    function draw2() {
      Array.prototype.forEach.call(tools.children, function (b, i) { b.className = 'btn small' + (used[i] ? '' : ' ghost'); });
    }
    draw();
  };

  // ---------------------------------------------------------------- ch39: a flow table, and a controller behind it
  // The same switch, rules and controller logic as labs/ch39 (controller.py driving Open vSwitch).

  WIDGETS.flowtable = function (el) {
    frame(el, 'Be the switch',
      'This is switch s1 from the lab, with its flow table. Send it packets. It checks its rules from the highest priority down, and does what the first match says. ' +
      'When only the bottom rule matches, it has to ask the controller, which learns, decides, and adds a rule so the switch never has to ask about that again.');
    var HOSTS = { h1: { port: 1, mac: '0a:39:00:00:00:01', ip: '10.39.0.1' }, h2: { port: 2, mac: '0a:39:00:00:00:02', ip: '10.39.0.2' },
      h3: { port: 9, mac: '0a:39:00:00:00:03', ip: '10.39.0.3' } };
    var BCAST = 'ff:ff:ff:ff:ff:ff';
    var PACKETS = [
      ['h1: who has 10.39.0.2? (ARP)', 'h1', null, 'arp'],
      ['h2: 10.39.0.2 is here (ARP reply)', 'h2', 'h1', 'arp'],
      ['h1 pings h2', 'h1', 'h2', 'ip'],
      ['h2 replies to h1', 'h2', 'h1', 'ip'],
      ['h3 pings h1', 'h3', 'h1', 'ip'],
      ['h1 pings h3', 'h1', 'h3', 'ip']];
    var table, macs, alone, asked, busy = false, blocked = false;
    var pk = h('div', { class: 'row', style: 'gap:6px' });
    PACKETS.forEach(function (p) { pk.appendChild(btn(p[0], function () { send(p); }, 'small')); });
    var blockBtn = btn('controller: block 10.39.0.3 everywhere', function () { block(); }, 'small ghost');
    var ctl = h('div', { class: 'row' }, blockBtn, btn('start again', function () { reset(); }, 'small ghost'));
    el.appendChild(h('div', { class: 'w-hint', html: '<b>Send a packet</b>' }));
    el.appendChild(pk);
    el.appendChild(ctl);
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 150', role: 'img', 'aria-label': 'Switch s1 with h1 on port 1, h2 on port 2, and a cable to s2 and h3 on port 9, with the controller above' });
    el.appendChild(svg);
    var wrap = h('div', { class: 'table-scroll' });
    var tbl = h('table', { class: 'data', style: 'font-size:88%;margin:6px 0' });
    wrap.appendChild(tbl);
    el.appendChild(wrap);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans);min-height:3.2em' });
    el.appendChild(out);

    function reset() {
      table = [{ prio: 0, match: {}, act: 'CONTROLLER', n: 0 }];
      macs = {}; alone = 0; asked = 0; blocked = false; busy = false;
      blockBtn.disabled = false;
      out.innerHTML = 'The table starts with one rule, priority 0, that matches anything: “send it to the controller”. Try h1’s ARP question first.';
      drawTable(); drawNet();
    }
    function matchText(m) {
      var p = [];
      if (m.ip) p.push('ip,nw_src=' + m.ip);
      if (m.in_port) p.push('in_port=' + m.in_port);
      if (m.dl_dst) p.push('dl_dst=' + m.dl_dst);
      return p.length ? p.join(',') : '(anything)';
    }
    function sorted() { return table.slice().sort(function (a, b) { return b.prio - a.prio; }); }
    function drawTable(hi, cls) {
      tbl.innerHTML = '';
      tbl.appendChild(h('tr', {}, h('th', { text: 'priority' }), h('th', { text: 'match' }), h('th', { text: 'actions' }), h('th', { text: 'n_packets' })));
      sorted().forEach(function (r) {
        var bg = r === hi ? 'background:var(--tint-' + (cls || 'yellow') + ')' : '';
        tbl.appendChild(h('tr', { style: bg }, h('td', { text: String(r.prio) }), h('td', { class: 'mono', style: 'font-family:var(--mono)', text: matchText(r.match) }),
          h('td', { style: 'font-family:var(--mono)', text: r.act }), h('td', { text: String(r.n) })));
      });
    }
    function drawNet(inPort, outs, toCtl) {
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 150, rx: 10, class: 'f-card' }));
      function node(x, y, w, label, sub, cls) {
        svg.appendChild(s('rect', { x: x - w / 2, y: y - 18, width: w, height: 36, rx: 7, class: cls || 'f-surface', stroke: 'var(--line)', 'stroke-width': 1.4 }));
        svg.appendChild(s('text', { x: x, y: y - 1, class: 'mid xs b', text: label }));
        if (sub) svg.appendChild(s('text', { x: x, y: y + 12, class: 'mid xs mono muted', text: sub }));
      }
      var PX = { 1: [90, 60], 2: [90, 122], 9: [630, 100] };
      function link(p, cls, w) {
        var a = PX[p];
        svg.appendChild(s('path', { d: 'M' + (p === 9 ? 405 : 315) + ',100 L' + (a[0] + (p === 9 ? -50 : 50)) + ',' + a[1], class: 'line ' + cls, 'stroke-width': w }));
        svg.appendChild(s('text', { x: p === 9 ? 420 : 300, y: p === 9 ? 92 : (p === 1 ? 88 : 116), class: (p === 9 ? '' : 'end ') + 'xs muted', text: 'port ' + p }));
      }
      [1, 2, 9].forEach(function (p) {
        var cls = 's-muted', w = 2.5;
        if (p === inPort) { cls = 's-blue'; w = 5; }
        if (outs && outs.indexOf(p) >= 0) { cls = 's-green'; w = 5; }
        link(p, cls, w);
      });
      svg.appendChild(s('path', { d: 'M360,82 L360,40', class: 'line ' + (toCtl ? 's-purple' : 's-line'), 'stroke-width': toCtl ? 4 : 1.5, 'stroke-dasharray': '5 4' }));
      node(360, 26, 150, 'controller', null, toCtl ? 't-purple' : 'f-surface');
      node(360, 100, 90, 'switch s1', null, 't-green');
      node(90, 60, 100, 'h1', '10.39.0.1');
      node(90, 122, 100, 'h2', '10.39.0.2');
      node(630, 100, 150, 's2, then h3', '10.39.0.3');
      svg.appendChild(s('text', { x: 700, y: 20, class: 'end xs', text: 'by the switch alone: ' + alone + '   ·   asked the controller: ' + asked }));
    }
    function ruleMatches(r, p) {
      var src = HOSTS[p[1]], dst = p[2] ? HOSTS[p[2]].mac : BCAST;
      if (r.match.ip && (p[3] !== 'ip' || src.ip !== r.match.ip)) return false;
      if (r.match.in_port && r.match.in_port !== src.port) return false;
      if (r.match.dl_dst && r.match.dl_dst !== dst) return false;
      return true;
    }
    function send(p) {
      if (busy) return;
      var rows = sorted(), i = 0, src = HOSTS[p[1]];
      busy = true;
      drawNet(src.port);
      function step() {
        var r = rows[i];
        drawTable(r, 'yellow');
        if (ruleMatches(r, p)) { setTimeout(function () { act(r, p); }, reduced ? 0 : 280); return; }
        i++;
        setTimeout(step, reduced ? 0 : 220);
      }
      step();
    }
    function act(r, p) {
      var src = HOSTS[p[1]], dstMac = p[2] ? HOSTS[p[2]].mac : BCAST;
      r.n++;
      busy = false;
      if (r.act === 'drop') {
        alone++;
        drawTable(r, 'red'); drawNet(src.port);
        out.innerHTML = 'Matched the priority-100 rule from the controller’s policy: <b>dropped</b>, by the switch itself. The controller never even hears about it.';
        return;
      }
      if (r.act !== 'CONTROLLER') {
        var port = +r.act.split(':')[1];
        alone++;
        drawTable(r, 'green'); drawNet(src.port, [port]);
        out.innerHTML = 'Matched a rule: out of <b>port ' + port + '</b>. The switch did this alone, at full speed, and counted it.' +
          (blocked && p[2] === 'h3' && p[3] === 'ip' ? ' (It gets there, but h3’s reply comes from 10.39.0.3, and s2 has the same drop rule.)' : '');
        return;
      }
      asked++;
      macs[src.mac] = src.port;
      var known = macs[dstMac], msg = 'No rule for this, so: <code>PACKET_IN</code> to the controller. It learns that ' + src.mac + ' is on port ' + src.port + '. ';
      if (known === undefined || dstMac === BCAST) {
        drawTable(r, 'purple'); drawNet(src.port, [1, 2, 9].filter(function (x) { return x !== src.port; }), true);
        out.innerHTML = msg + (dstMac === BCAST ? 'It’s a broadcast, so' : 'It doesn’t know where ' + dstMac + ' is yet, so') +
          ' it answers with a <code>PACKET_OUT</code>: <b>flood</b> it out of every other port. No rule is added.';
        return;
      }
      var nr = { prio: 10, match: { in_port: src.port, dl_dst: dstMac }, act: 'output:' + known, n: 0 };
      table.push(nr);
      drawTable(nr, 'green'); drawNet(src.port, [known], true);
      out.innerHTML = msg + 'It already knows ' + dstMac + ' is on port ' + known + ', so it sends a <code>FLOW_MOD</code> (the new green row) and a <code>PACKET_OUT</code>. Send the same packet again: the switch won’t need to ask.';
    }
    function block() {
      if (blocked) return;
      blocked = true; blockBtn.disabled = true;
      var nr = { prio: 100, match: { ip: '10.39.0.3' }, act: 'drop', n: 0 };
      table.push(nr);
      drawTable(nr, 'red'); drawNet(null, null, true);
      out.innerHTML = 'The controller sends one <code>FLOW_MOD</code> to every switch: priority 100, match IPv4 from 10.39.0.3, no actions (which means drop). It goes above every other rule. Now try h3’s ping, and h1’s.';
    }
    reset();
  };

  // ---------------------------------------------------------------- ch40: how high should a satellite be?

  WIDGETS.orbits = function (el) {
    frame(el, 'Pick an orbit',
      'Choose how high the satellites fly. The Earth is drawn to scale with the orbit; the green arc is the part of the orbit a dish on top can use ' +
      '(the satellite must be at least a certain angle above the horizon, or trees, hills and too much air get in the way). One second here is one minute of real time.');
    var MU = 398600.4418, RE = 6371, C = 299792.458;
    var PRESETS = [['Starlink', 480], ['OneWeb', 1200], ['O3b mPOWER', 8062], ['geostationary', 35786]];
    var km = 480, minEl = 25;
    var row = h('div', { class: 'row', style: 'gap:6px' });
    var pbtn = PRESETS.map(function (p) {
      var b = btn(p[0] + ' (' + p[1].toLocaleString('en-GB') + ' km)', function () { km = p[1]; alt.value = Math.log10(km); draw(true, p[1]); }, 'small ghost');
      row.appendChild(b); return b;
    });
    el.appendChild(row);
    var alt = document.createElement('input'); alt.type = 'range'; alt.min = Math.log10(300); alt.max = Math.log10(36000); alt.step = 0.001; alt.value = Math.log10(km);
    alt.setAttribute('aria-label', 'height');
    var elev = document.createElement('input'); elev.type = 'range'; elev.min = 5; elev.max = 45; elev.step = 1; elev.value = minEl;
    elev.setAttribute('aria-label', 'lowest usable angle');
    var altLab = document.createElement('span'), elLab = document.createElement('span');
    var r2 = document.createElement('div'); r2.className = 'row';
    var l1 = document.createElement('label'); l1.appendChild(document.createTextNode('height ')); l1.appendChild(alt); l1.appendChild(altLab);
    var l2 = document.createElement('label'); l2.appendChild(document.createTextNode('lowest usable angle ')); l2.appendChild(elev); l2.appendChild(elLab);
    r2.appendChild(l1); r2.appendChild(l2);
    el.appendChild(r2);
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 330', role: 'img', 'aria-label': 'The Earth, an orbit around it, and the part of the orbit a dish can use' });
    el.appendChild(svg);
    var out = document.createElement('div'); out.className = 'out'; out.style.cssText = 'white-space:normal;word-break:normal;font-family:var(--sans)';
    el.appendChild(out);
    var CX = 360, CY = 168, RING = 144;
    var phase = 0, last = null, serving = -1, changes = 0, visible = true, geo = false;
    var g = s('g'); svg.appendChild(g);
    var satG = s('g'); svg.appendChild(satG);
    var link = s('path', { class: 'line s-orange', 'stroke-width': 2.5 }); svg.appendChild(link);
    var hud = s('text', { x: 700, y: 22, class: 'end xs b' }); svg.appendChild(hud);
    var sats = [], lam = 0, period = 0, n = 0;
    function geom() {
      var r = RE + km, e = minEl * Math.PI / 180;
      lam = Math.acos(RE * Math.cos(e) / r) - e;                        // Earth-centre angle to the edge of coverage
      period = 2 * Math.PI * Math.sqrt(r * r * r / MU);                 // seconds
      geo = km > 35000;
      n = geo ? 3 : Math.min(48, Math.ceil(2 * Math.PI / (2 * lam * 0.85)));
    }
    function draw(reset, exact) {
      km = exact || Math.round(Math.pow(10, +alt.value)); minEl = +elev.value;
      altLab.textContent = ' ' + km.toLocaleString('en-GB') + ' km';
      elLab.textContent = ' ' + minEl + '°';
      pbtn.forEach(function (b, i) { b.className = 'btn small' + (Math.abs(PRESETS[i][1] - km) < km * 0.02 ? '' : ' ghost'); });
      geom();
      if (reset) { changes = 0; serving = -1; phase = 0; }
      var er = RING * RE / (RE + km);
      g.innerHTML = '';
      g.appendChild(s('rect', { width: 720, height: 330, rx: 10, class: 'f-card' }));
      g.appendChild(s('circle', { cx: CX, cy: CY, r: RING, fill: 'none', class: 'line s-line', 'stroke-width': 1.2, 'stroke-dasharray': '4 5' }));
      g.appendChild(s('circle', { cx: CX, cy: CY, r: er, class: 'f-teal2', stroke: 'var(--teal)', 'stroke-width': 1.5 }));
      // the usable arc
      var a0 = -Math.PI / 2 - lam, a1 = -Math.PI / 2 + lam;
      var p0 = [CX + RING * Math.cos(a0), CY + RING * Math.sin(a0)], p1 = [CX + RING * Math.cos(a1), CY + RING * Math.sin(a1)];
      g.appendChild(s('path', { d: 'M' + p0[0] + ',' + p0[1] + ' A' + RING + ',' + RING + ' 0 ' + (lam > Math.PI / 2 ? 1 : 0) + ',1 ' + p1[0] + ',' + p1[1], class: 'line s-green', 'stroke-width': 9, fill: 'none', opacity: 0.75 }));
      var ob = [CX, CY - er];
      g.appendChild(s('path', { d: 'M' + p0[0] + ',' + p0[1] + ' L' + ob[0] + ',' + ob[1] + ' L' + p1[0] + ',' + p1[1], class: 'line s-green', 'stroke-width': 1.2, 'stroke-dasharray': '4 4', fill: 'none' }));
      g.appendChild(s('circle', { cx: ob[0], cy: ob[1], r: 4, class: 'f-ink' }));
      g.appendChild(s('text', { x: 20, y: 22, class: 'xs b', text: 'drawn to scale: the Earth, and an orbit ' + km.toLocaleString('en-GB') + ' km up' }));
      g.appendChild(s('text', { x: 20, y: 324, class: 'xs muted', text: geo ? 'a geostationary orbit turns with the Earth: the satellite seems to hang still' : 'satellites: one every ' + Math.round(360 / n) + '° around this orbit (in reality, many orbits side by side)' }));
      var r = RE + km, e = minEl * Math.PI / 180;
      var edge = Math.sqrt(r * r - RE * RE * Math.cos(e) * Math.cos(e)) - RE * Math.sin(e);
      var speed = 2 * Math.PI * r / period * 3600;
      var passS = 2 * lam / (2 * Math.PI) * period;
      var need = Math.ceil(2 / (1 - Math.cos(lam)));
      function t(sec) { return sec >= 3 * 3600 ? (sec / 3600).toFixed(1) + ' hours' : sec >= 600 ? Math.round(sec / 60) + ' min' : Math.floor(sec / 60) + ' min ' + Math.round(sec % 60) + ' s'; }
      out.innerHTML = geo ?
        'At <b>35,786 km</b>, one orbit takes exactly one day, so the satellite stays over the same spot: no tracking, no handovers, and three satellites cover almost the whole Earth. ' +
        'But a round trip up, down, and back again is at least <b>' + (4 * km / C * 1000).toFixed(0) + ' ms</b>, or ' + (4 * edge / C * 1000).toFixed(0) + ' ms from near the edge of its view.' :
        'At <b>' + km.toLocaleString('en-GB') + ' km</b>, one orbit takes <b>' + t(period) + '</b>, at ' + Math.round(speed).toLocaleString('en-GB') + ' km/h. ' +
        'A satellite passing straight over the dish is usable for <b>' + t(passS) + '</b>. ' +
        'A round trip through it to a nearby ground station takes at least <b>' + (4 * km / C * 1000).toFixed(1) + ' ms</b> when it’s overhead, ' + (4 * edge / C * 1000).toFixed(1) + ' ms at the edge. ' +
        'To always have one in view, anywhere, you’d need at least <b>' + need.toLocaleString('en-GB') + '</b> satellites, even if their circles could tile the Earth perfectly; real constellations need several times that.';
      sats = [];
      satG.innerHTML = '';
      for (var i = 0; i < n; i++) {
        var node = s('g');
        node.appendChild(s('rect', { x: -5, y: -4, width: 10, height: 8, rx: 1.5, class: 'f-navy' }));
        node.appendChild(s('rect', { x: -15, y: -2.5, width: 9, height: 5, class: 'f-blue' }));
        node.appendChild(s('rect', { x: 6, y: -2.5, width: 9, height: 5, class: 'f-blue' }));
        satG.appendChild(node); sats.push(node);
      }
      place();
    }
    function place() {
      var er = RING * RE / (RE + km), best = -1, bestD = 1e9;
      sats.forEach(function (node, i) {
        var a = geo ? -Math.PI / 2 + (i - 1) * 2 * Math.PI / 3 : phase + i * 2 * Math.PI / n;
        var x = CX + RING * Math.cos(a), y = CY + RING * Math.sin(a);
        node.setAttribute('transform', 'translate(' + x.toFixed(1) + ',' + y.toFixed(1) + ') rotate(' + (a * 180 / Math.PI + 90).toFixed(1) + ')');
        var off = Math.atan2(Math.sin(a + Math.PI / 2), Math.cos(a + Math.PI / 2));      // angle from the top
        if (Math.abs(off) <= lam && Math.abs(off) < bestD) { bestD = Math.abs(off); best = i; }
        node.style.opacity = Math.abs(off) <= lam ? 1 : 0.45;
      });
      if (best >= 0) {
        var a = geo ? -Math.PI / 2 : phase + best * 2 * Math.PI / n;
        link.setAttribute('d', 'M' + CX + ',' + (CY - er) + ' L' + (CX + RING * Math.cos(a)).toFixed(1) + ',' + (CY + RING * Math.sin(a)).toFixed(1));
        if (serving !== -1 && best !== serving) changes++;
        serving = best;
      } else link.setAttribute('d', '');
      hud.textContent = geo ? 'handovers: none, ever' : 'satellite changes so far: ' + changes;
    }
    function tick(ts) {
      if (last !== null && visible && !geo) phase += (ts - last) / 1000 * 60 * 2 * Math.PI / period;   // one second = one real minute
      last = ts;
      if (visible) place();
      requestAnimationFrame(tick);
    }
    alt.addEventListener('input', function () { draw(true); });
    elev.addEventListener('input', function () { var keep = km; draw(true, PRESETS.some(function (p) { return p[1] === keep; }) ? keep : 0); });
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }).observe(el);
    draw(true, 480);
    if (!reduced) requestAnimationFrame(tick);
  };

  // ---------------------------------------------------------------- ch41: a message to Mars, on any date
  // The same planetary elements as labs/ch41/mars.py (JPL's approximate positions of the planets).

  WIDGETS.solarmail = function (el) {
    frame(el, 'Mail to Mars',
      'Drag the date. The planets move round the Sun, and the distance between Earth and Mars changes, and so does the time a message takes. ' +
      'Then send one. (The pulse travels at the real speed of light, speeded up 120 times.)');
    var AU = 149597870.7, C = 299792.458;
    var ORB = {
      earth: [[1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0], [0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0]],
      mars: [[1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891], [0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343]] };
    var R = Math.PI / 180;
    function where(p, ms) {
      var t = (ms - Date.UTC(2000, 0, 1, 12)) / 86400000 / 36525, o = ORB[p];
      var v = o[0].map(function (x, i) { return x + o[1][i] * t; });
      var a = v[0], e = v[1], inc = v[2] * R, L = v[3], peri = v[4], node = v[5] * R;
      var m = (((L - peri + 180) % 360 + 360) % 360 - 180) * R, w = (peri - v[5]) * R, E = m + e * Math.sin(m);
      for (var k = 0; k < 10; k++) E -= (E - e * Math.sin(E) - m) / (1 - e * Math.cos(E));
      var xp = a * (Math.cos(E) - e), yp = a * Math.sqrt(1 - e * e) * Math.sin(E);
      var cw = Math.cos(w), sw = Math.sin(w), cn = Math.cos(node), sn = Math.sin(node), ci = Math.cos(inc);
      return [(cw * cn - sw * sn * ci) * xp + (-sw * cn - cw * sn * ci) * yp, (cw * sn + sw * cn * ci) * xp + (-sw * sn + cw * cn * ci) * yp];
    }
    var START = Date.UTC(2026, 8, 28);
    var slider = h('input', { type: 'range', min: 0, max: 1600, step: 1, value: 0, 'aria-label': 'date', style: 'width:320px' });
    var dateLab = h('b');
    var sendBtn = btn('send a message', function () { send(); }, 'small');
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'date ', slider), dateLab, sendBtn));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 400', role: 'img', 'aria-label': 'The Sun, Earth and Mars from above, with the distance between them' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);
    var CX = 210, CY = 200, S = 112, pulse = null, anim = null;
    function draw() {
      var ms = START + (+slider.value) * 86400000, d = new Date(ms);
      dateLab.textContent = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
      var e = where('earth', ms), m = where('mars', ms);
      var dx = m[0] - e[0], dy = m[1] - e[1], dist = Math.sqrt(dx * dx + dy * dy) * AU;
      var ang = Math.acos((dx * -e[0] + dy * -e[1]) / (Math.sqrt(dx * dx + dy * dy) * Math.sqrt(e[0] * e[0] + e[1] * e[1]))) / R;
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 400, rx: 10, class: 'f-card' }));
      [['earth', 360], ['mars', 687]].forEach(function (p) {
        var pts = [];
        for (var k = 0; k <= p[1]; k += p[1] / 90) { var q = where(p[0], ms + k * 86400000); pts.push((CX + q[0] * S).toFixed(1) + ',' + (CY - q[1] * S).toFixed(1)); }
        svg.appendChild(s('path', { d: 'M' + pts.join(' L') + 'Z', class: 'line s-line', 'stroke-width': 1.2, fill: 'none', 'stroke-dasharray': '3 4' }));
      });
      svg.appendChild(s('circle', { cx: CX, cy: CY, r: 14, class: 'glow', stroke: 'var(--orange)', 'stroke-width': 2 }));
      var ex = CX + e[0] * S, ey = CY - e[1] * S, mx = CX + m[0] * S, my = CY - m[1] * S;
      var blocked = ang < 3;
      svg.appendChild(s('path', { d: 'M' + ex + ',' + ey + ' L' + mx + ',' + my, class: 'line ' + (blocked ? 's-red' : 's-muted'), 'stroke-width': 1.5, 'stroke-dasharray': '5 4' }));
      svg.appendChild(s('circle', { cx: ex, cy: ey, r: 7, class: 'f-blue' }));
      svg.appendChild(s('text', { x: ex + 10, y: ey - 8, class: 'xs b', text: 'Earth' }));
      svg.appendChild(s('circle', { cx: mx, cy: my, r: 6, class: 'f-red' }));
      svg.appendChild(s('text', { x: mx + 10, y: my - 8, class: 'xs b', text: 'Mars' }));
      pulse = s('circle', { cx: ex, cy: ey, r: 5, class: 'f-yellow', stroke: 'var(--orange)', 'stroke-width': 2, opacity: 0 });
      svg.appendChild(pulse);
      var lt = dist / C;
      var rows = [['distance', (dist / 1e6).toFixed(0) + ' million km'], ['one way, at the speed of light', Math.floor(lt / 60) + ' min ' + String(Math.round(lt % 60)).padStart(2, '0') + ' s'],
        ['a question and its answer', Math.round(2 * lt / 60) + ' minutes'], ['Mars, seen from Earth', ang.toFixed(0) + '° from the Sun'],
        ['a TCP connection', 'gives up after about 2 minutes']];
      rows.forEach(function (r, i) {
        svg.appendChild(s('text', { x: 440, y: 60 + i * 44, class: 'xs muted', text: r[0] }));
        svg.appendChild(s('text', { x: 440, y: 80 + i * 44, class: 'sm b' + (i === 4 ? ' f-red' : ''), text: r[1] }));
      });
      out.innerHTML = blocked ? '<b>Mars is almost behind the Sun.</b> The Sun’s own radio noise drowns any signal, so for a couple of weeks every 26 months, missions go quiet: nothing is sent that can’t wait.' :
        'At this distance, even the first SYN of a TCP handshake (Chapter 27) would take ' + (lt / 60).toFixed(1) + ' minutes to arrive, long after the sender had given up. Messages to Mars have to be sent, stored and delivered, not conversed.';
      if (anim) { cancelAnimationFrame(anim); anim = null; }
      sendBtn.disabled = blocked;
      draw.state = { ex: ex, ey: ey, mx: mx, my: my, lt: lt };
    }
    function send() {
      var st = draw.state, t0 = null, dur = st.lt / 120 * 1000;
      if (anim) cancelAnimationFrame(anim);
      function step(ts) {
        if (t0 === null) t0 = ts;
        var f = Math.min(1, (ts - t0) / dur);
        pulse.setAttribute('cx', st.ex + (st.mx - st.ex) * f); pulse.setAttribute('cy', st.ey + (st.my - st.ey) * f);
        pulse.setAttribute('opacity', 1);
        if (f < 1) anim = requestAnimationFrame(step);
        else { anim = null; pulse.setAttribute('r', 9); }
      }
      if (reduced) { pulse.setAttribute('cx', st.mx); pulse.setAttribute('cy', st.my); pulse.setAttribute('opacity', 1); return; }
      pulse.setAttribute('r', 5);
      anim = requestAnimationFrame(step);
    }
    slider.addEventListener('input', draw);
    draw();
  };

  // ---------------------------------------------------------------- ch42: learning with errors, on a clock
  // The noise is ML-KEM-768's own: w = v − sᵀu leaves  eᵀr − sᵀ(e1 + Δu) + e2 + Δv  on top of each message bit.

  WIDGETS.noiseclock = function (el) {
    frame(el, 'Noise, on purpose',
      'ML-KEM works with numbers from 0 to 3,328, arranged round a clock. Each bit of the secret is sent as a number near the top (a 0) or near the bottom (a 1), ' +
      'buried in noise that keeps everyone else out. After decrypting, the receiver is left with the bit plus a little leftover noise: each dot below is one of the 256 bits of a real-sized message. ' +
      'As long as every dot stays in its own half, every bit is read correctly.');
    var Q = 3329, LEVELS = [[0, 'none at all'], [2, 'ML-KEM-768’s own'], [4, '2× bigger'], [8, '4× bigger'], [16, '8× bigger']];
    var lvl = 1;
    var slider = h('input', { type: 'range', min: 0, max: LEVELS.length - 1, step: 1, value: lvl, 'aria-label': 'noise' });
    var lab = h('b');
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'noise ', slider), lab, btn('send another message', function () { run(); }, 'small')));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 300', role: 'img', 'aria-label': 'A clock of numbers mod 3329, with 256 dots showing where each message bit landed' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);
    var st = (Math.random() * 4294967295) >>> 0 || 1;
    function rnd() { st ^= st << 13; st >>>= 0; st ^= st >>> 17; st ^= st << 5; st >>>= 0; return st; }
    function pc(x) { x = x - ((x >>> 1) & 0x55555555); x = (x & 0x33333333) + ((x >>> 2) & 0x33333333); return (((x + (x >>> 4)) & 0x0F0F0F0F) * 0x01010101) >>> 24; }
    function cbd(eta) { if (!eta) return 0; var r = rnd(), m = eta === 16 ? 0xFFFF : (1 << eta) - 1; return pc(r & m) - pc((r >>> 16) & m); }
    function run() {
      lvl = +slider.value;
      var eta = LEVELS[lvl][0];
      lab.textContent = LEVELS[lvl][1];
      var pts = [], wrong = 0, biggest = 0;
      for (var i = 0; i < 256; i++) {
        var bit = rnd() & 1, n = 0;
        if (eta) {
          for (var t = 0; t < 768; t++) {
            n += cbd(eta) * cbd(eta);                              // eᵀr
            n -= cbd(eta) * (cbd(eta) + (rnd() % 5) - 2);         // sᵀ(e1 + rounding of u)
          }
          n += cbd(eta) + (rnd() % 209) - 104;                     // e2 + rounding of v
        }
        var w = ((bit * 1665 + n) % Q + Q) % Q;
        var read = (w > Q / 4 && w < 3 * Q / 4) ? 1 : 0;
        if (read !== bit) wrong++;
        biggest = Math.max(biggest, Math.abs(n));
        pts.push([w, bit, read !== bit]);
      }
      draw(pts, wrong, biggest, eta);
    }
    function draw(pts, wrong, biggest, eta) {
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 300, rx: 10, class: 'f-card' }));
      var cx = 180, cy = 150, R = 118;
      svg.appendChild(s('path', { d: 'M' + (cx - R - 14) + ',' + cy + ' A' + (R + 14) + ',' + (R + 14) + ' 0 0,1 ' + (cx + R + 14) + ',' + cy + ' Z', class: 't-blue', opacity: 0.5 }));
      svg.appendChild(s('path', { d: 'M' + (cx - R - 14) + ',' + cy + ' A' + (R + 14) + ',' + (R + 14) + ' 0 0,0 ' + (cx + R + 14) + ',' + cy + ' Z', class: 't-orange', opacity: 0.5 }));
      svg.appendChild(s('circle', { cx: cx, cy: cy, r: R, fill: 'none', class: 'line s-muted', 'stroke-width': 1.5 }));
      svg.appendChild(s('text', { x: cx, y: cy - R - 20, class: 'mid xs b', text: '0' }));
      svg.appendChild(s('text', { x: cx, y: cy + R + 30, class: 'mid xs b', text: '1,665' }));
      svg.appendChild(s('text', { x: cx + R + 20, y: cy + 4, class: 'xs muted', text: '832' }));
      svg.appendChild(s('text', { x: cx - R - 20, y: cy + 4, class: 'end xs muted', text: '2,497' }));
      svg.appendChild(s('text', { x: cx, y: cy - 30, class: 'mid xs b f-blue', text: 'reads as 0' }));
      svg.appendChild(s('text', { x: cx, y: cy + 40, class: 'mid xs b f-orange', text: 'reads as 1' }));
      pts.forEach(function (p, k) {
        var a = 2 * Math.PI * p[0] / Q - Math.PI / 2, r = R - 6 - (k % 7) * 3;
        svg.appendChild(s('circle', { cx: (cx + r * Math.cos(a)).toFixed(1), cy: (cy + r * Math.sin(a)).toFixed(1), r: p[2] ? 5 : 2.6,
          class: p[2] ? 'f-red' : (p[1] ? 'f-orange' : 'f-blue'), opacity: p[2] ? 1 : 0.8 }));
      });
      var rows = [['bits read wrongly', wrong + ' of 256'], ['biggest leftover noise', '±' + biggest], ['how much noise a bit can survive', '±832 (a quarter of the clock)']];
      rows.forEach(function (r, i) {
        svg.appendChild(s('text', { x: 400, y: 70 + i * 50, class: 'xs muted', text: r[0] }));
        svg.appendChild(s('text', { x: 400, y: 92 + i * 50, class: 'sm b' + (i === 0 && wrong ? ' f-red' : ''), text: r[1] }));
      });
      out.innerHTML = !eta ? '<b>No noise:</b> every bit lands exactly at the top or bottom. But without noise, the public key is just a set of linear equations, which anyone can solve with school algebra, and read every message. The noise is the lock.' :
        eta === 2 ? '<b>The real thing.</b> The leftover noise is tiny compared with a quarter of the clock, so every bit comes out right. (The odds of even one wrong bit, in a real key exchange, are about 1 in 2<sup>164</sup>.) Yet from the outside, that same noise makes the equations unsolvable.' :
          wrong ? '<b>Too much noise:</b> some dots have crossed into the wrong half, so those bits come out wrong, and the two sides end up with different secrets. Designing ML-KEM meant choosing noise big enough to keep attackers out, and small enough to keep this from ever happening.' :
            'More noise is harder to attack, but the dots are spreading towards the halfway line. Keep going.';
    }
    slider.addEventListener('input', run);
    run();
  };

  // ---------------------------------------------------------------- ch43: the same video, six times: IP vs NDN

  WIDGETS.cachenet = function (el) {
    frame(el, 'Six neighbours, one video',
      'Grandpa’s Pi holds a 5-part video of the garden. Press a house to have it watch the video, or have everyone watch at once. ' +
      'Compare today’s internet, where every copy comes from Grandpa’s Pi, with named data, where routers keep copies and merge identical requests. ' +
      'The numbers on the links count the video parts that crossed them.');
    var mode = 'ndn', SEGS = 5, HOP = 260;
    var N = { P: [360, 42, 'Grandpa’s Pi'], R1: [360, 120, 'internet provider'], A: [190, 195, 'street cabinet'], B: [530, 195, 'street cabinet'] };
    for (var i = 1; i <= 6; i++) N['h' + i] = [i <= 3 ? 70 + (i - 1) * 120 : 410 + (i - 4) * 120, 275, 'house ' + i];
    var UP = { R1: 'P', A: 'R1', B: 'R1', h1: 'A', h2: 'A', h3: 'A', h4: 'B', h5: 'B', h6: 'B' };
    var state, count, busy, gen = 0;
    var modeRow = h('div', { class: 'row' });
    var ipBtn = btn('today’s internet (IP)', function () { mode = 'ip'; reset(); }, 'small ghost');
    var ndnBtn = btn('named data (NDN)', function () { mode = 'ndn'; reset(); }, 'small');
    modeRow.appendChild(ipBtn); modeRow.appendChild(ndnBtn);
    el.appendChild(modeRow);
    var row = h('div', { class: 'row', style: 'gap:6px' });
    for (var k = 1; k <= 6; k++) (function (k) { row.appendChild(btn('house ' + k, function () { watch('h' + k); }, 'small ghost')); })(k);
    row.appendChild(btn('everyone at 7 pm', function () { for (var k = 1; k <= 6; k++) watch('h' + k); }, 'small'));
    row.appendChild(btn('start again', function () { reset(); }, 'small ghost'));
    el.appendChild(row);
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 310', role: 'img', 'aria-label': 'A tree: Grandpa’s Pi, a provider router, two street cabinets and six houses' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);
    var dots = s('g');
    function reset() {
      state = {}; count = {}; busy = {}; gen++; dots.innerHTML = '';
      Object.keys(N).forEach(function (n) { state[n] = { cs: {}, pit: {} }; });
      ipBtn.className = 'btn small' + (mode === 'ip' ? '' : ' ghost');
      ndnBtn.className = 'btn small' + (mode === 'ndn' ? '' : ' ghost');
      draw();
    }
    function draw() {
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 310, rx: 10, class: 'f-card' }));
      Object.keys(UP).forEach(function (n) {
        var a = N[n], b = N[UP[n]], key = n + '-' + UP[n], c = count[key] || 0, top = UP[n] === 'P';
        svg.appendChild(s('path', { d: 'M' + a[0] + ',' + a[1] + ' L' + b[0] + ',' + b[1], class: 'line ' + (top ? 's-orange' : 's-muted'), 'stroke-width': top ? 5 : 2.5 }));
        svg.appendChild(s('text', { x: (a[0] + b[0]) / 2 + 8, y: (a[1] + b[1]) / 2, class: 'xs b' + (top ? ' f-orange' : ''), text: c ? c + (top ? ' parts: Grandpa’s upload' : '') : '' }));
      });
      Object.keys(N).forEach(function (n) {
        var p = N[n], router = n === 'R1' || n === 'A' || n === 'B';
        svg.appendChild(s('rect', { x: p[0] - 52, y: p[1] - 16, width: 104, height: 32, rx: 6, class: n === 'P' ? 't-green' : router ? 't-blue' : 'f-surface', stroke: 'var(--line)', 'stroke-width': 1.3 }));
        svg.appendChild(s('text', { x: p[0], y: p[1] + 4, class: 'mid xs b', text: p[2] }));
        if (router && mode === 'ndn') {
          for (var i = 1; i <= SEGS; i++) svg.appendChild(s('rect', { x: p[0] - 30 + (i - 1) * 12, y: p[1] + 19, width: 9, height: 9, rx: 2,
            class: state[n].cs[i] ? 'f-purple' : 'f-surface', stroke: 'var(--line)', 'stroke-width': 0.8 }));
        }
        if (n.charAt(0) === 'h' && state[n].got) svg.appendChild(s('text', { x: p[0], y: p[1] + 30, class: 'mid xs', text: state[n].got + ' of ' + SEGS + ' parts' }));
      });
      svg.appendChild(dots);
      var up = count['R1-P'] || 0, total = Object.keys(count).reduce(function (a, k) { return a + count[k]; }, 0);
      var watched = Object.keys(N).filter(function (n) { return n.charAt(0) === 'h' && state[n].got === SEGS; }).length;
      out.innerHTML = (mode === 'ndn' ? '<b>Named data.</b> The small squares under each router are its content store. ' : '<b>Today’s internet.</b> Routers don’t keep anything: they only pass packets on. ') +
        watched + ' house' + (watched === 1 ? ' has' : 's have') + ' watched the video. Grandpa’s upload carried <b>' + up + '</b> video parts' +
        (watched ? ' (' + (up / watched).toFixed(1) + ' per viewer)' : '') + ', and all the links together ' + total + '.';
    }
    function hop(from, to, kind, done) {
      var a = N[from], b = N[to], dot = s('circle', { r: 6, class: kind === 'i' ? 'f-green' : 'f-purple' }), t0 = null, g = gen;
      dots.appendChild(dot);
      function step(ts) {
        if (t0 === null) t0 = ts;
        var f = reduced ? 1 : Math.min(1, (ts - t0) / HOP);
        dot.setAttribute('cx', a[0] + (b[0] - a[0]) * f); dot.setAttribute('cy', a[1] + (b[1] - a[1]) * f);
        if (g !== gen) return;                            // started again: forget this packet
        if (f < 1) requestAnimationFrame(step); else { dots.removeChild(dot); done(); }
      }
      requestAnimationFrame(step);
    }
    function data(from, to, seg) {                          // a Data packet crosses one link, downwards
      count[to + '-' + from] = (count[to + '-' + from] || 0) + 1;
      hop(from, to, 'd', function () { arrive(to, seg); });
    }
    function got(house, seg) {
      var st = state[house];
      st.got = seg; draw();
      if (seg < SEGS) (mode === 'ip' ? fetchIP : ask)(house, house, seg + 1); else busy[house] = false;
    }
    function arrive(node, seg) {                            // NDN: Data reaches a router or a house
      if (node.charAt(0) === 'h') { got(node, seg); return; }
      var st = state[node], waiting = st.pit[seg] || [];
      st.cs[seg] = true;                                    // keep a copy
      delete st.pit[seg];
      waiting.forEach(function (w) { data(node, w, seg); }); // and follow the breadcrumbs
      draw();
    }
    function ask(node, from, seg) {                          // NDN: an Interest reaches `node`, sent by `from`
      if (node === 'P') { data('P', from, seg); return; }
      if (node.charAt(0) !== 'h') {
        var st = state[node];
        if (st.cs[seg]) { data(node, from, seg); return; }  // in the content store: answer here
        if (st.pit[seg]) { st.pit[seg].push(from); return; } // already asked: just wait too
        st.pit[seg] = [from];
      }
      hop(node, UP[node], 'i', function () { ask(UP[node], node, seg); });
    }
    function fetchIP(house, _, seg) {                        // IP: all the way to Grandpa's Pi and back, every time
      var path = [house];
      while (UP[path[path.length - 1]]) path.push(UP[path[path.length - 1]]);
      (function goUp(i) {
        if (i === path.length - 1) return (function goDown(j) {
          if (j === 0) { got(house, seg); return; }
          count[path[j - 1] + '-' + path[j]] = (count[path[j - 1] + '-' + path[j]] || 0) + 1;
          hop(path[j], path[j - 1], 'd', function () { goDown(j - 1); });
        })(i);
        hop(path[i], path[i + 1], 'i', function () { goUp(i + 1); });
      })(0);
    }
    function watch(house) {
      if (busy[house]) return;
      busy[house] = true; state[house].got = 0; draw();
      (mode === 'ip' ? fetchIP : ask)(house, house, 1);
    }
    reset();
  };

  // ---------------------------------------------------------------- ch44: a village mesh you can break

  WIDGETS.meshsim = function (el) {
    frame(el, 'The village mesh',
      'Every house has a rooftop radio; the pub’s connects to the outside world. The further apart two radios are, the more of their packets are lost. ' +
      'Arrows show each house’s route out. <b>Drag</b> houses to move them; <b>click</b> one to knock it out (the storm), or bring it back. ' +
      'Then compare routing by the fewest hops with routing by link quality.');
    var R = 190, mode = 'etx';
    var nodes = [[70, 200, 'pub', 1], [160, 150], [250, 200], [340, 150], [430, 200], [520, 150], [610, 200], [250, 290], [430, 290], [610, 90]];
    nodes = nodes.map(function (n, i) { return { x: n[0], y: n[1], name: n[2] || 'house ' + i, gw: !!n[3], down: false }; });
    var row = h('div', { class: 'row' });
    var b1 = btn('route by fewest hops', function () { mode = 'hops'; draw(); }, 'small ghost');
    var b2 = btn('route by link quality', function () { mode = 'etx'; draw(); }, 'small');
    row.appendChild(b1); row.appendChild(b2);
    row.appendChild(btn('mend everything', function () { nodes.forEach(function (n) { n.down = false; }); draw(); }, 'small ghost'));
    el.appendChild(row);
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 340', role: 'img', 'aria-label': 'A village of houses joined by radio links, with routes to the pub', style: 'touch-action:none' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--sans)' });
    el.appendChild(out);
    function quality(a, b) {                                  // chance a packet gets across
      var d = Math.hypot(a.x - b.x, a.y - b.y);
      return d >= R ? 0 : Math.max(0.1, 1 - Math.pow(d / R, 4));
    }
    function routes() {                                       // Dijkstra, outwards from the pub (Chapter 23)
      var cost = nodes.map(function () { return Infinity; }), next = nodes.map(function () { return -1; }), done = [];
      nodes.forEach(function (n, i) { if (n.gw && !n.down) cost[i] = 0; });
      for (;;) {
        var u = -1;
        nodes.forEach(function (n, i) { if (!done[i] && !n.down && cost[i] < Infinity && (u < 0 || cost[i] < cost[u])) u = i; });
        if (u < 0) break;
        done[u] = true;
        nodes.forEach(function (n, v) {
          if (v === u || n.down || done[v]) return;
          var p = quality(nodes[u], n);
          if (!p) return;
          var c = cost[u] + (mode === 'hops' ? 1 : 1 / (p * p));      // expected transmissions (ETX) of this link
          if (c < cost[v]) { cost[v] = c; next[v] = u; }
        });
      }
      return next;
    }
    function draw() {
      b1.className = 'btn small' + (mode === 'hops' ? '' : ' ghost');
      b2.className = 'btn small' + (mode === 'etx' ? '' : ' ghost');
      var next = routes();
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 340, rx: 10, class: 'f-card' }));
      for (var i = 0; i < nodes.length; i++) for (var j = i + 1; j < nodes.length; j++) {
        var p = quality(nodes[i], nodes[j]);
        if (!p || nodes[i].down || nodes[j].down) continue;
        svg.appendChild(s('path', { d: 'M' + nodes[i].x + ',' + nodes[i].y + ' L' + nodes[j].x + ',' + nodes[j].y, class: 'line s-muted',
          'stroke-width': 1 + 3 * p, opacity: 0.25 + 0.6 * p, 'stroke-dasharray': p < 0.6 ? '3 5' : '' }));
      }
      var reach = 0, lost = 0, tx = 0, hopsum = 0;
      nodes.forEach(function (n, i) {
        if (n.gw || n.down) return;
        if (next[i] < 0) { lost++; return; }
        var k = i, deliver = 1, hops = 0;
        while (!nodes[k].gw) { var q = quality(nodes[k], nodes[next[k]]); deliver *= q; tx += 1 / (q * q); hops++; k = next[k]; }
        reach++; hopsum += hops;
        n.deliver = deliver;
        var t = nodes[next[i]], dx = t.x - n.x, dy = t.y - n.y, L = Math.hypot(dx, dy);
        svg.appendChild(s('path', { d: 'M' + (n.x + dx * 20 / L) + ',' + (n.y + dy * 20 / L) + ' L' + (t.x - dx * 24 / L) + ',' + (t.y - dy * 24 / L),
          class: 'line s-green', 'stroke-width': 3, 'marker-end': 'url(#ah-green)' }));
      });
      nodes.forEach(function (n, i) {
        var g = s('g', { style: 'cursor:pointer' });
        g.appendChild(s('circle', { cx: n.x, cy: n.y, r: 19, class: n.down ? 'f-surface' : n.gw ? 't-yellow' : 't-blue', stroke: n.down ? 'var(--red)' : 'var(--line)', 'stroke-width': 1.6 }));
        g.appendChild(s('text', { x: n.x, y: n.y + 4, class: 'mid xs b', text: n.gw ? 'pub' : String(i) }));
        if (n.down) g.appendChild(s('path', { d: 'M' + (n.x - 10) + ',' + (n.y - 10) + ' l20,20 M' + (n.x + 10) + ',' + (n.y - 10) + ' l-20,20', class: 'line s-red', 'stroke-width': 3 }));
        else if (!n.gw && next[i] >= 0) g.appendChild(s('text', { x: n.x, y: n.y + 34, class: 'mid xs muted', text: Math.round(n.deliver * 100) + '%' }));
        g.addEventListener('pointerdown', function (e) { start(e, i); });
        svg.appendChild(g);
      });
      out.innerHTML = '<b>' + (mode === 'etx' ? 'Routing by link quality' : 'Routing by fewest hops') + ':</b> ' +
        reach + ' of ' + (nodes.length - 1 - nodes.filter(function (n) { return n.down && !n.gw; }).length) + ' working houses can reach the pub' +
        (lost ? ', <b>' + lost + ' cut off</b>' : '') + '. ' +
        (reach ? 'On average ' + (hopsum / reach).toFixed(1) + ' hops, and ' + (tx / reach).toFixed(1) + ' radio transmissions per packet, counting the resends. ' : '') +
        'The percentages are the chance that a single packet gets to the pub first time. ' +
        (mode === 'hops' ? 'Fewest hops loves long, weak links.' : 'Link quality prefers more, shorter, reliable hops: that’s what batman-adv does.');
    }
    var drag = null;
    function pt(e) { var r = svg.getBoundingClientRect(); return [(e.clientX - r.left) * 720 / r.width, (e.clientY - r.top) * 340 / r.height]; }
    function start(e, i) { var p = pt(e); drag = { i: i, x: p[0], y: p[1], moved: false }; svg.setPointerCapture && svg.setPointerCapture(e.pointerId); e.preventDefault(); }
    svg.addEventListener('pointermove', function (e) {
      if (!drag) return;
      var p = pt(e);
      if (Math.hypot(p[0] - drag.x, p[1] - drag.y) > 4) drag.moved = true;
      if (drag.moved) { nodes[drag.i].x = Math.max(24, Math.min(696, p[0])); nodes[drag.i].y = Math.max(24, Math.min(316, p[1])); draw(); }
    });
    svg.addEventListener('pointerup', function () {
      if (drag && !drag.moved) { nodes[drag.i].down = !nodes[drag.i].down; draw(); }
      drag = null;
    });
    draw();
  };

  // ---------------------------------------------------------------- epilogue: the flashlight, one more time

  WIDGETS.flashmessage = function (el) {
    frame(el, 'Across the street',
      'Type a message and flash it, the way Alice and Bob did in Chapter 1: five bits a letter, green for 1, red for 0, and a dark gap after each. ' +
      'Bob’s side writes down the bits, and turns every five of them back into a letter.');
    var input = h('input', { type: 'text', value: 'HI BOB', maxlength: 24, 'aria-label': 'message', style: 'text-transform:uppercase;width:14em' });
    var go = btn('flash it', function () { start(); }, 'small');
    el.appendChild(h('div', { class: 'row' }, h('label', {}, 'message ', input), go));
    var svg = s('svg', { class: 'dia', viewBox: '0 0 720 170', role: 'img', 'aria-label': 'Alice’s lamp flashing bits across the street to Bob' });
    el.appendChild(svg);
    var out = h('div', { class: 'out', style: 'white-space:normal;word-break:normal;font-family:var(--mono)' });
    el.appendChild(out);
    var timer = null;
    function codes() {
      return input.value.toUpperCase().split('').map(function (c) { return CODEBOOK5.indexOf(c === ' ' ? ' ' : c); }).filter(function (i) { return i >= 0; });
    }
    function draw(color, bits, got) {
      svg.innerHTML = '';
      svg.appendChild(s('rect', { width: 720, height: 170, rx: 10, class: 'night' }));
      svg.appendChild(s('use', { href: '#house', x: 20, y: 20, width: 120, height: 130 }));
      svg.appendChild(s('use', { href: '#house', x: 580, y: 20, width: 120, height: 130 }));
      var lamp = { green: '#3fd67a', red: '#ff5a5a', off: '#333' }[color];
      if (color !== 'off') svg.appendChild(s('path', { d: 'M150,62 L570,40 L570,100 Z', fill: lamp, opacity: 0.18 }));
      svg.appendChild(s('circle', { cx: 146, cy: 70, r: 13, fill: lamp, stroke: '#111', 'stroke-width': 2 }));
      svg.appendChild(s('text', { x: 80, y: 164, class: 'mid xs b on-night', text: 'Alice' }));
      svg.appendChild(s('text', { x: 640, y: 164, class: 'mid xs b on-night', text: 'Bob' }));
      svg.appendChild(s('text', { x: 360, y: 140, class: 'mid sm mono on-night', text: bits || '' }));
      svg.appendChild(s('text', { x: 360, y: 30, class: 'mid lg b on-night', text: got || '' }));
    }
    function start() {
      if (timer) clearTimeout(timer);
      var cs = codes(), seq = [];
      cs.forEach(function (c) { for (var k = 4; k >= 0; k--) seq.push((c >> k) & 1); });
      out.textContent = cs.map(function (c) { return cbLabel(CODEBOOK5[c]) + ' ' + pad(c.toString(2), 5); }).join('   ');
      var i = 0, bits = '', got = '';
      (function step() {
        if (i >= seq.length) { draw('off', bits, got); timer = null; return; }
        var b = seq[i++];
        bits += b; if (bits.replace(/ /g, '').length % 5 === 0) { got += cbLabel(CODEBOOK5[parseInt(bits.replace(/ /g, '').slice(-5), 2)]); bits += ' '; }
        draw(b ? 'green' : 'red', bits.slice(-36), got);
        timer = setTimeout(function () { draw('off', bits.slice(-36), got); timer = setTimeout(step, reduced ? 0 : 110); }, reduced ? 0 : 220);
      })();
    }
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') start(); });
    draw('off', '', '');
  };

  // @@more-widgets@@

  // ---------------------------------------------------------------- boot

  function boot() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-widget]'), function (el) {
      var name = el.getAttribute('data-widget');
      if (WIDGETS[name]) {
        try { WIDGETS[name](el); } catch (err) { console.error('widget ' + name + ' failed', err); }
      } else {
        console.warn('unknown widget', name);
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.BitByBit = { WIDGETS: WIDGETS, h: h, s: s, btn: btn, frame: frame };
})();
