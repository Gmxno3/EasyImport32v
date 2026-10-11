# EasyImport — Asistanlı sürüm

Klasörler:
- `figma/` — Figma eklentisi (`code.js`, `ui.html`, `manifest.json`). Yeni: görsel ölçümü (`item.ei`), eğitim dosyası (`_egitim.json`), asistan özeti.
- `roblox-studio-plugin/` — Studio eklentisi. `EasyImportStudioPlugin.rbxmx` (Studio'ya sürüklenecek dosya; `.rbxm` ile aynıdır).
  `.lua` kaynağı tek doğruluk kaynağıdır; `python3 build_rbxmx.py` ile paketlenir.
- `assistant/` — asistan modülleri (`runtime/lua`), animasyon kütüphanesi, eğitim/doğrulama araçları.
- `tests/` — Figma birleştirme kapısı ve Studio köprü kapısı.

Kurulum: Figma'da `figma/manifest.json` ile eklentiyi içe aktar. Studio'da `EasyImportStudioPlugin.rbxmx`'i sürükle.

Asistan yalnızca Figma'dan gelen JSON'da `ei` ölçümü varsa devreye girer; yoksa v9 davranışı birebir korunur.

## Bu sürümde eklenenler

- **Figma paneli asistanı:** Sonuç ekranında her katmanın tahmini sınıfı (model / öğrenme / düşük güven), güven yüzdesi ve sınıf seçici var. Sınıf değiştirmek bir düzeltmedir: öğrenme durumuna yazılır ve Figma'nın kendi depolamasında (`clientStorage`) saklanır. "Öğrenme paketini indir" düğmesi kanonik `ei-learn v1` metnini indirir.
- **Studio öğrenmesi:** Düzeltmeler eklenti ayarında (`SetSetting`, anahtar `EasyImportLearn`) kalıcıdır.
- **Derleme:** `figma/ui.html` `figma/ui.base.html` + `assistant/runtime/js` + `figma/asistan_panel.*` dosyalarından `python3 figma/build_ui.py` ile üretilir. Kaynağı değiştirirsen ui.html'i yeniden üret.

Yapılmayanlar: animasyon seçici arayüzü, FX tespiti, `train_anim.py`, UIGridLayout/Item/DROP/MERGE öğrenmesi.

## Testler

- `tests/verify_figma_merge.js` — code.js birleştirmesi (v9 bayt eşitliği, ei ölçümü, E1)
- `tests/verify_learn_channel.js` — öğrenme kanalı (clientStorage kayıt/okuma)
- `tests/verify_studio_port.py` — Studio asistan köprüsü, gerçek fixture'larda
- `tests/verify_ekstra.js` — ekstra kütüphane (1022 simge) + öğrenen efekt simgesi sıralayıcı (kütüphane kökünü kendisi bulur)
- `tests/verify_panel_anim.py` — panel açılışı/çıkışı, `task.delay` ile gizleme, yarış iptali
- `tests/verify_panel_params.js` — "Süre"/"Kaç tane" önizleme planı, envanter, panel çıkış yuvası, kategori→yuva eşlemesi
- `tests/verify_transfer_to_studio.py` — **Roblox aktarımı uçtan uca**: gerçek Figma dışa aktarımı → JSON →
  Studio eklentisi bağlamaları → LocalScript → sahte Roblox (panel açılış/kapanış, döngü, geçiş/metin, efekt
  ayarları, envanter resimleri; 116 animasyonun 180 track'inin tamamı)
- `tests/verify_vfx.py` — **dünya efekti · karakter animasyonu · etkileşim (EIVfx)**: 55 kontrol (kütüphane bütünlüğü+gerekçe, bağlam→seçim, "efekt eklememek de karar", mobil bütçe, API reddi, cooldown/eşzamanlılık/kapasite, temizlik, animasyon önceliği, istemci–sunucu yetkisi, çalışma zamanı nesneleri)
- `tests/verify_vfx_parity.py` — **EIVfx Lua ≡ JS**: 4692 satır birebir karar (4480 suggest · 12 plan · 20 senaryo · 15 animPlan · 128 canPlay · 5 limits · 32 describe) + `build_vfx_lua.py --check` senkronu
- `assistant/tools/verify_anim.py`, `verify_learn.py`, `verify_merge.py`, `verify_anim_parity.py` — asistan modülleri

## Sürüm 3 (animasyon ve tamamlanan asistan)

- **Animasyon seçicisi (Figma paneli):** Her buton ve üst düzey öğe için giriş, hover ve basma animasyonu seçilebilir. Seçim öğrenmeye kaydedilir (kabul/ret). Gözlem olmadan sıralama v10 ile birebir aynıdır.
- **Studio:** Animasyon planı eklentinin öğrenme durumunu kullanır (`assist.learn`).
- **Lua ≡ JS parite kapısı:** `assistant/tools/verify_anim_parity.py` — plan, 840 seçenek sırası ve 8 LocalScript kaynağı iki dilde bayt birebir.
- **Veri üretimi:** `assistant/tools/build_anim_lua.py` hem `runtime/lua/EIAnim.lua` hem `runtime/js/ei-anim.js` veri bloğunu ve şablonu üretir.

## Sürüm 4 (v34 — dünya efekti · karakter animasyonu · etkileşim)

- **Yeni bağımsız modül: EIVfx** (`assistant/vfx/vfx-library.json` + `runtime/lua/EIVfx.lua` + `runtime/js/ei-vfx.js`).
  Mevcut `EIAnim` (GUI) **değişmedi**; EIVfx onun yanında durur ve dünya tarafını ekler.
- **32 preset:** world 12 · char 9 · interact 4 · post 3 · cam 2 · decide 2 (26 istemci / 6 sunucu; mobilde kapanan 2).
- **API beyaz listesi:** 23 sınıf + 10 enum; uydurma sınıf/özellik/enum → üreteç **durur** (kanıt: `ParticleEmitter.Gravity`,
  `ParticleEmitterShape.Torus`, `Trail2` reddedildi).
- **Karar:** `suggest` puanlı liste (daima `decide_none` ile biter) · `plan` alternatif + `skipped` sebep · `tryPlay`
  cooldown/eşzamanlılık/kapasite · `tick`/`release` temizlik · mobilde `{budget 1, maxActive 24}`.
- **Animasyon:** `animPlan` → `ok · tekrar · oncelik · asset-eksik · char-degil · animasyon-degil`; kimlik yoksa oynatılmaz.
- **Yetki:** sunucu presetleri istemcide reddedilir, istemci görselleri sunucuda; RemoteEvent yeniden kullanılır.
- **Paket:** `build_rbxmx.py` artık EIVfx'i de gömer (8 modül). Yeniden üretimden sonra `studio-plugin/` kopyasını güncelle.
- Ayrıntılı rapor: kök dizinde `Efekt-Animasyon-Sistemi-Raporu.md`.

## Sürüm 4 (v33 — GUI animasyonları, Süre, envanter)

- **GUI/UI animasyonları:** `cikis`/`gecis`/`metin`/`fx` kategorileri üretime girdi. Panel açılışı `panel_*` havuzundan
  (varsayılan **panel_slide_left_soft**: soldan sağa, yavaş, sönerek), kapanışta `exit_slide_left`; çıkış animasyonu
  bitince panel gizlenir. Studio eklentisi panel öğelerini `EI_Panel` ile işaretler, JSON'daki `anim.hide` bağlanır.
- **"Süre" ayarları:** kütüphane önizlemesi artık ayarlara uyar (`fxPreviewPlan`: Kaç tane / Süre / Görünürlük / Döngü …);
  önceden önizleme sabit değerlerle oynuyordu, kaydırıcı hiçbir şeyi değiştirmiyordu.
- **Envanter:** efekt resmi olarak kendi resimlerimiz (tasarımdaki PNG'ler) kullanılır; ek Figma katmanı yok;
  envanter Roblox aktarımında sıfırlanır.
- **Kapılar:** `tests/verify_panel_anim.py`, `tests/verify_panel_params.js`; parite fikstürüne panel + `cikis` eklendi.

Kalan (bilinçli kapsam dışı): `train_anim.py`, UIGridLayout/Item/DROP/MERGE öğrenmesi, gerçek Studio'da otomatik test.
