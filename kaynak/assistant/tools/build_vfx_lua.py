#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROBLOX VFX MODÜLÜ — veri üreteci + API doğrulayıcı (v34)

Kaynak: assistant/vfx/vfx-library.json   (dünya efekti · karakter animasyonu · etkileşim kuralları)
Çıktı : assistant/runtime/lua/EIVfx.lua   (<<EI_VFX_DATA>> bloğu)
        assistant/runtime/js/ei-vfx.js    (<<EI_VFX_DATA>> bloğu)

Neden doğrulayıcı: Roblox API'sinde OLMAYAN sınıf/özellik/enum yazılırsa kütüphane derlenmez.
Böylece "uydurulmuş API" sessizce üretime girmez (test: tests/verify_vfx.py · "desteklenmeyen özellik").

Kullanım:
    python3 tools/build_vfx_lua.py            # veri bloklarını yazar
    python3 tools/build_vfx_lua.py --check     # yazmadan senkron mu diye bakar (çıkış 0/1)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # assistant/
LIB = os.path.join(ROOT, "vfx", "vfx-library.json")
LUA_PATH = os.path.join(ROOT, "runtime", "lua", "EIVfx.lua")
JS_PATH = os.path.join(ROOT, "runtime", "js", "ei-vfx.js")

LUA_BEGIN, LUA_END = "-- <<EI_VFX_DATA>>", "-- <<END_EI_VFX_DATA>>"
JS_BEGIN, JS_END = "// <<EI_VFX_DATA>>", "// <<END_EI_VFX_DATA>>"

# ---------------------------------------------------------------- Roblox API beyaz listesi
# Yalnız modülün KULLANDIĞI sınıflar ve YAZILABİLİR özellikleri (Roblox dokümantasyonu).
API = {
    "Attachment": ["Name", "Position", "Orientation", "CFrame", "Visible", "WorldPosition"],
    "ParticleEmitter": ["Name", "Texture", "Rate", "Lifetime", "Speed", "SpreadAngle", "Size", "Transparency",
                        "Color", "LightEmission", "LightInfluence", "Acceleration", "Drag", "Rotation", "RotSpeed",
                        "ZOffset", "Shape", "ShapeStyle", "ShapeInOut", "EmissionDirection", "Enabled", "Squash",
                        "VelocityInheritance", "FlipbookLayout", "Orientation"],
    "PointLight": ["Name", "Color", "Brightness", "Range", "Shadows", "Enabled"],
    "Trail": ["Name", "Attachment0", "Attachment1", "Lifetime", "MinLength", "FaceCamera", "Color", "Transparency",
              "WidthScale", "LightEmission", "LightInfluence", "Texture", "TextureLength", "TextureMode", "Enabled"],
    "Beam": ["Name", "Attachment0", "Attachment1", "CurveSize0", "CurveSize1", "Width0", "Width1", "Segments",
             "Brightness", "LightEmission", "LightInfluence", "Color", "Transparency", "Texture", "TextureLength",
             "TextureSpeed", "TextureMode", "FaceCamera", "Enabled"],
    "Highlight": ["Name", "Adornee", "FillColor", "FillTransparency", "OutlineColor", "OutlineTransparency",
                  "DepthMode", "Enabled"],
    "ColorCorrectionEffect": ["Name", "TintColor", "Brightness", "Contrast", "Saturation", "Enabled"],
    "BlurEffect": ["Name", "Size", "Enabled"],
    "BloomEffect": ["Name", "Intensity", "Size", "Threshold", "Enabled"],
    "SunRaysEffect": ["Name", "Intensity", "Spread", "Enabled"],
    "DepthOfFieldEffect": ["Name", "FarIntensity", "FocusDistance", "InFocusRadius", "NearIntensity", "Enabled"],
    "Atmosphere": ["Name", "Density", "Offset", "Color", "Decay", "Glare", "Haze"],
    "Explosion": ["Name", "Position", "BlastPressure", "BlastRadius", "DestroyJointRadiusPercent", "Visible", "TimeScale"],
    "Animation": ["Name", "AnimationId", "Priority"],
    "Humanoid": ["WalkSpeed", "JumpPower", "JumpHeight", "CameraOffset", "AutoRotate"],
    "Camera": ["FieldOfView", "CameraType", "CFrame"],
    "ProximityPrompt": ["Name", "ActionText", "ObjectText", "HoldDuration", "MaxActivationDistance",
                        "RequiresLineOfSight", "KeyboardKeyCode", "GamepadKeyCode", "Enabled", "Style", "Exclusivity",
                        "UIOffset", "ClickablePrompt"],
    "ClickDetector": ["Name", "MaxActivationDistance", "MouseIcon"],
    "Tool": ["Name", "ToolTip", "TextureId", "CanBeDropped", "RequiresHandle", "Enabled", "ManualActivationOnly"],
    "RemoteEvent": ["Name"],
    "RemoteFunction": ["Name"],
}
# Yalnız enum ADI + izin verilen öğeler (desteklenen alt küme; yanlış yazım yakalanır).
ENUMS = {
    "ParticleEmitterShape": ["Sphere", "Block", "Cylinder", "Disc"],
    "ParticleEmitterShapeStyle": ["Volume", "Surface"],
    "NormalId": ["Top", "Bottom", "Left", "Right", "Front", "Back"],
    "TextureMode": ["Stretch", "Wrap", "Static"],
    "HighlightDepthMode": ["AlwaysOnTop", "Occluded"],
    "AnimationPriority": ["Core", "Idle", "Movement", "Action", "Action2", "Action3", "Action4"],
    "CameraType": ["Fixed", "Attach", "Watch", "Track", "Follow", "Custom", "Scriptable", "Orbital"],
    "KeyCode": ["E", "F", "Q", "R", "G", "T", "X", "C", "V", "B", "Space", "MouseButton1"],
    "ProximityPromptStyle": ["Default", "Custom"],
    "ProximityPromptExclusivity": ["OnePerButton", "OneGlobally", "AlwaysShow"],
}
# "n"/"b"/"s" tek değer (sayı / mantık / metin) · "c3"/"v2"/"v3"/"nr" sayı listesi · "seq"/"nseq"/"en" özel
VALUE_TAGS = {"n": 1, "b": 1, "s": 1, "c3": 3, "v2": 2, "v3": 3, "nr": 2, "seq": None, "nseq": None, "en": None}
LUA_KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto", "if", "in",
                "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while"}
PRESET_FIELDS = {"id": str, "cat": str, "label": str, "ctx": list, "events": list, "targets": list, "authority": str,
                 "cost": int, "mobile": bool, "trig": str, "freq": str, "dur": (int, float), "cooldown": (int, float),
                 "maxActive": int, "objects": list, "props": dict, "burst": (dict, type(None)), "cleanup": str, "why": str}

CATS = ("world", "post", "char", "cam", "interact", "decide")
CLEANUPS = ("delay", "stop", "none")
AUTHORITIES = ("client", "server")


def fail(msg):
    raise SystemExit("[HATA] vfx kütüphanesi: " + msg)


def check_value(pid, cls, prop, spec):
    if not isinstance(spec, dict) or "t" not in spec or "v" not in spec:
        fail("%s · %s.%s: değer {t,v} biçiminde olmalı" % (pid, cls, prop))
    t, v = spec["t"], spec["v"]
    if t not in VALUE_TAGS:
        fail("%s · %s.%s: bilinmeyen değer türü '%s'" % (pid, cls, prop, t))
    if t == "en":
        if not (isinstance(v, list) and len(v) == 2):
            fail("%s · %s.%s: enum [EnumAdı, Öğe] olmalı" % (pid, cls, prop))
        en, item = v
        if en not in ENUMS:
            fail("%s · %s.%s: Roblox'ta bu enum beyaz listede yok: %s" % (pid, cls, prop, en))
        if item not in ENUMS[en]:
            fail("%s · %s.%s: Enum.%s.%s yok" % (pid, cls, prop, en, item))
        return
    if t in ("seq", "nseq"):
        if not (isinstance(v, list) and v):
            fail("%s · %s.%s: %s boş olamaz" % (pid, cls, prop, t))
        for kp in v:
            if not (isinstance(kp, list) and len(kp) == 2):
                fail("%s · %s.%s: %s anahtar noktası [t, değer] olmalı" % (pid, cls, prop, t))
        return
    if t == "s":
        if not isinstance(v, str):
            fail("%s · %s.%s: metin bekleniyor" % (pid, cls, prop))
        # Boş metin bilinçli olabilir: AnimationId projeden gelir (bkz. library.anchors)
        return
    if t == "n":
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            fail("%s · %s.%s: sayı bekleniyor" % (pid, cls, prop))
        return
    if t == "b":
        if not isinstance(v, bool):
            fail("%s · %s.%s: true/false bekleniyor" % (pid, cls, prop))
        return
    need = VALUE_TAGS[t]
    if not isinstance(v, list) or len(v) != need:
        fail("%s · %s.%s: '%s' %d değer bekler" % (pid, cls, prop, t, need))
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
        fail("%s · %s.%s: sayı bekleniyor" % (pid, cls, prop))


def validate(lib):
    seen = set()
    for p in lib.get("presets", []):
        pid = p.get("id", "?")
        if pid in seen:
            fail("aynı kimlik iki kez: %s" % pid)
        seen.add(pid)
        for f, typ in PRESET_FIELDS.items():
            if f not in p:
                fail("%s: zorunlu alan eksik: %s" % (pid, f))
            if not isinstance(p[f], typ):
                fail("%s: alan '%s' tipi yanlış (%s)" % (pid, f, type(p[f]).__name__))
        if p["cat"] not in CATS:
            fail("%s: bilinmeyen kategori %s" % (pid, p["cat"]))
        if p["authority"] not in AUTHORITIES:
            fail("%s: yetki 'client' ya da 'server' olmalı" % pid)
        if p["cleanup"] not in CLEANUPS:
            fail("%s: temizleme 'delay' | 'stop' | 'none' olmalı" % pid)
        if p["cost"] not in (0, 1, 2, 3):
            fail("%s: maliyet 0-3 arası olmalı" % pid)
        objs = p["objects"]
        for cls in p["props"]:
            if cls not in API:
                fail("%s: Roblox'ta bu sınıf beyaz listede yok: %s" % (pid, cls))
            if cls not in objs:
                fail("%s: %s props'ta var ama objects listesinde yok" % (pid, cls))
            for prop, spec in p["props"][cls].items():
                if prop not in API[cls]:
                    fail("%s · %s.%s: Roblox'ta bu özellik beyaz listede yok" % (pid, cls, prop))
                if prop in ("Attachment0", "Attachment1", "Adornee"):
                    continue
                check_value(pid, cls, prop, spec)
        for cls in objs:
            if cls not in API:
                fail("%s: bilinmeyen sınıf: %s" % (pid, cls))
        for a in ("ctx", "events", "targets"):
            for x in p[a]:
                if not isinstance(x, str) or not x:
                    fail("%s: %s içinde boş değer" % (pid, a))
        if p["burst"] is not None:
            for k in ("times", "count"):
                if k not in p["burst"]:
                    fail("%s: burst.%s eksik" % (pid, k))
                check_value(pid, "burst", k, p["burst"][k])
        if p["cat"] == "char":
            for k in ("priority", "weight", "fadeIn", "fadeOut", "slot", "loop"):
                if k not in p:
                    fail("%s: karakter animasyonu '%s' alanını vermeli" % (pid, k))
            if p["priority"] is not None and p["priority"] not in ENUMS["AnimationPriority"]:
                fail("%s: AnimationPriority.%s yok" % (pid, p["priority"]))
            for k in ("fadeIn", "fadeOut"):
                if not isinstance(p[k], (int, float)) or p[k] < 0:
                    fail("%s: %s negatif olamaz" % (pid, k))
            if p["priority"] is not None and (not isinstance(p["weight"], (int, float)) or not 0 <= p["weight"] <= 1):
                fail("%s: weight 0-1 arası olmalı" % pid)
        if p.get("tween") is not None:
            tw = p["tween"]
            for k in ("object", "prop", "dur", "style", "dir"):
                if k not in tw:
                    fail("%s: tween.%s eksik" % (pid, k))
            if tw["object"] not in ("Camera", "self"):
                fail("%s: tween nesnesi Camera|self olmalı" % pid)
    if not seen:
        fail("hiç presets yok")
    return len(seen)


# ---------------------------------------------------------------- serileştirme
def lua_value(v):
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v) if isinstance(v, float) and v != int(v) else str(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, list):
        return "{" + ", ".join(lua_value(x) for x in v) + "}"
    if isinstance(v, dict):
        for k in v:
            # Lua anahtar sözcüğü alan adı olamaz ({ repeat = ... } sözdizimi hatası) → üreteç durdurur
            if isinstance(k, str) and k in LUA_KEYWORDS:
                fail("alan adı Lua anahtar sözcüğü olamaz: '%s' (ör. 'repeat' → 'freq')" % k)
        return "{" + ", ".join("[%s] = %s" % (lua_value(k), lua_value(x)) for k, x in v.items()) + "}"
    fail("serileştirilemeyen değer: %r" % (v,))


def lua_block(lib):
    rows = []
    for p in lib["presets"]:
        rows.append("  " + lua_value(p) + ",")
    body = ",\n".join([""] + rows) if False else "{\n" + "\n".join(rows) + "\n}"
    return ("local VFX_PRESETS = " + body + "\n")


def js_block(lib):
    return ("var VFX_PRESETS = " + json.dumps(lib["presets"], ensure_ascii=False, indent=1) + ";\n")


def splice(path, begin, end, block):
    src = open(path, encoding="utf-8").read()
    if begin not in src or end not in src:
        fail("%s içinde işaret bulunamadı (%s)" % (path, begin))
    a = src.index(begin) + len(begin)
    b = src.index(end)
    return src[:a] + "\n" + block + src[b:]


def main():
    check = "--check" in sys.argv
    lib = json.load(open(LIB, encoding="utf-8"))
    n = validate(lib)
    lua_new = splice(LUA_PATH, LUA_BEGIN, LUA_END, lua_block(lib))
    js_new = splice(JS_PATH, JS_BEGIN, JS_END, js_block(lib))
    lua_old = open(LUA_PATH, encoding="utf-8").read()
    js_old = open(JS_PATH, encoding="utf-8").read()
    in_sync = (lua_new == lua_old) and (js_new == js_old)
    if check:
        print("[%s] EIVfx.lua + ei-vfx.js kütüphane ile %s (%d preset doğrulandı)"
              % ("OK" if in_sync else "FAIL", "SENKRON" if in_sync else "SENKRON DEĞİL", n))
        return 0 if in_sync else 1
    open(LUA_PATH, "w", encoding="utf-8").write(lua_new)
    open(JS_PATH, "w", encoding="utf-8").write(js_new)
    print("[OK] yazıldı: %s + %s (%d preset, API beyaz listesinden geçti)" % (LUA_PATH, JS_PATH, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
