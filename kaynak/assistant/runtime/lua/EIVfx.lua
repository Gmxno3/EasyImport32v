-- EasyImport — ROBLOX DÜNYA EFEKTİ · KARAKTER ANİMASYONU · ETKİLEŞİM MOTORU (v34)
--
-- Neden ayrı modül: mevcut EIAnim yalnız GUI (Figma'dan gelen arayüz) animasyonlarını yönetir.
-- Bu modül onun YERİNE geçmez; dünya tarafını ekler: ParticleEmitter / Trail / Beam / Highlight /
-- post-process / karakter animasyonu (Animator + AnimationTrack) / dünya etkileşimi (ProximityPrompt,
-- ClickDetector, Tool, RemoteEvent) ve kamera.
--
-- Kurallar (mevcut sistemin kuralları korunur):
--   • Karar merkezîdir: kütüphane + puanlama; hiçbir yerde "her yere efekt" yok.
--   • Efekt EKLEMEMEK de bir karardır (decide_none) — UI olaylarında mevcut EIAnim yeniden kullanılır.
--   • Animasyon kimlikleri (AnimationId) UYDURULMAZ: proje kendi kimliğini verir; yoksa oynatılmaz.
--   • Görsel efekt istemcide, OYUN SONUCU sunucuda: yetki alanı veriyle belirtilir (authority).
--   • Tekrar sınırlanır: cooldown + eşzamanlı sınır + cihaz bütçesi (mobil = hafif havuz).
--   • Saf Lua bölümü (suggest / tryPlay / animPlan / tick) Roblox API'si KULLANMAZ → Lua ≡ JS parite kapısı.
--
-- Studio notu: modül EKLENTİ içine gömülür (build_rbxmx.py) ve yükleme anında Roblox API'sine dokunmaz.

local EIVfx = {}

-- <<EI_VFX_DATA>>
local VFX_PRESETS = {
  {["id"] = "world_hit_spark", ["cat"] = "world", ["label"] = "Çarpma Kıvılcımı", ["ctx"] = {"combat", "pvp", "rpg", "action", "survival"}, ["events"] = {"hit", "damage"}, ["targets"] = {"npc", "player", "part"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.6, ["cooldown"] = 0.12, ["maxActive"] = 14, ["objects"] = {"Attachment", "ParticleEmitter", "PointLight"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Hit"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Kivilcim"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243098098"}, ["Rate"] = {["t"] = "n", ["v"] = 0}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.15, 0.35}}, ["Speed"] = {["t"] = "nr", ["v"] = {18, 26}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {180, 180}}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.5}, {0.2, 0.15}, {1, 0}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0}, {0.4, 0.35}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {255, 235, 170}}, {0.5, {255, 190, 80}}, {1, {255, 150, 60}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.6}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0}, ["Acceleration"] = {["t"] = "v3", ["v"] = {0, -40, 0}}, ["Drag"] = {["t"] = "n", ["v"] = 6}, ["Rotation"] = {["t"] = "nr", ["v"] = {0, 360}}, ["RotSpeed"] = {["t"] = "nr", ["v"] = {-220, 220}}, ["ZOffset"] = {["t"] = "n", ["v"] = 2}, ["Shape"] = {["t"] = "en", ["v"] = {"ParticleEmitterShape", "Sphere"}}, ["ShapeStyle"] = {["t"] = "en", ["v"] = {"ParticleEmitterShapeStyle", "Volume"}}, ["EmissionDirection"] = {["t"] = "en", ["v"] = {"NormalId", "Top"}}}, ["PointLight"] = {["Color"] = {["t"] = "c3", ["v"] = {255, 190, 110}}, ["Brightness"] = {["t"] = "n", ["v"] = 2}, ["Range"] = {["t"] = "n", ["v"] = 9}, ["Shadows"] = {["t"] = "b", ["v"] = false}}}, ["burst"] = {["times"] = {["t"] = "n", ["v"] = 18}, ["count"] = {["t"] = "n", ["v"] = 1}}, ["cleanup"] = "delay", ["why"] = "Kısa ve sonlu: darbe anını okutur, sürekli yanmaz. Mobilde tek emitter + sonlu ömür.", ["freq"] = "per_event"},
  {["id"] = "world_slash_trail", ["cat"] = "world", ["label"] = "Kılıç İzi (Trail)", ["ctx"] = {"combat", "pvp", "rpg", "action"}, ["events"] = {"swing", "attack", "tool_activate"}, ["targets"] = {"player", "npc", "tool"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.35, ["cooldown"] = 0.18, ["maxActive"] = 8, ["objects"] = {"Attachment", "Trail"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Swing"}}, ["Trail"] = {["Name"] = {["t"] = "s", ["v"] = "Iz"}, ["Lifetime"] = {["t"] = "n", ["v"] = 0.22}, ["MinLength"] = {["t"] = "n", ["v"] = 0.15}, ["FaceCamera"] = {["t"] = "b", ["v"] = true}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {255, 255, 255}}, {1, {150, 200, 255}}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.1}, {1, 1}}}, ["WidthScale"] = {["t"] = "nseq", ["v"] = {{0, 1}, {1, 0.15}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.4}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0.2}, ["TextureMode"] = {["t"] = "en", ["v"] = {"TextureMode", "Stretch"}}}}, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Trail, parçacıktan ucuzdur ve saldırının YÖNÜNÜ gösterir (görsel okunabilirlik > süs).", ["freq"] = "per_event"},
  {["id"] = "world_muzzle_flash", ["cat"] = "world", ["label"] = "Namlu Ateşi", ["ctx"] = {"combat", "pvp", "shooter", "action"}, ["events"] = {"fire", "shoot", "tool_activate"}, ["targets"] = {"tool", "player", "part"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.15, ["cooldown"] = 0.08, ["maxActive"] = 10, ["objects"] = {"Attachment", "ParticleEmitter", "PointLight"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Muzzle"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Alev"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243660364"}, ["Rate"] = {["t"] = "n", ["v"] = 0}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.05, 0.12}}, ["Speed"] = {["t"] = "nr", ["v"] = {12, 20}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {12, 12}}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.6}, {1, 0.1}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.1}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {255, 240, 200}}, {1, {255, 140, 40}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 1}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0}, ["ZOffset"] = {["t"] = "n", ["v"] = 3}}, ["PointLight"] = {["Color"] = {["t"] = "c3", ["v"] = {255, 200, 120}}, ["Brightness"] = {["t"] = "n", ["v"] = 3}, ["Range"] = {["t"] = "n", ["v"] = 12}, ["Shadows"] = {["t"] = "b", ["v"] = false}}}, ["burst"] = {["times"] = {["t"] = "n", ["v"] = 1}, ["count"] = {["t"] = "n", ["v"] = 6}}, ["cleanup"] = "delay", ["why"] = "Tek karelik ışık: ateşin ANLIK olduğunu gösterir; kalıcı ışık yer (performans).", ["freq"] = "per_event"},
  {["id"] = "world_impact_dust", ["cat"] = "world", ["label"] = "İniş Tozu (halka)", ["ctx"] = {"obby", "parkour", "combat", "survival", "simulator"}, ["events"] = {"land", "impact", "jump_land"}, ["targets"] = {"player", "npc", "part"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.8, ["cooldown"] = 0.25, ["maxActive"] = 6, ["objects"] = {"Attachment", "ParticleEmitter"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Land"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Toz"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243660364"}, ["Rate"] = {["t"] = "n", ["v"] = 0}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.4, 0.8}}, ["Speed"] = {["t"] = "nr", ["v"] = {4, 9}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {70, 70}}, ["Acceleration"] = {["t"] = "v3", ["v"] = {0, -8, 0}}, ["Drag"] = {["t"] = "n", ["v"] = 3}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.8}, {1, 2.2}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.35}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {210, 200, 180}}, {1, {170, 165, 150}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0}, ["LightInfluence"] = {["t"] = "n", ["v"] = 1}, ["Rotation"] = {["t"] = "nr", ["v"] = {0, 360}}, ["Shape"] = {["t"] = "en", ["v"] = {"ParticleEmitterShape", "Disc"}}, ["EmissionDirection"] = {["t"] = "en", ["v"] = {"NormalId", "Top"}}}}, ["burst"] = {["times"] = {["t"] = "n", ["v"] = 1}, ["count"] = {["t"] = "n", ["v"] = 10}}, ["cleanup"] = "delay", ["why"] = "İnişin ağırlığını gösterir; sürekli değil, tek dalga.", ["freq"] = "per_event"},
  {["id"] = "world_pickup_pop", ["cat"] = "world", ["label"] = "Toplama Patlaması", ["ctx"] = {"simulator", "tycoon", "rpg", "casual", "obby"}, ["events"] = {"pickup", "collect", "claim"}, ["targets"] = {"part", "item", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.5, ["cooldown"] = 0.05, ["maxActive"] = 12, ["objects"] = {"Attachment", "ParticleEmitter"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Pick"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Parlama"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243098098"}, ["Rate"] = {["t"] = "n", ["v"] = 0}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.25, 0.5}}, ["Speed"] = {["t"] = "nr", ["v"] = {6, 12}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {180, 180}}, ["Acceleration"] = {["t"] = "v3", ["v"] = {0, 6, 0}}, ["Drag"] = {["t"] = "n", ["v"] = 2}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.35}, {1, 0}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.1}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {255, 245, 190}}, {1, {255, 200, 70}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.8}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0}}}, ["burst"] = {["times"] = {["t"] = "n", ["v"] = 1}, ["count"] = {["t"] = "n", ["v"] = 8}}, ["cleanup"] = "delay", ["why"] = "Ödül anında kısa vurgu; kalıcı bilgi mevcut UI animasyon sistemiyle verilir (yeniden kullanım).", ["freq"] = "per_event"},
  {["id"] = "world_death_burst", ["cat"] = "world", ["label"] = "Yok Olma Patlaması", ["ctx"] = {"combat", "pvp", "rpg", "action", "survival"}, ["events"] = {"death", "defeat", "destroy"}, ["targets"] = {"npc", "part", "item"}, ["authority"] = "client", ["cost"] = 2, ["mobile"] = true, ["trig"] = "event", ["dur"] = 1.0, ["cooldown"] = 0.3, ["maxActive"] = 5, ["objects"] = {"Attachment", "ParticleEmitter", "Highlight"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Death"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Dagilma"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243098098"}, ["Rate"] = {["t"] = "n", ["v"] = 0}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.4, 0.9}}, ["Speed"] = {["t"] = "nr", ["v"] = {10, 18}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {180, 180}}, ["Acceleration"] = {["t"] = "v3", ["v"] = {0, -25, 0}}, ["Drag"] = {["t"] = "n", ["v"] = 1.5}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.6}, {1, 0.1}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0}, {0.5, 0.4}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {255, 120, 90}}, {1, {120, 40, 40}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.5}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0.3}}, ["Highlight"] = {["FillColor"] = {["t"] = "c3", ["v"] = {255, 90, 70}}, ["FillTransparency"] = {["t"] = "n", ["v"] = 0.55}, ["OutlineColor"] = {["t"] = "c3", ["v"] = {255, 255, 255}}, ["OutlineTransparency"] = {["t"] = "n", ["v"] = 0}, ["DepthMode"] = {["t"] = "en", ["v"] = {"HighlightDepthMode", "AlwaysOnTop"}}}}, ["burst"] = {["times"] = {["t"] = "n", ["v"] = 1}, ["count"] = {["t"] = "n", ["v"] = 14}}, ["cleanup"] = "delay", ["why"] = "Yok olma anını netleştirir; Highlight okunurluğu artırır ve süre sonunda temizlenir.", ["freq"] = "per_event"},
  {["id"] = "world_heal_aura", ["cat"] = "world", ["label"] = "Şifa Aurası (durum boyunca)", ["ctx"] = {"rpg", "survival", "combat", "simulator"}, ["events"] = {"heal_start", "buff_start"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 2, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0, ["maxActive"] = 3, ["objects"] = {"Attachment", "ParticleEmitter"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Aura"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Sifa"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243098098"}, ["Rate"] = {["t"] = "n", ["v"] = 14}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.8, 1.4}}, ["Speed"] = {["t"] = "nr", ["v"] = {2, 5}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {12, 12}}, ["Acceleration"] = {["t"] = "v3", ["v"] = {0, 14, 0}}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.3}, {1, 0.9}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.5}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {170, 255, 190}}, {1, {90, 220, 140}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.7}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0}, ["Shape"] = {["t"] = "en", ["v"] = {"ParticleEmitterShape", "Cylinder"}}, ["EmissionDirection"] = {["t"] = "en", ["v"] = {"NormalId", "Top"}}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Durum aktif kaldığı sürece sürer; durum bitince DURDURULUR (sürekli efekt sızıntısı yok).", ["freq"] = "while_active"},
  {["id"] = "world_quest_highlight", ["cat"] = "world", ["label"] = "Görev Vurgusu (Highlight)", ["ctx"] = {"rpg", "simulator", "tycoon", "casual", "obby"}, ["events"] = {"spawn", "quest_target", "interactable"}, ["targets"] = {"part", "item", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0, ["maxActive"] = 8, ["objects"] = {"Highlight"}, ["props"] = {["Highlight"] = {["FillColor"] = {["t"] = "c3", ["v"] = {255, 225, 120}}, ["FillTransparency"] = {["t"] = "n", ["v"] = 0.75}, ["OutlineColor"] = {["t"] = "c3", ["v"] = {255, 235, 150}}, ["OutlineTransparency"] = {["t"] = "n", ["v"] = 0.2}, ["DepthMode"] = {["t"] = "en", ["v"] = {"HighlightDepthMode", "Occluded"}}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Süslü parçacık yerine ucuz vurgu: oyuncu hedefi bulur, performans düşmez. Hedef yoksa kapatılır.", ["freq"] = "while_active"},
  {["id"] = "world_speed_trail", ["cat"] = "world", ["label"] = "Hız İzi (Trail)", ["ctx"] = {"obby", "parkour", "racing", "action"}, ["events"] = {"sprint", "dash"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.4, ["maxActive"] = 4, ["objects"] = {"Attachment", "Trail"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Speed"}}, ["Trail"] = {["Name"] = {["t"] = "s", ["v"] = "Hiz"}, ["Lifetime"] = {["t"] = "n", ["v"] = 0.35}, ["MinLength"] = {["t"] = "n", ["v"] = 0.4}, ["FaceCamera"] = {["t"] = "b", ["v"] = false}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {150, 220, 255}}, {1, {90, 140, 255}}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.25}, {1, 1}}}, ["WidthScale"] = {["t"] = "nseq", ["v"] = {{0, 1}, {1, 0.2}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.3}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Durum izi: koşarken görünür, durunca söner (koşula bağlı görünürlük).", ["freq"] = "while_active"},
  {["id"] = "world_lightning_beam", ["cat"] = "world", ["label"] = "Yıldırım Hüzmesi (Beam)", ["ctx"] = {"combat", "rpg", "action", "pvp"}, ["events"] = {"cast", "zap", "hit"}, ["targets"] = {"npc", "player", "part"}, ["authority"] = "client", ["cost"] = 2, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.3, ["cooldown"] = 0.35, ["maxActive"] = 6, ["objects"] = {"Attachment", "Beam", "PointLight"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_BeamA"}}, ["Beam"] = {["Name"] = {["t"] = "s", ["v"] = "Yildirim"}, ["CurveSize0"] = {["t"] = "n", ["v"] = 1.2}, ["CurveSize1"] = {["t"] = "n", ["v"] = -1.2}, ["Width0"] = {["t"] = "n", ["v"] = 1.4}, ["Width1"] = {["t"] = "n", ["v"] = 0.6}, ["Segments"] = {["t"] = "n", ["v"] = 12}, ["Brightness"] = {["t"] = "n", ["v"] = 2.5}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.9}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {190, 220, 255}}, {1, {120, 170, 255}}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.1}, {1, 1}}}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243098098"}, ["TextureLength"] = {["t"] = "n", ["v"] = 1}, ["TextureSpeed"] = {["t"] = "n", ["v"] = 0.35}, ["TextureMode"] = {["t"] = "en", ["v"] = {"TextureMode", "Wrap"}}, ["FaceCamera"] = {["t"] = "b", ["v"] = true}}, ["PointLight"] = {["Color"] = {["t"] = "c3", ["v"] = {150, 200, 255}}, ["Brightness"] = {["t"] = "n", ["v"] = 2.5}, ["Range"] = {["t"] = "n", ["v"] = 14}, ["Shadows"] = {["t"] = "b", ["v"] = false}}}, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Beam, iki bağlantı noktası arasını tek nesneyle doldurur (parçacık yağmurundan ucuz ve net).", ["freq"] = "per_event"},
  {["id"] = "world_footstep_puff", ["cat"] = "world", ["label"] = "Adım Tozu (kısıtlı tekrar)", ["ctx"] = {"horror", "survival", "rpg", "obby"}, ["events"] = {"step", "footstep"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.4, ["cooldown"] = 0.35, ["maxActive"] = 4, ["objects"] = {"Attachment", "ParticleEmitter"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Step"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Adim"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243660364"}, ["Rate"] = {["t"] = "n", ["v"] = 0}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.25, 0.5}}, ["Speed"] = {["t"] = "nr", ["v"] = {2, 5}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {45, 45}}, ["Acceleration"] = {["t"] = "v3", ["v"] = {0, -6, 0}}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.35}, {1, 0.9}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.5}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {200, 195, 185}}, {1, {170, 165, 155}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0}}}, ["burst"] = {["times"] = {["t"] = "n", ["v"] = 1}, ["count"] = {["t"] = "n", ["v"] = 3}}, ["cleanup"] = "delay", ["why"] = "Sık tetiklenen olay: cooldown + tek dalga ile sınırlanır; kalabalıkta otomatik seyreltilir (maks. aktif 4).", ["freq"] = "conditional"},
  {["id"] = "world_vfx_combo_stage", ["cat"] = "world", ["label"] = "Büyü Aşamaları (şarj→fırlat→çarpma)", ["ctx"] = {"rpg", "combat", "action"}, ["events"] = {"cast", "channel", "spell"}, ["targets"] = {"player", "npc", "part"}, ["authority"] = "client", ["cost"] = 3, ["mobile"] = false, ["trig"] = "event", ["dur"] = 1.6, ["cooldown"] = 1.0, ["maxActive"] = 3, ["objects"] = {"Attachment", "ParticleEmitter", "Beam"}, ["props"] = {["Attachment"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Combo"}}, ["ParticleEmitter"] = {["Name"] = {["t"] = "s", ["v"] = "Enerji"}, ["Texture"] = {["t"] = "s", ["v"] = "rbxassetid://243098098"}, ["Rate"] = {["t"] = "n", ["v"] = 30}, ["Lifetime"] = {["t"] = "nr", ["v"] = {0.3, 0.7}}, ["Speed"] = {["t"] = "nr", ["v"] = {1, 4}}, ["SpreadAngle"] = {["t"] = "v2", ["v"] = {20, 20}}, ["Acceleration"] = {["t"] = "v3", ["v"] = {0, 10, 0}}, ["Size"] = {["t"] = "nseq", ["v"] = {{0, 0.2}, {1, 0.7}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.3}, {1, 1}}}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {200, 170, 255}}, {1, {120, 90, 255}}}}, ["LightEmission"] = {["t"] = "n", ["v"] = 0.9}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0}}, ["Beam"] = {["Name"] = {["t"] = "s", ["v"] = "Huzme"}, ["Width0"] = {["t"] = "n", ["v"] = 2.2}, ["Width1"] = {["t"] = "n", ["v"] = 1.2}, ["Segments"] = {["t"] = "n", ["v"] = 10}, ["Brightness"] = {["t"] = "n", ["v"] = 3}, ["LightEmission"] = {["t"] = "n", ["v"] = 1}, ["LightInfluence"] = {["t"] = "n", ["v"] = 0}, ["Color"] = {["t"] = "seq", ["v"] = {{0, {230, 210, 255}}, {1, {150, 120, 255}}}}, ["Transparency"] = {["t"] = "nseq", ["v"] = {{0, 0.15}, {0.7, 0.4}, {1, 1}}}, ["TextureLength"] = {["t"] = "n", ["v"] = 1.5}, ["TextureSpeed"] = {["t"] = "n", ["v"] = 0.6}, ["TextureMode"] = {["t"] = "en", ["v"] = {"TextureMode", "Wrap"}}, ["FaceCamera"] = {["t"] = "b", ["v"] = true}}}, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Aşamalı saldırı: şarj (Rate>0) → fırlatma (Beam) → çarpma (world_hit_spark ile zincirlenir). Ağır sayılır, mobilde düşürülür.", ["freq"] = "per_event"},
  {["id"] = "post_hit_flash", ["cat"] = "post", ["label"] = "Hasar Flaşı (ekran)", ["ctx"] = {"combat", "pvp", "action", "horror", "survival"}, ["events"] = {"hit_taken", "damage_taken"}, ["targets"] = {"player"}, ["authority"] = "client", ["cost"] = 2, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.18, ["cooldown"] = 0.3, ["maxActive"] = 1, ["objects"] = {"ColorCorrectionEffect", "BlurEffect"}, ["props"] = {["ColorCorrectionEffect"] = {["Name"] = {["t"] = "s", ["v"] = "EI_HitFlash"}, ["TintColor"] = {["t"] = "c3", ["v"] = {255, 120, 110}}, ["Brightness"] = {["t"] = "n", ["v"] = -0.05}, ["Contrast"] = {["t"] = "n", ["v"] = 0.1}, ["Saturation"] = {["t"] = "n", ["v"] = -0.25}, ["Enabled"] = {["t"] = "b", ["v"] = true}}, ["BlurEffect"] = {["Name"] = {["t"] = "s", ["v"] = "EI_HitBlur"}, ["Size"] = {["t"] = "n", ["v"] = 6}, ["Enabled"] = {["t"] = "b", ["v"] = true}}}, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Ekran geri bildirimi oynanışı okutur; süre kısa (0.18 sn) ve cooldown'lu — baş döndürmez, mobilde de ucuz.", ["freq"] = "conditional"},
  {["id"] = "post_low_health_state", ["cat"] = "post", ["label"] = "Düşük Can Durumu (vinyet)", ["ctx"] = {"combat", "pvp", "action", "survival", "horror"}, ["events"] = {"low_health", "danger_state"}, ["targets"] = {"player"}, ["authority"] = "client", ["cost"] = 2, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.5, ["maxActive"] = 1, ["objects"] = {"ColorCorrectionEffect", "BlurEffect"}, ["props"] = {["ColorCorrectionEffect"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Low"}, ["TintColor"] = {["t"] = "c3", ["v"] = {255, 90, 90}}, ["Brightness"] = {["t"] = "n", ["v"] = -0.1}, ["Contrast"] = {["t"] = "n", ["v"] = 0.2}, ["Saturation"] = {["t"] = "n", ["v"] = -0.4}, ["Enabled"] = {["t"] = "b", ["v"] = true}}, ["BlurEffect"] = {["Name"] = {["t"] = "s", ["v"] = "EI_LowBlur"}, ["Size"] = {["t"] = "n", ["v"] = 3}, ["Enabled"] = {["t"] = "b", ["v"] = true}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Durum göstergesi: can normale dönünce KAPATILIR (kalıcı karartma riski yok). Tek örnek (maxActive=1).", ["freq"] = "while_active"},
  {["id"] = "post_mood_atmosphere", ["cat"] = "post", ["label"] = "Atmosfer / Ruh Hali", ["ctx"] = {"horror", "rpg", "survival", "roleplay"}, ["events"] = {"zone_enter", "time_change", "scene"}, ["targets"] = {"world"}, ["authority"] = "server", ["cost"] = 3, ["mobile"] = false, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 1.0, ["maxActive"] = 1, ["objects"] = {"Atmosphere", "BloomEffect"}, ["props"] = {["Atmosphere"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Atmosphere"}, ["Density"] = {["t"] = "n", ["v"] = 0.42}, ["Offset"] = {["t"] = "n", ["v"] = 0.1}, ["Color"] = {["t"] = "c3", ["v"] = {120, 130, 150}}, ["Decay"] = {["t"] = "c3", ["v"] = {90, 100, 120}}, ["Glare"] = {["t"] = "n", ["v"] = 0.15}, ["Haze"] = {["t"] = "n", ["v"] = 1.4}}, ["BloomEffect"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Bloom"}, ["Intensity"] = {["t"] = "n", ["v"] = 0.7}, ["Size"] = {["t"] = "n", ["v"] = 18}, ["Threshold"] = {["t"] = "n", ["v"] = 1.1}, ["Enabled"] = {["t"] = "b", ["v"] = true}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Ortak görünüm SUNUCUDA değişir (herkese aynı), oyuncuya özel karartma istemcide kalır — sorumluluk ayrımı.", ["freq"] = "while_active"},
  {["id"] = "char_idle_breath", ["cat"] = "char", ["label"] = "Nefes (Idle)", ["ctx"] = {"rpg", "roleplay", "simulator", "casual", "horror"}, ["events"] = {"idle", "spawn"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.5, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Idle"}}}}, ["asset"] = "idle", ["slot"] = "movement", ["priority"] = "Idle", ["weight"] = 1.0, ["fadeIn"] = 0.3, ["fadeOut"] = 0.3, ["loop"] = true, ["stopLower"] = false, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Idle katmanı Movement altındadır: yürüyüşü EZMEZ. Animasyon kimliği projeden gelir (uydurulmaz).", ["freq"] = "while_active"},
  {["id"] = "char_walk_cycle", ["cat"] = "char", ["label"] = "Yürüyüş Çevrimi", ["ctx"] = {"rpg", "roleplay", "simulator", "obby", "casual"}, ["events"] = {"walk", "move"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.4, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Movement"}}}}, ["asset"] = "walk", ["slot"] = "movement", ["priority"] = "Movement", ["weight"] = 1.0, ["fadeIn"] = 0.2, ["fadeOut"] = 0.2, ["loop"] = true, ["stopLower"] = false, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Movement katmanı: Idle'ı bastırır, Action'ı bastırmaz (öncelik düzeni).", ["freq"] = "while_active"},
  {["id"] = "char_run_cycle", ["cat"] = "char", ["label"] = "Koşu Çevrimi", ["ctx"] = {"obby", "parkour", "racing", "combat", "survival"}, ["events"] = {"sprint", "run"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.4, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Movement"}}}}, ["asset"] = "run", ["slot"] = "movement", ["priority"] = "Movement", ["weight"] = 1.0, ["fadeIn"] = 0.15, ["fadeOut"] = 0.2, ["loop"] = true, ["stopLower"] = false, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Aynı slota (movement) yazdığı için yürüyüşle ÇAKIŞMAZ: son çağrılan kazanır, eski iz söner.", ["freq"] = "while_active"},
  {["id"] = "char_jump_launch", ["cat"] = "char", ["label"] = "Zıplama (hava)", ["ctx"] = {"obby", "parkour", "combat", "action", "racing"}, ["events"] = {"jump", "launch"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.5, ["cooldown"] = 0.2, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Action"}}}}, ["asset"] = "jump", ["slot"] = "action", ["priority"] = "Action", ["weight"] = 1.0, ["fadeIn"] = 0.1, ["fadeOut"] = 0.15, ["loop"] = false, ["stopLower"] = true, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Action katmanı hareketi kısa süre EZER (stopLower) çünkü zıplama okutulmalı; sonra serbest bırakır.", ["freq"] = "per_event"},
  {["id"] = "char_fall_loop", ["cat"] = "char", ["label"] = "Düşme (döngü)", ["ctx"] = {"obby", "parkour", "action", "racing"}, ["events"] = {"fall", "airborne"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.3, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Movement"}}}}, ["asset"] = "fall", ["slot"] = "movement", ["priority"] = "Movement", ["weight"] = 0.9, ["fadeIn"] = 0.25, ["fadeOut"] = 0.2, ["loop"] = true, ["stopLower"] = false, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Havada kaldığı sürece sürer; yere inince dur_Fall→land ile değişir (durum geçişi).", ["freq"] = "while_active"},
  {["id"] = "char_land_recover", ["cat"] = "char", ["label"] = "İniş Toparlanma", ["ctx"] = {"obby", "parkour", "combat", "action"}, ["events"] = {"land", "jump_land"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.45, ["cooldown"] = 0.25, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Action"}}}}, ["asset"] = "land", ["slot"] = "action", ["priority"] = "Action", ["weight"] = 1.0, ["fadeIn"] = 0.08, ["fadeOut"] = 0.2, ["loop"] = false, ["stopLower"] = true, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "İniş anı kısa bir Action: bir sonraki hareket animasyonunu 0.2 sn içinde serbest bırakır.", ["freq"] = "per_event"},
  {["id"] = "char_attack_combo", ["cat"] = "char", ["label"] = "Saldırı Kombosu", ["ctx"] = {"combat", "pvp", "rpg", "action"}, ["events"] = {"attack", "tool_activate", "swing"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 2, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.7, ["cooldown"] = 0.25, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Action2"}}}}, ["asset"] = "attack", ["slot"] = "action", ["priority"] = "Action2", ["weight"] = 1.0, ["fadeIn"] = 0.1, ["fadeOut"] = 0.15, ["loop"] = false, ["stopLower"] = true, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Action2: aynı anda gelen zıplama/iniş (Action) ile ÇAKIŞMAZ ama hareketi kısa süre ezer; oyun mantığı sunucuda doğrulanır.", ["freq"] = "per_event"},
  {["id"] = "char_hit_react", ["cat"] = "char", ["label"] = "Hasar Tepkisi (flinch)", ["ctx"] = {"combat", "pvp", "rpg", "action", "survival"}, ["events"] = {"hit_taken", "damage_taken", "stagger"}, ["targets"] = {"player", "npc"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.3, ["cooldown"] = 0.35, ["maxActive"] = 1, ["objects"] = {"Animation"}, ["props"] = {["Animation"] = {["AnimationId"] = {["t"] = "s", ["v"] = ""}, ["Priority"] = {["t"] = "en", ["v"] = {"AnimationPriority", "Action"}}}}, ["asset"] = "hit", ["slot"] = "action", ["priority"] = "Action", ["weight"] = 0.85, ["fadeIn"] = 0.05, ["fadeOut"] = 0.12, ["loop"] = false, ["stopLower"] = false, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Ağırlık 0.85: yürüyüşü tamamen kesmez, üstüne biner (blending). Cooldown, üst üste hasarda spam engeller.", ["freq"] = "conditional"},
  {["id"] = "char_npc_patrol", ["cat"] = "char", ["label"] = "NPC Devriye (prosedürel hareket)", ["ctx"] = {"rpg", "horror", "survival", "tycoon", "roleplay"}, ["events"] = {"patrol", "ai_move"}, ["targets"] = {"npc"}, ["authority"] = "server", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = 4.0, ["cooldown"] = 0.5, ["maxActive"] = 6, ["objects"] = {"Humanoid"}, ["props"] = {["Humanoid"] = {["WalkSpeed"] = {["t"] = "n", ["v"] = 8}, ["JumpPower"] = {["t"] = "n", ["v"] = 40}}}, ["asset"] = nil, ["slot"] = "movement", ["priority"] = nil, ["weight"] = nil, ["fadeIn"] = 0, ["fadeOut"] = 0, ["loop"] = true, ["stopLower"] = false, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Animasyon kimliği GEREKMEZ: modeli yürüten oyun tarafı, görsel yürüyüş çevrimi (varsa) duruma bağlanır. Sunucu sahipliği.", ["freq"] = "interval"},
  {["id"] = "char_camera_shake", ["cat"] = "cam", ["label"] = "Kamera Sarsıntısı", ["ctx"] = {"combat", "pvp", "action", "horror", "racing"}, ["events"] = {"impact", "hit", "explosion_near"}, ["targets"] = {"player"}, ["authority"] = "client", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.35, ["cooldown"] = 0.25, ["maxActive"] = 1, ["objects"] = {"Camera"}, ["props"] = {["Camera"] = {["FieldOfView"] = {["t"] = "n", ["v"] = 74}, ["CameraType"] = {["t"] = "en", ["v"] = {"CameraType", "Custom"}}}}, ["tween"] = {["object"] = "Camera", ["prop"] = "FieldOfView", ["from"] = 74, ["to"] = 78, ["dur"] = 0.12, ["style"] = "Quad", ["dir"] = "Out", ["back"] = true}, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "Kamera geri bildirimi darbenin ŞİDDETİNİ anlatır; kısa ve kapatılabilir (ayarlardan azaltılabilir).", ["freq"] = "conditional"},
  {["id"] = "char_camera_focus", ["cat"] = "cam", ["label"] = "Kamera Odaklanma", ["ctx"] = {"rpg", "casual", "roleplay", "simulator", "tycoon"}, ["events"] = {"interact", "open_ui", "inspect"}, ["targets"] = {"player", "part"}, ["authority"] = "client", ["cost"] = 2, ["mobile"] = true, ["trig"] = "event", ["dur"] = 1.0, ["cooldown"] = 0.6, ["maxActive"] = 1, ["objects"] = {"Camera"}, ["props"] = {["Camera"] = {["FieldOfView"] = {["t"] = "n", ["v"] = 70}, ["CameraType"] = {["t"] = "en", ["v"] = {"CameraType", "Scriptable"}}}}, ["tween"] = {["object"] = "Camera", ["prop"] = "FieldOfView", ["from"] = 70, ["to"] = 55, ["dur"] = 0.5, ["style"] = "Quint", ["dir"] = "Out", ["back"] = true}, ["burst"] = nil, ["cleanup"] = "delay", ["why"] = "İnceleme/etkileşimde dikkat çeker; Scriptable mod KISA tutulur (oyuncu kontrolü geri verilir).", ["freq"] = "per_event"},
  {["id"] = "interact_proximity_prompt", ["cat"] = "interact", ["label"] = "ProximityPrompt (E ile aç)", ["ctx"] = {"rpg", "simulator", "tycoon", "horror", "obby", "casual"}, ["events"] = {"interactable", "quest_target"}, ["targets"] = {"part", "item", "npc"}, ["authority"] = "server", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.3, ["maxActive"] = 40, ["objects"] = {"ProximityPrompt"}, ["props"] = {["ProximityPrompt"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Prompt"}, ["ActionText"] = {["t"] = "s", ["v"] = "Aç"}, ["ObjectText"] = {["t"] = "s", ["v"] = "Kutu"}, ["HoldDuration"] = {["t"] = "n", ["v"] = 0.4}, ["MaxActivationDistance"] = {["t"] = "n", ["v"] = 8}, ["RequiresLineOfSight"] = {["t"] = "b", ["v"] = false}, ["KeyboardKeyCode"] = {["t"] = "en", ["v"] = {"KeyCode", "E"}}, ["Enabled"] = {["t"] = "b", ["v"] = true}, ["Style"] = {["t"] = "en", ["v"] = {"ProximityPromptStyle", "Default"}}, ["UIOffset"] = {["t"] = "v2", ["v"] = {0, 20}}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Dünya etkileşimi: Prompt SUNUCUDA doğrulanır (Triggered), görsel açılış istemcide oynar. Mobilde otomatik dokunma düğmesi çıkar.", ["freq"] = "while_active"},
  {["id"] = "interact_click_detector", ["cat"] = "interact", ["label"] = "ClickDetector (tıkla)", ["ctx"] = {"simulator", "tycoon", "obby", "casual", "simulator"}, ["events"] = {"interactable", "click"}, ["targets"] = {"part", "item"}, ["authority"] = "server", ["cost"] = 1, ["mobile"] = true, ["trig"] = "state", ["dur"] = -1, ["cooldown"] = 0.2, ["maxActive"] = 60, ["objects"] = {"ClickDetector"}, ["props"] = {["ClickDetector"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Click"}, ["MaxActivationDistance"] = {["t"] = "n", ["v"] = 12}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "En ucuz etkileşim: tıklama oyun mantığı SUNUCUDA (MouseClick), görsel tepki istemcide. Hover'da imleç değişir.", ["freq"] = "while_active"},
  {["id"] = "interact_tool_activate", ["cat"] = "interact", ["label"] = "Tool Kullanımı", ["ctx"] = {"combat", "pvp", "simulator", "survival"}, ["events"] = {"tool_activate", "equip"}, ["targets"] = {"tool"}, ["authority"] = "server", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = -1, ["cooldown"] = 0.1, ["maxActive"] = 4, ["objects"] = {"Tool"}, ["props"] = {["Tool"] = {["ToolTip"] = {["t"] = "s", ["v"] = "Kullan"}, ["CanBeDropped"] = {["t"] = "b", ["v"] = false}, ["RequiresHandle"] = {["t"] = "b", ["v"] = true}, ["Enabled"] = {["t"] = "b", ["v"] = true}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Tool.Activated İSTEMCİDE tetiklenir; sonucu (hasar/ödül) SUNUCU doğrular. İstemci sadece görsel oynatır.", ["freq"] = "per_event"},
  {["id"] = "interact_remote_event", ["cat"] = "interact", ["label"] = "İstemci↔Sunucu Kanalı (RemoteEvent)", ["ctx"] = {"combat", "pvp", "rpg", "simulator", "tycoon", "obby", "horror", "racing", "survival", "casual", "roleplay"}, ["events"] = {"client_notify", "server_confirm", "custom"}, ["targets"] = {"player", "world", "part", "npc"}, ["authority"] = "server", ["cost"] = 1, ["mobile"] = true, ["trig"] = "event", ["dur"] = -1, ["cooldown"] = 0, ["maxActive"] = 200, ["objects"] = {"RemoteEvent"}, ["props"] = {["RemoteEvent"] = {["Name"] = {["t"] = "s", ["v"] = "EI_Event"}}}, ["burst"] = nil, ["cleanup"] = "stop", ["why"] = "Sözleşme: görsel efekt istemcide, OYUN SONUCU sunucuda. Saldırı görseli oynasa bile isabet sunucu onayıyla sayılır.", ["freq"] = "per_event"},
  {["id"] = "reuse_ui_anim", ["cat"] = "decide", ["label"] = "Mevcut UI animasyonunu kullan", ["ctx"] = {"*"}, ["events"] = {"ui_click", "menu", "ui_change", "button", "hud"}, ["targets"] = {"ui", "player"}, ["authority"] = "client", ["cost"] = 0, ["mobile"] = true, ["trig"] = "event", ["dur"] = 0.2, ["cooldown"] = 0, ["maxActive"] = 99, ["objects"] = {}, ["props"] = {}, ["burst"] = nil, ["cleanup"] = "none", ["why"] = "Arayüz içi olaylarda YENİ dünya efekti eklenmez: mevcut GUI animasyon sistemi (EIAnim) yeterli ve daha ucuz.", ["freq"] = "per_event"},
  {["id"] = "decide_none", ["cat"] = "decide", ["label"] = "Efekt yok (bilinçli karar)", ["ctx"] = {"*"}, ["events"] = {"*"}, ["targets"] = {"*"}, ["authority"] = "client", ["cost"] = 0, ["mobile"] = true, ["trig"] = "none", ["dur"] = 0, ["cooldown"] = 0, ["maxActive"] = 0, ["objects"] = {}, ["props"] = {}, ["burst"] = nil, ["cleanup"] = "none", ["why"] = "Sık tetiklenen + önemsiz olaylarda, performans sınırındayken ya da görsel gürültü riskinde doğru cevap efekt EKLEMEMEKTİR.", ["freq"] = "none"},
}
-- <<END_EI_VFX_DATA>>

local VERSION = 1

-- ---------------------------------------------------------------- dizin
local LIB, IDS = {}, {}
for _, p in ipairs(VFX_PRESETS) do
	LIB[p.id] = p
	IDS[#IDS + 1] = p.id
end
table.sort(IDS)

local function has(list, v)
	for _, x in ipairs(list or {}) do if x == v then return true end end
	return false
end

-- ---------------------------------------------------------------- cihaz bütçesi (mobil = hafif havuz)
local LIMITS = {
	desktop = { budget = 3, maxActive = 60 },
	mobile = { budget = 1, maxActive = 24 },
}

function EIVfx.limits(opts)
	if type(opts) ~= "table" then opts = {} end
	local base = opts.mobile and LIMITS.mobile or LIMITS.desktop
	-- Açıkça sayı verilmişse o kullanılır (0 dahil); aksi hâlde taban değer. JS aynası birebir aynı kural.
	local budget = base.budget
	if type(opts.budget) == "number" then budget = opts.budget end
	local maxActive = base.maxActive
	if type(opts.maxActive) == "number" then maxActive = opts.maxActive end
	return { budget = budget, maxActive = maxActive }
end

function EIVfx.get(id) return LIB[id] end
function EIVfx.ids() return IDS end
function EIVfx.count() return #IDS end
function EIVfx.version() return VERSION end

-- UI içi olaylar: yeni dünya efekti yerine mevcut GUI animasyon sistemi kullanılır (yeniden kullanım kararı).
local UI_EVENTS = { ui_click = true, menu = true, ui_change = true, button = true, hud = true, ui_open = true }

-- ---------------------------------------------------------------- SORGU: bağlam + olay + hedef → sıralı öneri
-- Puanlama tamsayıdır (Lua ≡ JS birebir): bağlam 40/20 · olay 50/20 · hedef 15/5 · maliyet (3-cost)*5 · mobil 5.
-- Kütüphane dışı hiçbir öneri ÜRETİLMEZ; uydurma efekt yoktur.
function EIVfx.suggest(ctxName, eventName, targetName, opts)
	if type(opts) ~= "table" then opts = {} end
	local lim = EIVfx.limits(opts)
	local out, skipped, seen = {}, {}, {}
	for _, id in ipairs(IDS) do
		local p = LIB[id]
		if p.cat ~= "decide" then
			local ctxHit, evHit, tgtHit = 0, 0, 0
			if has(p.ctx, ctxName) then ctxHit = 40 elseif has(p.ctx, "*") then ctxHit = 20 end
			if has(p.events, eventName) then evHit = 50 elseif has(p.events, "*") then evHit = 20 end
			if has(p.targets, targetName) then tgtHit = 15 elseif has(p.targets, "*") then tgtHit = 5 end
			if ctxHit > 0 and evHit > 0 and tgtHit > 0 then
				if p.cost <= lim.budget and (not opts.mobile or p.mobile) then
					local score = ctxHit + evHit + tgtHit + (3 - p.cost) * 5 + ((opts.mobile and p.mobile) and 5 or 0)
					out[#out + 1] = { id = id, score = score, label = p.label, why = p.why, cost = p.cost,
						mode = p.authority, cat = p.cat, freq = p.freq, dur = p.dur }
					seen[id] = true
				else
					skipped[#skipped + 1] = { id = id, reason = p.mobile and "butce" or "mobil", cost = p.cost }
				end
			end
		end
	end
	table.sort(out, function(a, b)
		if a.score ~= b.score then return a.score > b.score end
		return a.id < b.id
	end)
	-- Geri dönüşler: UI olayında mevcut animasyon sistemi, her durumda "efekt yok" seçeneği
	local reuse = LIB.reuse_ui_anim
	if not seen.reuse_ui_anim and (ctxName == "ui" or targetName == "ui" or UI_EVENTS[eventName]) then
		out[#out + 1] = { id = "reuse_ui_anim", score = 1, label = reuse.label, why = reuse.why, cost = 0,
			mode = reuse.authority, cat = reuse.cat, freq = reuse.freq, dur = reuse.dur }
	end
	local none = LIB.decide_none
	out[#out + 1] = { id = "decide_none", score = 0, label = none.label, why = none.why, cost = 0,
		mode = none.authority, cat = none.cat, freq = none.freq, dur = none.dur }
	return { list = out, skipped = skipped, limits = lim }
end

-- En iyi öneri + gerekçe (arayüz ve rapor için)
function EIVfx.plan(ctxName, eventName, targetName, opts)
	local r = EIVfx.suggest(ctxName, eventName, targetName, opts)
	local top = r.list[1]
	return { id = top.id, why = top.why, score = top.score, alternatives = r.list, skipped = r.skipped, limits = r.limits }
end

-- ---------------------------------------------------------------- TEKRAR KONTROLÜ (cooldown · eşzamanlı sınır · bütçe)
function EIVfx.newState()
	return { last = {}, active = {}, seq = 0 }
end

local function activeCount(state)
	local n = 0
	for _ in ipairs(state.active) do n = n + 1 end
	return n
end

function EIVfx.tryPlay(state, id, now, opts)
	opts = opts or {}
	state = state or EIVfx.newState()
	local p = LIB[id]
	if not p then return false, "bilinmeyen", state end
	local lim = EIVfx.limits(opts)
	if activeCount(state) >= lim.maxActive then return false, "kapasite", state end
	local mine = 0
	for _, e in ipairs(state.active) do if e.id == id then mine = mine + 1 end end
	if mine >= (p.maxActive or 1) then return false, "es-zamanli", state end
	local last = state.last[id]
	if last ~= nil and (p.cooldown or 0) > 0 and (now - last) < (p.cooldown or 0) then return false, "bekleme", state end
	state.seq = state.seq + 1
	state.active[#state.active + 1] = { id = id, t = now, dur = p.dur, seq = state.seq }
	state.last[id] = now
	return true, "ok", state
end

-- Süresi dolan kayıtları düşürür (temizlik); eski cooldown kayıtlarını da budar (bellek sınırı).
function EIVfx.tick(state, now)
	state = state or EIVfx.newState()
	local keep, removed = {}, 0
	for _, e in ipairs(state.active) do
		if e.dur ~= nil and e.dur >= 0 and (now - e.t) >= e.dur then
			removed = removed + 1
		else
			keep[#keep + 1] = e
		end
	end
	state.active = keep
	local last = {}
	for id, t in pairs(state.last) do
		if (now - t) <= 60 then last[id] = t end
	end
	state.last = last
	return removed
end

-- "Durum aktif olduğu sürece" efekti bittiğinde: kaydı düşür (sürekli efekt sızıntısı olmaz).
function EIVfx.release(state, id)
	state = state or EIVfx.newState()
	local keep, removed = {}, 0
	for _, e in ipairs(state.active) do
		if e.id == id then removed = removed + 1 else keep[#keep + 1] = e end
	end
	state.active = keep
	return removed
end

-- ---------------------------------------------------------------- YETKİ: görsel istemcide, oyun sonucu sunucuda
function EIVfx.canPlay(id, opts)
	opts = opts or {}
	local p = LIB[id]
	if not p then return false, "bilinmeyen" end
	if p.authority == "server" and not opts.server then return false, "yetki-sunucu" end
	if p.authority == "client" and opts.serverOnly then return false, "yetki-istemci" end
	return true, "ok"
end

-- ---------------------------------------------------------------- KARAKTER ANİMASYONU: öncelik · ağırlık · çakışma
local PRIO = { Core = 0, Idle = 1, Movement = 2, Action = 3, Action2 = 4, Action3 = 5, Action4 = 6 }

-- Dönüş: plan, durum. "ok" ve "tekrar" (aynı animasyon yeniden) oynatılır; "asset-eksik" (kimlik yok),
-- "oncelik" (aynı slotta farklı animasyon aynı katmanda) ve "char-degil"/"animasyon-degil" oynatılmaz.
function EIVfx.animPlan(id, opts)
	opts = opts or {}
	local p = LIB[id]
	if not p or p.cat ~= "char" then return nil, "char-degil" end
	if not p.priority then return nil, "animasyon-degil" end -- prosedürel (ör. NPC devriyesi)
	local plan = { id = id, slot = p.slot, priority = p.priority, weight = p.weight, fadeIn = p.fadeIn,
		fadeOut = p.fadeOut, loop = p.loop and true or false, stopLower = p.stopLower and true or false,
		asset = p.asset, assetId = opts.assetId or "", hold = p.dur }
	local active = opts.active or {}
	local cur = active[p.slot]
	-- active[slot] iki biçimde olabilir: "Action2" (yalnız öncelik) ya da { id = ..., priority = ... }
	local curPrio, curId = cur, nil
	if type(cur) == "table" then curPrio, curId = cur.priority, cur.id end
	local a, b = curPrio and PRIO[curPrio] or nil, PRIO[p.priority]
	if a ~= nil and b ~= nil and a >= b then
		if curId == p.id then return plan, "tekrar" end -- aynı animasyon: yeniden başlatılır (kombo zinciri)
		return plan, "oncelik"                                -- farklı animasyon aynı katmanda: başlatılmaz
	end
	if a ~= nil and b ~= nil and b > a then plan.stopLower = true end
	if p.asset and plan.assetId == "" then return plan, "asset-eksik" end
	return plan, "ok"
end

function EIVfx.describe(id)
	local p = LIB[id]
	if not p then return nil end
	return { id = p.id, label = p.label, cat = p.cat, why = p.why, cost = p.cost, mode = p.authority,
		freq = p.freq, cooldown = p.cooldown, maxActive = p.maxActive, objects = p.objects }
end

-- ================================================================ ROBLOX ÇALIŞMA ZAMANI (saf bölümün üstüne)
-- Yükleme anında hiçbir servis çağrılmaz; servisler ilk kullanımda alınır (eklentiye gömülebilir).
local ACTIVE = {}    -- id → { [instance] = { objects = {...} } }
local STATE = EIVfx.newState()

local function services()
	local ok, s = pcall(function()
		return { Lighting = game:GetService("Lighting"), RS = game:GetService("ReplicatedStorage"),
			Run = game:GetService("RunService") }
	end)
	if not ok then return nil end
	local cam = workspace and workspace.CurrentCamera
	s.Camera = cam
	return s
end

-- TweenService yalnızca servisten alınır (ilk kullanımda, pcall korumalı) — yükleme anında API çağrısı yok.
local TWEEN_SVC = nil
local function tweenService()
	if TWEEN_SVC then return TWEEN_SVC end
	local ok, svc = pcall(function() return game:GetService("TweenService") end)
	if ok and svc then TWEEN_SVC = svc end
	return TWEEN_SVC
end

local function valOf(spec)
	local t, v = spec.t, spec.v
	if t == "n" or t == "b" or t == "s" then return v end
	if t == "c3" then return Color3.fromRGB(v[1], v[2], v[3]) end
	if t == "seq" then
		local kp = {}
		for i, k in ipairs(v) do kp[i] = ColorSequenceKeypoint.new(k[1], Color3.fromRGB(k[2][1], k[2][2], k[2][3])) end
		return ColorSequence.new(kp)
	end
	if t == "nseq" then
		local kp = {}
		for i, k in ipairs(v) do kp[i] = NumberSequenceKeypoint.new(k[1], k[2]) end
		return NumberSequence.new(kp)
	end
	if t == "v2" then return Vector2.new(v[1], v[2]) end
	if t == "v3" then return Vector3.new(v[1], v[2], v[3]) end
	if t == "nr" then return NumberRange.new(v[1], v[2]) end
	if t == "en" then return Enum[v[1]][v[2]] end
	return nil
end

local function hostOf(inst)
	if not inst then return nil end
	local ok, isPart = pcall(function() return inst:IsA("BasePart") end)
	if ok and isPart then return inst end
	pcall(function()
		local hrp = inst:FindFirstChild("HumanoidRootPart")
		if hrp then inst = hrp end
	end)
	pcall(function() if inst.PrimaryPart then inst = inst.PrimaryPart end end)
	return inst
end

-- Bir preset'in nesnelerini kurar; kurulanları döndürür (temizlik için).
local function build(inst, p, opts)
	local created, refs = {}, {}
	local host = hostOf(inst)
	local function new(cls)
		local ok, o = pcall(Instance.new, cls)
		if not ok or not o then return nil end
		created[#created + 1] = o
		return o
	end
	local attach, attachB
	for _, cls in ipairs(p.objects) do
		if cls ~= "Attachment" then
			local props = p.props[cls] or {}
			local o = new(cls)
			if o then
				for prop, spec in pairs(props) do
					if prop ~= "Name" then pcall(function() o[prop] = valOf(spec) end) end
				end
				pcall(function() o.Name = (props.Name and props.Name.v) or p.id end)
				local promptTarget = (cls == "ProximityPrompt" or cls == "ClickDetector") and (host or inst) or nil
				if cls == "Highlight" then
					pcall(function() if o.Adornee == nil then o.Adornee = inst end end)
				end
				if cls == "Trail" or cls == "Beam" then
					pcall(function() o.Attachment0 = attach; o.Attachment1 = attachB end)
				end
				if cls == "Atmosphere" or cls == "ColorCorrectionEffect" or cls == "BlurEffect" or cls == "BloomEffect" then
					local svc = services()
					local parent = (cls == "Atmosphere") and (svc and svc.Lighting)
						or ((p.authority == "client" and svc and svc.Camera) or (svc and svc.Lighting))
					pcall(function() o.Parent = parent end)
				elseif cls == "RemoteEvent" then
					local svc = services()
					pcall(function()
						local ex = svc.RS:FindFirstChild(o.Name)
						if ex then created[#created] = ex else o.Parent = svc.RS end
					end)
				else
					pcall(function() o.Parent = promptTarget or attach or host or inst end)
				end
				refs[cls] = o
			end
		else
			attach = new("Attachment")
			if attach then
				pcall(function() attach.Name = (p.props.Attachment and p.props.Attachment.Name and p.props.Attachment.Name.v) or (p.id .. "_A") end)
				local pos = opts.position
				if pos then pcall(function() attach.WorldPosition = pos end) end
				pcall(function() attach.Parent = opts.part or host or inst end)
				if p.props.Attachment then
					for prop, spec in pairs(p.props.Attachment) do
						pcall(function() attach[prop] = valOf(spec) end)
					end
				end
				if has(p.objects, "Trail") or has(p.objects, "Beam") then
					attachB = new("Attachment")
					if attachB then
						pcall(function() attachB.Name = attach.Name .. "_B"; attachB.Parent = attach.Parent end)
						local okp = pcall(function()
							attachB.Position = attach.Position + Vector3.new(0, 0.6, 0)
							if pos then attachB.WorldPosition = pos end
						end)
						if not okp then pcall(function() attachB.Parent = attach.Parent end) end
					end
				end
			end
		end
	end
	-- Emitter patlaması: Rate = 0 olan emitter'lar Emit ile tek dalga gönderir (sürekli yanmaz).
	if p.burst and refs.ParticleEmitter then
		local times = p.burst.times and p.burst.times.v or 1
		local count = p.burst.count and p.burst.count.v or 1
		local em = refs.ParticleEmitter
		task.spawn(function()
			for i = 1, times do
				pcall(function() em:Emit(count) end)
				if i < times then task.wait(0.05) end
			end
		end)
	end
	-- Kamera geçişi (prosedürel): TweenService SERVİSTEN alınır (Roblox'ta global TweenService yoktur)
	if p.tween and p.tween.object == "Camera" then
		local svc = services()
		local cam = svc and svc.Camera
		local ts = tweenService()
		if cam and ts then
			local tw = p.tween
			local okInfo, info = pcall(function()
				return TweenInfo.new(tw.dur, Enum.EasingStyle[tw.style], Enum.EasingDirection[tw.dir])
			end)
			if okInfo then
				local g1, g2 = {}, {}
				pcall(function()
					g1[tw.prop] = valOf({ t = "n", v = tw.to })
					g2[tw.prop] = valOf({ t = "n", v = tw.from })
					ts:Create(cam, info, g1):Play()
				end)
				if tw.back then
					created[#created + 1] = { Destroy = function()
						pcall(function() ts:Create(cam, info, g2):Play() end)
					end }
				end
			end
		end
	end
	return created, refs
end

-- Karakter animasyonu: proje kendi AnimationId'sini verir (uydurulmaz).
local function playAnim(inst, p, opts)
	local plan, why = EIVfx.animPlan(p.id, { active = opts.active, assetId = opts.assetId })
	if why ~= "ok" and why ~= "tekrar" then return nil, why end
	local hum
	pcall(function() hum = inst:FindFirstChildOfClass("Humanoid") end)
	if not hum then return nil, "humanoid-yok" end
	local animator
	pcall(function() animator = hum:FindFirstChildOfClass("Animator") end)
	local anim = Instance.new("Animation")
	anim.AnimationId = plan.assetId
	anim.Priority = Enum.AnimationPriority[plan.priority]
	local ok, track = pcall(function()
		local loader = animator or hum
		local t = loader:LoadAnimation(anim)
		t.Priority = Enum.AnimationPriority[plan.priority]
		t:Play(plan.fadeIn, plan.weight)
		return t
	end)
	if not ok or not track then return nil, "anim-yuklenemedi" end
	return { track = track, stop = function()
		pcall(function() track:Stop(plan.fadeOut) end)
		pcall(function() anim:Destroy() end)
	end }, "ok"
end

-- Efekti oynatır. Dönüş: rapor { ok, reason, mode, cost, objects, duration }
function EIVfx.play(inst, id, opts)
	opts = opts or {}
	local p = LIB[id]
	if not p then return { ok = false, reason = "bilinmeyen" } end
	local okPlay, why = EIVfx.canPlay(id, opts)
	if not okPlay then return { ok = false, reason = why } end
	local now = opts.now or os.clock()
	local st = opts.state or STATE
	local ok, reason = EIVfx.tryPlay(st, id, now, opts)
	if not ok then return { ok = false, reason = reason } end
	local report = { ok = true, reason = "ok", mode = p.authority, cost = p.cost, duration = p.dur, objects = 0 }
	if p.cat == "char" and p.priority then
		local a, aWhy = playAnim(inst, p, opts)
		if not a then
			EIVfx.release(st, id)
			return { ok = false, reason = aWhy }
		end
		ACTIVE[id] = ACTIVE[id] or {}
		ACTIVE[id][inst] = { anim = a }
		report.anim = { priority = p.priority, weight = p.weight, stopLower = p.stopLower and true or false }
		if p.cleanup == "delay" and p.dur > 0 then
			task.delay(p.dur, function() if EIVfx.stop(inst, id) then end end)
		end
		return report
	end
	local created = build(inst, p, opts)
	report.objects = #created
	ACTIVE[id] = ACTIVE[id] or {}
	ACTIVE[id][inst] = { objects = created }
	if p.cleanup == "delay" and p.dur and p.dur > 0 then
		task.delay(p.dur, function() EIVfx.stop(inst, id) end)
	end
	return report
end

-- Temizlik: kurulan nesneleri yok eder, durum kaydını düşürür (sızıntı yok).
function EIVfx.stop(inst, id)
	local byInst = ACTIVE[id]
	local rec = byInst and byInst[inst] or nil
	if not rec then return false end
	if rec.anim then
		pcall(rec.anim.stop)
	else
		for _, o in ipairs(rec.objects or {}) do pcall(function() o:Destroy() end) end
	end
	byInst[inst] = nil
	EIVfx.release(STATE, id)
	return true
end

-- Aktif efekt sayısı (bütçe denetimi ve rapor için)
function EIVfx.activeCount() return activeCount(STATE) end
function EIVfx.state() return STATE end

EIVfx.VERSION = VERSION
EIVfx.LIMITS = LIMITS

return EIVfx
