#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAPI: Figma → JSON → Studio eklentisi → LocalScript → (sahte) Roblox  [v33 aktarım zinciri]

  Amaç: "Roblox eklentisine aktarma" adımının yeni animasyon/efektlerle uçtan uca çalıştığını kanıtlamak.

  1) FIGMA (gerçek code.js, sahte Figma): panel/aksiyon etiketleri dışa aktarılır (tests/figma_mock.js)
  2) PANEL SÖZLEŞMESİ: asistan_panel.js'in yazdığı JSON biçimi kaynaktan doğrulanır
     (doc.anims["_Animasyon N"] = {src, cat, trig, tracks} · düğüm.anim = {show, hide, hover, press, loop, selA, delay, fx, params, fxImages})
  3) KÜTÜPHANE: animasyon track'leri GERÇEK çalışma zamanından (assistant/runtime/js/ei-anim.js, EIAnim.getAnim) alınır
  4) EKLENTİ (gerçek .lua kaynağı): JSON'daki her animasyon alanı bağlamaya kopyalanır, panel EI_Panel alır,
     LocalScript EIAnim.buildSourceSpec ile üretilir, rbxmx gömülü modüllerle senkron
  5) SAHTE ROBLOX: üretilen LocalScript koşar — panel yumuşak açılır, çıkış animasyonu biter → gizlenir,
     döngü animasyonu (fx_*) döner, geçiş/metin girişleri oynar, efekt ayarları (Süre/Kaç tane) uygulanır

  Not: Bu kapı, Figma panelinin tarayıcı tarafını (jsdom) koşmaz; onun yerine panelin JSON sözleşmesini
  kaynak üzerinden doğrular ve tam o biçimde JSON üretir. Tarayıcı tarafı ayrıca elle (jsdom koşumu) doğrulandı.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "assistant", "tools"))
sys.path.insert(0, os.path.join(ROOT, "roblox-studio-plugin"))
import build_anim_lua as B  # noqa: E402
import build_rbxmx  # noqa: E402
import verify_anim as V  # noqa: E402
from verify_anim_spec import lua_val  # noqa: E402

CODE_JS = os.path.join(ROOT, "figma", "code.js")
PANEL_JS = os.path.join(ROOT, "figma", "asistan_panel.js")
PLUGIN_LUA = os.path.join(ROOT, "roblox-studio-plugin", "EasyImportStudioPlugin.lua")
VENDOR = os.path.join(ROOT, "assistant", "tools", "vendor")

# ---------------------------------------------------------------- Figma dışa aktarımı (gerçek code.js)
EXPORT_JS = r"""
'use strict';
const path = require('path');
const fs = require('fs');
const M = require(%(mock)s);
const kids = [
  M.txt('2:2', 'Baslik_Text', 20, 20, 'Merhaba'),
  M.frame('2:3', 'Hazine_fall_Frame', 20, 80, 200, 120, [M.txt('2:4', 'Icerik', 10, 8, 'Odul')]),
  M.frame('2:5', 'Menu_panel', 240, 80, 140, 160, [
    M.frame('2:6', 'Kapat_close', 10, 10, 60, 30, []),
    M.frame('2:7', 'Odul_shine_Frame', 10, 50, 120, 40, []),
  ]),
  M.frame('2:8', 'Ac_open:Menu_button', 20, 220, 120, 40, []),
];
const root = M.frame('2:1', 'Ana_Panel', 0, 0, 420, 320, kids);
(async () => {
  const exp = await M.runExport(%(code)s, { root: root, sizes: {} });
  fs.writeFileSync(__dirname + '/out.json', exp.result.json);
})();
"""

# ---------------------------------------------------------------- kütüphane track'leri (gerçek ei-anim.js)
TRACKS_JS = r"""
'use strict';
const path = require('path');
const EI = require(process.argv[2]);
const ids = JSON.parse(process.argv[3]);
const out = {};
ids.forEach((id) => { const a = EI.getAnim(id); if (a) out[id] = { cat: a.cat, trig: a.trig, tracks: a.tracks }; });
process.stdout.write(JSON.stringify(out));
"""


def run_node(script, args, cwd=None):
    """Node betiğini koşar; stdout + yazılan dosya yolunu döndürür."""
    tmp = tempfile.mkdtemp(prefix="xfer")
    path = os.path.join(tmp, "s.js")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(script)
    env = dict(os.environ, NODE_PATH=VENDOR)
    p = subprocess.run(["node", path] + args, capture_output=True, text=True, cwd=cwd or ROOT, env=env)
    if p.returncode != 0:
        raise RuntimeError("node hatası: %s\n%s" % (p.stdout[-2000:], p.stderr[-2000:]))
    return p.stdout, tmp


# Sahte Roblox: task.delay kuyruğu (panel kapanışı) + task.wait günlüğü (yağmur aralığı) + TweenService gözlemi
EXTRA = r"""
local PENDING = {}
task.delay = function(t, f) PENDING[#PENDING + 1] = { t = t, f = f } end
local WAITS = {}
-- Kaç parça doğduğunu sayabilmek için birkaç bekleme adımına izin verilir; sonra döngü kesilir.
task.wait = function(t) WAITS[#WAITS + 1] = t or 0; if #WAITS >= 8 then error("STOP") end end
local function runPending()
  local p = PENDING
  PENDING = {}
  for _, e in ipairs(p) do log("DELAY", e.t); e.f() end
end
do
  local base = tweenSvc.Create
  tweenSvc.Create = function(self2, obj, info, goal)
    if obj.Position and obj.Position.X then log("FROM", obj.Name, tostring(obj.Position.X.Scale)) end
    return base(self2, obj, info, goal)
  end
end
local function ff(self, n) for _, c in ipairs(self.children) do if c.Name == n then return c end end return nil end
local function isDesc(self, anc) local p = self.Parent while p do if p == anc then return true end p = p.Parent end return false end
local function runClicks(o) for _, f in ipairs(o.MouseButton1Click.fns) do f() end end
local function kids(o) return o.children end
-- Parlama bandı gradyanı için eksik sahte türler (gerçek Roblox API'si)
NumberSequence = { new = function(t) return t end }
NumberSequenceKeypoint = { new = function(a, b) return { a, b } end }
ColorSequence = { new = function(c) return c end }
-- Şablon kopyası: mock'ta Clone yok → adı koruyan kopya (gerçekte Instance:Clone)
local function cloneOf(tpl, nm) return makeInst(tpl.ClassName, nm or tpl.Name) end
"""


def main():
    fails = []

    def check(c, m):
        print(("  [OK] " if c else "  [FAIL] ") + m)
        if not c:
            fails.append(m)

    mock = os.path.join(ROOT, "tests", "figma_mock.js")
    _out, tmp = run_node(EXPORT_JS % {"mock": json.dumps(mock), "code": json.dumps(CODE_JS)}, [])
    doc = json.load(open(os.path.join(tmp, "out.json"), encoding="utf-8"))

    print("== 1) Figma dışa aktarımı (gerçek code.js)")
    def find(prefix):
        def w(n):
            if str(n.get("name", "")).startswith(prefix):
                return n
            for c in (n.get("children") or []):
                r = w(c)
                if r:
                    return r
        return w(doc["root"])

    menu, kapat, ac = find("Menu_panel"), find("Kapat_close"), find("Ac_open")
    check(menu is not None and menu.get("panel") is True, "Menu_panel panel olarak işaretlendi (_close içeriyor)")
    check((kapat or {}).get("action", {}).get("kind") == "close", "Kapat_close → kapatma aksiyonu")
    check((ac or {}).get("action", {}).get("kind") == "open", "Ac_open:Menu_button → açma aksiyonu")

    print("== 2) Figma paneli JSON sözleşmesi (asistan_panel.js kaynağı)")
    psrc = open(PANEL_JS, encoding="utf-8").read()
    check("specs[names[id]] = { src: id, cat: def ? def.cat : '', trig: def ? def.trig : '', tracks: def ? def.tracks : [] };" in psrc,
          "panel animasyon tanımını {src, cat, trig, tracks} olarak yazıyor (track'ler çalışma zamanından)")
    check("{ giris: 'show', cikis: 'hide', hover: 'hover', basma: 'press', dongu: 'loop', secim: 'selA' }" in psrc,
          "panel yuvaları JSON anahtarlarına birebir çevriliyor (cikis→hide dâhil)")
    check("allImageFiles()" in psrc or "designImages()" in psrc, "envanter: dışa aktarılan tasarım resimleri kullanılıyor")
    check("String(f.file).replace(/\.png$/i, '')" in psrc,
          "envanter adı = ZIP dosya adı (Studio'da 'İsimden eşleştir' bu adla bağlar)")
    base = open(os.path.join(ROOT, "figma", "ui.base.html"), encoding="utf-8").read()
    check("allImageFiles()" in base,
          "ZIP (tümünü indir), envanterin kaynağı olan tasarım resimlerini de içerir")

    print("== 3) Animasyon track'leri gerçek çalışma zamanından (ei-anim.js)")
    ids = ["panel_slide_left_soft", "exit_slide_left", "enter_fade", "fx_aura_rotate_pulse",
           "page_slide_left", "text_typewriter"]
    tout, _ = run_node(TRACKS_JS, [os.path.join(ROOT, "assistant", "runtime", "js", "ei-anim.js"), json.dumps(ids)])
    tracks = json.loads(tout)
    for aid in ids:
        check(aid in tracks and len(tracks[aid]["tracks"]) > 0, "%s: track'ler geldi (%d)" % (aid, len(tracks.get(aid, {}).get("tracks", []))))

    print("== 4) Panelin yazacağı JSON üretiliyor (aktarım girdisi)")
    specs = {}
    for i, aid in enumerate(ids, 1):
        specs["_Animasyon %d" % i] = {"src": aid, "cat": tracks[aid]["cat"], "trig": tracks[aid]["trig"],
                                      "tracks": tracks[aid]["tracks"]}
    doc["anims"] = specs
    # Düğüm seçimleri (panel applyToJson ile aynı alanlar)
    find("Menu_panel")["anim"] = {"show": "_Animasyon 1", "hide": "_Animasyon 2"}
    find("Ac_open")["anim"] = {"show": "_Animasyon 5"}                       # Geçiş kategorisi → giriş yuvası
    find("Baslik_Text")["anim"] = {"show": "_Animasyon 6"}                   # Metin kategorisi → giriş yuvası
    find("Hazine_fall_Frame")["anim"] = {"loop": "_Animasyon 4", "fx": "fall",
                                         "params": {"count": 8, "seconds": 4, "fade": 0.5, "smallest": 0.5,
                                                    "largest": 1.2, "loop": 1},
                                         "fxImages": ["Hazine_Kart_1-9"]}
    find("Kapat_close")["anim"] = {"hide": "_Animasyon 2"}
    find("Odul_shine_Frame")["anim"] = {"fx": "shine",
                                        "params": {"sweep": 2, "pause": 0.5, "width": 0.4, "tilt": 25,
                                                   "strength": 0.6, "loop": 1},
                                        "fxImages": ["ei_shine_rectangle"]}
    check(len(doc["anims"]) == 6, "tanımlar JSON'a girdi (6 animasyon)")

    print("== 5) Studio eklentisi: JSON → bağlama (gerçek .lua)")
    lua = open(PLUGIN_LUA, encoding="utf-8").read()
    for f in ("show = a.show", "hide = a.hide", "hover = a.hover", "press = a.press", "loop = a.loop",
              "selA = a.selA", "delay = a.delay", "fx = a.fx", "params = a.params"):
        check(f in lua, "bağlamaya kopyalanıyor: %s" % f)
    check('inst:SetAttribute("EI_Panel", true)' in lua and "table.insert(panelList, animIdCounter)" in lua,
          "panel öğesi EI_Panel alır ve panels listesine girer")
    check("EIAnim.buildSourceSpec(animBindings, doc.anims or {}" in lua,
          "LocalScript, JSON'daki tanımlarla (doc.anims) üretilir")
    check('tplImg:SetAttribute("EI_FxTpl", true)' in lua and 'for _, nm in ipairs(item.anim.fxImages)' in lua,
          "envanter resimleri (fxImages) Studio'da gizli şablon ImageLabel olur (ad = dosya adı)")

    print("== 6) Paket: rbxmx gömülü modüllerle senkron ve yeni animasyonları içeriyor")
    p = subprocess.run([sys.executable, os.path.join(ROOT, "roblox-studio-plugin", "build_rbxmx.py"), "--check"],
                       capture_output=True, text=True, cwd=os.path.join(ROOT, "roblox-studio-plugin"))
    check(p.returncode == 0 and "SENKRON" in p.stdout, "build_rbxmx --check: %s" % p.stdout.strip().splitlines()[-1][:90])
    mods = build_rbxmx.module_block()
    check(all(k in mods for k in ("panel_slide_left_soft", "exit_slide_left", "fx_aura_rotate_pulse")),
          "gömülü modüllerde v33 animasyonları var")

    print("== 7) Sahte Roblox: üretilen LocalScript oynar")
    spec_lua = lua_val({k: {"tracks": v["tracks"]} for k, v in specs.items()})
    prog = (
        "local EIAnim = (function()\n" + V.module_src() + "\nend)()\n"
        + V.MOCK + "\n" + EXTRA
        + "ROOT.children = {}\n"
        + "local function mk(cls, name, id, parent)\n"
        + "  local o = makeInst(cls, name); o.attrs.EI_Id = id; o.Size = UDim2.new(0, 200, 0, 120)\n"
        + "  o.FindFirstChild = ff; o.IsDescendantOf = isDesc; o.GetChildren = kids\n"
        + "  o.MouseButton1Click = { fns = {}, Connect = function(self, f) self.fns[#self.fns + 1] = f end }\n"
        + "  addChild(parent or ROOT, o); return o\n"
        + "end\n"
        + "local ANA = mk('Frame', 'Ana_Panel', 1)\n"
        + "local BASLIK = mk('TextLabel', 'Baslik_Text', 2); BASLIK.Text = 'Merhaba'\n"
        + "local HAZINE = mk('Frame', 'Hazine_fall_Frame', 3)\n"
        + "HAZINE.GetChildren = function(self) return self.children end\n"
        + "local TPL = mk('ImageLabel', 'Hazine_Kart_1-9', 9, HAZINE); TPL.attrs.EI_FxTpl = true; TPL.Visible = false; TPL.Image = 'rbxassetid://1'\n"
        + "TPL.GetChildren = function(self) return self.children end\n"
        + "TPL.Clone = function(self) return cloneOf(self, self.Name) end\n"
        + "local MENU = mk('Frame', 'Menu_panel', 5); MENU.Visible = false; MENU.attrs.EI_Panel = true\n"
        + "local KAPAT = mk('TextButton', 'Kapat_close', 6, MENU)\n"
        + "local PARLAK = mk('Frame', 'Odul_shine_Frame', 7)\n"
        + "local AC = mk('TextButton', 'Ac_open:Menu_button', 8)\n"
        + "local BIND = {\n"
        + "  { id = 5, show = '_Animasyon 1', hide = '_Animasyon 2' },\n"
        + "  { id = 8, show = '_Animasyon 5' },\n"
        + "  { id = 2, show = '_Animasyon 6' },\n"
        + "  { id = 3, loop = '_Animasyon 4', fx = 'fall', params = { count = 8, seconds = 4, fade = 0.5, smallest = 0.5, largest = 1.2, loop = 1 } },\n"
        + "  { id = 6, hide = '_Animasyon 2' },\n"
        + "  { id = 7, fx = 'shine', params = { sweep = 2, pause = 0.5, width = 0.4, tilt = 25, strength = 0.6, loop = 1 } } }\n"
        + "local SPECS = " + spec_lua + "\n"
        + "local SRC = EIAnim.buildSourceSpec(BIND, SPECS, { actions = { { id = 8, kind = 'open', target = 5 },\n"
        + "  { id = 6, kind = 'close', target = nil } }, panels = { 5 }, groups = {} })\n"
        + "local chunk, err = load(SRC, 'EI_Animator')\n"
        + "if not chunk then io.write('LOADERR|' .. tostring(err) .. '\\n') return end\n"
        + "chunk()\n"
        + "log('VIS0', tostring(MENU.Visible))\n"
        + "runClicks(AC)\n"
        + "log('VIS1', tostring(MENU.Visible))\n"
        + "runClicks(KAPAT)\n"
        + "log('VIS2', tostring(MENU.Visible))\n"
        + "runPending()\n"
        + "log('VIS3', tostring(MENU.Visible))\n"
        + "local pieces = 0\n"
        + "for _, l in ipairs(LOG) do if l:find('TWEEN|Hazine_Kart_1-9|', 1, true) and l:find('|Position|', 1, true) then pieces = pieces + 1 end end\n"
        + "log('WAIT', tostring(WAITS[1]))\n"
        + "log('PIECES', tostring(pieces))\n"
        + "for _, l in ipairs(LOG) do io.write(l, '\\n') end\n"
    )
    out = V.run_lua_program(prog)
    check("LOADERR" not in out, "üretilen LocalScript derlenir ve yüklenir (Studio'da çalışacak betik)")
    lines = [ln for ln in out.split("\n") if ln.startswith(("TWEEN|", "VIS", "DELAY|", "FROM|", "WAIT|", "PIECES|"))]

    def val(prefix):
        for ln in lines:
            if ln.startswith(prefix):
                return ln.split("|", 1)[1]
        return None

    menu_pos = [ln for ln in lines if ln.startswith("TWEEN|Menu_panel|") and "|Position|" in ln]
    check(any("|0.55|Quint|Out|" in ln for ln in menu_pos), "panel yumuşak açılış tween'i (0.55 sn, Quint Out)")
    froms = [ln for ln in lines if ln.startswith("FROM|Menu_panel|")]
    check(bool(froms) and froms[0].endswith("|-1"), "panel soldan gelir (ölçek -1 → 0): %s" % (froms[:1] or ["-"]))
    check(val("VIS0") == "false" and val("VIS1") == "true", "panel başlangıçta kapalı, _open ile açıldı")
    close_pos = [ln for ln in menu_pos if "|0.3|" in ln]
    check(bool(close_pos), "kapanışta çıkış animasyonu oynar (exit_slide_left 0.3 sn)")
    check(val("VIS2") == "true" and val("VIS3") == "false", "panel animasyon bitince gizlendi (VIS true → false)")
    check(any(ln.startswith("DELAY|0.3") for ln in lines), "gizleme, tween süresi kadar sonra (task.delay 0.3)")
    fade = [ln for ln in lines if ln.startswith("TWEEN|Menu_panel|") and "Transparency|" in ln]
    check(bool(fade) and any("|BackgroundTransparency|0|" in ln for ln in fade),
          "açılışta sönerek gelme (Frame'de Transparency → BackgroundTransparency, hedef 0): %s" % (fade[:1] or ["-"]))
    check(any(ln.startswith("TWEEN|Ac_open:Menu_button|") and "|Position|" in ln for ln in lines),
          "geçiş animasyonu (page_slide_left) butonda oynar")
    check(any(ln.startswith("TWEEN|Baslik_Text|") and "|MaxVisibleGraphemes|" in ln for ln in lines),
          "metin animasyonu (text_typewriter) yazıda oynar")
    rot = [ln for ln in lines if ln.startswith("TWEEN|Hazine_fall_Frame|") and "|Rotation|" in ln]
    rf = rot[0].split("|") if rot else []
    check(bool(rot) and rf[4] == "360" and rf[5] == "8" and rf[8] == "-1",
          "döngü animasyonu (fx_aura_rotate_pulse): 360°, 8 sn, rep = -1 (sonsuz): %s" % (rot[:1] or ["-"]))
    check(val("WAIT") is not None and abs(float(val("WAIT")) - 0.5) < 1e-9,
          "efekt ayarı uygulanır: yağmur aralığı = Süre ÷ Kaç tane = 4 ÷ 8 = 0.5 sn (%s)" % val("WAIT"))
    check(int(val("PIECES") or 0) >= 3,
          "yağmur parçaları ENVANTERDEKİ kendi resmimizden kopyalanır (%s parça: Hazine_Kart_1-9)" % val("PIECES"))
    shine = [ln for ln in lines if ln.startswith("TWEEN|") and ln.split("|")[5:7] == ["2", "Quad"]]
    check(bool(shine), "Rectangle parlama ayarı uygulanır (Süpürme = 2 sn, Quad InOut): %s" % (shine[:1] or ["-"]))

    print("== 8) TÜM kütüphane aktarılabilir mi? (her animasyon → JSON → LocalScript → sahte Roblox)")
    ui = open(os.path.join(ROOT, "assistant", "runtime", "js", "ei-animlib-ui.js"), encoding="utf-8").read()
    all_ids = sorted(json.loads(ui[ui.index("=") + 1:ui.rindex(";")].strip()).keys())
    ta, _ = run_node(TRACKS_JS, [os.path.join(ROOT, "assistant", "runtime", "js", "ei-anim.js"), json.dumps(all_ids)])
    all_tracks = json.loads(ta)
    check(len(all_tracks) == len(all_ids) == 116, "kütüphanedeki 116 animasyonun tamamı için track alındı")
    _out2, tmp2 = run_node(EXPORT_JS % {"mock": json.dumps(mock), "code": json.dumps(CODE_JS)}, [])
    doc2 = json.load(open(os.path.join(tmp2, "out.json"), encoding="utf-8"))
    specs2 = {}
    for i, aid in enumerate(all_ids, 1):
        specs2["_Animasyon %d" % i] = {"src": aid, "cat": all_tracks[aid]["cat"], "trig": all_tracks[aid]["trig"],
                                       "tracks": all_tracks[aid]["tracks"]}
    spec2_lua = lua_val({k: {"tracks": v["tracks"]} for k, v in specs2.items()})
    bind2_lua = "local BIND = {\n" + ",\n".join(
        "  { id = %d, show = '_Animasyon %d' }" % (i, i) for i in range(1, len(all_ids) + 1)) + " }\n"
    prog2 = (
        "local EIAnim = (function()\n" + V.module_src() + "\nend)()\n"
        + V.MOCK + "\n" + EXTRA
        + "ROOT.children = {}\n"
        + "local function mk(cls, name, id)\n"
        + "  local o = makeInst(cls, name); o.attrs.EI_Id = id; o.Size = UDim2.new(0, 200, 0, 120)\n"
        + "  o.FindFirstChild = ff; o.IsDescendantOf = isDesc; o.Text = 'Merhaba dunya'\n"
        + "  addChild(ROOT, o); return o\n"
        + "end\n"
        + "for i = 1, %d do mk('Frame', 'Oge' .. i, i) end\n" % len(all_ids)
        + bind2_lua
        + "local SRC = EIAnim.buildSourceSpec(BIND, " + spec2_lua + ", { actions = {}, panels = {}, groups = {} })\n"
        + "local chunk, err = load(SRC, 'EI_Animator')\n"
        + "if not chunk then io.write('LOADERR|' .. tostring(err) .. '\\n') return end\n"
        + "chunk()\n"
        + "local n, own, seen = 0, {}, {}\n"
        + "for _, l in ipairs(LOG) do\n"
        + "  if l:sub(1, 6) == 'TWEEN|' then\n"
        + "    n = n + 1\n"
        + "    local full = l:match('^TWEEN|([^|]+)|')\n"
        + "    if full then seen[full] = true end\n"
        + "    local i = l:match('^TWEEN|Oge(%d+)|')\n"
        + "    if i then own[i] = true end\n"
        + "  end\n"
        + "end\n"
        + "local k, h = 0, 0\n"
        + "for _ in pairs(own) do k = k + 1 end\n"
        + "for _, nm in ipairs({ 'UIScale', 'UIStroke', 'UIGradient' }) do if seen[nm] then h = h + 1 end end\n"
        + "io.write('TOPLAM|' .. tostring(n) .. '|' .. tostring(k) .. '|' .. tostring(h) .. '\\n')\n"
    )
    out2 = V.run_lua_program(prog2)
    check("LOADERR" not in out2, "116 animasyonlu LocalScript derlenir (kesme yok)")
    tot = [ln for ln in out2.split("\n") if ln.startswith("TOPLAM|")]
    ntween = int(tot[0].split("|")[1]) if tot else 0
    nuniq = int(tot[0].split("|")[2]) if tot else 0
    expected = sum(len(all_tracks[a]["tracks"]) for a in all_ids)
    self_anims = sum(1 for a in all_ids if any(t["t"] == "self" for t in all_tracks[a]["tracks"]))
    nholders = int(tot[0].split("|")[3]) if tot else 0
    check(ntween == expected,
          "kütüphanedeki %d track'in TAMAMI oynar (%d tween; her track → bir tween)" % (expected, ntween))
    check(nuniq == self_anims,
          "kendi öğesinde oynayan animasyon: %d/%d (kalan %d yalnız tutucu öğe kullanır)"
          % (nuniq, self_anims, len(all_ids) - self_anims))
    check(nholders == 3,
          "tutucu öğeler de üretilir (UIScale/UIStroke/UIGradient: %d/3) — ölçek/kenarlık/gradyan animasyonları çalışır" % nholders)

    print("== 9) Efektler: Figma listesi ≡ Studio motoru")
    import re
    fx_list = re.findall(r"\['([a-z]+)', '[^']+'\]", re.search(r"var FX_KINDS = \[(.*?)\];", psrc, re.S).group(1))
    rout, _ = run_node("const E=require(process.argv[2]);process.stdout.write(JSON.stringify(Object.keys(E.FX_DEFAULTS)))",
                       [os.path.join(ROOT, "assistant", "runtime", "js", "ei-anim.js")])
    rt_fx = json.loads(rout)
    check(sorted(fx_list) == sorted(rt_fx) and len(fx_list) == 10,
          "Figma'daki 10 efekt ≡ çalışma zamanı varsayılanları (%s)" % ", ".join(fx_list))
    mods2 = build_rbxmx.module_block()
    fxblock = mods2[mods2.index("local function startFx"):]
    fxblock = fxblock[:fxblock.index("\nfor _, b in ipairs(BINDINGS) do")]
    missing = [k for k in fx_list if ('"%s"' % k) not in fxblock and ("%s = " % k) not in fxblock]
    check(not missing, "Studio motoru 10 efektin hepsini tanır (eksik: %s)" % (missing or "yok"))
    pk = re.search(r"var PIC_KINDS = \{(.*?)\};", psrc, re.S)
    pics = re.findall(r"(\w+):", pk.group(1)) if pk else []
    check(sorted(pics) == ["burst", "confetti", "fall", "orbit", "twinkle"],
          "kendi resmimizi (envanter) kullanabilen efektler: %s" % ", ".join(pics))

    print()
    if fails:
        print("SONUÇ: BAŞARISIZ (%d)" % len(fails))
        return 1
    print("SONUÇ: GEÇTİ — Figma → JSON → Studio eklentisi → LocalScript zinciri yeni animasyon/efektlerle çalışıyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
