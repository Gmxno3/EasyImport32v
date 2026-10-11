#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANİMASYON VERİ ÜRETİCİSİ — anim-library.json → runtime/lua/EIAnim.lua (veri bloğu)
                                   + runtime/js/ei-anim.js (veri bloğu)
                                   + runtime/js/ei-animlib-ui.js (kütüphane kutusu adları)

Yalnızca üretimde kullanılabilir kısmı alır:
  • kategori → çalışma zamanı yuvası: giris (show) · cikis (hide) · hover (mouseEnter) · basma (click)
    · dongu/dikkat (always) · secim (stateChange). "gecis" (sayfa/panel geçişi) ve "metin" giriş yuvasına,
    "fx" (döngülü resim efektleri) döngü yuvasına katlanır; bu üçü yalnız seçenek listelerinde görünür
    (genel sıralama havuzuna girmez: pool = "extra").
  • UIShadow hedefli tween'ler DIŞARIDA (karar L10: glow için UIShadow kullanılmaz)
  • desteklenen hedef/özellik/değer: t ∈ {self, UIScale, UIStroke, UIGradient, parent},
    p ∈ {Scale, Rotation, *Transparency, Thickness, Position, Size, Offset, MaxVisibleGraphemes,
         TextStrokeTransparency}, from/to ∈ {sayı, "cur", "len" (metnin uzunluğu), iki elemanlı liste}
  • u (birim): "scale" → Position: temel konuma göre ölçek farkı (1 = üst öğe genişliği kadar sağda),
    Size: UDim2.fromScale(v1,v2) · yok/"offset" → Position/Size: UDim2.fromOffset (piksel)
  • dl: sayı → sayı · "random:a:b" → {a,b} (çalışma anında rastgele) · "stagger:x" → 0
    (stagger tek öğe bağlamasında anlamsızdır; raporda sayılır)
  • bir animasyonun hiçbir track'i kalmazsa atılır.

Kullanım:
    python3 tools/build_anim_lua.py          # EIAnim.lua + ei-anim.js + ei-animlib-ui.js yazar (rapor basar)
    python3 tools/build_anim_lua.py --check  # yazmadan senkron mu? çıkış 0/1
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIB = os.path.join(ROOT, "anim", "anim-library.json")
LUA = os.path.join(ROOT, "runtime", "lua", "EIAnim.lua")
BEGIN = "-- <<EI_ANIM_DATA>>"
END = "-- <<END_EI_ANIM_DATA>>"

USED_CATS = {"giris": "show", "cikis": "hide", "hover": "mouseEnter", "basma": "click",
             "dongu": "always", "secim": "stateChange", "dikkat": "always",
             # katlanan kategoriler (v33): panel/sayfa geçişleri ve metin girişleri → giris, döngülü resim efektleri → dongu
             "gecis": "show", "metin": "show", "fx": "always"}
# Çalışma zamanı yuvasına katlanan kategoriler: yalnız seçenek listelerinde görünür, varsayılan seçilmez.
CAT_ALIAS = {"gecis": "giris", "metin": "giris", "fx": "dongu"}
EXTRA_CATS = set(CAT_ALIAS.keys())
ALLOWED_T = {"self", "UIScale", "UIStroke", "UIGradient", "parent"}
ALLOWED_P = {"Scale", "Rotation", "ImageTransparency", "BackgroundTransparency",
             "TextTransparency", "GroupTransparency", "Thickness", "Transparency",
             "Position", "Size", "Offset", "MaxVisibleGraphemes", "TextStrokeTransparency"}
# Position/Size: iki elemanlı liste (u = "scale" → ölçek/UDim2.fromScale, yoksa piksel ofseti)
# Offset (UIGradient): Vector2 · MaxVisibleGraphemes: "len" = metnin karakter sayısı
NEEDS_UNIT = {"Size"}  # birimsiz Size yanlış anlaşılır (ofset sanılır) → iz düşürülür
MAX_LEN = 60


def lua_num(v):
    s = ("%.6g" % float(v))
    return s


LUA_KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto", "if",
                "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while"}


def lua_key(k):
    return k if (k not in LUA_KEYWORDS and k.replace("_", "a").isalnum()) else '["%s"]' % k


def lua_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return lua_num(v)
    if isinstance(v, str):
        assert all(c.isalnum() or c in "_-." for c in v), "güvensiz metin: " + v
        return '"%s"' % v
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return "{" + ", ".join("%s = %s" % (lua_key(k), lua_val(v[k])) for k in keys) + "}"
    if isinstance(v, list):
        return "{" + ", ".join(lua_val(x) for x in v) + "}"
    raise TypeError(type(v))


def convert(lib):
    report = {"kept": 0, "dropped_cat": 0, "dropped_fx": 0, "dropped_empty": 0,
              "tracks_dropped": 0, "stagger_to_zero": 0, "random_delay": 0,
              "folded_cat": {}, "grapheme_len": 0, "scale_unit": 0}
    anims = {}
    for a in lib["anims"]:
        if a["cat"] not in USED_CATS:
            report["dropped_cat"] += 1
            continue
        cat = CAT_ALIAS.get(a["cat"], a["cat"])
        if cat != a["cat"]:
            report["folded_cat"][a["cat"]] = report["folded_cat"].get(a["cat"], 0) + 1
        # fx bayrağı artık dışlama nedeni değil: izlerin desteklenmesi belirler (Studio'da çalışabilirlik)
        tracks = []
        for tr in a["tracks"]:
            t, p, u = tr.get("t"), tr.get("p"), tr.get("u")
            frm, to = tr.get("from"), tr.get("to")
            def _val_ok(x):
                if isinstance(x, (int, float)) or x in ("cur", "len"):
                    return True
                return isinstance(x, list) and len(x) == 2 and all(isinstance(y, (int, float)) for y in x)
            ok = (t in ALLOWED_T and p in ALLOWED_P and _val_ok(frm) and _val_ok(to))
            if ok and p in NEEDS_UNIT and u not in ("scale", "offset"):
                ok = False   # birimi belirsiz Size: yanlış yorumlanacağına iz düşsün
            if ok and u is not None and u not in ("scale", "offset"):
                ok = False
            if not ok or frm is None or to is None:
                report["tracks_dropped"] += 1
                continue
            dl = tr.get("dl", 0)
            if isinstance(dl, str):
                if dl.startswith("random:"):
                    _, lo, hi = dl.split(":")
                    dl = {"a": float(lo), "b": float(hi)}
                    report["random_delay"] += 1
                else:
                    dl = 0
                    report["stagger_to_zero"] += 1
            if to == "len":
                report["grapheme_len"] += 1
            if u == "scale":
                report["scale_unit"] += 1
            out = {
                "t": t, "p": p, "from": frm, "to": to, "d": float(tr["d"]),
                "dl": dl, "e": tr["e"], "ed": tr["ed"],
                "rep": int(tr.get("rep", 0)), "rev": bool(tr.get("rev", False)),
            }
            if u:
                out["u"] = u
            tracks.append(out)
        if not tracks:
            report["dropped_empty"] += 1
            continue
        if not all(c.isalnum() or c == "_" for c in a["id"]):
            raise ValueError("id Lua tanımlayıcısı değil: " + a["id"])
        entry = {
            "cat": cat,
            # katlanan kategorilerde tetikleyici yuvanın tetikleyicisidir (gecis → show, fx → always)
            "trig": (USED_CATS[a["cat"]] if a["cat"] in EXTRA_CATS else a["trig"]),
            "cls": sorted(a["cls"]), "roles": sorted(a["roles"]),
            "beauty": int(a["q"]["beauty"]), "tracks": tracks,
        }
        if a["cat"] in EXTRA_CATS or a.get("pool") == "extra":
            entry["pool"] = "extra"
        anims[a["id"]] = entry
        report["kept"] += 1
    return anims, report


def render_block(anims):
    ids = sorted(anims.keys())
    lines = [BEGIN]
    lines.append("local ANIM_IDS = {" + ", ".join('"%s"' % i for i in ids) + "}")
    lines.append("local ANIM_LIB = {")
    for i in ids:
        a = anims[i]
        lines.append('\t["%s"] = {' % i)
        lines.append("\t\tcat = %s, trig = %s," % (lua_val(a["cat"]), lua_val(a["trig"])))
        lines.append("\t\tcls = %s," % lua_val(a["cls"]))
        lines.append("\t\troles = %s," % lua_val(a["roles"]))
        lines.append("\t\tbeauty = %d," % a["beauty"])
        if a.get("pool"):
            lines.append('\t\tpool = "%s",' % a["pool"])
        lines.append("\t\ttracks = {")
        for tr in a["tracks"]:
            lines.append("\t\t\t" + lua_val(tr) + ",")
        lines.append("\t\t},")
        lines.append("\t},")
    lines.append("}")
    lines.append(END)
    return "\n".join(lines)


def splice(src, block):
    b = src.index(BEGIN)
    e = src.index(END) + len(END)
    return src[:b] + block + src[e:]


def main():
    check = "--check" in sys.argv
    lib = json.load(open(LIB, encoding="utf-8"))
    anims, rep = convert(lib)
    block = render_block(anims)
    src = open(LUA, encoding="utf-8").read()
    new = splice(src, block)
    print("[i] kullanılan animasyon: %d · dışarıda (kategori): %d · (fx): %d · boş kaldı: %d"
          % (rep["kept"], rep["dropped_cat"], rep["dropped_fx"], rep["dropped_empty"]))
    print("[i] track atıldı: %d · stagger→0: %d · random gecikme: %d · daktilo (len): %d · ölçek birimi: %d"
          % (rep["tracks_dropped"], rep["stagger_to_zero"], rep["random_delay"],
             rep["grapheme_len"], rep["scale_unit"]))
    if rep["folded_cat"]:
        print("[i] katlanan kategoriler: " + ", ".join("%s→%d" % (k, v) for k, v in sorted(rep["folded_cat"].items())))
    ui_text = render_ui_names(lib, anims)
    if check:
        ok = (new == src) and check_js(anims) and check_ui(ui_text)
        print("[%s] EIAnim.lua + ei-anim.js + ei-animlib-ui.js kütüphane ile %s"
              % ("OK" if ok else "FAIL", "SENKRON" if ok else "SENKRON DEĞİL"))
        sys.exit(0 if ok else 1)
    open(LUA, "w", encoding="utf-8").write(new)
    print("[OK] yazıldı: %s (%d bayt)" % (LUA, len(new.encode("utf-8"))))
    js_text = write_js(anims)  # önce hesapla (dosya henüz açılmadan)
    open(JS_PATH, "w", encoding="utf-8").write(js_text)
    print("[OK] yazıldı: %s" % JS_PATH)
    open(UI_PATH, "w", encoding="utf-8").write(ui_text)
    print("[OK] yazıldı: %s (%d animasyon)" % (UI_PATH, len(anims)))




# ---------------------------------------------------------------- JS karşılığı (runtime/js/ei-anim.js)
JS_PATH = os.path.join(ROOT, "runtime", "js", "ei-anim.js")
JS_BEGIN = "// <<EI_ANIM_DATA>>"
JS_END = "// <<END_EI_ANIM_DATA>>"
# Figma kütüphane kutusunun animasyon listesi (ad/kategori/süre/tetikleyici/güzellik)
UI_PATH = os.path.join(ROOT, "runtime", "js", "ei-animlib-ui.js")
UI_HEADER = ("// KÜTÜPHANE ÖNİZLEME VERİSİ (otomatik: tools/build_anim_lua.py). Figma kütüphane kutusunun animasyon adları.\n"
             "// Kategoriler kütüphane kategorileridir. Çalışma zamanı yuvaları: gecis/metin → giris, durum → basma, fx → dongu.\n")


def render_ui_names(lib, anims):
    """Figma kütüphane kutusu için id → {name, cat, dur, trig, beauty} (yalnız çalıştırılabilir animasyonlar)."""
    src = {a["id"]: a for a in lib["anims"]}
    out = {}
    for i in sorted(anims.keys()):
        a = anims[i]
        s = src[i]
        out[i] = {"name": s["name"], "cat": a["cat"], "dur": s["dur"], "trig": a["trig"], "beauty": a["beauty"]}
    return UI_HEADER + "var ANIM_UI_NAMES = " + json.dumps(out, ensure_ascii=False, sort_keys=True) + ";\n"


def check_ui(ui_text):
    src = open(UI_PATH, encoding="utf-8").read()
    return ui_text == src


def lua_template():
    """EIAnim.lua içindeki TEMPLATE uzun dizesini (tek kaynak) çıkarır."""
    src = open(LUA, encoding="utf-8").read()
    start = src.index("local TEMPLATE = [==[\n") + len("local TEMPLATE = [==[\n")
    end = src.index("]==]", start)
    return src[start:end]


def render_js_data(anims):
    ids = sorted(anims.keys())
    lines = [JS_BEGIN]
    lines.append("var ANIM_IDS = " + json.dumps(ids, ensure_ascii=False) + ";")
    lines.append("var ANIM_LIB = " + json.dumps(anims, ensure_ascii=False, indent=1, sort_keys=True) + ";")
    lines.append(JS_END)
    return "\n".join(lines)


def write_js(anims):
    src = open(JS_PATH, encoding="utf-8").read()
    b = src.index(JS_BEGIN)
    e = src.index(JS_END) + len(JS_END)
    src = src[:b] + render_js_data(anims) + src[e:]
    tpl_line = "  var TEMPLATE = " + json.dumps(lua_template(), ensure_ascii=False) + ";"
    lines = src.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("  var TEMPLATE = ")]
    assert len(idx) == 1, "TEMPLATE satırı bulunamadı"
    lines[idx[0]] = tpl_line
    return "\n".join(lines)


def check_js(anims):
    src = open(JS_PATH, encoding="utf-8").read()
    return write_js(anims) == src


if __name__ == "__main__":
    main()
