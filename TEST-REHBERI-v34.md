# Test Rehberi — v34 (dünya efekti · karakter animasyonu · etkileşim)

v33 rehberi (`TEST-REHBERI-v33.md`) arayüz/animasyon/envanter adımlarını anlatır; bu rehber **yeni EIVfx
modülünü** nasıl test edeceğini söyler. Kural: burada yazmayan hiçbir şey "test edildi" sayılmaz.

## 1) Otomatik kapılar (iki komut, hepsi yeşil olmalı)

```bash
cd kaynak

# a) Motor kararları + çalışma zamanı (sahte Roblox bu dosyanın içinde) — 55 kontrol
python3 tests/verify_vfx.py

# b) Lua ≡ JS parite + kütüphane/modül senkronu — 4692 satır birebir
python3 tests/verify_vfx_parity.py

# c) Kütüphaneyi elle mi düzenledin? (senkron denetimi; yazmaz)
python3 assistant/tools/build_vfx_lua.py --check
```

Beklenen çıktı son satırları:
- `SONUÇ: GEÇTİ — dünya efekti · karakter animasyonu · etkileşim motoru kararları doğru ve güvenli`
- `SONUÇ: GEÇTİ — Lua ≡ JS (4692 satır, fark yok)`
- `[OK] EIVfx.lua + ei-vfx.js kütüphane ile SENKRON (32 preset doğrulandı)` (32 preset)

Kapının yakaladığı şeylerden örnek (elle denemek istersen):
`assistant/vfx/vfx-library.json` içinde bir presetin `props` bölümüne `"Gravity": {"t":"n","v":9}` yaz → `--check`
**[HATA] … ParticleEmitter.Gravity: Roblox'ta bu özellik yok** diyerek durur. Aynısı uydurma sınıf (`Trail2`) ve
uydurma enum öğesi (`ParticleEmitterShape.Torus`) için geçerli. Denemeyi bitirince dosyayı geri al (ya da
`python3 assistant/tools/build_vfx_lua.py` ile üreteçten yeniden üret).

## 2) Eklentiye aktarma (Studio'ya giden dosya)

```bash
cd kaynak/roblox-studio-plugin
python3 build_rbxmx.py          # .lua + 8 gömülü modül → .rbxmx (454 KB)
python3 build_rbxmx.py --check  # senkron mu?
cp EasyImportStudioPlugin.rbxmx /home/user/EasyImport32v/studio-plugin/EasyImportStudioPlugin.rbxm
```

`studio-plugin/EasyImportStudioPlugin.rbxm` ile `kaynak/roblox-studio-plugin/EasyImportStudioPlugin.rbxmx`
**bayt eşit** olmalı (md5). Studio'da eski eklentiyi silip bu dosyayı sürükle.

## 3) Studio'da elle deneme (yapılmadı — senin yapacağın kısım)

Şu an panel/eklenti arayüzünde "VFX motorunu oyuna koy" düğmesi **yok**; modül eklenti paketinin içinde taşınıyor.
Elle denemek için:

1. Studio'da `ServerScriptService` (oyun durumu) ve `StarterPlayerScripts` (görsel) altına birer **ModuleScript** aç.
2. İçine `kaynak/assistant/runtime/lua/EIVfx.lua` içeriğini yapıştır (dosya olduğu gibi geçerli Lua'dır).
3. Karakter animasyonu için projendeki `AnimationId`'yi ver:
   ```lua
   local EIVfx = require(script.Parent.EIVfx)              -- istemci tarafı
   local ok, reason = EIVfx.tryPlay(EIVfx.state(), "world_hit_spark", os.clock(), { mobile = false })
   if ok then EIVfx.play(characterOrPart, "world_hit_spark", { now = os.clock() }) end

   -- kimlik yoksa oynatılmaz (uydurmaz):
   local plan, why = EIVfx.animPlan("char_attack_combo", { assetId = "rbxassetid://SENIN_KIMLIGIN", active = {} })
   ```
4. Sunucu tarafında yetkili olanlar: `EIVfx.play(part, "post_mood_atmosphere", { server = true })` (atmosfer),
   `interact_proximity_prompt`, `interact_click_detector`, `interact_tool_activate`, `interact_remote_event`.
   Bunları istemcide çağırırsan `yetki-sunucu` sebebiyle reddedilir — istemciye ait görseli (`world_hit_spark`)
   sunucuda çağırırsan `yetki-istemci` alırsın.

**Bakılacaklar (gözle):** parçacık yoğunluğu/kıvılcım görünümü · trail/beam estetiği · ışık parlaklığı ·
highlight okunurluğu · kamera geçişinde rahatsızlık · mobil cihazda FPS ve ısınma.
Bu 6 madde **ölçülmedi**; geri bildirime göre preset `props` değerleri üreteçle ayarlanır.

## 4) Bilinen sınırlar (bu sürümde kabul edilen)

- Gerçek Studio ve gerçek mobil cihaz testi yok; kapılar sahte Roblox + iki dilde parite ile doğrular.
- Resmî Roblox dokümantasyonu bu ortamın ağ kısıtı nedeniyle çekilemedi; API beyaz listesi koddaki bilgiyle kuruldu.
- Ses (3B efekt) kapsam dışı; mevcut projede ses nesnesi üretilmiyor.
- Figma tarafında dünya etiketleri (`_3d`, `_tilt`, `_billboard`, `_surface`, `_prompt`, `_hold`) hâlâ yok.
- Bakım dışı 6 kapı (`verify_generalization`, `verify_model`, `verify_plugin_v9`, `verify_real_dataset`,
  `verify_real_run`, `verify_teacher`) bu sürümde de düşük; VFX ile ilgisi yok.
