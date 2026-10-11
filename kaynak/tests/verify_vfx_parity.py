#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAPI: EIVfx paritesi — EIVfx.lua ≡ ei-vfx.js (karar bölümü) + kütüphane senkronu

Neden gerekli: EIVfx karar motoru (suggest/plan/tryPlay/tick/release/canPlay/animPlan/limits/describe)
iki dilde yaşar. Lua tarafı Roblox'ta koşar, JS tarafı panel/figma tarafında aynı kararı verir.
İkisi ayrışırsa aynı olay iki farklı efekt seçer — bu kapı birebir eşitliği kanıtlar.

Kontroller:
  1) Kütüphane ↔ her iki modül SENKRON (build_vfx_lua.py --check; elle düzenleme yasak)
  2) suggest: 14 bağlam × 20 olay × 8 hedef × mobil/masaüstü = 4480 girdide aynı liste/sıra/puan
  3) plan: en iyi seçim + alternatif sayısı + düşürülenler + limitler
  4) tryPlay/tick/release: aynı zaman çizelgesinde aynı kararlar (bekleme/eşzamanlı/kapasite)
  5) animPlan: öncelik/ağırlık/çakışma/yeniden tetikleme/asset-eksik — aynı sebep
  6) canPlay: yetki (sunucu/istemci) — tüm presetler × 4 yetki kipi
  7) limits + describe: bütçe, eşzamanlı sınır, etiket/maliyet/yetki alanları

Kullanım: python3 tests/verify_vfx_parity.py     (çıkış 0 = GEÇTİ)
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "assistant", "tools"))
import build_vfx_lua as BV  # noqa: E402
import verify_anim as V  # noqa: E402

LUA_JS = os.path.join(ROOT, "assistant", "runtime", "js", "ei-vfx.js")
LUA_MOD = os.path.join(ROOT, "assistant", "runtime", "lua", "EIVfx.lua")
BUILDER = os.path.join(ROOT, "assistant", "tools", "build_vfx_lua.py")

CTXS = ["combat", "pvp", "rpg", "simulator", "tycoon", "obby", "parkour", "racing", "horror",
        "roleplay", "casual", "survival", "ui", "bilinmeyen"]
EVENTS = ["hit", "hit_taken", "pickup", "collect", "land", "cast", "sprint", "run", "jump", "fall",
          "idle", "menu", "zzz", "zone_enter", "quest_target", "low_health", "death", "fire", "swing", "footstep"]
TARGETS = ["npc", "player", "part", "item", "tool", "ui", "world", "belinmeyen"]
MOBILES = [False, True]

PLAN_CASES = [
    ["combat", "hit", "npc", False],
    ["combat", "hit", "npc", True],
    ["ui", "menu", "ui", False],
    ["rpg", "cast", "player", False],
    ["rpg", "cast", "player", True],
    ["horror", "zone_enter", "world", False],
    ["obby", "land", "player", False],
    ["simulator", "pickup", "part", False],
    ["racing", "sprint", "player", False],
    ["belinmeyen", "zzz", "belinmeyen", False],
    ["combat", "low_health", "player", True],
    ["survival", "death", "npc", False],
]

SCENARIO = [
    ["try", "world_hit_spark", 1.00, False],
    ["try", "world_hit_spark", 1.05, False],
    ["try", "world_hit_spark", 1.13, False],
    ["try", "world_hit_spark", 1.25, False],
    ["try", "world_pickup_pop", 1.30, False],
    ["try", "world_pickup_pop", 1.30, False],
    ["try", "world_footstep_puff", 2.00, False],
    ["try", "world_footstep_puff", 2.10, False],
    ["try", "world_footstep_puff", 2.60, False],
    ["try", "world_footstep_puff", 2.70, False],
    ["tick", 3.00],
    ["tick", 9.00],
    ["try", "world_death_burst", 9.00, False],
    ["release", "world_death_burst"],
    ["release", "bilinmeyen_efekt"],
    ["try", "bilinmeyen_efekt", 9.50, False],
    ["try", "world_hit_spark", 9.50, True],
    ["tick", 70.00],
    ["try", "world_hit_spark", 70.10, False],
    ["try", "world_vfx_combo_stage", 70.20, False],
]

ANIM_CASES = [
    ["char_idle_breath", None, ""],
    ["char_idle_breath", None, "rbxassetid://1"],
    ["char_walk_cycle", {"movement": "Idle"}, "rbxassetid://2"],
    ["char_walk_cycle", {"movement": "Movement"}, "rbxassetid://2"],
    ["char_walk_cycle", {"movement": {"id": "char_run_cycle", "priority": "Movement"}}, "rbxassetid://2"],
    ["char_run_cycle", {"movement": {"id": "char_run_cycle", "priority": "Movement"}}, "rbxassetid://3"],
    ["char_attack_combo", {"action": "Action2"}, "rbxassetid://4"],
    ["char_attack_combo", {"action": {"id": "char_attack_combo", "priority": "Action2"}}, "rbxassetid://4"],
    ["char_hit_react", {"action": {"id": "char_jump_launch", "priority": "Action"}}, "rbxassetid://5"],
    ["char_hit_react", {"action": "Idle"}, "rbxassetid://5"],
    ["char_jump_launch", {"action": "Action3"}, "rbxassetid://6"],
    ["char_jump_launch", {}, ""],
    ["char_npc_patrol", None, "rbxassetid://7"],
    ["world_hit_spark", None, "x"],
    ["yok_boyle_efekt", None, "x"],
]

LIMIT_CASES = [
    [False, None, None],
    [True, None, None],
    [True, 0, 10],
    [False, 2, 5],
    [True, 3, 0],
]


def lua_lit(obj):
    """Python nesnesini Lua tablosu/değeri olarak yazar (anahtarlar açıkça köşeli parantezle)."""
    if obj is None:
        return "nil"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, str):
        return '"' + obj.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, float):
        return repr(obj)
    if isinstance(obj, list):
        return "{" + ", ".join(lua_lit(x) for x in obj) + "}"
    if isinstance(obj, dict):
        return "{" + ", ".join("[%s] = %s" % (lua_lit(k), lua_lit(v)) for k, v in obj.items()) + "}"
    raise TypeError(type(obj))


LUA_PROG = r"""
local EIVfx = (function()
%(mod)s
end)()
local prog = %(prog)s
local out = {}
local function emit(...)
  local t = {}
  for i = 1, select('#', ...) do t[#t + 1] = tostring((select(i, ...))) end
  out[#out + 1] = table.concat(t, '|')
end
local function f4(v)
  if v == nil then return '-' end
  if type(v) == 'number' then return string.format('%%.4f', v) end
  return tostring(v)
end
for _, c in ipairs(prog.suggest) do
  local r = EIVfx.suggest(c[1], c[2], c[3], { mobile = c[4] })
  local names, skips = {}, {}
  for _, e in ipairs(r.list) do names[#names + 1] = e.id .. ':' .. tostring(e.score) end
  for _, s in ipairs(r.skipped) do skips[#skips + 1] = s.id .. ':' .. s.reason .. ':' .. tostring(s.cost) end
  emit('S', c[1], c[2], c[3], c[4], r.list[1].id, r.list[1].score, #r.list, r.list[#r.list].id,
       table.concat(names, ','), table.concat(skips, ','))
end
for _, c in ipairs(prog.plans) do
  local p = EIVfx.plan(c[1], c[2], c[3], { mobile = c[4] })
  emit('P', c[1], c[2], c[3], c[4], p.id, p.score, #p.alternatives, #p.skipped, p.limits.budget, p.limits.maxActive)
end
local st = EIVfx.newState()
for _, op in ipairs(prog.scenario) do
  if op[1] == 'try' then
    local ok, rs = EIVfx.tryPlay(st, op[2], op[3], { mobile = op[4] })
    emit('Y', 'try', op[2], f4(op[3]), op[4], ok, rs, #st.active)
  elseif op[1] == 'tick' then
    emit('Y', 'tick', '-', f4(op[2]), '-', '-', tostring(EIVfx.tick(st, op[2])), #st.active)
  else
    emit('Y', 'release', op[2], '-', '-', '-', tostring(EIVfx.release(st, op[2])), #st.active)
  end
end
for _, c in ipairs(prog.anims) do
  local plan, why = EIVfx.animPlan(c[1], { active = c[2], assetId = c[3] })
  if plan then
    emit('A', c[1], c[3], why, plan.priority, f4(plan.weight), plan.stopLower, plan.loop, f4(plan.fadeIn), plan.slot, plan.asset)
  else
    emit('A', c[1], c[3], why, '-', '-', '-', '-', '-', '-', '-')
  end
end
for _, c in ipairs(prog.canplay) do
  local ok, rs = EIVfx.canPlay(c[1], { server = c[2], serverOnly = c[3] })
  emit('C', c[1], c[2], c[3], ok, rs)
end
for _, c in ipairs(prog.limits) do
  local l = EIVfx.limits({ mobile = c[1], budget = c[2], maxActive = c[3] })
  emit('L', c[1], tostring(c[2]), tostring(c[3]), l.budget, l.maxActive)
end
for _, id in ipairs(prog.ids) do
  local d = EIVfx.describe(id)
  if d then
    emit('D', id, d.label, d.cat, d.mode, d.cost, f4(d.cooldown), d.maxActive, #d.objects)
  else
    emit('D', id, '-', '-', '-', '-', '-', '-', '-')
  end
end
io.write(table.concat(out, '\n'), '\n')
"""

JS_RUNNER = r"""
const fs = require('fs');
const EIVfx = require(process.argv[2]);
const prog = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = [];
function emit() { out.push(Array.prototype.slice.call(arguments).map(String).join('|')); }
function f4(v) {
  if (v === null || v === undefined) return '-';
  if (typeof v === 'number') return v.toFixed(4);
  return String(v);
}
function s(x) { return x === null || x === undefined ? 'nil' : String(x); }
for (const c of prog.suggest) {
  const r = EIVfx.suggest(c[0], c[1], c[2], { mobile: c[3] });
  const names = r.list.map(e => e.id + ':' + e.score);
  const skips = r.skipped.map(e => e.id + ':' + e.reason + ':' + e.cost);
  emit('S', c[0], c[1], c[2], c[3], r.list[0].id, r.list[0].score, r.list.length, r.list[r.list.length - 1].id,
       names.join(','), skips.join(','));
}
for (const c of prog.plans) {
  const p = EIVfx.plan(c[0], c[1], c[2], { mobile: c[3] });
  emit('P', c[0], c[1], c[2], c[3], p.id, p.score, p.alternatives.length, p.skipped.length, p.limits.budget, p.limits.maxActive);
}
const st = EIVfx.newState();
for (const op of prog.scenario) {
  if (op[0] === 'try') {
    const r = EIVfx.tryPlay(st, op[1], op[2], { mobile: op[3] });
    emit('Y', 'try', op[1], f4(op[2]), op[3], r.ok, r.reason, st.active.length);
  } else if (op[0] === 'tick') {
    emit('Y', 'tick', '-', f4(op[1]), '-', '-', EIVfx.tick(st, op[1]), st.active.length);
  } else {
    emit('Y', 'release', op[1], '-', '-', '-', EIVfx.release(st, op[1]), st.active.length);
  }
}
for (const c of prog.anims) {
  const r = EIVfx.animPlan(c[0], { active: c[1] || {}, assetId: c[2] });
  const p = r.plan;
  if (p) {
    emit('A', c[0], c[2], r.reason, p.priority, f4(p.weight), p.stopLower, p.loop, f4(p.fadeIn), p.slot, p.asset);
  } else {
    emit('A', c[0], c[2], r.reason, '-', '-', '-', '-', '-', '-', '-');
  }
}
for (const c of prog.canplay) {
  const r = EIVfx.canPlay(c[0], { server: c[1], serverOnly: c[2] });
  emit('C', c[0], c[1], c[2], r.ok, r.reason);
}
for (const c of prog.limits) {
  const l = EIVfx.limits({ mobile: c[0], budget: c[1], maxActive: c[2] });
  emit('L', c[0], s(c[1]), s(c[2]), l.budget, l.maxActive);
}
for (const id of prog.ids) {
  const d = EIVfx.describe(id);
  if (d) emit('D', id, d.label, d.cat, d.mode, d.cost, f4(d.cooldown), d.maxActive, d.objects.length);
  else emit('D', id, '-', '-', '-', '-', '-', '-', '-');
}
process.stdout.write(out.join('\n') + '\n');
"""


def run_js(cases):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(cases, fh, ensure_ascii=False)
        progp = fh.name
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
        fh.write(JS_RUNNER)
        rp = fh.name
    try:
        r = subprocess.run(["node", rp, LUA_JS, progp], capture_output=True, text=True, timeout=280)
        if r.returncode != 0:
            raise RuntimeError("JS hatası: " + (r.stderr or "")[:1500])
        return r.stdout
    finally:
        os.unlink(progp)
        os.unlink(rp)


def run_lua(cases):
    mod = open(LUA_MOD, encoding="utf-8").read()
    prog = LUA_PROG % {"mod": mod, "prog": lua_lit(cases)}
    out = V.run_lua_program(prog)
    # Lua tamponu '\\n' dizisini çözmez (fengari io.write) → gerçek satır sonuna çevir
    return out.replace("\\n", "\n")


def build_cases():
    ids = [p["id"] for p in json.load(open(BV.LIB, encoding="utf-8"))["presets"]]
    suggest = [[c, e, t, m] for c in CTXS for e in EVENTS for t in TARGETS for m in MOBILES]
    canplay = [[i, srv, so] for i in ids for srv in (False, True) for so in (False, True)]
    return {
        "suggest": suggest,
        "plans": PLAN_CASES,
        "scenario": SCENARIO,
        "anims": ANIM_CASES,
        "canplay": canplay,
        "limits": LIMIT_CASES,
        "ids": ids,
    }, ids


def main():
    fails = []

    def check(c, m):
        print(("  [OK] " if c else "  [FAIL] ") + m)
        if not c:
            fails.append(m)

    print("== 1) kütüphane ↔ modüller senkron (elle düzenleme yasak)")
    r = subprocess.run([sys.executable, BUILDER, "--check"], capture_output=True, text=True, timeout=120)
    check(r.returncode == 0, "build_vfx_lua.py --check: %s" % (r.stdout.strip().splitlines() or ["?"])[-1][:110])

    cases, ids = build_cases()
    print("== 2) aynı girdiler iki dilde koşuluyor (%d suggest · %d plan · %d senaryo · %d anim · %d yetki)"
          % (len(cases["suggest"]), len(cases["plans"]), len(cases["scenario"]), len(cases["anims"]), len(cases["canplay"])))
    js = run_js(cases).rstrip("\n").split("\n")
    lua = run_lua(cases).rstrip("\n").split("\n")

    counts = {k: 0 for k in "SPYACLD"}
    for ln in js:
        if ln[:1] in counts:
            counts[ln[0]] += 1
    check(len(js) == len(lua), "satır sayısı eşit (JS %d · Lua %d)" % (len(js), len(lua)))
    check(counts["S"] == len(cases["suggest"]), "suggest: %d girdi tarandı" % counts["S"])
    check(counts["Y"] == len(cases["scenario"]), "senaryo: %d adım koşuldu" % counts["Y"])
    check(counts["A"] == len(cases["anims"]), "animPlan: %d girdi tarandı" % counts["A"])
    check(counts["C"] == len(cases["canplay"]), "canPlay: %d girdi tarandı" % counts["C"])
    check(counts["D"] == len(ids), "describe: %d preset tarandı" % counts["D"])

    diff = [(i, a, b) for i, (a, b) in enumerate(zip(js, lua)) if a != b]
    if len(js) != len(lua):
        diff.append(("uzunluk", "JS %d satır" % len(js), "Lua %d satır" % len(lua)))
    print("== 3) karşılaştırma")
    check(not diff, "iki dil BAYT birebir aynı karar verdi (%d fark)" % len(diff))
    for i, a, b in diff[:6]:
        print("    fark[%s]\n      JS : %s\n      Lua: %s" % (i, a[:150], b[:150]))

    if diff:
        print("\nSONUÇ: BAŞARISIZ (%d)" % len(diff))
        return 1
    total = len(js)
    print("\n%s" % ("-" * 70))
    for name, cnt in (("suggest (liste+sıra+puan)", counts["S"]), ("plan", counts["P"]), ("zaman çizelgesi", counts["Y"]),
                      ("animPlan", counts["A"]), ("canPlay", counts["C"]), ("limits", counts["L"]), ("describe", counts["D"])):
        print("  %-26s %5d satır birebir" % (name, cnt))
    print("\nSONUÇ: GEÇTİ — Lua ≡ JS (%d satır, fark yok)" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
