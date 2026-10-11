  // ============ ASİSTAN PANELİ (Figma) ============
  // Studio'daki Assist köprüsünün tarayıcı karşılığı: RAW → stil → 379 özellik → model.
  // Kullanıcı bir katmanın sınıfını değiştirirse bu bir düzeltmedir: öğrenme durumuna yazılır
  // (EILearn, kanonik ei-learn v1 metni) ve clientStorage'a kaydedilir. Sunucu yoktur.
  var AS = (function () {
    var CONF_MIN = 0.70;   // Assist.CONF_MIN (PLAN §M1)
    var LEARN_MIN = 2;     // Assist.LEARN_MIN
    var learn = EILearn.newState();
    var rows = [];
    var lastStyle = 'belirsiz', lastConf = 0;
    var slots = [];   // animasyon seçici yuvaları: {name, cls, depth, cat, role, ctx, options, selected}
    var rowNodes = [];// satır i ↔ JSON düğümü (aynı DFS sırası)
    var rowFx = [];   // satır i ↔ efekt kimliği (ad etiketinden; yoksa null)
    var rowParams = {};   // satır i → efekt parametreleri (kaydırıcılardan; JSON'a gider)
    var fxLibPick = {};   // satır i → seçilen ekstra kütüphane simge kimlikleri (JSON fxImages'e girer)
    var fxOwnPick = {};   // satır i → kendi resimlerimiz (tasarımdaki PNG'ler) — Roblox aktarımında sıfırlanır
    var userFx = {};      // satır i → kütüphaneden atanan efekt ('none' = kaldır) — belge değişince sıfırlanır
    var userAnim = {};    // satır i → { kategori: animasyonKimliği } — kütüphaneden atanan animasyonlar
    var libCat = '', libQuery = '';
    var fxSel = null;     // seçili efekt satırı
    var FX_LABEL = {
      fall: 'Yağmur (düşen öğeler)', confetti: 'Konfeti', burst: 'Patlama (basınca)', orbit: 'Yörünge',
      twinkle: 'Parıltı', sweep: 'Işık süpürme', orb: 'Dev hale', smooth: 'Büyüme (hover / basma)',
      gleam: 'Metin parıltısı (yazı üzerinde)', shine: 'Rectangle parlama (soldan sağa, içeride)'
    };
    // Bu efektler kopyalanacak bir resim (şablon) kullanır → "Resim seç" bölümü görünür.
    var PIC_KINDS = { fall: true, confetti: true, burst: true, orbit: true, twinkle: true };
    var PIC_MAX = 4, PIC_BYTES = 2 * 1024 * 1024;
    var PARAM_UI = {
      count: ['Kaç tane', 1, 30, 1], seconds: ['Süre (sn)', 0.5, 12, 0.1], fade: ['Görünürlük', 0, 1, 0.05],
      smallest: ['En küçük boyut', 0.1, 2, 0.05], largest: ['En büyük boyut', 0.1, 2, 0.05],
      distance: ['Yayılma mesafesi', 0.2, 1.2, 0.05], hover: ['Üzerine gelince büyüme', 1, 1.3, 0.01],
      press: ['Basınca küçülme', 0.5, 1, 0.01], sweep: ['Süpürme süresi (sn)', 0.5, 6, 0.1],
      pause: ['Geçişler arası bekleme (sn)', 0, 4, 0.1], width: ['Bant genişliği', 0.05, 0.5, 0.01],
      scale: ['Çap (katı)', 1, 3, 0.05], pulse: ['Nefes büyüklüğü', 1, 1.4, 0.01],
      tilt: ['Eğim (derece)', -45, 45, 1], strength: ['Parlaklık', 0.1, 1, 0.05], loop: ['Döngü', 0, 1, 1]
    };

    // Döngü aç/kapat düğmesi (efekt ayarlarında) — hedef.loop: 1 = sürekli, 0 = bir kez
    function loopRow(target, onChange) {
      var line = document.createElement('div'); line.className = 'as-fxline';
      var lab = document.createElement('span'); lab.className = 'as-fxlab'; lab.textContent = 'Döngü';
      var b = document.createElement('button'); b.type = 'button'; b.className = 'ghost';
      var paint = function () { b.textContent = target.loop === 0 ? 'Kapalı: bir kez oynar (aç)' : 'Açık: sürekli oynar (kapat)'; };
      b.onclick = function () { target.loop = target.loop === 0 ? 1 : 0; paint(); onChange(); };
      paint(); line.appendChild(lab); line.appendChild(b);
      return line;
    }
    // Hover / tıklama ses ID alanları (boş = standart ses, numara = o ses, none = sessiz)
    function soundRows(box, target, onChange) {
      [['hoverSound', 'Hover ses ID'], ['clickSound', 'Tıklama ses ID']].forEach(function (p) {
        var line = document.createElement('div'); line.className = 'as-fxline';
        var lab = document.createElement('span'); lab.className = 'as-fxlab'; lab.textContent = p[1];
        var inp = document.createElement('input'); inp.type = 'text'; inp.placeholder = 'default';
        inp.style.cssText = 'flex:1;min-width:0;text-align:left;';
        inp.value = typeof target[p[0]] === 'string' ? target[p[0]] : '';
        inp.onchange = function () { var v = inp.value.replace(/^\s+|\s+$/g, ''); if (v) target[p[0]] = v; else delete target[p[0]]; onChange(); };
        line.appendChild(lab); line.appendChild(inp); box.appendChild(line);
      });
      var hint = document.createElement('div'); hint.className = 'as-fxlab';
      hint.style.cssText = 'opacity:.7;font-size:11px;margin-top:2px;';
      hint.textContent = 'Boş = standart ses · numara = o ses · none = sessiz';
      box.appendChild(hint);
    }


    // Katmanın ilk görünür düz dolgusu (önizleme için): rgba metni
    function fillOf(item) {
      var f = (item.fills || []).filter(function (x) { return x && x.type === 'SOLID' && x.visible !== false; })[0];
      if (!f || !f.color) return null;
      var c = f.color, sc = (c.r <= 1 && c.g <= 1 && c.b <= 1) ? 255 : 1;
      return 'rgba(' + Math.round(c.r * sc) + ',' + Math.round(c.g * sc) + ',' + Math.round(c.b * sc) + ',' + (f.opacity == null ? 1 : f.opacity) + ')';
    }

    function run(doc) {
      rows = []; rowNodes = []; lastStyle = 'belirsiz'; lastConf = 0;
      if (!doc || !doc.root) return rows;
      var raw = EIRaw.extract(doc);
      var nodes = raw.nodes || [];
      try {
        var st = EIStyle.decide(EIStyle.signals(raw.gui || {}, nodes));
        lastStyle = st.style || 'belirsiz';
        lastConf = st.conf || 0;
      } catch (e) {}
      var k = 0;
      // Ağaç sırası = RAW sırası (DFS, kök dâhil) — Assist.prepare ile aynı eşleme.
      (function walk(item, depth, parentRow) {
        if (!item) return;
        var myRow = rows.length;
        var r = nodes[k++];
        var fx = (r && typeof r.fxKind === 'string' && r.fxKind) ? r.fxKind : '-';
        var pred = null;
        try { pred = EIModel.predict(EI.compute(EI_FEATURES_SPEC, r)); } catch (e) { pred = null; }
        var mcls = pred ? pred.cls : '-';
        var mconf = pred ? pred.conf : 0;
        var ctx = EILearn.ctxKey(lastStyle, mcls, '-', fx);
        var pref = EILearn.preferredClass(learn, ctx);
        var cls = mcls, src = 'model';
        if (pref && pref.n >= LEARN_MIN) { cls = pref.cls; src = 'öğrenme'; }
        else if (mconf < CONF_MIN) { src = 'düşük güven'; }
        var kind = item.kind ? String(item.kind) : (item.image ? 'image' : '-');
        rows.push({ name: String(item.name || 'Layer'), kind: kind, depth: depth, model: mcls, conf: mconf,
                    cls: cls, src: src, ctx: ctx, parent: (parentRow === undefined ? null : parentRow),
                    w: item.w, h: item.h, fill: fillOf(item), radius: item.radius || 0,
                    text: (item.text && item.text.characters) ? String(item.text.characters) : '' });
        rowNodes.push(item);
        (item.children || []).forEach(function (c) { walk(c, depth + 1, myRow); });
      })(doc.root, 0, null);
      return rows;
    }

    // Her katman için bağlanacak animasyon yuvaları (Studio EIAnim.plan ile AYNI kural):
    //   giriş → depth ≤ 1 · hover ve basma → yalnız buton sınıfları
    function buildSlots() {
      slots = [];
      // Tasarım kararı (madde 3 + P1): stil, konum, tutarlılık, öğrenme, kaskad, döngü, seçim grubu.
      // Studio ile AYNI kurallar (EIAnim.decideRanked).
      var els = rows.map(function (row, i) {
        var node = rowNodes[i] || {};
        return { id: i + 1, name: row.name, cls: row.cls, depth: row.depth,
                 parent: (row.parent === null ? null : row.parent + 1),
                 panel: !!node.panel };   // _open hedefi ya da içinde _close olan öğe (code.js markPanels)
      });
      var per = EIAnim.decideRanked(els, lastStyle, learn);
      rowFx = [];
      per.forEach(function (pe) {
        var i = pe.id - 1, row = rows[i];
        rowFx[i] = pe.fx || null;
        ['giris', 'cikis', 'hover', 'basma', 'dongu', 'secim'].forEach(function (cat) {
          var opts = pe.rank[cat];
          if (!opts || !opts.length) return;
          // Tüm uygun animasyonlar: öneri başta, geri kalanları kategori sırasıyla (eskiden yalnız 1-2 seçenek vardı)
          var all = EIAnim.allForCat(cat);
          // Not: kütüphane kategorileri üreteçte yuvaya katlanır (fx→dongu, gecis/metin→giris);
          // bu yüzden allForCat yuvanın tüm animasyonlarını (kendi resim efektleri dâhil) verir.
          opts = opts.concat(all.filter(function (id) { return opts.indexOf(id) === -1; }));
          slots.push({ rowIndex: i, name: row.name, cls: row.cls, depth: row.depth, cat: cat, role: pe.role,
                       ctx: EILearn.ctxKey(lastStyle, row.cls, pe.role, cat), options: opts, selected: opts[0],
                       delay: (cat === 'giris' && pe.delay) ? pe.delay : 0 });
        });
      });
      // Kütüphaneden yapılan atamalar (efekt ve animasyon) — yeniden kurulumda kaybolmaz
      Object.keys(userFx).forEach(function (ri) {
        var i = Number(ri);
        if (rows[i]) rowFx[i] = userFx[ri] === 'none' ? null : userFx[ri];
      });
      Object.keys(userAnim).forEach(function (ri) {
        var i = Number(ri);
        Object.keys(userAnim[ri]).forEach(function (cat) {
          var id = userAnim[ri][cat];
          var sl = slots.filter(function (x) { return x.rowIndex === i && x.cat === cat; })[0];
          if (!sl) {
            var row = rows[i];
            if (!row) return;
            sl = { rowIndex: i, name: row.name, cls: row.cls, depth: row.depth, cat: cat, role: '-',
                   ctx: EILearn.ctxKey(lastStyle, row.cls, '-', cat), options: [id], selected: id, delay: 0 };
            slots.push(sl);
          }
          if (sl.options.indexOf(id) === -1) sl.options.unshift(id);
          sl.selected = id;
        });
      });
    }

    function chooseAnim(si, chosen) {
      var slot = slots[si];
      if (!slot || chosen === slot.selected) return;
      EILearn.recordAnim(learn, slot.ctx, chosen, true);      // seçilen kabul edildi
      EILearn.recordAnim(learn, slot.ctx, slot.selected, false); // önceki seçim reddedildi
      slot.selected = chosen;
      save();
      buildSlots();
      applyToJson();
      render();
    }

    // Seçilen animasyonları dışa aktarılan JSON'a işler (senin tarifin):
    //   doc.anims["_Animasyon N"] = { src: <kütüphane kimliği>, cat, tracks }   (ad kullanıcıya gösterilmez)
    //   düğüm.anim = { show?, hover?, press? }  → değerler "_Animasyon N" adlarıdır
    // Ad sırası ilk kullanıma göre atanır; yeniden hesap aynı adları verir.
    // Efekt satırlarının parametreleri: yoksa varsayılanlardan kopyalanır.
    function fxRowIndexes() {
      var out = [];
      rowFx.forEach(function (fx, i) { if (fx && fx !== 'tpl' && EIAnim.FX_DEFAULTS[fx]) out.push(i); });
      return out;
    }
    function paramsFor(i) {
      var kind = rowFx[i];
      if (!rowParams[i]) {
        rowParams[i] = {};
        var d = EIAnim.FX_DEFAULTS[kind] || {};
        Object.keys(d).forEach(function (k) { rowParams[i][k] = d[k]; });
      }
      return rowParams[i];
    }

    function renderFx() {
      var list = $('fxList'), box = $('fxParams');
      if (!list || !box) return;
      list.innerHTML = '';
      var idx = fxRowIndexes();
      if (idx.length && (fxSel === null || idx.indexOf(fxSel) === -1)) fxSel = idx[0];
      idx.forEach(function (i) {
        var b = document.createElement('button');
        b.className = 'as-fxrow' + (i === fxSel ? ' on' : '');
        b.textContent = rows[i].name + '  ·  ' + (FX_LABEL[rowFx[i]] || rowFx[i]);
        b.onclick = function () { fxSel = i; renderFx(); };
        list.appendChild(b);
      });
      $('fxCount').textContent = idx.length + ' efekt';
      box.innerHTML = '';
      if (fxSel === null) {
        box.textContent = 'Efekt yok. Katman adına efekt etiketi yaz (örnek: Hazine_fall_Frame).';
        return;
      }
      var kind = rowFx[fxSel], params = paramsFor(fxSel);
      var title = document.createElement('div');
      title.className = 'as-fxtitle';
      title.textContent = (FX_LABEL[kind] || kind) + ' ayarları';
      box.appendChild(title);
      if (PIC_KINDS[kind]) {
        var pic = document.createElement('div');
        pic.className = 'as-fxpics';
        var lab = document.createElement('div');
        lab.className = 'as-fxlab';
        lab.textContent = 'Kopyalanacak resim (en çok ' + PIC_MAX + ', her biri 2 MB)';
        var inp = document.createElement('input');
        inp.type = 'file'; inp.accept = 'image/png,image/jpeg'; inp.multiple = true;
        inp.onchange = function () { addPictures(fxSel, inp.files); inp.value = ''; };
        pic.appendChild(lab); pic.appendChild(inp);
        // Envanter: tasarımdaki kendi resimlerimiz (ek katman açmadan efekt resmi olur)
        var di = designImages();
        var ownLab = document.createElement('div');
        ownLab.className = 'as-fxlab';
        ownLab.textContent = 'Envanter · kendi resimlerim (' + di.length + ') — Roblox aktarımında sıfırlanır';
        pic.appendChild(ownLab);
        var ownBox = document.createElement('div');
        ownBox.className = 'as-fxthumbs';
        if (!di.length) {
          var none = document.createElement('span');
          none.className = 'as-fxlab';
          none.style.cssText = 'opacity:.7;font-size:11px;';
          none.textContent = 'Tasarımda dışa aktarılabilir PNG yok (önce dışa aktar) — ya da yukarıdan dosya yükle.';
          pic.appendChild(none);
        } else {
          var picked = ownPickedNames2(fxSel);
          di.forEach(function (f) {
            var nm = String(f.file).replace(/\.png$/i, '');
            var t = document.createElement('button');
            t.className = 'as-fxthumb' + (picked.indexOf(nm) !== -1 ? ' on' : '');
            t.title = f.file + ' · efekte ekle/çıkar';
            var im = document.createElement('img');
            im.src = ownUrl(f); im.alt = f.file;
            t.appendChild(im);
            t.onclick = function () { toggleOwn(fxSel, f); };
            ownBox.appendChild(t);
          });
          pic.appendChild(ownBox);
        }
        var resetBtn = document.createElement('button');
        resetBtn.type = 'button'; resetBtn.className = 'ghost';
        resetBtn.textContent = 'Envanteri sıfırla';
        resetBtn.title = 'Kendi resim seçimlerini ve yüklenen dosyaları temizler';
        resetBtn.onclick = function () { resetInventory(); };
        pic.appendChild(resetBtn);
        var thumbs = document.createElement('div');
        thumbs.className = 'as-fxthumbs';
        (fxUploads[fxSel] || []).forEach(function (u) {
          var t = document.createElement('div');
          t.className = 'as-fxthumb';
          var im = document.createElement('img');
          im.src = u.url; im.alt = u.file;
          var x = document.createElement('button');
          x.textContent = '×'; x.title = 'Bu resmi kaldır';
          x.onclick = function () { removePicture(fxSel, u); };
          t.appendChild(im); t.appendChild(x); thumbs.appendChild(t);
        });
        (fxLibPick[fxSel] || []).forEach(function (id) {
          var t = document.createElement('div');
          t.className = 'as-fxthumb';
          var im = document.createElement('img');
          im.src = EKSTRA_THUMBS[id] || ''; im.alt = id;
          var x = document.createElement('button');
          x.textContent = '×'; x.title = 'Bu simgeyi kaldır';
          x.onclick = function () { toggleIcon(fxSel, id); };
          t.appendChild(im); t.appendChild(x); thumbs.appendChild(t);
        });
        pic.appendChild(thumbs);
        box.appendChild(pic);

        // Ekstra kütüphane: öğrenen sıralama (tohum + seçimlerin), kategori ve arama
        var lib = document.createElement('div');
        lib.className = 'as-fxlib';
        var libLab = document.createElement('div');
        libLab.className = 'as-fxlab';
        libLab.textContent = 'Ekstra kütüphane (' + EKSTRA_INDEX.length + ' simge) · sıra seçimlerinden öğrenilir';
        var bar = document.createElement('div');
        bar.className = 'as-fxbar';
        var catSel = document.createElement('select');
        var cats = {};
        EKSTRA_INDEX.forEach(function (ic) { cats[ic.cat] = true; });
        var catOpts = [''].concat(Object.keys(cats).sort());
        catOpts.forEach(function (c) {
          var o = document.createElement('option');
          o.value = c; o.textContent = c || 'Tüm kategoriler';
          catSel.appendChild(o);
        });
        catSel.value = libCat;
        var q = document.createElement('input');
        q.type = 'search'; q.placeholder = 'ara…'; q.value = libQuery;
        var grid = document.createElement('div');
        grid.className = 'as-fxgrid';
        var drawGrid = function () {
          grid.innerHTML = '';
          var kindNow = rowFx[fxSel];
          var ranked = EIFxPick.rank(kindNow, EKSTRA_INDEX, learn, lastStyle);
          var needle = libQuery.toLowerCase();
          var shown = 0;
          for (var k = 0; k < ranked.length && shown < 60; k++) {
            var ic = ranked[k];
            if (libCat && ic.cat !== libCat) continue;
            if (needle && (ic.label + ' ' + ic.name).toLowerCase().indexOf(needle) === -1) continue;
            shown++;
            var b = document.createElement('button');
            var on = (fxLibPick[fxSel] || []).indexOf(ic.id) !== -1;
            b.className = 'as-fxicon' + (on ? ' on' : '');
            b.title = ic.cat + ' · ' + ic.label;
            var im = document.createElement('img');
            im.src = EKSTRA_THUMBS[ic.id]; im.alt = ic.label;
            b.appendChild(im);
            (function (id) { b.onclick = function () { toggleIcon(fxSel, id); drawGrid(); }; })(ic.id);
            grid.appendChild(b);
          }
          if (!shown) grid.textContent = 'Eşleşen simge yok.';
        };
        catSel.onchange = function () { libCat = catSel.value; drawGrid(); };
        q.oninput = function () { libQuery = q.value; drawGrid(); };
        bar.appendChild(catSel); bar.appendChild(q);
        lib.appendChild(libLab); lib.appendChild(bar); lib.appendChild(grid);
        box.appendChild(lib);
        drawGrid();
      }
      Object.keys(EIAnim.FX_DEFAULTS[kind]).forEach(function (k) {
        if (k === 'loop') { box.appendChild(loopRow(params, function () { applyToJson(); })); return; }
        var ui = PARAM_UI[k] || [k, 0, 1, 0.01];
        var line = document.createElement('div');
        line.className = 'as-fxline';
        var lab = document.createElement('span');
        lab.className = 'as-fxlab';
        lab.textContent = ui[0];
        var rng = document.createElement('input');
        rng.type = 'range'; rng.min = ui[1]; rng.max = ui[2]; rng.step = ui[3]; rng.value = params[k];
        var num = document.createElement('input');
        num.type = 'number'; num.min = ui[1]; num.max = ui[2]; num.step = ui[3]; num.value = params[k];
        num.className = 'as-fxnum';
        var setVal = function (v) {
          var n = Number(v);
          if (!isFinite(n)) return;
          params[k] = n;
          rng.value = n; num.value = n;
          applyToJson();
          if (window.__ktRepaint) window.__ktRepaint();   // kütüphane önizlemesi anında tazelensin
        };
        rng.oninput = function () { setVal(rng.value); };
        num.onchange = function () { setVal(num.value); };
        line.appendChild(lab); line.appendChild(rng); line.appendChild(num);
        box.appendChild(line);
      });
      soundRows(box, params, function () { applyToJson(); });
    }

    function cleanBase(name) {
      return String(name || 'Layer').replace(/[^A-Za-z0-9_]/g, '_').slice(0, 40);
    }
    function nextPicIndex(i) {
      var used = {};
      (fxUploads[i] || []).forEach(function (u) { used[u.index] = true; });
      for (var k = 1; k <= PIC_MAX; k++) if (!used[k]) return k;
      return 0;
    }
    function addPictures(i, fileList) {
      if (!fxUploads[i]) fxUploads[i] = [];
      var jobs = [];
      Array.prototype.forEach.call(fileList, function (f) {
        if (!/^image\/(png|jpeg)$/.test(f.type)) return;
        if (f.size > PIC_BYTES) return;
        var idx = nextPicIndex(i);
        if (!idx) return;
        var ext = f.type === 'image/png' ? '.png' : '.jpg';
        var base = 'fx_' + cleanBase(rows[i].name) + '_' + idx;
        var slot = { index: idx, base: base, file: base + ext, bytes: null, url: URL.createObjectURL(f) };
        fxUploads[i].push(slot);
        jobs.push(new Promise(function (resolve) {
          var fr = new FileReader();
          fr.onload = function () { slot.bytes = new Uint8Array(fr.result); resolve(); };
          fr.onerror = function () { resolve(); };
          fr.readAsArrayBuffer(f);
        }));
      });
      Promise.all(jobs).then(function () {
        fxUploads[i] = (fxUploads[i] || []).filter(function (u) { return u.bytes; });
        applyToJson(); renderFx();
        if (typeof refreshDlAll === 'function') refreshDlAll();
      });
    }
    function picCount(i) {
      return (fxUploads[i] || []).filter(function (u) { return u.bytes; }).length
        + (fxLibPick[i] || []).length + (fxOwnPick[i] || []).length;
    }
    // ---- Envanter (v33): kendi resimlerimiz — tasarımdaki PNG'ler + yüklediklerimiz.
    // Roblox aktarımında (yeni dışa aktarma) liste sıfırlanır; bu yüzden burada yalnız bu oturumun seçimleri tutulur.
    var ownUrls = {};   // dosya adı → blob URL (önbellek)
    function ownUrl(f) {
      if (ownUrls[f.file] === undefined) {
        try { ownUrls[f.file] = URL.createObjectURL(new Blob([f.bytes], { type: 'image/png' })); }
        catch (e) { ownUrls[f.file] = ''; }
      }
      return ownUrls[f.file];
    }
    function designImages() {
      var list = (typeof files !== 'undefined' && files) ? files : [];
      return list.filter(function (f) { return f && f.bytes; });
    }
    // Kütüphane kartındaki bilgi satırına güvenli mesaj (iki IIFE ayrı kapsamda)
    function note(t) { try { if (typeof window.__ktSay === 'function') window.__ktSay(t); } catch (e) {} }
    function ownPickedNames2(i) { return (fxOwnPick[i] || []).map(function (o) { return o.name; }); }
    function toggleOwn(i, f) {
      var name = String(f.file).replace(/\.png$/i, '');
      var picks = fxOwnPick[i] || (fxOwnPick[i] = []);
      var at = -1;
      picks.forEach(function (o, k) { if (o.name === name) at = k; });
      if (at >= 0) picks.splice(at, 1);
      else {
        if (picCount(i) >= PIC_MAX) { note('En çok ' + PIC_MAX + ' resim seçilebilir; birini kaldır.'); return; }
        picks.push({ name: name, file: f.file });
      }
      save(); applyToJson(); renderFx();
      if (typeof refreshDlAll === 'function') refreshDlAll();
    }
    // Envanteri sıfırla: kendi resim seçimleri + yüklenen dosyalar temizlenir (Studio'ya aktarımdan sonra istendiği gibi)
    function resetInventory() {
      var n = 0;
      Object.keys(fxOwnPick).forEach(function (k) { n += (fxOwnPick[k] || []).length; });
      Object.keys(fxUploads).forEach(function (k) { n += (fxUploads[k] || []).length; delete fxUploads[k]; });
      fxOwnPick = {};
      applyToJson(); renderFx();
      if (typeof refreshDlAll === 'function') refreshDlAll();
      if (n) note('Envanter sıfırlandı (' + n + ' resim).');
    }
    function toggleIcon(i, id) {
      var picks = fxLibPick[i] || (fxLibPick[i] = []);
      var kind = rowFx[i];
      var at = picks.indexOf(id);
      if (at >= 0) {
        picks.splice(at, 1);
        EIFxPick.record(learn, lastStyle, kind, id, false);
      } else {
        if (picCount(i) >= PIC_MAX) return;
        picks.push(id);
        EIFxPick.record(learn, lastStyle, kind, id, true);
      }
      save();
      applyToJson(); renderFx();
      if (typeof refreshDlAll === 'function') refreshDlAll();
    }
    function removePicture(i, slot) {
      fxUploads[i] = (fxUploads[i] || []).filter(function (u) { return u !== slot; });
      applyToJson(); renderFx();
      if (typeof refreshDlAll === 'function') refreshDlAll();
    }

    // Kütüphaneden atama: efekt (kind | null = kaldır)
    function setFx(i, kind) {
      if (!rows[i]) return;
      userFx[i] = kind ? kind : 'none';
      if (kind && rowFx[i] !== kind) delete rowParams[i];   // tür değişti: ayarlar yeniden varsayılandan
      buildSlots();
      if (kind) { paramsFor(i); fxSel = i; }
      applyToJson(); render(); renderFx();
    }
    // Kütüphaneden atama: animasyon (cat: giris | hover | basma | dongu | secim)
    function setAnim(i, id, cat) {
      if (!rows[i] || !id) return;
      userAnim[i] = userAnim[i] || {};
      userAnim[i][cat] = id;
      buildSlots(); applyToJson(); render();
    }
    // Bir katmanın mevcut durumu (kütüphane önizlemesi ve özet için)
    function stateOf(i) {
      var row = rows[i];
      if (!row) return null;
      var anims = {};
      slots.forEach(function (sl) { if (sl.rowIndex === i && sl.selected) anims[sl.cat] = sl.selected; });
      return { name: row.name, cls: row.cls, fx: rowFx[i] || null,
               params: rowFx[i] ? paramsFor(i) : null,
               picks: (fxLibPick[i] || []).slice().concat((fxOwnPick[i] || []).map(function (o) { return o.name; })),
               anims: anims };
    }

    // Kütüphaneden "İçeri ekle": simgeyi seçili öğenin içine görüntü olarak koyar (Studio ad eşleşmesiyle bağlanır)
    function addIconChild(i, id) {
      var node = rowNodes[i];
      if (!node || !id) return false;
      var W = node.w || 64, H = node.h || 64;
      var sz = Math.round(Math.max(16, Math.min(64, Math.min(W, H) * 0.5)));
      node.children = node.children || [];
      node.children.push({ name: id, kind: 'image', image: id + '.png', x: Math.round((W - sz) / 2), y: Math.round((H - sz) / 2),
                           w: sz, h: sz, rot: 0, opacity: 1, fills: [], radius: 0, clips: false, children: [], visible: true });
      applyToJson(); render();
      return true;
    }

    function applyToJson() {
      if (!lastDoc || !lastDoc.root) return;
      var names = {};   // kütüphane kimliği → "_Animasyon N"
      var specs = {};
      var counter = 0;
      function nameOf(id) {
        if (!names[id]) {
          counter += 1;
          names[id] = '_Animasyon ' + counter;
          var def = EIAnim.getAnim(id);
          specs[names[id]] = { src: id, cat: def ? def.cat : '', trig: def ? def.trig : '', tracks: def ? def.tracks : [] };
        }
        return names[id];
      }
      rowNodes.forEach(function (node) { delete node.anim; });
      var byRow = {};
      slots.forEach(function (sl) {
        var key = { giris: 'show', cikis: 'hide', hover: 'hover', basma: 'press', dongu: 'loop', secim: 'selA' }[sl.cat];
        var entry = (byRow[sl.rowIndex] = byRow[sl.rowIndex] || {});
        entry[key] = nameOf(sl.selected);
        if (sl.delay > 0) entry.delay = sl.delay;
      });
      rowFx.forEach(function (fx, ri) {
        if (!fx) return;
        byRow[ri] = byRow[ri] || {};
        byRow[ri].fx = fx;
        if (fx !== 'tpl' && EIAnim.FX_DEFAULTS[fx]) byRow[ri].params = paramsFor(ri);
        var pics = (fxUploads[ri] || []).filter(function (u) { return u.bytes; }).map(function (u) { return u.base; });
        pics = pics.concat((fxOwnPick[ri] || []).map(function (o) { return o.name; }));
        pics = pics.concat(fxLibPick[ri] || []);
        if (fx === 'shine' || fx === 'sweep') pics.unshift('ei_shine_rectangle');
        if (pics.length) byRow[ri].fxImages = pics;
      });
      Object.keys(byRow).forEach(function (ri) {
        var node = rowNodes[Number(ri)];
        if (node) node.anim = byRow[ri];
      });
      if (Object.keys(specs).length) lastDoc.anims = specs; else delete lastDoc.anims;
      lastJsonStr = JSON.stringify(lastDoc);
      refreshBox();
      if (window.__eiAsReady && $('view-result') && $('view-result').style.display !== 'none') {
        setStatus('Ayar uygulandı: JSON güncellendi. Studio’ya yapıştırmadan önce "Kopyala"ya yeniden bas.');
      }
    }

    function save() {
      parent.postMessage({ pluginMessage: { type: 'learn-save', text: EILearn.encode(learn) } }, '*');
    }

    function correct(i, chosen) {
      var row = rows[i];
      if (!row || chosen === row.cls) return;
      if (chosen !== row.model) EILearn.recordClass(learn, row.ctx, chosen, 1);
      row.cls = chosen;
      row.src = 'düzeltme';
      save();
      render();
    }

    function render() {
      var list = $('asistList');
      list.innerHTML = '';
      var shown = rows.slice(0, 200);
      shown.forEach(function (row, i) {
        var line = document.createElement('div');
        line.className = 'as-row';
        var nm = document.createElement('span');
        nm.className = 'nm';
        nm.style.paddingLeft = (row.depth * 12) + 'px';
        nm.textContent = row.name;
        var kd = document.createElement('span');
        kd.className = 'kd';
        kd.textContent = row.kind;
        var sel = document.createElement('select');
        EIModel.CLASSES.forEach(function (c) {
          var o = document.createElement('option');
          o.value = c; o.textContent = c;
          if (c === row.cls) o.selected = true;
          sel.appendChild(o);
        });
        sel.onchange = function () { correct(i, sel.value); };
        var sr = document.createElement('span');
        sr.className = 'src ' + (row.src === 'öğrenme' || row.src === 'düzeltme' ? 'as-src-learn'
          : (row.src === 'model' ? 'as-src-model' : 'as-src-low'));
        sr.textContent = row.src + (row.model !== '-' ? ' · ' + Math.round(row.conf * 100) + '%' : '');
        line.appendChild(nm); line.appendChild(kd); line.appendChild(sel); line.appendChild(sr);
        list.appendChild(line);
      });
      if (rows.length > shown.length) {
        var more = document.createElement('div');
        more.className = 'as-row';
        more.textContent = '… ilk ' + shown.length + ' katman gösteriliyor (toplam ' + rows.length + ')';
        list.appendChild(more);
      }
      var al = $('animList');
      al.innerHTML = '';
      slots.slice(0, 200).forEach(function (sl, si) {
        var line = document.createElement('div');
        line.className = 'as-row';
        var nm = document.createElement('span');
        nm.className = 'nm';
        nm.style.paddingLeft = (sl.depth * 12) + 'px';
        nm.textContent = sl.name + '  ·  ' + sl.cat;
        var sel = document.createElement('select');
        sel.className = 'as-anim';
        sl.options.forEach(function (id, k) {
          var o = document.createElement('option');
          o.value = id;
          o.textContent = id + (k === 0 ? '  (varsayılan)' : '');
          if (id === sl.selected) o.selected = true;
          sel.appendChild(o);
        });
        sel.onchange = function () {
          chooseAnim(si, sel.value);
          // Canlı: seçilen animasyon o öğede hemen oynar (kütüphane önizlemesi)
          if (window.__ktPreviewAnim) window.__ktPreviewAnim(sl.rowIndex, sel.value);
        };
        line.appendChild(nm); line.appendChild(sel);
        al.appendChild(line);
      });
      $('animCount').textContent = slots.length + ' seçim';
      renderFx();
      $('asistCount').textContent = rows.length + ' katman';
      $('asistInfo').textContent = 'stil: ' + lastStyle + ' (' + Math.round(lastConf * 100) + '%)';
      $('asistLearn').textContent = 'düzeltme ' + (learn.events || 0);
    }

    // Kütüphane kartı için güvenli köprü (yalnız okuma + kullanıcı atamaları)
    window.__AS = {
      rows: function () { return rows; },
      stateOf: stateOf, setFx: setFx, setAnim: setAnim, toggleIcon: toggleIcon, addIcon: addIconChild,
      applyToJson: applyToJson, paramsFor: paramsFor, PARAM_UI: PARAM_UI, FX_LABEL: FX_LABEL,
      loopRow: loopRow, soundRows: soundRows, ownPick: fxOwnPick, PIC_KINDS: PIC_KINDS
    };
    return {
      show: function (doc) {
        var card = $('asistCard');
        rowParams = {}; fxSel = null; userFx = {}; userAnim = {};
        Object.keys(fxUploads).forEach(function (k) { delete fxUploads[k]; });
        fxLibPick = {};
        fxOwnPick = {};   // envanter: Roblox aktarımı (yeni dışa aktarma) ile sıfırlanır
        try {
          run(doc);
          buildSlots();
          applyToJson();
          render();
          card.style.display = rows.length ? '' : 'none';
          if (window.__ktReplay) window.__ktReplay();
          if (window.__ktRefresh) window.__ktRefresh();
          window.__eiAsReady = true;
        } catch (e) {
          rows = [];
          card.style.display = 'none';
        }
      },
      applyLearn: function (text) {
        try { if (text) learn = EILearn.decode(text); } catch (e) {}
        if (rows.length) { buildSlots(); applyToJson(); render(); }
      },
      downloadPack: function () {
        download('easyimport-ogrenme.txt', new Blob([EILearn.encode(learn)], { type: 'text/plain' }));
      }
    };
  })();
  $('asistPack').onclick = function () { AS.downloadPack(); };
  parent.postMessage({ pluginMessage: { type: 'learn-load' } }, '*');

// ---- KÜTÜPHANE (v29): katmana uygulanabilir önizleme; efekt, animasyon ve ikon ataması; ayarlar ----
(function () {
  var box = document.getElementById('kt-box');
  if (!box || !window.__AS) return;
  var $ = function (id) { return document.getElementById(id); };
  var list = $('kt-list'), catSel = $('kt-cat'), qIn = $('kt-q'), info = $('kt-info'),
      playBtn = $('kt-play'), countEl = $('kt-count'), layerSel = $('kt-layer'), nowEl = $('kt-now'),
      paramsEl = $('kt-params'), applyBtn = $('kt-apply'), removeBtn = $('kt-remove'), insertBtn = $('kt-insert');
  var mode = 'anim', sel = null, timer = null, layer = -1, draft = {};
  var FX_KINDS = [['fall', 'Yağmur'], ['confetti', 'Konfeti'], ['burst', 'Patlama'], ['orbit', 'Yörünge'],
                  ['twinkle', 'Parıltı'], ['smooth', 'Büyüme (buton)'], ['gleam', 'Metin parıltısı'],
                  ['sweep', 'Işık süpürme'], ['shine', 'Rectangle parlama (içeride)'], ['orb', 'Dev hale']];
  var EASE = { Linear: 'linear', Sine: 'ease-in-out', Quad: 'ease-out', Quint: 'cubic-bezier(.22,1,.36,1)',
               Back: 'cubic-bezier(.34,1.56,.64,1)', Elastic: 'cubic-bezier(.68,-.55,.27,1.55)',
               Bounce: 'cubic-bezier(.5,1.6,.4,.7)', Exponential: 'cubic-bezier(.16,1,.3,1)' };
  // Kütüphane kategorisi → çalışma zamanı yuvası. Kategoriler üreteçte katlanmıştır (fx→dongu,
  // gecis/metin→giris, durum dışarıda), bu yüzden yedi kategori kalan her şeyi kapsar.
  var CAT_MAP = { giris: 'giris', cikis: 'cikis', hover: 'hover', basma: 'basma', dongu: 'dongu', dikkat: 'dongu', secim: 'secim' };

  function rowsNow() { return window.__AS.rows(); }
  function hasRows() { return rowsNow().length > 0; }
  // Dışa aktarmadan önce: seçili Figma katmanı sahte satır olur (atamalar 'bekleyen' listesinde tutulur)
  function curRow() {
    if (layer >= 0 && rowsNow()[layer]) return rowsNow()[layer];
    if (!hasRows() && window.__selName) return { name: window.__selName, cls: 'Seçim', w: window.__selW, h: window.__selH, pending: true };
    return null;
  }
  // Bekleyen işlemler: {t:'anim'|'fx'|'pick'|'insert', id, cat, target:katman adı, params}
  // Dışa aktarmadan önce de çalışır; dışa aktarınca ve her yeniden aktarımda katman adına göre yeniden uygulanır.
  var pend = [];
  function pkey(o) { return o.t + '|' + (o.cat || '') + '|' + o.target + ((o.t === 'pick' || o.t === 'insert') ? '|' + o.id : ''); }
  function pendPut(o) {
    var k = pkey(o);
    for (var i = 0; i < pend.length; i++) if (pkey(pend[i]) === k) { pend[i] = o; return; }
    pend.push(o);
  }
  function pendHas(o) { var k = pkey(o); return pend.some(function (x) { return pkey(x) === k; }); }
  function pendDrop(fn) { pend = pend.filter(function (o) { return !fn(o); }); }
  function pendState(tgt) {
    var fx = null, picks = [], anims = {};
    pend.forEach(function (o) {
      if (o.target !== tgt) return;
      if (o.t === 'fx') fx = o.id; else if (o.t === 'pick') picks.push(o.id); else if (o.t === 'anim') anims[o.cat] = o.id;
    });
    return { name: tgt, cls: 'Seçim', fx: fx, params: null, picks: picks, anims: anims };
  }
  function st() {
    if (layer >= 0 && hasRows()) return window.__AS.stateOf(layer);
    var r = curRow();
    return r ? pendState(r.name) : null;
  }
  window.__ktReplay = function () {
    if (!pend.length || !hasRows()) return;
    var rows = rowsNow();
    var idx = function (name) { for (var i = 0; i < rows.length; i++) if (rows[i].name === name) return i; return 0; };
    ['fx', 'pick', 'anim', 'insert'].forEach(function (t) {
      pend.forEach(function (o) {
        if (o.t !== t) return;
        var i = idx(o.target);
        if (t === 'fx') {
          window.__AS.setFx(i, o.id);
          var s = window.__AS.stateOf(i);
          if (o.params && s && s.params) { Object.keys(o.params).forEach(function (k) { s.params[k] = o.params[k]; }); window.__AS.applyToJson(); }
        } else if (t === 'pick') window.__AS.toggleIcon(i, o.id);
        else if (t === 'anim') window.__AS.setAnim(i, o.id, o.cat);
        else window.__AS.addIcon(i, o.id);
      });
    });
    layer = idx(pend[pend.length - 1].target);   // son işlem yapılan katman seçili gelsin
  };
  function clearBox() { if (timer) { clearInterval(timer); timer = null; } box.innerHTML = ''; }
  function num(v, d) { return typeof v === 'number' ? v : d; }
  function arr2(v) { return (v && v.length === 2) ? v : [0, 0]; }
  function say(t) { info.textContent = t; }
  window.__ktSay = say;

  // Seçili katmanın gerçek görüntüsü (Figma'dan PNG); yoksa dolgu/yazıdan yedek kutu
  function snapFor(i) {
    var fid = (typeof lastFids !== 'undefined') ? lastFids[i] : null;
    if (!fid) return null;
    if (snaps[fid] === undefined) requestSnap(fid);
    return snaps[fid] || null;
  }
  function snapSel() {
    var fid = window.__selFid;
    if (!fid) return null;
    if (snaps[fid] === undefined) requestSnap(fid);
    return snaps[fid] || null;
  }
  function layerEl(row) {
    var W = box.clientWidth || 230, H = box.clientHeight || 200;
    var src = (layer >= 0 && hasRows()) ? snapFor(layer) : snapSel();
    if (src) {
      var im = document.createElement('img');
      im.src = src;
      im.style.cssText = 'max-width:88%;max-height:88%;object-fit:contain;';
      box.appendChild(im);
      return im;
    }
    var w = (row && row.w) || 120, h = (row && row.h) || 44;
    var k = Math.min((W * 0.85) / w, (H * 0.85) / h, 2);
    var d = document.createElement('div');
    d.style.cssText = 'width:' + Math.max(8, w * k) + 'px;height:' + Math.max(8, h * k) + 'px;' +
      'border-radius:' + Math.min(((row && row.radius) || 0) * k, 60) + 'px;' +
      'background:' + ((row && row.fill) || 'rgba(255,255,255,.07)') + ';' +
      (row && row.fill ? '' : 'border:1px dashed #6f7587;') +
      'display:grid;place-items:center;color:#fff;font:700 ' + Math.max(9, Math.min(16, 14 * k)) + 'px system-ui;' +
      'overflow:hidden;';
    var t = (row && row.text) ? row.text : '';
    d.textContent = t.length > 16 ? t.slice(0, 16) : t;
    box.appendChild(d);
    return d;
  }

  // Animasyon: parça verileri (Scale, Rotation, Position/Offset, Transparency, Thickness) → Web Animations
  function playAnim(id) {
    clearBox();
    var a = EIAnim.getAnim(id), meta = ANIM_UI_NAMES[id] || {};
    if (!a) { say('Bu animasyon bu sürümde kullanılamıyor.'); return; }
    var el = layerEl(curRow());
    var scl = null, rot = null, pos = null, tr = null, th = null, loop = false, rev = false, dur = 0, easing = 'ease-in-out';
    (a.tracks || []).forEach(function (t) {
      if (t.p === 'Scale' && !scl) scl = t;
      else if (t.p === 'Rotation' && !rot) rot = t;
      else if ((t.p === 'Position' || t.p === 'Offset') && !pos) pos = t;
      else if (/Transparency/.test(t.p) && !tr) tr = t;
      else if (t.p === 'Thickness' && !th) th = t;
      dur = Math.max(dur, (t.d || 0) + (t.dl || 0));
      if (t.rep === -1) loop = true;
      if (t.rev) rev = true;
      if (t.e && EASE[t.e]) easing = EASE[t.e];
    });
    var s0 = scl ? num(scl.from, 1) : 1, s1 = scl ? num(scl.to, 1) : 1;
    var r0 = rot ? num(rot.from, 0) : 0, r1 = rot ? num(rot.to, 0) : 0;
    var p0 = pos ? arr2(pos.from) : [0, 0], p1 = pos ? arr2(pos.to) : [0, 0];
    var o0 = tr ? 1 - num(tr.from, 0) : 1, o1 = tr ? 1 - num(tr.to, 0) : 1;
    var w0 = th ? num(th.from, 0) : 0, w1 = th ? num(th.to, 0) : 0;
    var tf = function (s, r, p) { return 'translate(' + p[0] + 'px,' + p[1] + 'px) rotate(' + r + 'deg) scale(' + s + ')'; };
    var sh = function (w) { return w > 0 ? '0 0 0 ' + w + 'px rgba(255,255,255,.9)' : 'none'; };
    el.animate([
      { transform: tf(s0, r0, p0), opacity: o0, boxShadow: sh(w0) },
      { transform: tf(s1, r1, p1), opacity: o1, boxShadow: sh(w1) }
    ], { duration: Math.max(200, dur * 1000), easing: easing, iterations: Infinity,
         direction: (rev || !loop) ? 'alternate' : 'normal', endDelay: loop ? 0 : 450, fill: 'both' });
    say((meta.name || id) + ' · ' + (meta.cat || '') + (meta.trig ? ' · ' + meta.trig : '') +
        ' · ' + (dur ? dur.toFixed(2) + ' sn' : '') + (loop ? ' · sürekli' : ''));
  }

  function showIcon(id) {
    clearBox();
    layerEl(curRow());
    var W = box.clientWidth || 230, H = box.clientHeight || 200;
    var im = document.createElement('img');
    im.src = EKSTRA_THUMBS[id] || ''; im.className = 'kt-fxp';
    im.style.width = '56px'; im.style.height = '56px';
    im.style.left = (W / 2 - 28) + 'px'; im.style.top = (H / 2 - 28) + 'px';
    box.appendChild(im);
    im.animate([{ transform: 'scale(.9)' }, { transform: 'scale(1.12)' }], { duration: 700, direction: 'alternate', iterations: Infinity, easing: 'ease-in-out' });
    var ic = EKSTRA_INDEX.filter(function (x) { return x.id === id; })[0];
    say(ic ? (ic.cat + ' · ' + ic.label + (ic.wide ? ' (geniş)' : '')) : id);
  }

  // Önizleme planı (v33): efekt ayarlarını (kaç tane / süre / görünürlük …) JS önizlemesine çevirir.
  // Kullanıcı kaydırıcıyı oynatınca önizleme ANINDA değişir — ayarların çalıştığı burada görülür.
  function fxPreviewPlan(kind, p) {
    var d = EIAnim.FX_DEFAULTS[kind] || {};
    var v = function (k, lo, hi) {
      var x = (p && typeof p[k] === 'number') ? p[k] : d[k];
      if (typeof x !== 'number') x = lo;
      return Math.min(hi, Math.max(lo, x));
    };
    var raw = (p && typeof p.loop === 'number') ? p.loop : d.loop;
    return { loop: raw !== 0, count: Math.round(v('count', 1, 30)), seconds: v('seconds', 0.2, 12),
             fade: v('fade', 0, 1), smallest: v('smallest', 0.1, 2), largest: v('largest', 0.1, 2),
             distance: v('distance', 0.2, 1.2), sweep: v('sweep', 0.5, 6), pause: v('pause', 0, 4),
             width: v('width', 0.05, 0.5), tilt: v('tilt', -45, 45), strength: v('strength', 0.1, 1),
             scale: v('scale', 1, 3), pulse: v('pulse', 1, 1.4), hover: v('hover', 1, 1.3), press: v('press', 0.5, 1) };
  }
  window.__ktPreviewPlan = fxPreviewPlan;

  // Efekt önizlemesi: katmanın üstünde, seçili simgelerin (yoksa para) kopyalarıyla.
  // Ayarlar (Süre / Kaç tane / …) plana göre ANINDA uygulanır (v33 düzeltmesi).
  function playFx(kind) {
    clearBox();
    var row = curRow(); layerEl(row);
    var W = box.clientWidth || 230, H = box.clientHeight || 200;
    var s = st(), picks = (s && s.picks) || [];
    var fallIc = EKSTRA_INDEX.filter(function (x) { return x.cat === 'Currency'; })[0] || EKSTRA_INDEX[0];
    var pick = function () { return picks.length ? picks[Math.floor(Math.random() * picks.length)] : fallIc.id; };
    var piece = function (x, y, size) {
      var im = document.createElement('img'); im.src = EKSTRA_THUMBS[pick()]; im.className = 'kt-fxp';
      im.style.width = size + 'px'; im.style.height = size + 'px'; im.style.left = x + 'px'; im.style.top = y + 'px';
      box.appendChild(im); return im;
    };
    var plan = fxPreviewPlan(kind, paramTarget(kind));
    if (kind === 'fall' || kind === 'confetti') {
      var made = 0;
      var fall = function () {
        var size = 18 + 12 * plan.largest;
        var p = piece(Math.random() * (W - 40), -30, size);
        p.style.opacity = plan.fade;
        var d = plan.seconds * 1000;
        p.animate([{ transform: 'translateY(0) rotate(0deg)' },
                   { transform: 'translateY(' + (H + 60) + 'px) rotate(' + (Math.random() * 720 - 360) + 'deg)' }],
                  { duration: d, easing: 'linear', fill: 'forwards' });
        setTimeout(function () { p.remove(); }, d + 50);
        made += 1;
        if (!plan.loop && made >= plan.count && timer) { clearInterval(timer); timer = null; }
      };
      timer = setInterval(fall, Math.max(30, plan.seconds * 1000 / plan.count));
    } else if (kind === 'burst') {
      var burst = function () {
        for (var i = 0; i < plan.count; i++) {
          (function (ang) {
            var p = piece(W / 2 - 10, H / 2 - 10, 20);
            p.style.opacity = plan.fade;
            var dx = Math.cos(ang) * 70 * plan.distance, dy = Math.sin(ang) * 70 * plan.distance;
            p.animate([{ transform: 'translate(0,0) scale(1)', opacity: plan.fade },
                       { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(.6)', opacity: 0 }],
                      { duration: 800, easing: 'ease-out', fill: 'forwards' });
            setTimeout(function () { p.remove(); }, 850);
          })(i / plan.count * Math.PI * 2);
        }
      };
      burst();
      if (plan.loop) timer = setInterval(burst, 1400);
    } else if (kind === 'orbit') {
      var ring = document.createElement('div');
      ring.style.cssText = 'position:absolute;left:50%;top:50%;width:0;height:0';
      box.appendChild(ring);
      for (var k = 0; k < plan.count; k++) {
        var p = document.createElement('img'); p.src = EKSTRA_THUMBS[pick()]; p.className = 'kt-fxp';
        var rad = k / plan.count * Math.PI * 2;
        var sz = 14 + 10 * plan.largest;
        p.style.width = sz + 'px'; p.style.height = sz + 'px';
        p.style.left = (Math.cos(rad) * 58 - sz / 2) + 'px'; p.style.top = (Math.sin(rad) * 58 - sz / 2) + 'px';
        ring.appendChild(p);
      }
      ring.animate([{ transform: 'rotate(0deg)' }, { transform: 'rotate(360deg)' }],
                   { duration: plan.seconds * 1000, iterations: plan.loop ? Infinity : 1, easing: 'linear' });
    } else if (kind === 'twinkle') {
      var twMade = 0;
      var tw = function () {
        var p = piece(Math.random() * (W - 20), Math.random() * (H - 20), 12 + 12 * plan.largest);
        var d = plan.seconds * 1000;
        p.animate([{ transform: 'scale(0)', opacity: 0 }, { transform: 'scale(1)', opacity: plan.fade }, { transform: 'scale(0)', opacity: 0 }],
                  { duration: d, easing: 'ease-in-out' });
        setTimeout(function () { p.remove(); }, d + 50);
        twMade += 1;
        if (!plan.loop && twMade >= plan.count && timer) { clearInterval(timer); timer = null; }
      };
      timer = setInterval(tw, Math.max(30, plan.seconds * 1000 / plan.count));
    } else if (kind === 'shine' || kind === 'sweep') {
      // Parlama, öğenin İÇİNDE kırpılır; soldan sağa geçer
      var base = box.firstChild, rr = base ? base.getBoundingClientRect() : null, bb = box.getBoundingClientRect();
      if (rr) {
        var wrap = document.createElement('div');
        wrap.style.cssText = 'position:absolute;overflow:hidden;pointer-events:none;border-radius:' + ((base.style && base.style.borderRadius) || '0') +
          ';left:' + (rr.left - bb.left) + 'px;top:' + (rr.top - bb.top) + 'px;width:' + rr.width + 'px;height:' + rr.height + 'px;';
        var band = document.createElement('div');
        band.style.cssText = 'position:absolute;top:-30%;height:160%;width:' + (plan.width * 100) + '%;' +
          'transform:rotate(' + plan.tilt + 'deg);' +
          'background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,' + plan.strength + '),rgba(255,255,255,0));';
        wrap.appendChild(band); box.appendChild(wrap);
        band.animate([{ left: '-45%' }, { left: '110%' }],
                     { duration: plan.sweep * 1000, iterations: plan.loop ? Infinity : 1,
                       easing: 'ease-in-out', endDelay: plan.pause * 1000 });
      }
    } else if (kind === 'orb') {
      var glow = document.createElement('div');
      glow.className = 'kt-fxp';
      var gs = 110 * plan.scale;
      glow.style.cssText = 'left:' + (W / 2 - gs / 2) + 'px;top:' + (H / 2 - gs / 2) + 'px;width:' + gs + 'px;height:' + gs +
        'px;border-radius:50%;background:rgba(255,220,120,.28);';
      box.insertBefore(glow, box.firstChild);
      glow.animate([{ transform: 'scale(1)' }, { transform: 'scale(' + plan.pulse + ')' }],
                   { duration: 1600, direction: 'alternate', iterations: Infinity, easing: 'ease-in-out' });
    } else if (kind === 'smooth') {
      layerEl(row).animate([{ transform: 'scale(1)' }, { transform: 'scale(' + plan.hover + ')' }], { duration: 300, fill: 'forwards', easing: 'ease-out' });
    }
    var f = FX_KINDS.filter(function (x) { return x[0] === kind; })[0];
    say((f ? f[1] : kind) + ' · ' + (row ? row.name : '') + ' · ' + (picks.length ? picks.length + ' simge' : 'varsayılan para'));
  }

  // Seçili efektin ayarları: uygulanmış katmansa doğrudan, değilse taslağa
  function paramTarget(kind) {
    var s = st();
    if (s && s.fx === kind && s.params) return s.params;
    draft[kind] = draft[kind] || {};
    var d = EIAnim.FX_DEFAULTS[kind] || {};
    Object.keys(d).forEach(function (k) { if (draft[kind][k] === undefined) draft[kind][k] = d[k]; });
    return draft[kind];
  }
  function renderParams() {
    paramsEl.innerHTML = '';
    if (mode !== 'fx' || !sel) return;
    var target = paramTarget(sel);
    var ranges = window.__AS.PARAM_UI;
    var changed = function () { var s = st(); if (s && s.fx === sel) window.__AS.applyToJson(); };
    Object.keys(EIAnim.FX_DEFAULTS[sel] || {}).forEach(function (k) {
      if (k === 'loop') { paramsEl.appendChild(window.__AS.loopRow(target, changed)); return; }
      var ui = ranges[k] || [k, 0, 1, 0.01];
      var line = document.createElement('div'); line.className = 'as-fxline';
      var lab = document.createElement('span'); lab.className = 'as-fxlab'; lab.textContent = ui[0];
      var rng = document.createElement('input'); rng.type = 'range'; rng.min = ui[1]; rng.max = ui[2]; rng.step = ui[3]; rng.value = target[k];
      var nb = document.createElement('input'); nb.type = 'number'; nb.className = 'as-fxnum'; nb.min = ui[1]; nb.max = ui[2]; nb.step = ui[3]; nb.value = target[k];
      var set = function (v) {
        var n = Number(v); if (!isFinite(n)) return;
        target[k] = n; rng.value = n; nb.value = n;
        var s = st(); if (s && s.fx === sel) window.__AS.applyToJson();
        replayCurrent();   // ayar değişti → önizleme anında yenisini gösterir (v33 düzeltmesi)
      };
      rng.oninput = function () { set(rng.value); };
      nb.onchange = function () { set(nb.value); };
      line.appendChild(lab); line.appendChild(rng); line.appendChild(nb);
      paramsEl.appendChild(line);
    });
    if (EIAnim.FX_DEFAULTS[sel]) window.__AS.soundRows(paramsEl, target, changed);
  }

  // Seçili katmanın mevcut atamalarını özetler
  function updateNow() {
    var s = st();
    if (!s) { nowEl.textContent = 'Figma’da bir katman seç.'; return; }
    var parts = [];
    parts.push(s.fx ? 'efekt: ' + ((window.__AS.FX_LABEL[s.fx]) || s.fx) + (s.picks.length ? ' · ' + s.picks.length + ' simge' : '') : 'efekt yok');
    Object.keys(s.anims).forEach(function (c) { parts.push(c + ': ' + ((ANIM_UI_NAMES[s.anims[c]] || {}).name || s.anims[c])); });
    nowEl.textContent = (hasRows() ? 'Bu katmanda → ' : 'Seçimde (dışa aktarınca uygulanır) → ') + parts.join(' · ');
  }

  function fillLayers() {
    var rows = rowsNow();
    var keep = layer;
    layerSel.innerHTML = '';
    if (!rows.length) {
      layer = -1; var o = document.createElement('option'); o.value = '-1';
      o.textContent = window.__selName ? 'Seçili: ' + window.__selName : 'Figma’da bir katman seç';
      layerSel.appendChild(o); return;
    }
    rows.forEach(function (r, i) {
      var o = document.createElement('option'); o.value = i; o.textContent = r.name + '  ·  ' + r.cls;
      layerSel.appendChild(o);
    });
    if (keep < 0 || keep >= rows.length) {
      layer = 0;
      for (var i = 0; i < rows.length; i++) { if (rows[i].cls === 'TextButton' || rows[i].cls === 'ImageButton') { layer = i; break; } }
    }
    layerSel.value = String(layer);
  }

  function renderList() {
    list.innerHTML = '';
    if (mode === 'anim') {
      var ids = Object.keys(ANIM_UI_NAMES).filter(function (id) {
        var m = ANIM_UI_NAMES[id];
        return (!catSel.value || m.cat === catSel.value) && (!qIn.value || (m.name + id).toLowerCase().indexOf(qIn.value.toLowerCase()) !== -1);
      }).sort(function (a, b) { return ANIM_UI_NAMES[b].beauty - ANIM_UI_NAMES[a].beauty; });
      countEl.textContent = ids.length + ' animasyon';
      ids.forEach(function (id) {
        var m = ANIM_UI_NAMES[id], b = document.createElement('button');
        b.className = 'kt-row' + (sel === id ? ' on' : '');
        b.textContent = m.name;
        var sm = document.createElement('small'); sm.textContent = m.cat + ' · ' + (m.trig || '') + ' · ' + m.dur + ' sn';
        b.appendChild(sm);
        b.onclick = function () { sel = id; renderList(); playAnim(id); updateButtons(); };
        b.onmouseenter = function () { playAnim(id); };
        b.onmouseleave = function () { if (sel) playAnim(sel); };
        list.appendChild(b);
      });
    } else if (mode === 'icon') {
      var items = EKSTRA_INDEX.filter(function (ic) {
        return (!catSel.value || ic.cat === catSel.value) && (!qIn.value || (ic.label + ic.id).toLowerCase().indexOf(qIn.value.toLowerCase()) !== -1);
      });
      countEl.textContent = items.length + ' simge';
      var grid = document.createElement('div'); grid.className = 'kt-grid';
      items.slice(0, 240).forEach(function (ic) {
        var b = document.createElement('button');
        var picked = st() && st().picks.indexOf(ic.id) !== -1;
        b.className = 'kt-icon' + (sel === ic.id ? ' on' : '') + (picked ? ' picked' : '');
        b.title = ic.label;
        var im = document.createElement('img'); im.src = EKSTRA_THUMBS[ic.id]; im.alt = ic.label;
        b.appendChild(im);
        b.onclick = function () { sel = ic.id; renderList(); showIcon(ic.id); updateButtons(); };
        grid.appendChild(b);
      });
      list.appendChild(grid);
    } else {
      countEl.textContent = FX_KINDS.length + ' efekt';
      FX_KINDS.forEach(function (f) {
        var b = document.createElement('button');
        var applied = st() && st().fx === f[0];
        b.className = 'kt-row' + (sel === f[0] ? ' on' : '') + (applied ? ' picked' : '');
        b.textContent = f[1];
        var sm = document.createElement('small'); sm.textContent = '_' + f[0] + (applied ? ' · bu katmanda uygulu' : '');
        b.appendChild(sm);
        b.onclick = function () { sel = f[0]; renderList(); playFx(f[0]); renderParams(); updateButtons(); };
        list.appendChild(b);
      });
    }
  }

  function updateButtons() {
    var row = curRow();
    var s0 = st();
    applyBtn.style.display = '';
    if (mode === 'icon') {
      insertBtn.style.display = '';
      applyBtn.disabled = !(row && sel);
      applyBtn.textContent = 'Efekt olarak kullan';
      insertBtn.disabled = !(row && sel);
      insertBtn.textContent = 'İçeri ekle';
    } else {
      insertBtn.style.display = 'none';
      applyBtn.disabled = !row || !sel;
      if (mode === 'anim') applyBtn.textContent = sel ? 'Uygula: ' + ((ANIM_UI_NAMES[sel] || {}).name || sel) : 'Uygula';
      else applyBtn.textContent = sel ? 'Uygula: ' + ((FX_KINDS.filter(function (x) { return x[0] === sel; })[0] || [sel, sel])[1]) : 'Uygula';
    }
    removeBtn.style.display = (mode === 'fx' && s0 && s0.fx) ? '' : 'none';
    updateNow();
  }

  function setMode(m) {
    mode = m; sel = null; draft = draft || {};
    ['anim', 'icon', 'fx'].forEach(function (k) { $('kt-t-' + k).classList.toggle('on', k === m); });
    var names = m === 'anim' ? Array.from(new Set(Object.keys(ANIM_UI_NAMES).map(function (id) { return ANIM_UI_NAMES[id].cat; }))).sort()
              : m === 'icon' ? Array.from(new Set(EKSTRA_INDEX.map(function (ic) { return ic.cat; }))).sort() : [];
    catSel.innerHTML = '';
    var o0 = document.createElement('option'); o0.value = ''; o0.textContent = 'Tümü'; catSel.appendChild(o0);
    names.forEach(function (c) { var o = document.createElement('option'); o.value = c; o.textContent = c; catSel.appendChild(o); });
    catSel.style.display = m === 'fx' ? 'none' : '';
    qIn.style.display = m === 'fx' ? 'none' : '';
    clearBox(); say(''); paramsEl.innerHTML = '';
    renderList(); updateButtons();
  }

  // Uygula / ekle / kaldır — tasarım dışa aktarılmış olsun ya da olmasın çalışır
  applyBtn.onclick = function () {
    var row = curRow();
    if (!row) { say('Önce Figma’da bir katman seç.'); return; }
    var live = hasRows(), tgt = row.name, tail = live ? '' : ' · dışa aktarınca uygulanır';
    if (mode === 'anim' && sel) {
      var cat = CAT_MAP[(ANIM_UI_NAMES[sel] || {}).cat];
      if (!cat) { say('Bu animasyon kategorisi katmana uygulanamıyor.'); return; }
      pendPut({ t: 'anim', id: sel, cat: cat, target: tgt });
      if (live) window.__AS.setAnim(layer, sel, cat);
      say('Uygulandı: ' + ((ANIM_UI_NAMES[sel] || {}).name || sel) + ' → ' + tgt + tail);
    } else if (mode === 'fx' && sel) {
      var dr = draft[sel] ? JSON.parse(JSON.stringify(draft[sel])) : null;
      pendPut({ t: 'fx', id: sel, target: tgt, params: dr });
      if (live) {
        window.__AS.setFx(layer, sel);
        var target = draft[sel];
        if (target) { var s1 = st(); if (s1 && s1.params) Object.keys(target).forEach(function (k) { s1.params[k] = target[k]; }); window.__AS.applyToJson(); }
      }
      say('Uygulandı: efekt ' + sel + ' → ' + tgt + tail);
    } else if (mode === 'icon' && sel) {
      var cur = st();
      var has = cur.picks.indexOf(sel) !== -1;
      if (!has && cur.picks.length >= 4) { say('En çok 4 simge seçilebilir; birini kaldır.'); return; }
      var note = '';
      if (!cur.fx) {                               // efekt yoksa varsayılan yağmur efekti otomatik eklenir
        pendPut({ t: 'fx', id: 'fall', target: tgt });
        if (live) window.__AS.setFx(layer, 'fall');
        note = ' (yağmur efekti otomatik eklendi; Efektler sekmesinden değiştirebilirsin)';
      }
      if (has) pendDrop(function (o) { return o.t === 'pick' && o.id === sel && o.target === tgt; });
      else pendPut({ t: 'pick', id: sel, target: tgt });
      if (live) window.__AS.toggleIcon(layer, sel);
      say((has ? 'Efektten çıkarıldı: ' : 'Efekt resmi olarak eklendi: ') + sel + ' → ' + tgt + note + tail);
    }
    renderList(); updateButtons(); if (mode === 'fx') renderParams();
  };
  insertBtn.onclick = function () {
    var row = curRow();
    if (!row || !sel) return;
    var o = { t: 'insert', id: sel, target: row.name };
    if (pendHas(o)) { say('Bu simge zaten eklendi: ' + sel + ' → ' + row.name); return; }
    pendPut(o);
    if (hasRows()) {
      var ok = window.__AS.addIcon(layer, sel);
      say(ok ? 'İçeri eklendi: ' + sel + ' → ' + row.name : 'Eklenemedi: ' + sel);
    } else say('İçeri eklenecek: ' + sel + ' → ' + row.name + ' · dışa aktarınca uygulanır');
    updateButtons();
  };
  removeBtn.onclick = function () {
    var row = curRow();
    if (!row) return;
    pendDrop(function (o) { return o.target === row.name && (o.t === 'fx' || o.t === 'pick'); });
    if (hasRows()) window.__AS.setFx(layer, null);
    say('Efekt kaldırıldı: ' + row.name);
    renderList(); updateButtons(); renderParams();
  };

  layerSel.onchange = function () {
    layer = Number(layerSel.value);
    var s = st();
    if (mode === 'fx' && sel) { renderParams(); playFx(sel); }
    else if (mode === 'anim' && sel) playAnim(sel);
    else { clearBox(); layerEl(curRow()); }
    renderList(); updateButtons();
  };
  $('kt-t-anim').onclick = function () { setMode('anim'); };
  $('kt-t-icon').onclick = function () { setMode('icon'); };
  $('kt-t-fx').onclick = function () { setMode('fx'); };
  catSel.onchange = renderList;
  qIn.oninput = renderList;
  playBtn.onclick = function () {
    if (mode === 'anim' && sel) playAnim(sel);
    else if (mode === 'fx' && sel) playFx(sel);
    else if (mode === 'icon' && sel) showIcon(sel);
  };
  // Panelde bir animasyon seçilince: katman seçilir, animasyon o öğede canlı oynar
  window.__ktPreviewAnim = function (row, id) {
    if (!window.__AS || row == null || !id) return;
    layer = row;
    fillLayers();
    setMode('anim');
    sel = id; renderList(); playAnim(id); updateButtons(); renderParams();
  };
  function replayCurrent() {
    if (mode === 'anim' && sel) playAnim(sel);
    else if (mode === 'fx' && sel) playFx(sel);
    else if (mode === 'icon' && sel) showIcon(sel);
    else { clearBox(); layerEl(curRow()); }
  }
  window.__ktRepaint = replayCurrent;
  window.__ktRefresh = function () { fillLayers(); renderList(); updateButtons(); renderParams(); replayCurrent(); };

  fillLayers();
  setMode('anim');
  clearBox(); layerEl(curRow());
  if (!rowsNow().length) say('Figma’da bir katman seç; animasyon, efekt ve ikonu hemen önizleyip uygulayabilirsin.');
})();
