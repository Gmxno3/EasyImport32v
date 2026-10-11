#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAPI: EIVfx — Roblox dünya efekti · karakter animasyonu · etkileşim modülü (v34)

Kontroller (kullanıcının istediği başlıklarla):
  1) Kütüphane bütünlüğü + gerekçe (why) ve kategori dağılımı
  2) Doğru bağlam için doğru efekt seçimi · yanlış bağlamda düzeltme
  3) Efekt EKLEMEMEK de karar (decide_none) · UI olayında mevcut animasyon sistemini yeniden kullan
  4) Performans: mobil bütçesi ağır efektleri düşürür (sebebiyle birlikte)
  5) Desteklenmeyen API özelliği REDDEDİLİR (üreteç beyaz listesi)
  6) Tekrar sınırlama: cooldown · eşzamanlı sınır · genel kapasite · aynı karede çift tetikleme
  7) Temizlik: nesneler süre sonunda yok edilir, durum kaydı düşer (sızıntı yok)
  8) Karakter animasyonu: öncelik/ağırlık/çakışma yönetimi ve "kimlik yoksa oynatma" (uydurmama)
  9) İstemci–sunucu sorumluluğu: görsel istemcide, oyun durumu sunucuda (yetki reddi kanıtlı)
 10) Çalışma zamanı: doğru nesneler + doğru özellik değerleri (parçacık/iz/hüzme/vurgu/kamera/prompt)

Sahte Roblox bu dosyanın içindedir (paylaşılan mock'a dokunulmaz: mevcut kapılar etkilenmez).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "assistant", "tools"))
import build_vfx_lua as BV  # noqa: E402
import verify_anim as V  # noqa: E402

LIB = os.path.join(ROOT, "assistant", "vfx", "vfx-library.json")

# ---------------------------------------------------------------- sahte Roblox (yalnız EIVfx'in kullandığı API)
MOCK = r"""
local ALL, PENDING, EMITS, TWEENS = {}, {}, {}, {}
local KNOWN = { ScreenGui = true, Frame = true, Attachment = true, ParticleEmitter = true, PointLight = true,
  Trail = true, Beam = true, Highlight = true, ColorCorrectionEffect = true, BlurEffect = true, BloomEffect = true,
  Atmosphere = true, Animation = true, Humanoid = true, Animator = true, ProximityPrompt = true, ClickDetector = true,
  Tool = true, RemoteEvent = true, Model = true, Part = true, Camera = true }
local function classList(cls)
  if cls == "Part" then return { "BasePart", "Instance" } end
  if cls == "Model" then return { "PVInstance", "Instance" } end
  if cls == "Camera" then return { "Instance" } end
  if cls == "Humanoid" or cls == "Animator" or cls == "Animation" then return { "Instance" } end
  return { "Instance" }
end
local function makeInst(cls, name)
  local o = { ClassName = cls, Name = name or cls, children = {}, Parent = nil, destroyed = false, attrs = {} }
  o.IsA = function(self, c) if self.ClassName == c then return true end for _, k in ipairs(classList(cls)) do if k == c then return true end end return false end
  o.GetChildren = function(self) return self.children end
  o.FindFirstChild = function(self, n) for _, c in ipairs(self.children) do if c.Name == n then return c end end return nil end
  o.FindFirstChildOfClass = function(self, c) for _, ch in ipairs(self.children) do if ch.ClassName == c then return ch end end return nil end
  o.GetAttribute = function(self, k) return self.attrs[k] end
  o.SetAttribute = function(self, k, v) self.attrs[k] = v end
  o.Destroy = function(self)
    self.destroyed = true
    local p = self.Parent
    if p then for i, c in ipairs(p.children) do if c == self then table.remove(p.children, i) break end end end
    self.Parent = nil
  end
  if cls == "ParticleEmitter" then o.Emit = function(self, n) EMITS[#EMITS + 1] = { emitter = self, n = n } end end
  if cls == "Humanoid" or cls == "Animator" then
    o.LoadAnimation = function(self, anim)
      local track = { anim = anim, plays = 0, stops = 0, Priority = nil,
        Play = function(self2, fade, weight) self2.plays = self2.plays + 1; self2.fadeIn = fade; self2.weight = weight end,
        Stop = function(self2, fade) self2.stops = self2.stops + 1; self2.fadeOut = fade end }
      return track
    end
  end
  local proxy
  proxy = setmetatable({}, { __index = o, __newindex = function(t, k, v)
    if k == "Parent" then
      local oldp = o.Parent
      if oldp then for i, c in ipairs(oldp.children) do if c == t then table.remove(oldp.children, i) break end end end
      o.Parent = v
      if v then v.children[#v.children + 1] = t end
    else o[k] = v end
  end })
  ALL[#ALL + 1] = proxy
  return proxy
end
local services = setmetatable({}, { __index = function(t, k)
  if k == "Lighting" or k == "ReplicatedStorage" or k == "RunService" then
    local s = makeInst("Frame", k); rawset(t, k, s); return s
  end
  return nil
end })
Instance = { new = function(cls) return makeInst(cls) end }
game = { GetService = function(_, n) return services[n] end }
workspace = { CurrentCamera = makeInst("Camera", "Camera") }
TweenInfo = { new = function(d, s, dir, rep, rev, dl) return { d = d, s = s, dir = dir, rep = rep, rev = rev, dl = dl } end }
local tweenSvc = { Create = function(_, obj, info, goal)
  local tw = { obj = obj, info = info, goal = goal }
  tw.Play = function(self) TWEENS[#TWEENS + 1] = { obj = obj, info = info, goal = goal }
    for k, v in pairs(goal) do obj[k] = v end end
  return tw
end }
services.TweenService = tweenSvc
local base = game.GetService
game.GetService = function(self, n) if n == "TweenService" then return tweenSvc end return base(self, n) end
local Task = {}
Task.spawn = function(f) f() end
Task.wait = function() return 0 end
Task.delay = function(t, f) PENDING[#PENDING + 1] = { t = t, f = f } end
_G.task = Task
local function runPending() local p = PENDING; PENDING = {}; for _, e in ipairs(p) do e.f() end end
local V2, V3 = {}, {}
V2.new = function(x, y) return { X = x, Y = y } end
V3.new = function(x, y, z) return { X = x, Y = y, Z = z, __add = true } end
Vector2 = V2
Vector3 = { new = function(x, y, z)
  local v = { X = x, Y = y, Z = z }
  setmetatable(v, { __add = function(a, b) return Vector3.new(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end })
  return v end }
NumberRange = { new = function(a, b) return { Min = a, Max = b } end }
Color3 = { fromRGB = function(r, g, b) return { R = r, G = g, B = b } end, new = function(r, g, b) return { R = r, G = g, B = b } end }
ColorSequenceKeypoint = { new = function(t, c) return { Time = t, Value = c } end }
ColorSequence = { new = function(k) return { keypoints = k } end }
NumberSequenceKeypoint = { new = function(t, v) return { Time = t, Value = v } end }
NumberSequence = { new = function(k) return { keypoints = k } end }
Enum = setmetatable({}, { __index = function(_, k)
  return setmetatable({}, { __index = function(_, k2) return k .. "." .. k2 end })
end })
local function findAll(cls)
  local out = {}
  for _, o in ipairs(ALL) do if o.ClassName == cls and not o.destroyed then out[#out + 1] = o end end
  return out
end
local function findName(n)
  local out = {}
  for _, o in ipairs(ALL) do if o.Name == n and not o.destroyed then out[#out + 1] = o end end
  return out
end
"""

PROG = r"""
-- <<PURE>>  (kütüphane gövdesi buraya gelir)
"""


def load_lua_module():
    """EIVfx.lua kaynağını döndürür (modül saf; yükleme anında Roblox API'si çağırmaz)."""
    return open(os.path.join(ROOT, "assistant", "runtime", "lua", "EIVfx.lua"), encoding="utf-8").read()


def run(prog):
    out = V.run_lua_program(MOCK + "\nlocal EIVfx = (function()\n" + load_lua_module() + "\nend)()\n" + prog)
    # Lua tarafındaki metin '\\n' dizisi gerçek satır sonuna çevrilir (fengari io tamponu kaçışları çözmez)
    return out.replace(chr(92) + "n", "\n")


def main():
    fails = []

    def check(c, m):
        print(("  [OK] " if c else "  [FAIL] ") + m)
        if not c:
            fails.append(m)

    lib = json.load(open(LIB, encoding="utf-8"))
    presets = {p["id"]: p for p in lib["presets"]}

    print("== 1) kütüphane bütünlüğü ve gerekçe")
    check(len(presets) == 32, "32 preset (dünya · ışık · karakter · kamera · etkileşim · karar): %d" % len(presets))
    cats = {}
    for p in presets.values():
        cats[p["cat"]] = cats.get(p["cat"], 0) + 1
    check(all(cats.get(k, 0) > 0 for k in ("world", "post", "char", "cam", "interact", "decide")),
          "tüm kategoriler dolu: %s" % ", ".join("%s=%d" % kv for kv in sorted(cats.items())))
    check(all(p["why"].strip() and p["why"].endswith(".") for p in presets.values()),
          "her preset GEREKÇE taşır (why) — gerekçesiz efekt kütüphaneye giremez")
    api_classes = {c for p in presets.values() for c in p["objects"]}
    check("ParticleEmitter" in api_classes and "Trail" in api_classes and "Beam" in api_classes
          and "Highlight" in api_classes and "ProximityPrompt" in api_classes and "Animation" in api_classes,
          "istenen Roblox sınıfları kapsanıyor: %s" % ", ".join(sorted(api_classes)))

    print("== 2) doğru bağlam → doğru seçim · yanlış bağlamda düzeltme")
    out = run(
        "local cases = {\n"
        "  {'combat','hit','npc',{}}, {'combat','hit_taken','player',{}}, {'simulator','pickup','part',{}},\n"
        "  {'obby','land','player',{}}, {'rpg','cast','player',{}}, {'horror','zone_enter','world',{}},\n"
        "  {'combat','zzz','npc',{}}, {'ui','menu','ui',{}}, {'racing','sprint','player',{}},\n"
        "  {'rpg','quest_target','part',{}},\n"
        "  {'combat','hit','npc',{mobile=true}},\n"
        "}\n"
        "for _, c in ipairs(cases) do\n"
        "  local r = EIVfx.suggest(c[1], c[2], c[3], c[4] or {})\n"
        "  io.write(string.format('P|%s|%s|%s|%s|%s|%d\\n', c[1], c[2], c[3], tostring(c[4].mobile or false), r.list[1].id, r.list[1].score))\n"
        "  io.write('K|' .. r.list[1].id .. '|' .. r.list[1].why .. '\\n')\n"
        "end\n")
    rows = [ln.split("|") for ln in out.split("\n") if ln.startswith("P|")]
    pick = {(r[1], r[2], r[3], r[4]): r[5] for r in rows}
    check(pick.get(("combat", "hit", "npc", "false")) == "world_hit_spark",
          "PvP/dövüş · isabet · NPC → Çarpma Kıvılcımı (%s)" % pick.get(("combat", "hit", "npc", "false")))
    check(pick.get(("simulator", "pickup", "part", "false")) == "world_pickup_pop",
          "Simulator · toplama · eşya → Toplama Patlaması (%s)" % pick.get(("simulator", "pickup", "part", "false")))
    check(pick.get(("obby", "land", "player", "false")) in ("char_land_recover", "world_impact_dust"),
          "Parkur · iniş · oyuncu → iniş animasyonu/tozu (%s)" % pick.get(("obby", "land", "player", "false")))
    check(pick.get(("rpg", "cast", "player", "false")) in ("world_vfx_combo_stage", "world_lightning_beam"),
          "RPG · büyü · oyuncu → büyü efekti (%s)" % pick.get(("rpg", "cast", "player", "false")))
    check(pick.get(("horror", "zone_enter", "world", "false")) == "post_mood_atmosphere",
          "Korku · bölgeye giriş → atmosfer (sunucu) (%s)" % pick.get(("horror", "zone_enter", "world", "false")))
    check(pick.get(("racing", "sprint", "player", "false")) in ("world_speed_trail", "char_run_cycle"),
          "Yarış · koşu · oyuncu → hız izi/koşu animasyonu (%s)"
          % pick.get(("racing", "sprint", "player", "false")))
    alt = run("local r = EIVfx.suggest('racing','sprint','player',{})\n"
              "for i, x in ipairs(r.list) do io.write('A' .. i .. '|' .. x.id .. '\\n') end\n")
    alt_ids = [l.split("|")[1] for l in alt.split("\n") if l.startswith("A")]
    check("char_run_cycle" in alt_ids and "world_speed_trail" in alt_ids,
          "iki doğru seçenek de listede, karar alternatifli: %s" % ", ".join(alt_ids[:4]))
    check(pick.get(("rpg", "quest_target", "part", "false")) in ("interact_proximity_prompt", "world_quest_highlight"),
          "RPG · görev hedefi → ucuz vurgu (%s)" % pick.get(("rpg", "quest_target", "part", "false")))

    print("== 3) efekt EKLEMEMEK de karar · UI'da mevcut sistemi yeniden kullan")
    check(pick.get(("combat", "zzz", "npc", "false")) == "decide_none",
          "Tanınmayan olay → 'Efekt yok' kararı (uydurma efekt üretilmez)")
    check(pick.get(("ui", "menu", "ui", "false")) == "reuse_ui_anim",
          "Arayüz olayı → 'mevcut UI animasyonunu kullan' (yeni efekt eklenmez)")
    many = run("local r = EIVfx.suggest('combat','hit','npc',{})\n"
               "io.write('N|' .. tostring(#r.list) .. '\\n')\n"
               "io.write('L|' .. r.list[#r.list].id .. '\\n')\n")
    check("N|" in many and int([l for l in many.split("\n") if l.startswith("N|")][0].split("|")[1]) >= 2,
          "öneri listesi alternatiflerle döner (karar tek seçenek değil)")
    check([l for l in many.split("\n") if l.startswith("L|")][0].split("|")[1] == "decide_none",
          "listenin sonu her zaman 'efekt yok' seçeneğidir")

    print("== 4) performans: mobil bütçesi")
    mob = run("local r = EIVfx.suggest('rpg','cast','player',{mobile=true})\n"
              "io.write('TOP|' .. r.list[1].id .. '|' .. tostring(r.list[1].cost) .. '\\n')\n"
              "for _, s in ipairs(r.skipped) do io.write('SKIP|' .. s.id .. '|' .. s.reason .. '\\n') end\n")
    top = [l for l in mob.split("\n") if l.startswith("TOP|")][0].split("|")
    skips = {l.split("|")[1]: l.split("|")[2] for l in mob.split("\n") if l.startswith("SKIP|")}
    check(top[1] != "world_vfx_combo_stage" and int(top[2]) <= 1,
          "mobilde ağır efekt seçilmez, hafif havuzdan seçer (%s · maliyet %s)" % (top[1], top[2]))
    check(skips.get("world_vfx_combo_stage") == "mobil" or skips.get("world_vfx_combo_stage") == "butce",
          "düşürülen efekt SEBEBİYLE rapor edilir (sessizce kaybolmaz): %s" % skips.get("world_vfx_combo_stage"))
    check("world_lightning_beam" in skips, "mobil dışı işaretli efektler de düşürülür (%s)" % ", ".join(sorted(skips)))

    print("== 5) desteklenmeyen Roblox API özelliği reddedilir (üreteç beyaz listesi)")
    bad = json.loads(json.dumps(lib))
    bad["presets"][0]["props"]["ParticleEmitter"]["Gravity"] = {"t": "n", "v": 5}   # Roblox'ta böyle bir özellik yok
    try:
        BV.validate(bad)
        check(False, "uydurma özellik yakalanmadı!")
    except SystemExit as e:
        check("Gravity" in str(e) or "beyaz liste" in str(e), "uydurma özellik reddedildi: %s" % str(e)[:80])
    bad2 = json.loads(json.dumps(lib))
    bad2["presets"][0]["props"]["ParticleEmitter"]["Shape"] = {"t": "en", "v": ["ParticleEmitterShape", "Torus"]}
    try:
        BV.validate(bad2)
        check(False, "uydurma enum öğesi yakalanmadı!")
    except SystemExit as e:
        check("Torus" in str(e), "Roblox'ta olmayan enum öğesi reddedildi: %s" % str(e)[:80])
    bad3 = json.loads(json.dumps(lib))
    bad3["presets"][0]["objects"].append("Trail2")
    try:
        BV.validate(bad3)
        check(False, "uydurma sınıf yakalanmadı!")
    except SystemExit as e:
        check("Trail2" in str(e), "uydurma sınıf reddedildi: %s" % str(e)[:80])

    print("== 6) tekrar sınırlama (cooldown · eşzamanlılık · kapasite · aynı karede çift tetikleme)")
    dup = run(
        "local s = EIVfx.newState()\n"
        "local a, _ = EIVfx.tryPlay(s, 'world_hit_spark', 1.0, {})\n"
        "local _, rb = EIVfx.tryPlay(s, 'world_hit_spark', 1.05, {})\n"
        "local c, _ = EIVfx.tryPlay(s, 'world_hit_spark', 1.25, {})\n"
        "io.write('T|' .. tostring(a) .. '|' .. rb .. '|' .. tostring(c) .. '\\n')\n"
        "local s2 = EIVfx.newState()\n"
        "for i = 1, 3 do EIVfx.tryPlay(s2, 'world_vfx_combo_stage', i, {}) end\n"
        "local _, rd = EIVfx.tryPlay(s2, 'world_vfx_combo_stage', 9.0, {})\n"
        "io.write('S|' .. rd .. '|' .. tostring(EIVfx.tick(s2, 9.0)) .. '\\n')\n"
        "local dolgu = EIVfx.newState()\n"
        "for i = 1, 30 do dolgu.active[i] = { id = 'dolgu' .. i, t = 0, dur = 99, seq = i } end\n"
        "local _, rk = EIVfx.tryPlay(dolgu, 'world_hit_spark', 99.0, {mobile = true})\n"
        "io.write('KAP|' .. rk .. '\\n')\n"
        "local az = EIVfx.newState()\n"
        "for i = 1, 23 do az.active[i] = { id = 'dolgu' .. i, t = 0, dur = 99, seq = i } end\n"
        "local _, rk2 = EIVfx.tryPlay(az, 'world_hit_spark', 99.0, {mobile = true})\n"
        "io.write('AZ|' .. rk2 .. '\\n')\n"
        "io.write('C|' .. tostring(EIVfx.limits({mobile = true}).maxActive) .. '\\n')\n")
    t = [l for l in dup.split("\n") if l.startswith("T|")][0].split("|")
    check(t[1] == "true" and t[2] == "bekleme" and t[3] == "true",
          "aynı karede ikinci tetikleme engellenir (cooldown), süre geçince izin verilir")
    s = [l for l in dup.split("\n") if l.startswith("S|")][0].split("|")
    check(s[1] == "es-zamanli", "aynı efekten eşzamanlı üst sınır aşılamaz (%s)" % s[1])
    check(int(s[2]) >= 1, "süresi dolan kayıtlar tick ile düşer (%s kayıt)" % s[2])
    cap = [l for l in dup.split("\n") if l.startswith("KAP|")][0].split("|")
    az = [l for l in dup.split("\n") if l.startswith("AZ|")][0].split("|")
    check(cap[1] == "kapasite", "genel kapasite dolunca yeni efekt başlamaz (%s)" % cap[1])
    check(az[1] == "ok", "kapasite sınırının altında efekt başlar (%s)" % az[1])
    c = [l for l in dup.split("\n") if l.startswith("C|")][0].split("|")
    check(int(c[1]) == 24, "mobil eşzamanlı sınırı 24 (ölçülen: %s)" % c[1])

    print("== 7) temizlik: nesneler yok edilir, durum düşer")
    clean = run(
        "local host = makeInst('Part', 'Zemin')\n"
        "local r = EIVfx.play(host, 'world_hit_spark', { now = 1.0 })\n"
        "io.write('A|' .. tostring(r.ok) .. '|' .. tostring(r.objects) .. '|' .. r.mode .. '\\n')\n"
        "io.write('N1|' .. tostring(#findAll('ParticleEmitter')) .. '|' .. tostring(#findAll('PointLight')) .. '|' .. tostring(#findAll('Attachment')) .. '\\n')\n"
        "local st = EIVfx.state()\n"
        "io.write('ACT1|' .. tostring(#st.active) .. '\\n')\n"
        "runPending()\n"
        "io.write('N2|' .. tostring(#findAll('ParticleEmitter')) .. '|' .. tostring(#findAll('PointLight')) .. '|' .. tostring(#findAll('Attachment')) .. '\\n')\n"
        "io.write('ACT2|' .. tostring(#EIVfx.state().active) .. '\\n')\n"
        "io.write('EMIT|' .. tostring(#EMITS) .. '|' .. tostring(EMITS[1] and EMITS[1].n or -1) .. '\\n')\n")
    n1 = [l for l in clean.split("\n") if l.startswith("N1|")][0].split("|")
    n2 = [l for l in clean.split("\n") if l.startswith("N2|")][0].split("|")
    act = [l for l in clean.split("\n") if l.startswith("ACT1|")][0].split("|")
    act2 = [l for l in clean.split("\n") if l.startswith("ACT2|")][0].split("|")
    emit = [l for l in clean.split("\n") if l.startswith("EMIT|")][0].split("|")
    check(int(n1[1]) == 1 and int(n1[2]) == 1 and int(n1[3]) == 1,
          "efekt nesneleri kuruldu (parçacık + ışık + bağlantı noktası)")
    check(int(act[1]) == 1, "durum kaydı açıldı (bütçe sayacı)")
    check(int(n2[1]) == 0 and int(n2[2]) == 0 and int(n2[3]) == 0, "süre sonunda HEPSİ yok edildi (sızıntı yok)")
    check(int(act2[1]) == 0, "durum kaydı düştü")
    check(int(emit[1]) == 18 and int(emit[2]) == 1,
          "tek dalga 18 parçacık gönderdi (18 × Emit(1) — sürekli yayın yok, %s çağrı)" % emit[1])

    print("== 8) karakter animasyonu: öncelik · ağırlık · çakışma · kimlik uydurmama")
    anim = run(
        "local m = makeInst('Model', 'NPC'); local h = makeInst('Humanoid', 'Humanoid'); h.Parent = m\n"
        "local an = makeInst('Animator', 'Animator'); an.Parent = h\n"
        "local r1 = EIVfx.play(m, 'char_attack_combo', { now = 1.0 })\n"
        "io.write('NOASSET|' .. tostring(r1.ok) .. '|' .. r1.reason .. '\\n')\n"
        "local r2 = EIVfx.play(m, 'char_attack_combo', { now = 2.0, assetId = 'rbxassetid://123' })\n"
        "io.write('YES|' .. tostring(r2.ok) .. '|' .. tostring(r2.anim.priority) .. '|' .. tostring(r2.anim.weight) .. '|' .. tostring(r2.anim.stopLower) .. '\\n')\n"
        "local pl, why = EIVfx.animPlan('char_attack_combo', { assetId = 'x', active = { action = 'Action2' } })\n"
        "io.write('CONFLICT|' .. why .. '\\n')\n"
        "local pl2, why2 = EIVfx.animPlan('char_hit_react', { assetId = 'x', active = {} })\n"
        "io.write('FLINCH|' .. why2 .. '|' .. tostring(pl2.weight) .. '|' .. tostring(pl2.stopLower) .. '\\n')\n"
        "local pl3 = EIVfx.animPlan('char_run_cycle', { assetId = 'x', active = { movement = 'Idle' } })\n"
        "io.write('RUN|' .. tostring(pl3.stopLower) .. '|' .. tostring(pl3.priority) .. '\\n')\n"
        "local pl4, why4 = EIVfx.animPlan('char_attack_combo', { assetId = 'x', active = { action = { id = 'char_attack_combo', priority = 'Action2' } } })\n"
        "io.write('RETRIG|' .. tostring(pl4 and pl4.priority) .. '|' .. why4 .. '\\n')\n"
        "local pl5, why5 = EIVfx.animPlan('char_hit_react', { assetId = 'x', active = { action = { id = 'char_jump_launch', priority = 'Action' } } })\n"
        "io.write('BLOCK|' .. why5 .. '\\n')\n"
        "local r3 = EIVfx.play(m, 'char_run_cycle', { now = 9.0, assetId = 'rbxassetid://9' })\n"
        "local an = findAll('Animation')\n"
        "io.write('PLAYED|' .. tostring(r3.ok) .. '|' .. tostring(#an) .. '|' .. tostring(an[#an] and an[#an].AnimationId) .. '\\n')\n")
    noasset = [l for l in anim.split("\n") if l.startswith("NOASSET|")][0].split("|")
    yes = [l for l in anim.split("\n") if l.startswith("YES|")][0].split("|")
    conf = [l for l in anim.split("\n") if l.startswith("CONFLICT|")][0].split("|")
    flinch = [l for l in anim.split("\n") if l.startswith("FLINCH|")][0].split("|")
    runrow = [l for l in anim.split("\n") if l.startswith("RUN|")][0].split("|")
    retrig = [l for l in anim.split("\n") if l.startswith("RETRIG|")][0].split("|")
    block = [l for l in anim.split("\n") if l.startswith("BLOCK|")][0].split("|")
    played = [l for l in anim.split("\n") if l.startswith("PLAYED|")][0].split("|")
    check(noasset[1] == "false" and noasset[2] == "asset-eksik",
          "animasyon kimliği yoksa OYNATILMAZ ve uydurulmaz (sebep: %s)" % noasset[2])
    check(yes[1] == "true" and yes[2] == "Action2" and abs(float(yes[3]) - 1.0) < 1e-9 and yes[4] == "true",
          "saldırı Action2 önceliğiyle, tam ağırlıkla ve alttakini durdurarak oynar (%s)" % yes[2])
    check(conf[1] == "oncelik", "aynı slotta aynı öncelik aktifken İKİNCİ animasyon başlatılmaz (%s)" % conf[1])
    check(flinch[1] == "ok" and abs(float(flinch[2]) - 0.85) < 1e-9 and flinch[3] == "false",
          "hasar tepkisi 0.85 ağırlıkla BİNER (yürüyüşü kesmez)")
    check(runrow[1] == "true" and runrow[2] == "Movement",
          "Movement, Idle'ın üstüne yazar (stopLower) ama Action'ı ezmez")
    check(retrig[1] == "Action2" and retrig[2] == "tekrar",
          "AYNI animasyonun yeniden tetiklenmesi engellenmez — kombo zinciri çalışır (%s)" % retrig[2])
    check(block[1] == "oncelik",
          "aynı slotta FARKLI animasyon aynı katmanda başlatılmaz (%s)" % block[1])
    check(played[1] == "true" and int(played[2]) >= 1 and played[3] == "rbxassetid://9",
          "kimliği verilen animasyon gerçekten yüklendi (Animation.AnimationId = %s)" % played[3])

    print("== 9) istemci–sunucu sorumluluğu (yetki kanıtlı)")
    auth = run(
        "local part = makeInst('Part', 'Kutu')\n"
        "local c1 = EIVfx.play(part, 'post_mood_atmosphere', { now = 1.0 })\n"
        "io.write('CLIENT|' .. tostring(c1.ok) .. '|' .. c1.reason .. '\\n')\n"
        "local c2 = EIVfx.play(part, 'interact_proximity_prompt', { now = 1.0 })\n"
        "io.write('CLIENT2|' .. tostring(c2.ok) .. '|' .. c2.reason .. '\\n')\n"
        "local c3 = EIVfx.play(part, 'world_hit_spark', { now = 1.0, serverOnly = true })\n"
        "io.write('SERVERONLY|' .. tostring(c3.ok) .. '|' .. c3.reason .. '\\n')\n"
        "local c4 = EIVfx.play(part, 'interact_proximity_prompt', { now = 2.0, server = true })\n"
        "io.write('SRVOK|' .. tostring(c4.ok) .. '\\n')\n"
        "io.write('ATMOS0|' .. tostring(#findAll('Atmosphere')) .. '\\n')\n"
        "local c5 = EIVfx.play(part, 'post_mood_atmosphere', { now = 3.0, server = true })\n"
        "local atmo = findAll('Atmosphere')[1]\n"
        "io.write('ATMOS|' .. tostring(c5.ok) .. '|' .. tostring(atmo ~= nil) .. '|' .. tostring(atmo and atmo.Parent == game:GetService('Lighting')) .. '\\n')\n")
    cl = [l for l in auth.split("\n") if l.startswith("CLIENT|")][0].split("|")
    cl2 = [l for l in auth.split("\n") if l.startswith("CLIENT2|")][0].split("|")
    so = [l for l in auth.split("\n") if l.startswith("SERVERONLY|")][0].split("|")
    srv = [l for l in auth.split("\n") if l.startswith("SRVOK|")][0].split("|")
    a0 = [l for l in auth.split("\n") if l.startswith("ATMOS0|")][0].split("|")
    at = [l for l in auth.split("\n") if l.startswith("ATMOS|")][0].split("|")
    check(cl[1] == "false" and cl[2] == "yetki-sunucu",
          "istemci, SUNUCU yetkili ortak görünümü (atmosfer) değiştiremez")
    check(cl2[1] == "false" and cl2[2] == "yetki-sunucu",
          "istemci, sunucuda doğrulanacak etkileşimi (ProximityPrompt) kuramaz")
    check(so[1] == "false" and so[2] == "yetki-istemci",
          "sunucu, istemciye ait görseli (kıvılcım) kendi tarafında oynatmaz")
    check(srv[1] == "true", "sunucu tarafında etkileşim (ProximityPrompt) kurulabilir")
    check(int(a0[1]) == 0, "istemci reddi sonrası ortada efekt nesnesi kalmaz (%s)" % a0[1])
    check(at[1] == "true" and at[2] == "true" and at[3] == "true",
          "sunucu tarafında atmosfer kuruldu ve Lighting servisine bağlandı")

    print("== 10) çalışma zamanı: nesne ve özellik değerleri")
    rt = run(
        "local p = makeInst('Part', 'Govde')\n"
        "local r = EIVfx.play(p, 'world_slash_trail', { now = 1.0 })\n"
        "local tr = findAll('Trail')[1]\n"
        "io.write('TRAIL|' .. tostring(r.ok) .. '|' .. tostring(tr.Attachment0 ~= nil) .. '|' .. tostring(tr.Attachment1 ~= nil) .. '|' .. tostring(tr.FaceCamera) .. '\\n')\n"
        "local h = makeInst('Part', 'Hedef')\n"
        "EIVfx.play(h, 'world_quest_highlight', { now = 1.0 })\n"
        "local hi = findAll('Highlight')[1]\n"
        "io.write('HL|' .. tostring(hi.Adornee == h) .. '|' .. tostring(hi.DepthMode) .. '|' .. tostring(hi.FillTransparency) .. '\\n')\n"
        "local cam = workspace.CurrentCamera\n"
        "local before = cam.FieldOfView\n"
        "EIVfx.play(p, 'char_camera_shake', { now = 1.0 })\n"
        "io.write('CAM|' .. tostring(#TWEENS) .. '|' .. tostring(cam.FieldOfView) .. '\\n')\n"
        "local k = makeInst('Part', 'Kutu')\n"
        "EIVfx.play(k, 'interact_click_detector', { now = 1.0, server = true })\n"
        "local cd = findAll('ClickDetector')[1]\n"
        "io.write('CD|' .. tostring(cd.Parent == k) .. '|' .. tostring(cd.MaxActivationDistance) .. '\\n')\n"
        "EIVfx.play(k, 'interact_remote_event', { now = 1.0, server = true })\n"
        "io.write('RE|' .. tostring(#findName('EI_Event')) .. '\\n')\n"
        "local em = findAll('ParticleEmitter')[1]\n"
        "local hitHost = makeInst('Part', 'Vurulan')\n"
        "EIVfx.play(hitHost, 'world_hit_spark', { now = 5.0 })\n"
        "local em2 = findAll('ParticleEmitter')[#findAll('ParticleEmitter')]\n"
        "io.write('PROPS|' .. tostring(em2.Rate) .. '|' .. tostring(em2.LightEmission) .. '|' .. tostring(em2.Shape) .. '|' .. tostring(em2.Texture) .. '\\n')\n"
        "io.write('SEQ|' .. tostring(#em2.Color.keypoints) .. '|' .. em2.Color.keypoints[1].Value.R .. '|' .. tostring(#em2.Size.keypoints) .. '\\n')\n"
        "io.write('PARENT|' .. tostring(em2.Parent.ClassName) .. '|' .. tostring(em2.Parent.Parent == hitHost) .. '\\n')\n")
    trail = [l for l in rt.split("\n") if l.startswith("TRAIL|")][0].split("|")
    hl = [l for l in rt.split("\n") if l.startswith("HL|")][0].split("|")
    cam = [l for l in rt.split("\n") if l.startswith("CAM|")][0].split("|")
    cd = [l for l in rt.split("\n") if l.startswith("CD|")][0].split("|")
    re = [l for l in rt.split("\n") if l.startswith("RE|")][0].split("|")
    pr = [l for l in rt.split("\n") if l.startswith("PROPS|")][0].split("|")
    sq = [l for l in rt.split("\n") if l.startswith("SEQ|")][0].split("|")
    pa = [l for l in rt.split("\n") if l.startswith("PARENT|")][0].split("|")
    check(trail[1] == "true" and trail[2] == "true" and trail[3] == "true" and trail[4] == "true",
          "Trail iki bağlantı noktasıyla kuruldu ve yüze dönük")
    check(hl[1] == "true" and "Occluded" in hl[2] and abs(float(hl[3]) - 0.75) < 1e-9,
          "Highlight hedefe bağlandı (Adornee) ve ucuz vurgu ayarları uygulandı")
    check(int(cam[1]) >= 1 and abs(float(cam[2]) - 78) < 1e-9,
          "kamera geçişi TweenService ile uygulandı (FOV 74 → 78)")
    check(cd[1] == "true" and abs(float(cd[2]) - 12) < 1e-9, "ClickDetector doğru öğeye ve mesafeyle kuruldu")
    check(int(re[1]) == 1, "RemoteEvent kanalı oluşturuldu (oyun sonucu sunucuda)")
    check(int(pr[1]) == 0 and abs(float(pr[2]) - 0.6) < 1e-9 and "Sphere" in pr[3] and pr[4] == "rbxassetid://243098098",
          "parçacık özellikleri kütüphaneden birebir uygulandı (Rate 0 = tek dalga, LightEmission 0.6)")
    check(int(sq[1]) == 3 and int(sq[2]) == 255 and int(sq[3]) == 3, "renk/boyut dizileri gerçek Roblox türlerine çevrildi")
    check(pa[1] == "Attachment" and pa[2] == "true", "parçacık, bağlantı noktası üzerinden hedefe bağlandı")

    print()
    if fails:
        print("SONUÇ: BAŞARISIZ (%d)" % len(fails))
        return 1
    print("SONUÇ: GEÇTİ — dünya efekti · karakter animasyonu · etkileşim motoru kararları doğru ve güvenli")
    return 0


if __name__ == "__main__":
    sys.exit(main())
