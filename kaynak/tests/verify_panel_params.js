// KAPI: panel ayarları (v33, madde 2 "Süre") + envanter (madde 1) + panel animasyon yuvası (madde 3)
//  • fxPreviewPlan: efekt ayarları JS önizlemesine çevrilir (Süre / Kaç tane / Döngü … artık önizlemeyi değiştirir)
//  • Envanter: kendi resimlerimiz (tasarımdaki PNG'ler) efekt resmi olur; Roblox aktarımında sıfırlanır
//  • Panel öğeleri _open/_close ile giriş + çıkış (hide) animasyonu alır; üretilen ui.html bu kodu içerir
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');
const PANEL = path.join(ROOT, 'figma', 'asistan_panel.js');
const UI = path.join(ROOT, 'figma', 'ui.html');

let pass = 0;
function ok(cond, msg) { assert.ok(cond, msg); pass++; console.log('  [OK] ' + msg); }

// --- 1) fxPreviewPlan kaynaktan çıkarılıp gerçek FX_DEFAULTS ile koşturulur
const src = fs.readFileSync(PANEL, 'utf8');
const start = src.indexOf('function fxPreviewPlan(kind, p) {');
ok(start !== -1, 'asistan_panel.js içinde fxPreviewPlan bulundu');
let i = src.indexOf('{', start), depth = 0, end = -1;
for (let k = i; k < src.length; k++) {
  if (src[k] === '{') depth++;
  else if (src[k] === '}') { depth--; if (depth === 0) { end = k + 1; break; } }
}
ok(end > start, 'fxPreviewPlan gövdesi ayrıştırıldı');
const fnSrc = src.slice(start, end);

const rt = path.join(ROOT, 'assistant', 'runtime', 'js');
const ctx = { EIAnim: null, window: {}, Math: Math };
ctx.EIAnim = require(path.join(rt, 'ei-anim.js'));
vm.createContext(ctx);
vm.runInContext(fnSrc + '\n; fxPreviewPlan_ = fxPreviewPlan;', ctx);
const plan = ctx.fxPreviewPlan_;
ok(typeof plan === 'function', 'fxPreviewPlan koşturulabilir');

const a = plan('fall', { count: 20, seconds: 8, fade: 0.5, smallest: 0.4, largest: 1.6, loop: 0 });
ok(a.count === 20 && a.seconds === 8 && a.loop === false && a.fade === 0.5,
  'Süre/Kaç tane/Döngü önizleme planına geçer (count=20, seconds=8, loop kapalı)');
const b = plan('fall', {});
const d = ctx.EIAnim.FX_DEFAULTS.fall;
ok(b.count === d.count && b.seconds === d.seconds && b.loop === true,
  'ayar verilmezse FX_DEFAULTS kullanılır (kaç tane=' + b.count + ', süre=' + b.seconds + ')');
const c = plan('fall', { count: 999, seconds: 0.01 });
ok(c.count === 30 && c.seconds === 0.2, 'kaydırıcı sınırları kırpılır (kaç tane ≤ 30, süre ≥ 0.2)');
const sh = plan('shine', { sweep: 3, pause: 1, width: 0.2, strength: 0.5, tilt: 10, loop: 0 });
ok(sh.sweep === 3 && sh.pause === 1 && sh.width === 0.2 && sh.strength === 0.5 && sh.tilt === 10 && sh.loop === false,
  'süpürme/parlama ayarları da plana girer (shine)');
const orb = plan('orb', { scale: 2.5, pulse: 1.3 });
ok(orb.scale === 2.5 && orb.pulse === 1.3, 'orb çapı ve nefes büyüklüğü plana girer');
ok(plan('confetti', {}).count === ctx.EIAnim.FX_DEFAULTS.confetti.count,
  'konfeti varsayılanları tanımlı (Süre kaydırıcısı çıkar)');

// --- 2) Envanter: kendi resimlerimiz + aktarımda sıfırlama + panel animasyon yuvası
ok(/fxOwnPick/.test(src) && /Envanteri sıfırla/.test(src) && /Roblox aktarımında sıfırlanır/.test(src),
  'envanter: kendi resimlerim bölümü ve sıfırlama düğmesi var');
ok(/fxOwnPick = \{\};/.test(src) && /AS\.show|show: function/.test(src),
  'envanter yeni dışa aktarmada (Roblox aktarımı) sıfırlanır');
ok(/'cikis', 'hover', 'basma', 'dongu', 'secim'|cikis: 'hide'/.test(src) && /cikis: 'hide'/.test(src),
  'animasyon yuvaları çıkış (cikis → hide) içerir');
ok(/panel: !!node\.panel/.test(src), 'panel öğeleri decideRanked\'a panel bayrağıyla gider');

// --- 3) Kütüphanedeki HER animasyon katmana uygulanabilir mi? (madde 3: ekstra animasyon + efektler)
// Kütüphane kategorileri üreteçte yuvaya katlanır (fx→dongu, gecis/metin→giris); kütüphane kutusunun
// kategori listesi bu katlanmış hâldir. CAT_MAP her kategoriyi bir yuvaya bağlamalı, yoksa "uygulanamıyor" der.
const uiSrc = fs.readFileSync(path.join(rt, 'ei-animlib-ui.js'), 'utf8');
const uiNames = JSON.parse(uiSrc.slice(uiSrc.indexOf('=') + 1, uiSrc.lastIndexOf(';')).trim());
const cats = Array.from(new Set(Object.keys(uiNames).map((id) => uiNames[id].cat))).sort();
const catMapSrc = src.slice(src.indexOf('var CAT_MAP = '), src.indexOf('};', src.indexOf('var CAT_MAP = ')) + 2);
const CAT_MAP = vm.runInNewContext(catMapSrc + '; CAT_MAP');
const SLOTS = ['giris', 'cikis', 'hover', 'basma', 'dongu', 'secim'];
const unmapped = cats.filter((c) => SLOTS.indexOf(CAT_MAP[c]) === -1);
ok(unmapped.length === 0,
  'kütüphanedeki ' + cats.length + ' kategori de bir yuvaya bağlı (' + cats.join(', ') + ')');
ok(Object.keys(uiNames).length === 116,
  'kütüphane kutusu 116 çalıştırılabilir animasyon listeliyor');
// v33'te eklenen kayıtlar ve katlanan kategoriler listede mi?
[['panel_slide_left_soft', 'giris'], ['panel_slide_up_soft', 'giris'], ['panel_fade_soft', 'giris'],
 ['exit_slide_left', 'cikis'], ['exit_fade_soft', 'cikis'],
 ['fx_aura_rotate_pulse', 'dongu'], ['fx_rays_rotate', 'dongu'],
 ['page_slide_left', 'giris'], ['text_typewriter', 'giris']].forEach(function (pair) {
  var v = uiNames[pair[0]];
  ok(v && v.cat === pair[1], 'listede: ' + (v ? v.name : pair[0]) + ' → yuva ' + pair[1]);
});
ok(uiNames.panel_slide_left_soft.beauty >= 5 && uiNames.exit_slide_left.dur <= 0.4,
  'panel açılışı önerilen havuzda, çıkış girişten hızlı (0.3 sn ≤ 0.4)');
ok(cats.indexOf('durum') === -1, 'durum kategorisi (8 kayıt) üretime alınmadı — bilinçli kapsam');

// --- 4) Üretilen ui.html bu değişiklikleri içeriyor mu? (kaynak ↔ ürün senkronu)
const ui = fs.readFileSync(UI, 'utf8');
ok(ui.indexOf('function fxPreviewPlan(kind, p) {') !== -1, 'ui.html derlemesi fxPreviewPlan içeriyor');
ok(ui.indexOf('fxOwnPick') !== -1 && ui.indexOf('Envanteri sıfırla') !== -1, 'ui.html derlemesi envanteri içeriyor');
ok(ui.indexOf("cikis: 'hide'") !== -1, 'ui.html derlemesi cikis → hide eşlemesini içeriyor');
ok(ui.indexOf('panel: !!node.panel') !== -1, 'ui.html derlemesi panel bayrağını içeriyor');
ok(ui.indexOf('var CAT_MAP = { giris') !== -1 && ui.indexOf('FX: Aura Dönüş') !== -1,
  'ui.html derlemesi kütüphane listesini (fx/panel/page animasyonları) içeriyor');

console.log('\nSONUÇ: GEÇTİ — panel ayarları (Süre) önizlemeye geçer · envanter kendi resimlerimizi efekte bağlar · panel çıkış yuvası hazır (' + pass + ' kontrol)');
