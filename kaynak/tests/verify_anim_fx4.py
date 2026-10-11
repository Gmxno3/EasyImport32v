#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAPI (v32): efekt döngüsü, içeride kırpma, Rectangle parlama, resim parçasında renkli kutu yok, katman bazlı ses
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "assistant", "tools"))
import verify_anim as V  # noqa: E402


def main():
    fails = []

    def check(c, m):
        print(("  [OK] " if c else "  [FAIL] ") + m)
        if not c:
            fails.append(m)

    prog = (
        "local EIAnim = (function()\n" + V.module_src() + "\nend)()\n"
        + V.MOCK + "\n"
        + "ROOT.children = {}\n"
        + "local function mk(cls, name, id, w, h)\n"
        + "  local o = makeInst(cls, name); o.attrs.EI_Id = id; o.ZIndex = 1; addChild(ROOT, o)\n"
        + "  o.AbsoluteSize = { X = w or 300, Y = h or 100 }\n"
        + "  o.FindFirstChild = function(self, n) for _, c in ipairs(self.children) do if c.Name == n then return c end end return nil end\n"
        + "  o.GetChildren = function(self) return self.children end\n"
        + "  return o\n"
        + "end\n"
        + "NumberSequence = { new = function(t) return t end }; NumberSequenceKeypoint = { new = function(a, b) return { a, b } end }\n"
        + "ColorSequence = { new = function(c) return c end }\n"
        + "local CREATED = {}; local _new = Instance.new\n"
        + "Instance.new = function(cls) local o = _new(cls); CREATED[#CREATED + 1] = o; return o end\n"
        + "local A = mk('Frame', 'A', 1)            -- yağmur, döngü kapalı\n"
        + "local B = mk('Frame', 'B', 2)            -- yuvarlak köşeli + parlama\n"
        + "makeInst('UICorner', 'K'); local kc = makeInst('UICorner', 'K'); kc.CornerRadius = 8; addChild(B, kc)\n"
        + "local C = mk('Frame', 'C', 3)            -- resim parçalı yağmur\n"
        + "local TPL = makeInst('ImageLabel', 'Ikon_fx'); TPL.attrs.EI_Id = 9; TPL.ZIndex = 1; addChild(C, TPL)\n"
        + "TPL.Clone = function(self) local c = makeInst('ImageLabel', 'Ikon_clone'); c.BackgroundTransparency = 1; return c end\n"
        + "local D = mk('Frame', 'D', 4)            -- yalnız parlama, döngü kapalı değil\n"
        + "local BIND = {\n"
        + "  { id = 1, fx = 'fall', params = { count = 3, seconds = 3, loop = 0 } },\n"
        + "  { id = 2, fx = 'shine', params = { sweep = 2, tilt = 15, strength = 0.5, width = 0.4 } },\n"
        + "  { id = 9, fx = 'tpl' }, { id = 3, fx = 'fall' },\n"
        + "  { id = 4, fx = 'sweep' },\n"
        + "}\n"
        + "local SRC = EIAnim.buildSourceSpec(BIND, {})\n"
        + "local chunk, err = load(SRC, 'EI_Animator')\n"
        + "if not chunk then io.write('LOADERR|' .. tostring(err) .. '\\n') return end\n"
        + "chunk()\n"
        + "for _, l in ipairs(LOG) do io.write(l, '\\n') end\n"
        + "local function layerOf(parent, name) for _, o in ipairs(CREATED) do if o.Name == name and o.Parent == parent then return o end end end\n"
        + "local lb, la = layerOf(B, 'EI_FXTop'), layerOf(A, 'EI_FX')\n"
        + "io.write('LAYER_B|' .. tostring(lb and lb.ClassName) .. '\\n')\n"
        + "io.write('LAYER_A|' .. tostring(la and la.ClassName) .. '|' .. tostring(la and la.ClipsDescendants) .. '\\n')\n"
        + "local corner = false\n"
        + "for _, o in ipairs(CREATED) do if o.ClassName == 'UICorner' and o.Parent == lb and o.CornerRadius == 8 then corner = true end end\n"
        + "io.write('CORNER_B|' .. tostring(corner) .. '\\n')\n"
    )
    out = V.run_lua_program(prog)
    check("LOADERR" not in out, "döngü / shine içeren LocalScript derlenir ve yüklenir")
    lines = [ln for ln in out.split("\n") if ln]
    check("LAYER_B|CanvasGroup" in lines, "yuvarlak köşeli öğede efekt katmanı CanvasGroup (köşeden taşmaz)")
    check("CORNER_B|true" in lines, "efekt katmanı köşe yuvarlaklığını kopyalar (içeride kalır)")
    check("LAYER_A|Frame|true" in lines, "köşesiz öğede efekt katmanı Frame (+ClipsDescendants)")
    shine = [ln for ln in lines if ln.startswith("TWEEN|Frame|Frame|Position|") and "|2|Quad|InOut" in ln]
    check(len(shine) >= 1, "shine: bant soldan sağa Position tween'i, süre kaydırıcıdan 2 sn (%d)" % len(shine))
    sweepd = [ln for ln in lines if ln.startswith("TWEEN|Frame|Frame|Position|") and "|1.4|Quad|InOut" in ln]
    check(len(sweepd) >= 1, "sweep: varsayılan parlama (1.4 sn) çalışır")
    fall_a = [ln for ln in lines if ln.startswith("TWEEN|Frame|Frame|Position|") and "|3|Linear|In" in ln]
    check(len(fall_a) == 1, "döngü kapalı yağmur: ilk parça düşer, sonra döngü durur / count sınırı (%d)" % len(fall_a))
    imgs = [ln for ln in lines if ln.startswith("TWEEN|Ikon_clone|ImageLabel|Position|")]
    check(len(imgs) >= 1, "resim şablonlu yağmur kopya üretir")
    check(not any(ln.startswith("TWEEN|Ikon_clone|ImageLabel|BackgroundTransparency") for ln in lines),
          "resim parçasında arka plan dolgusu (renkli kutu) yok")

    # --- ses betiği: katman bazlı özel ses + varsayılan ---
    sprog = (
        "local EIAnim = (function()\n" + V.module_src() + "\nend)()\n"
        + V.MOCK + "\n"
        + "ROOT.children = {}\n"
        + "ROOT.GetDescendants = function(self) return ALL end\n"
        + "Enum.UserInputType = { MouseButton1 = 'MB1', Touch = 'T' }\n"
        + "local function sig(n) return { fns = {}, Connect = function(self, f) self.fns[#self.fns + 1] = f end } end\n"
        + "local function mkb(cls, name, attrs)\n"
        + "  local o = makeInst(cls, name); for k, v in pairs(attrs or {}) do o.attrs[k] = v end\n"
        + "  o.MouseButton1Click = sig(); o.InputBegan = sig(); addChild(ROOT, o); return o end\n"
        + "local B1 = mkb('TextButton', 'Varsayilan')\n"
        + "local B2 = mkb('TextButton', 'Ozel', { EI_SndHover = 'rbxassetid://111', EI_SndClick = 'rbxassetid://222' })\n"
        + "local B3 = mkb('TextButton', 'Sessiz', { EI_SndHover = 'none', EI_SndClick = 'none' })\n"
        + "local F1 = mkb('Frame', 'Cerceve', { EI_SndClick = 'rbxassetid://333' })\n"
        + "local SOUNDS = {}\n"
        + "Instance.new = function(cls) local o = makeInst(cls); o.Play = function() SOUNDS[#SOUNDS + 1] = o.SoundId end; return o end\n"
        + "local chunk = load(EIAnim.buildSoundSource(), 'EI_Sesler'); chunk()\n"
        + "local function fire(sg) for _, f in ipairs(sg.fns) do f({ UserInputType = 'MB1' }) end end\n"
        + "for _, f in ipairs(B1.MouseEnter.fns) do f() end\n"
        + "for _, f in ipairs(B2.MouseEnter.fns) do f() end\n"
        + "for _, f in ipairs(B2.MouseButton1Click.fns) do f() end\n"
        + "for _, f in ipairs(B3.MouseEnter.fns) do f() end\n"
        + "for _, f in ipairs(B3.MouseButton1Click.fns) do f() end\n"
        + "fire(F1.InputBegan)\n"
        + "io.write('SND|' .. table.concat(SOUNDS, ',') .. '\\n')\n"
    )
    sout = V.run_lua_program(sprog)
    snd = [ln for ln in sout.split("\n") if ln.startswith("SND|")]
    got = snd[0][4:] if snd else ""
    check(got == "rbxassetid://139719503904449,rbxassetid://111,rbxassetid://222,rbxassetid://333",
          "ses: varsayılan hover, özel hover/tıklama, 'none' sessiz, çerçeve tıklaması (%s)" % got)
    print()
    if fails:
        print("SONUÇ: BAŞARISIZ (%d)" % len(fails)); return 1
    print("SONUÇ: GEÇTİ — döngü, içeride kırpma, Rectangle parlama ve katman bazlı ses sahte Roblox'ta çalışır")
    return 0


if __name__ == "__main__":
    sys.exit(main())
