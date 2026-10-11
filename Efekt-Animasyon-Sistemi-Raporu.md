# EasyImport — Roblox Studio Efekt & Animasyon Sistemi Raporu (v34)

**Kapsam:** Mevcut sistemin analizi → eksiklerin sınıflandırılması (A/B/C/D) → plan → uyumluluk kontrolü →
entegrasyon → test → bu rapor.
**Kural:** Kaynak görülmeden hiçbir dosya/iç yapı "var" sayılmadı; hiçbir Roblox API özelliği uydurulmadı;
test edilmeyen hiçbir davranış "test edildi" diye yazılmadı.

---

## 1. Mevcut sistem (analizden çıkan, kanıtlı)

| Katman | Dosya | Satır | Görev |
|---|---|---|---|
| Karar motoru (GUI) | `kaynak/assistant/runtime/lua/EIAnim.lua` | 2591 | Figma öğeleri → animasyon planı → LocalScript kaynağı |
| Öğrenme kanalı | `EILearn.lua` / `ei-learn.js` | 279 / 295 | Sayaç tabanlı tercih öğrenme (Lua ≡ JS), `plugin:SetSetting("EasyImportLearn")` |
| Ham veri / model / stil | `EIRaw.lua`, `EIModel.lua`, `EIStyle.lua` | 1236 / 599 / 313 | Etiket ham verisi, sınıf modeli, stil sezgisi |
| Kütüphaneler | `anim/anim-library.json`, `vfx/vfx-library.json` | 116 animasyon / 32 VFX preset | Tek doğruluk kaynağı; elle düzenlenmez |
| Panel (Figma) | `figma/asistan_panel.js` (+ `code.js`) | 1212 + 1126 | Yuva haritası, efekt seçimi, önizleme planı, envanter (kendi resimlerimiz) |
| Eklenti (Studio) | `roblox-studio-plugin/EasyImportStudioPlugin.lua` | 3058 | JSON → nesne ağacı + LocalScript üretimi |
| Paket | `EasyImportStudioPlugin.rbxmx` | 454 KB · 8 gömülü modül | Studio'ya sürüklenen dağıtım dosyası |
| Kapılar | 18 Python + 6 Node + ui-tools | — | Parite, aktarım, panel, efekt, sözleşme |

**Mevcut durum (A — doğrulanmış):** GUI/arayüz animasyonları (116 animasyon, 180 track), 10 GUI efekti
(fall/coin/smooth/gleam/burst/orbit/twinkle/sweep/orb + `PIC_KINDS`), panel açılış/kapanış, "Süre" ve
"Kaç tane" alanlarının uçtan uca çalışması, Figma → JSON → Studio → LocalScript zinciri (54 kontrol),
Lua ≡ JS parite (840 seçenek sırası + 8 script kaynağı bayt birebir), envanterin kendi resimlerimizden gelmesi.

**Kritik analiz bulgusu (C — eksik):** 19 Roblox sınıfı için tüm depo tarandı:
`ParticleEmitter, Highlight, Explosion, Attachment, ProximityPrompt, ClickDetector, AnimationTrack, Humanoid,
RemoteEvent, ContextActionService` **hiçbir dosyada yok**; `Beam`/`Trail`/`Lighting` yalnız `ei-ekstra.js` içinde
**2B GUI önizleme sınıf adı** olarak geçiyordu (gerçek API kullanımı değil); `Animator` yalnız üretilen betiğin adı
(`EI_Animator`); `Tool` yalnız eklenti sözlüklerinde. Yani **dünya efekti, karakter animasyonu ve dünya
etkileşimi tamamen yoktu** — bu raporun konusu budur.

---

## 2. Sistem analizi ve sınıflandırma

| # | Alan | Sınıf | Kanıt |
|---|---|---|---|
| A1 | GUI animasyon motoru + parite + aktarım | **A** (var, doğrulanmış) | `verify_anim_parity.py`, `verify_transfer_to_studio.py` yeşil |
| A2 | 10 GUI efekti, envanterden kendi resmimiz | **A** | `verify_ekstra.js`, `verify_panel_params.js` yeşil |
| A3 | Öğrenme kanalı (kalıcı kayıt) | **A** | `EILearn` + `plugin:SetSetting`; "öğrenildi" iddiası yalnız bu kanal için geçerli |
| B1 | GUI efekt parametreleri (Süre, Kaç tane) | **B** (geliştirilebilir) | Panel alanları var; dünya efektleri bu kadranları **kullanmıyor** → VFX tarafına taşındı |
| B2 | Eklenti dağıtımı | **B** | 7 modül gömülüyordu; EIVfx eklenerek 8'e çıkarıldı (davranış değişmedi) |
| C1 | Dünya VFX (ParticleEmitter/Trail/Beam/Highlight/ışık) | **C** → eklendi | Tarama: hiç kullanılmıyordu |
| C2 | Karakter animasyonu (Animator + AnimationTrack, öncelik/ağırlık) | **C** → eklendi | Tarama: `AnimationTrack` yok |
| C3 | Dünya etkileşimi (ProximityPrompt, ClickDetector, Tool, RemoteEvent) | **C** → eklendi | Tarama: hiçbiri yok |
| C4 | Post-process (renk/blur/bloom/atmosfer) | **C** → eklendi | Tarama: `ColorCorrectionEffect` vb. yok |
| C5 | Kamera (FOV tween) | **C** → eklendi | Tarama: kamera hiç ele alınmıyordu |
| C6 | Istemci/sunucu yetki ayrımı | **C** → eklendi | Eskiden yalnız tek bir LocalScript vardı; yetki kavramı yoktu |
| D1 | Gerçek Studio'da görsel sonuç | **D** (doğrulanamadı) | Bu ortamda Roblox Studio yok |
| D2 | Roblox dokümantasyonuyla son teyit | **D** | Ortamın ağ erişimi yalnız github/npm/pypi → resmî doküman çekilemedi; doğrulama **yerleşik beyaz liste** ile |
| D3 | Gerçek mobil cihazda FPS/bellek ölçümü | **D** | Yalnız tasarım bütçesi + birim testi var |
| D4 | Gerçek AnimationId varlıkları | **D** | Kimlikler **projeden** gelir; motor kimlik uydurmaz (yoksa oynatmaz) |
| D5 | Panel/eklenti arayüzünde VFX düğmeleri | **D / kalan iş** | Bu turda kapsam dışı bırakıldı (mevcut panel davranışı bozulmasın) |

Ayrım notu: "2 preset mobilde kapanır" = **tasarım ilkesi**; "Süre alanı 0,55 sn" = **kullanıcı tercihi**;
"aynı karede çift tetikleme engellenir" = **teknik güvence**. Üçü raporda karıştırılmadı.

---

## 3. Geliştirme planı (uygulanan sıra)

1. **Kaynak gör, say** — modül satırları, sınıf taraması, mevcut belgeler (`EFEKT-ARASTIRMA.md`). ✅
2. **Tek doğruluk kaynağı** — `vfx/vfx-library.json` (32 preset; her presetin gerekçesi `why`).
3. **API beyaz listesi + şema kapısı** — üreteç uydurma özellik/sınıf/enum görürse **durur**.
4. **Karar çekirdeği (saf)** — `suggest/plan/tryPlay/tick/release/canPlay/animPlan/limits/describe`;
   Roblox API'sine yükleme anında dokunmaz (eklentiye gömülebilir olması için şart).
5. **Çalışma zamanı (Lua)** — nesne kurulumu, particle patlaması, trail/beam, highlight, post-process,
   kamera tween, ProximityPrompt/ClickDetector/Tool/RemoteEvent, Animator:LoadAnimation; hepsi `pcall` korumalı.
6. **JS aynası** — panel tarafı aynı kararı verir; parite kapısı Lua ≡ JS kanıtlar.
7. **Kapılar** — `tests/verify_vfx.py` (55 kontrol) + `tests/verify_vfx_parity.py` (4692 satır birebir).
8. **Entegrasyon** — EIVfx, `build_rbxmx.py` ile eklenti paketine gömüldü (8. modül), dağıtım kopyası güncellendi.
9. **Rapor + belge güncellemesi.**

---

## 4. Yeni sistem

**Ad:** EIVfx — dünya efekti · karakter animasyonu · etkileşim motoru (mevcut `EIAnim`'in **yerine geçmez**, yanında durur).

**Dosyalar**
- `kaynak/assistant/vfx/vfx-library.json` (3128 satır) — 32 preset: **world 12 · char 9 · interact 4 · post 3 · cam 2 · decide 2**;
  yetki: 26 istemci / 6 sunucu; mobilde kapanan 2; 17 farklı Roblox sınıfı.
- `kaynak/assistant/runtime/lua/EIVfx.lua` (502 satır) — saf karar bölümü + Roblox çalışma zamanı.
- `kaynak/assistant/runtime/js/ei-vfx.js` (3269 satır) — aynı kararın JS aynası (veri blokları üreteçten).
- `kaynak/assistant/tools/build_vfx_lua.py` (265 satır) — veri → iki dil + **API beyaz listesi** (23 sınıf, 10 enum) + şema kapısı; `--check`.

**Karar sözleşmesi (tam sayı puan):** bağlam 40 / joker `*` 20 · olay 50 / `*` 20 · hedef 15 / `*` 5 ·
`(3 − maliyet) × 5` · mobilde uygunluk +5. Sıralama: puan ↓, kimlik ↑. Liste **daima** `decide_none` ile biter;
UI olayında `reuse_ui_anim` (yeni efekt eklenmez, mevcut GUI animasyonu kullanılır).
`plan()` = en iyi + alternatifler + `skipped` (sebep: `butce` / `mobil`) + `limits`.

**Bütçe:** masaüstü `{budget 3, maxActive 60}` · mobil `{budget 1, maxActive 24}`.
`tryPlay` sebepleri: `bekleme` (cooldown) · `es-zamanli` (aynı efektin eşzamanlı sınırı) · `kapasite` · `bilinmeyen`.
`tick` süresi dolanı düşürür, `last` kayıtlarını 60 sn sonra budar; `release` durumu temizler.

**Animasyon (karakter):** `animPlan(id, {assetId, active})` →
`ok` · **`tekrar`** (aynı animasyonun yeniden tetiklenmesi: kombo zinciri) · `oncelik` (aynı slotta **farklı**
animasyon, aynı ya da düşük katman) · `asset-eksik` (**kimlik yoksa oynatılmaz**) · `char-degil` · `animasyon-degil`.
Öncelikler: Core 0 · Idle 1 · Movement 2 · Action 3 · Action2 4 · Action3 5 · Action4 6.
Yükselen öncelik `stopLower=true` ile alttakini durdurur; hasar tepkisi (`hit_react`) 0.85 ağırlıkla **biner**, kesmez.

**Yetki ayrımı (oyun sonucu ≠ görsel):** `authority:server` presetler (atmosfer/bloom, ProximityPrompt,
ClickDetector, Tool, RemoteEvent) istemcide `yetki-sunucu` ile reddedilir; istemciye ait görseller
(`world_hit_spark`) sunucu tarafında `yetki-istemci` ile reddedilir. RemoteEvent kanalı `ReplicatedStorage`'ta
yeniden kullanılır (çift kanal açmaz).

**Temizlik/performans:** her preset `cleanup` (delay/stop) + `dur` + `cooldown` + `maxActive` taşır; nesneler
süre sonunda `Destroy` edilir; mobilde bütçeyi aşan efektler **sebebiyle birlikte** listelenir (sessizce kaybolmaz).

**API uydurma yasağının uygulanışı:** beyaz liste dışı her şey üreteci durdurur —
kanıt: `ParticleEmitter.Gravity`, `ParticleEmitterShape.Torus`, sınıf `Trail2` → **[HATA] vfx kütüphanesi: …** ile reddedildi.

---

## 5. Yapılan değişiklikler

**Yeni (5 dosya):** `assistant/vfx/vfx-library.json`, `assistant/runtime/lua/EIVfx.lua`,
`assistant/runtime/js/ei-vfx.js`, `assistant/tools/build_vfx_lua.py`, `tests/verify_vfx.py`, `tests/verify_vfx_parity.py`.

**Değişen (1 satır):** `roblox-studio-plugin/build_rbxmx.py` → `MODULES` listesine `("EIVfx", "EIVfx.lua")`
(eklenti paketi 8 modül; **davranış değişikliği yok**, geri almak için satırı silmek yeter).
Yeniden üretim: `python3 build_rbxmx.py` → `EasyImportStudioPlugin.rbxmx` (454 KB) → `studio-plugin/EasyImportStudioPlugin.rbxm`
(md5 eşit: `ae0c633d…`).

**Kapıların bulduğu ve düzelttiğim 5 gerçek hata (uydurma değil, kanıtlı):**
1. `TweenService` **global** sanılıp doğrudan çağrılıyordu → Roblox'ta böyle bir global yok; `game:GetService("TweenService")` ile servisten alınır hâle getirildi (kamera geçişi artık gerçekten çalışıyor).
2. `animPlan` aynı öncelikte **her** çağrıyı engelliyordu → aynı animasyonun yeniden tetiklenmesi (`tekrar`) serbest, yalnız **farklı** animasyon aynı katmanda engelli.
3. Veri şemasında `repeat` alanı **Lua anahtar sözcüğü** → `{ repeat = … }` sözdizimi hatası; alan `freq` oldu, üreteç artık anahtar sözcüğü **hata vererek** reddediyor.
4. `limits` Lua'da `or`, JS'te `||` kullanıyordu → `budget = 0` iki dilde farklı sonuç veriyordu; ikisi de "sayı verilmişse onu kullan" kuralına çekildi (parite kapısı bunu artık test ediyor).
5. Kütüphanede boş `AnimationId` (projeden gelecek) şemaca reddediliyordu → anchor alanı istisna oldu; **kimlik yoksa çalışma zamanı oynatmıyor** (uydurmuyor).

Yan bulgu: `verify_vfx.py`'de Lua `io` tamponu kaçışları çözmediği için satır sonları normalize ediliyor
(bu, testin kendi altyapı düzeltmesi — motor değil).

---

## 6. Test sonuçları

| Kapı | Ne kanıtlıyor | Sonuç |
|---|---|---|
| `tests/verify_vfx.py` | **55 kontrol**: kütüphane bütünlüğü+gerekçe · doğru bağlam→doğru seçim · efekt eklememek de karar · mobil bütçe · API reddi · cooldown/eşzamanlılık/kapasite · temizlik (sızıntı yok) · animasyon öncelik/ağırlık/çakışma · istemci–sunucu yetkisi · çalışma zamanı nesne+değerleri | **GEÇTİ** |
| `tests/verify_vfx_parity.py` | Lua ≡ JS: **4692 satır birebir** (4480 suggest · 12 plan · 20 senaryo · 15 animPlan · 128 canPlay · 5 limits · 32 describe) + kütüphane/modül senkronu | **GEÇTİ** |
| `assistant/tools/build_vfx_lua.py --check` | Kütüphane ↔ iki modül senkron (elle düzenleme yasak) | **SENKRON (32 preset)** |
| Tam süit | 18 Python + 6 Node + ui-tools | **29 geçti · 6 düştü** — düşenler **bakım dışı** (`verify_generalization`, `verify_model`, `verify_plugin_v9`, `verify_real_dataset`, `verify_real_run`, `verify_teacher`; ikisi eksik veri kümesi, biri eski eklenti işareti). VFX değişiklikleriyle ilgisi yok, HEAD'de de düşüyorlar. |
| `tests/verify_transfer_to_studio.py`, `verify_studio_port.py` | Figma→JSON→Studio zinciri ve asistan köprüsü (EIVfx gömülünce bozulmadı) | **GEÇTİ** |

Kanıt örnekleri (gerçek çıktılardan):
- `combat/hit/npc` → `world_hit_spark` (115 puan); `ui/menu/ui` → `reuse_ui_anim`; `combat/zzz/npc` → `decide_none`.
- Mobilde `world_lightning_beam` (sebep `butce`) ve `world_vfx_combo_stage` (sebep `mobil`) düşürüldü.
- Cooldown: 1.00 ok → 1.05 `bekleme` → 1.25 ok; aynı efektten 4. çağrı `es-zamanli`; 24 dolgu kaydıyla `kapasite`, 23 ile `ok`.
- `world_hit_spark` tek dalga = **18 × Emit(1)** (Rate 0; sürekli yayın yok), süre sonunda **0 nesne** kaldı.
- `char_attack_combo` Action2 / ağırlık 1.0 / `stopLower`; kimlik yoksa `asset-eksik` → **oynatılmadı**;
  `AnimationId = rbxassetid://9` gerçekten yüklendi; hasar tepkisi 0.85 ağırlık, kesmiyor.
- Kamera: FOV 74 → 78 (TweenService servisten), `release` ile geri dönüş kaydı kurulu.

---

## 7. Kalan işler / doğrulanmayanlar

1. **Gerçek Studio'da görsel doğrulama (D1).** Parçacık görünümü, trail/beam estetiği, kamera hissi gözle onaylanmadı.
2. **Resmî doküman teyidi (D2).** Beyaz liste koddaki bilgiyle kuruldu; ortamın ağ kısıtı nedeniyle Roblox dokümanı çekilemedi.
3. **Mobil ölçüm (D3).** 24 eşzamanlı sınır ve bütçe **tasarım** kararı; gerçek cihazda FPS ölçülmedi.
4. **Gerçek animasyon varlıkları (D4).** `AnimationId` projeden gelir; kullanıcı kendi kimliklerini verecek.
5. **Panel/eklenti arayüzü (D5).** VFX için panel düğmesi ve "motoru oyuna yerleştir" akışı yok; modül şu an eklenti paketinde taşınıyor ama oyuna yazılmıyor.
6. **Ses.** 3B ses efektleri kapsam dışı (mevcut "ses nesnesi yok" sınırı korunuyor).
7. **Bakım dışı 6 kapı.** VFX ile ilgisiz; ayrı bir iş olarak duruyor.

> Bu bölümdeki maddeler **yapılmadı**; hiçbiri "tamamlandı" sayılmadı.
