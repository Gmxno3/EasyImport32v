#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAPI: GUI/UI panel animasyonları (v33, madde 3)

  • Panel açılışı yumuşak açılış havuzundan gelir (panel_slide_left_soft: soldan sağa, yavaş, sönerek)
  • _open → panel görünür olur ve giriş tween'i oynar
  • _close / _toggle / _tab → ÇIKIŞ (hide) tween'i oynar; panel animasyon BİTİNCE gizlenir
  • Panel içindeki hide bağlamalı öğeler de çıkış animasyonu oynar
  • Açma/kapama yarışı: kapanış beklerken yeniden açılırsa panel gizlenmez (sıra numarası iptali)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "assistant", "tools"))
import build_anim_lua as B  # noqa: E402
import verify_anim as V  # noqa: E402
from verify_anim_spec import lua_val  # noqa: E402

# Sahte ortam eklentisi: Tween.Completed sinyali + task.delay kuyruğu (kapanış beklemesi için)
EXTRA = r"""
local PENDING = {}
task.delay = function(t, f) PENDING[#PENDING + 1] = { t = t, f = f } end
local function runPending()
  local p = PENDING
  PENDING = {}
  for _, e in ipairs(p) do
    log("DELAY", e.t)
    e.f()
  end
end
-- Tween "from" değerini de kaydet (soldan kayma: -1 → 0 doğrulaması için)
do
  local g = game
  local base = g.GetService
  local svc = nil
  g.GetService = function(self, n)
    local s = base(self, n)
    if n == "TweenService" and s and not svc then
      svc = s
      local old = s.Create
      s.Create = function(self2, obj, info, goal)
        local x = obj.Position and obj.Position.X and obj.Position.X.Scale
        log("FROM", obj.Name, tostring(x))
        return old(self2, obj, info, goal)
      end
    end
    return s
  end
end
local function ff(self, n) for _, c in ipairs(self.children) do if c.Name == n then return c end end return nil end
local function isDesc(self, anc) local p = self.Parent while p do if p == anc then return true end p = p.Parent end return false end
local function runClicks(o)
  for _, f in ipairs(o.MouseButton1Click.fns) do f() end
end
"""


def main():
    fails = []

    def check(c, m):
        print(("  [OK] " if c else "  [FAIL] ") + m)
        if not c:
            fails.append(m)

    anims, _ = B.convert(json.load(open(B.LIB, encoding="utf-8")))
    for aid in ("panel_slide_left_soft", "exit_slide_left", "enter_fade"):
        check(aid in anims, "kütüphane dönüşümünde var: %s" % aid)
    # Panel açılışı gerçekten soldan sağa mı? (Position from = [-1, 0] ölçek birimi)
    pos = [t for t in anims["panel_slide_left_soft"]["tracks"] if t["p"] == "Position"][0]
    check(pos["u"] == "scale" and pos["from"] == [-1, 0] and pos["to"] == [0, 0],
          "panel_slide_left_soft soldan ([-1,0] → [0,0], ölçek birimi) kayarak açılır")
    check(anims["panel_slide_left_soft"]["tracks"][0]["d"] >= 0.5,
          "açılış yavaş (%.2f sn) ve yumuşak" % anims["panel_slide_left_soft"]["tracks"][0]["d"])

    specs = {"_Animasyon 1": {"tracks": anims["panel_slide_left_soft"]["tracks"]},
             "_Animasyon 2": {"tracks": anims["exit_slide_left"]["tracks"]},
             "_Animasyon 3": {"tracks": anims["enter_fade"]["tracks"]}}
    specs_lua = lua_val({k: {"tracks": v["tracks"]} for k, v in specs.items()})
    prog = (
        "local EIAnim = (function()\n" + V.module_src() + "\nend)()\n"
        + V.MOCK + "\n" + EXTRA
        + "ROOT.children = {}\n"
        + "local function mk(cls, name, id, parent)\n"
        + "  local o = makeInst(cls, name); o.attrs.EI_Id = id; o.Size = UDim2.new(0, 200, 0, 120)\n"
        + "  o.FindFirstChild = ff; o.IsDescendantOf = isDesc\n"
        + "  o.MouseButton1Click = { fns = {}, Connect = function(self, f) self.fns[#self.fns + 1] = f end }\n"
        + "  addChild(parent or ROOT, o); return o\n"
        + "end\n"
        + "local ANA = mk('Frame', 'Ana', 1)\n"
        + "local MENU = mk('Frame', 'Menu_panel', 10); MENU.Visible = false\n"
        + "local ICERIK = mk('TextLabel', 'Icerik', 11, MENU)\n"
        + "local AC = mk('TextButton', 'Ac_open:Menu_button', 12)\n"
        + "local KAPAT = mk('TextButton', 'Kapat_close', 13, MENU)\n"
        + "local BIND = {\n"
        + "  { id = 10, show = '_Animasyon 1', hide = '_Animasyon 2' },\n"
        + "  { id = 11, show = '_Animasyon 3', hide = '_Animasyon 2' },\n"
        + "  { id = 13, hide = '_Animasyon 2' } }\n"
        + "local SPECS = " + specs_lua + "\n"
        + "local SRC = EIAnim.buildSourceSpec(BIND, SPECS, { actions = { { id = 12, kind = 'open', target = 10 },\n"
        + "  { id = 13, kind = 'close', target = nil } }, panels = { 10 }, groups = {} })\n"
        + "local chunk, err = load(SRC, 'EI_Animator')\n"
        + "if not chunk then io.write('LOADERR|' .. tostring(err) .. '\\n') return end\n"
        + "chunk()\n"
        + "log('VIS0', tostring(MENU.Visible))\n"
        + "runClicks(AC)\n"
        + "log('VIS1', tostring(MENU.Visible))\n"
        + "local before = MENU.Position.X.Scale\n"
        + "log('POS_AFTER_OPEN', tostring(before))\n"
        + "runClicks(KAPAT)\n"
        + "log('VIS2', tostring(MENU.Visible))\n"
        + "runPending()\n"
        + "log('VIS3', tostring(MENU.Visible))\n"
        + "runClicks(KAPAT)\n"
        + "runClicks(AC)\n"
        + "runPending()\n"
        + "log('VIS4', tostring(MENU.Visible))\n"
        + "for _, l in ipairs(LOG) do io.write(l, '\\n') end\n"
    )
    out = V.run_lua_program(prog)
    check("LOADERR" not in out, "üretilen LocalScript derlenir ve yüklenir")
    lines = [ln for ln in out.split("\n") if ln.startswith(("TWEEN|", "VIS", "DELAY|", "POS_", "FROM|"))]

    def val(prefix):
        for ln in lines:
            if ln.startswith(prefix):
                return ln.split("|", 1)[1]
        return None

    t10 = [ln for ln in lines if ln.startswith("TWEEN|Menu_panel|")]
    open_tween = [ln for ln in t10 if "|Position|" in ln]
    check(bool(open_tween), "açılışta panel Position tween'i oynar (soldan kayma)")
    check(any("Quint|Out" in ln for ln in open_tween), "açılış yumuşak (Quint Out)")
    check(any("|0.55|" in ln for ln in open_tween), "açılış süresi 0.55 sn")
    check(val("VIS0") == "false" and val("VIS1") == "true", "panel başlangıçta kapalı, _open ile açıldı")
    check(val("POS_AFTER_OPEN") is not None and abs(float(val("POS_AFTER_OPEN"))) < 1e-9,
          "panel açılış sonunda hedef konumda (%s)" % val("POS_AFTER_OPEN"))
    check(any("|Position|(0,20)|" in ln or "|Position|(0,20.0)|" in ln for ln in open_tween),
          "açılış hedefi temel konum (ölçek 0): panel yerine oturur (%s)" % (open_tween[0][:80] if open_tween else "-"))
    froms = [ln for ln in lines if ln.startswith("FROM|Menu_panel|")]
    check(len(froms) >= 2 and froms[0].endswith("|-1") and froms[1].endswith("|0"),
          "panel soldan gelir (-1 ölçek) → açılış tween'i 0'a taşır (%s)" % ", ".join(froms[:2]))

    close_tween = [ln for ln in t10 if "|Position|" in ln and "|0.3|" in ln]
    check(bool(close_tween), "kapanışta panel çıkış (hide) tween'i oynar")
    check(val("VIS2") == "true", "kapanış animasyonu bitmeden panel gizlenmez")
    check(val("VIS3") == "false", "kapanış animasyonu bitince panel gizlenir")
    check(any("DELAY|0.3" in ln for ln in lines), "gizleme, tween süresi kadar sonra (task.delay 0.3)")
    child = [ln for ln in lines if ln.startswith("TWEEN|Icerik|")]
    check(bool(child), "panel içindeki hide bağlamalı öğe de çıkış animasyonu oynar")
    check(val("VIS4") == "true", "kapanış beklerken yeniden açılırsa panel gizlenmez (yarış iptali)")

    print()
    if fails:
        print("SONUÇ: BAŞARISIZ (%d)" % len(fails))
        return 1
    print("SONUÇ: GEÇTİ — panel yumuşak açılır, çıkış animasyonu biter ve panel gizlenir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
