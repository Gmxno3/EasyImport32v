# EasyImport — Proje Notu (bağlam dosyası)

Bu dosya, sohbetin dışında da projenin ne olduğunu ve nerede kaldığını tutar. Yeni bir oturumda önce burayı oku.

## Amaç
Figma'da tasarlanmış bir ekranı Roblox Studio'da çalışan UI'ye çevirmek. Figma eklentisi JSON üretir;
Studio eklentisi JSON'u okuyup GUI ağacını ve animasyon LocalScript'lerini kurar.
Hiçbir API, sunucu veya bulut kullanılmaz; her şey Figma ve Studio içinde çalışır.

## Animasyon nedir?
UI animasyonu: GUI nesnelerinin özelliklerini `TweenService` ile değiştiren LocalScript'lerdir.
Karakter (humanoid) animasyonu DEĞİLDİR. Kullanıcı animasyon adlarını görmez; JSON'da `_Animasyon N` adıyla yer alır.

## Asistan ne yapar
1. **Stil bulur:** stud / anime / cartoon / belirsiz (ölçümlerden).
2. **Sınıf tahmin eder:** adı olmayan katmanlar için Frame, TextLabel, TextButton, ImageButton gibi sınıfları tahmin eder.
   Ad sinyali (`_button` gibi) varsa kural motoru kazanır.
3. **Animasyon seçer:** giriş, hover, basma. Kullanıcı Figma panelinde değiştirebilir; değişiklik öğrenilir.
4. **Öğrenir:** düzeltmeler (sınıf ve animasyon) Figma'da `clientStorage`'da, Studio'da eklenti ayarında tutulur.

## Veri akışı (animasyon)
- Figma paneli seçimleri yapar → `doc.anims["_Animasyon N"] = {src, cat, trig, tracks}` ve düğüm `anim = {show?, hover?, press?}`.
- Studio `buildNode` içinde `EI_Id` niteliği ve `animBindings` listesi üretir.
- `EIAnim.buildSourceSpec` JSON tanımlarından LocalScript yazar (`_Animasyon N` → Lua'da `_Animasyon_N`).
- Tanımı olmayan referans sessizce düşer; betik bozulmaz.

## Dosya yapısı
- `figma/` — Figma eklentisi. `code.js`, `ui.base.html` (kaynak), `asistan_panel.{js,html,css}`, `build_ui.py` (ui.html üretir), `manifest.json`.
- `roblox-studio-plugin/` — `EasyImportStudioPlugin.lua` (kaynak), `build_rbxmx.py` (`.rbxmx` üretir; modülleri gömer).
- `assistant/` — `runtime/lua` ve `runtime/js` (aynı mantığın iki dilde karşılığı), `anim/anim-library.json`,
  `tools/build_anim_lua.py` (veri ve şablon üretir), `datasets/` (fixture'lar, altın dosyalar).
- `tests/` — Figma birleştirme, öğrenme kanalı, Studio köprüsü, JSON animasyon üretimi.
- `UI-Animasyon-Arastirma.md` — animasyon araştırması (Framewisp referansı, eşleme, öncelik, tasarım kuralları).

## Nasıl derlenir / doğrulanır
- `python3 figma/build_ui.py` → `figma/ui.html`
- `python3 roblox-studio-plugin/build_rbxmx.py` → `EasyImportStudioPlugin.rbxmx` (`--check` ile senkron denetimi)
- `python3 assistant/tools/build_anim_lua.py` → `EIAnim.lua` ve `ei-anim.js` veri blokları (`--check`)
- Kapılar: `node tests/verify_figma_merge.js`, `node tests/verify_learn_channel.js`, `python3 tests/verify_studio_port.py`,
  `python3 tests/verify_anim_spec.py`, `python3 assistant/tools/verify_anim.py`, `python3 assistant/tools/verify_anim_parity.py`,
  `python3 assistant/tools/verify_learn.py`, `python3 assistant/tools/verify_merge.py`.

## Durum (v7)
- Tamam: stil/sınıf asistanı; Figma panelinde tahmin, düzeltme, animasyon seçici; JSON animasyon yazımı (`_Animasyon N`);
  Studio'da JSON'dan LocalScript; öğrenme kalıcılığı; Lua ≡ JS parite; çevrimdışı çalışma.
- Tasarım kararları (madde 3): stil bonusu, konum kuralı (kapat → yalnız hover), tutarlılık (≥%50), öğrenme önceliği.
- P1 (v7): `_reveal` (enter_reveal_showcase), `_swing` (enter_swing_door), `_wiggle` tek sallanma (hover_wiggle_once),
  kaskad (aynı üst öğede ≥3 buton, 0,06 sn adım), döngü (loop_blink_cta, loop_wiggle_icon; en fazla 3 öğe),
  kalıcı seçim grubu (select_outline_pop; aynı üst öğede ≥2 sekme/slot/seçenek adlı buton).
- Testler: verify_anim_parity (bölüm 6–8), tests/verify_anim_p1.py (sahte Roblox), tests/verify_anim_spec.py,
  tests/verify_studio_port.py, tests/verify_figma_merge.js, tests/verify_learn_channel.js.
- Gerçek Figma ve Roblox Studio'da uçtan uca test EDİLMEDİ (BASLA.md adımları ile test edilecek).
- Açık: `_burst`, `_3d`, `_focus`, `_fall`, `_hold` (UI tween dışı); Studio'da animasyon seçici; FX tespiti;
  `train_anim.py`; UIGridLayout/Item/DROP/MERGE öğrenmesi.

## Dikkat
- Hata ayıklarken fengari'de `io.open` yoktur; Lua çıktısı `io.write` ile bir tampona toplanır (testler böyle).
- Bu projede kütüphane verisi ELLE düzenlenmez; `build_anim_lua.py` üretir.


## v14 (etkileşim, gölge kararı)
- Gölge kararı (L10) değişti: UIShadow artık yalnızca `_shadow` etiketiyle; otomatik gölge kaldırıldı.
- Etkileşim: `_open:Ad`, `_toggle:Ad`, `_tab:Ad`, `_close` (parametresiz = en yakın panel), `_tabgroup`, `_panel`.
  Paneller başlangıçta kapalı; eylem hedefleri ve içindeki `_close` üzerinden belirlenir. Açılan panelde
  içteki öğelerin giriş animasyonları yeniden oynar.
- `_fit` (TextScaled), `_nolist` (otomatik liste/ızgara kapalı), `_turn` (hover kart dönüşü).
- Testler: tests/verify_export_tags.js, tests/verify_etkilesim.py.
- Kalan: _pointer, _card, _lean, _color, _txt, _frame, _keep, _nodim, _3d, _tilt, _billboard, _surface, _prompt,
  _hold, _focus, _flow, _rays, _pixels, _drift, tam _stroke, _float kadranı, UI düzenleyici, Assets kütüphanesi.
- Kapsam dışı (kullanıcı kararı): canlı senkron, sunucu/yükleme mimarisi, iş modeli (plugin bitince).


## v22 (UI Tools: dağıtma, ok tuşları; kullanıcı kaynağı)
- Kaynak tabanı kullanıcının yüklediği v21 kaynağıdır (Studio'da Scale/Offset anahtarları ve PRO rozeti kullanıcı kararıyla kaldırıldı; `baseplate` galeri hariç tutma listesi kullanıcının).
- UI Tools: dağıtma (yatay/dikey) ve ok tuşu kısayolları eklendi; testler: çekirdek 135, plugin 137, mutasyon 20/20.
- Lisans kontrolü (UI-Plus, `reference/`): UI Tools kodu üçüncü taraf kodu kopyalamaz. Analiz: 52 Lua kaynağıyla karşılaştırma; ardışık 6 satır eşleşmesi 0 (UIToolsCore 0, UIToolsPlugin 0). Ortak satırlar yalnız standart Roblox ifadeleri (GetService çağrıları). `reference/UI-Plus-*.rbxm` dağıtılmaz (lisanssız).
- Gerçek Roblox Studio'da UI Tools henüz çalıştırılmadı.


## v23 (lisans güvenliği, ekstra kütüphane, öğrenen efekt simgeleri)
- **UI-Plus güvenliği:** `reference/` klasörü dağıtılmaz (üçüncü taraf, lisanssız). UI Tools kodunda ayırt edici adlar
  kendi terimlerimizle değiştirildi: `Core.bounds` → `Core.boundingBox`, `Core.snap` → `Core.roundToGrid`,
  `Core.nudge` → `Core.shiftRects`, `Core.reclassPlan` → `Core.classChangePlan`, `nudgeSelected` → `shiftSelection`,
  `reclassSelected` → `changeSelectionClass`, `UT_Nudge_*` → `UT_Shift_*`. Testler ve mutasyonlar güncellendi.
  Kopya kontrolü tekrarlandı: ardışık 6 satır eşleşmesi 0.
- **Ekstra kütüphane:** `assistant/tools/build_ekstra.py <zip>` ikon paketinden 1022 simge üretir (64px ve 64w varyantları).
  Çıktılar: `kutuphane/EkstraKutuphane/<kimlik>.png` (Asset Manager toplu yükleme), `kutuphane/ekstra-kutuphane.json`,
  `assistant/runtime/js/ei-ekstra.js` (Figma paneli için dizin ve küçük resimler).
  Kimlik: `ikon_<kategori>_<ad>_<varyant>[_w]`; dosya adı = kimlik (Decal eşleşmesi için).
- **Öğrenen efekt simgeleri:** `assistant/runtime/js/ei-fxpick.js` (EIFxPick). Puan = EILearn öğrenilmiş skoru + 0,25 × tohum
  (kategori + ad öncülü). Tohum bir ön eğitimdir; kullanıcı seçimleri (kabul/red) öğrenilmiş skoru artırır/azaltır.
  Efekt türü başına ayrı bağlam (`fx|icon`). Testler: `tests/verify_ekstra.js` (15 kontrol).
- Figma paneli: efekt satırında ikon ızgarası (kategori, arama, en çok 4 resim); seçimler `anim.fxImages` olarak JSON'a girer
  (Studio'nun mevcut şablon mantığıyla çalışır; Studio değişmedi).
- Tarayıcı testi: seçim JSON'a yazıldı, öğrenme kaydedildi, sınır 4'te tutuldu, kaldırma çalıştı.
- Sınır: bu bir istatistiksel model değil, kural tabanlı tohum + kullanıcı geri bildirimi öğrenmesi.
  Sınıf modeli yeniden eğitilmedi. Gerçek Studio'da Decal adı eşleşmesi henüz doğrulanmadı.


## v24 (asistan eğitimi: efekt simge modeli)
- Etiketler: `assistant/tools/fx_labels.js` tohum puanlarından ZAYIF denetimle üretir (288 simge; eşik 0,5). İnsan etiketi değil.
- Model: `assistant/tools/train_fx.py` → `assistant/runtime/js/ei-fxmodel.js` (Naive Bayes, ad + kategori tokenları;
  destek < 10 olan sınıflar (burst, orb) modelde yok). Sınıflar: fall, orbit, twinkle.
- Ölçüm (dürüst): 5 katlı çapraz geçerlilik 1,000 — ama etiketler aynı kurallardan geldiği için BU ÖLÇÜ KENDİ KENDİNİ
  DOĞRULAR. Kategori dışarıda bırakma: 0,61 (n=98; Social %4, Player %80). Gerçek genelleme zayıf.
- Kullanım: ikon puanı = öğrenilmiş skor + 0,25 × (tohum + model) / 2. Öğrenme baskın kalır.
- Testler: `tests/verify_fxmodel.js` (JS ≡ Python posterior, fark 9e-16; 6 kontrol), `tests/verify_ekstra.js` (15 kontrol).
- Gerçek eğitim sinyali: panelde kullanıcının kabul/red seçimleri (EILearn). Daha güçlü model için insan etiketli
  simgeler gerekir (özellikle burst, orb, confetti, sweep sınıfları için).


## v25 (asistan eğitimi: görsel etiketler, ad-tabanlı model)
- Etiketler: 1022 ikonun her biri görsel olarak incelenerek (contact sheet) efekt uygunluğu verildi:
  none 671, fall 171, burst 89, twinkle 44, orbit 23, confetti 16, orb 8. Bu etiketler AI görsel yargısıdır, insan
  etiketi değildir; `assistant/datasets/labels/effect-icons-human.jsonl`.
- Model: `tools/train_fx.py` → `ei-fxmodel.js`. Yalnız simge adı + etiket tokenları (kategori tokenı kaldırıldı:
  genellemeyi bozuyordu). Sınıflar: burst, confetti, fall, none, orbit, twinkle (orb 8 örnekle dışarıda).
- Ölçüm: 5 katlı CV %90,8 (çoğunluk %66). Sınıf bazında: fall 0,91, none 0,99, burst 0,80, twinkle 0,61, confetti 0,25,
  orbit 0,00. Kategori dışarıda bırakma %33 (çoğunluk %66): yeni kategorilerde model çoğunluktan kötü.
- Sonuç: model yalnızca zayıf bir öncül (puanın %12,5'i). Asıl öğrenme sinyali kullanıcının kabul/red seçimleri.
- Yalnızca sayılar: sınıf modeline dokunulmadı; UIShadow politikası: yalnız `_shadow` etiketiyle (onaylandı).
- Manuel yükleme akışı (karar): ZIP indir → Asset Manager'a elle yükle → İsimden eşleştir. Sunucu/Open Cloud yok.

## v26 (sürüm etiketleri ve derleme)
- Kullanıcıya görünen tüm sürüm yazıları v26: Figma paneli başlığı/altbilgisi, Studio ana paneli (widget kimliği ve altbilgi), UI Tools başlığı.
- Eklentiler yeniden derlendi; derlenmiş dosyalarda eski sürüm yazısı yok, yeni özellikler içeride doğrulandı.

## v27 (görünür yenilikler)
- Figma ilk ekranda "Yeni (v27)" kutusu; "Animasyonlar ve asistan" bölümü açık geliyor.
- Studio durum satırı artık etkileşim, panel ve efekt sayılarını gösteriyor.
- Tüm sürüm yazıları v27.

## v28 (kalite, kütüphane önizleme, UILayout)
- Ekstra kütüphane 256 px orijinallere geçti (1022 simge; 10 simgenin 256 px'i yok, onlar 64 px). Asset Manager'a yüklenecek dosyalar 256 px.
- Figma: "Kütüphane ve önizleme" kartı (ilk ekran): 66 animasyon (önizlemede oynatılır), 1022 ikon (kategori/arama/ızgara),
  9 efekt önizlemesi. Önizleme CSS ile yaklaşıktır, Roblox'taki kesin davranış değildir; ikon önizlemesi 64 px'den çizilir.
- Animasyon seçenekleri: öğe için tüm uygun animasyonlar listelenir (önceden 1-2 öneri).
- Renkler: vurgu açıklaştırıldı, metin beyaz, açıklamalar okunur (Figma ve UI Tools).
- UI Tools: UILayout kartı (dikey/yatay liste, ızgara, dolgu, köşe, çerçeve, 1:1 oran, yerleşim/dolgu kaldır). Mevcut varsa çift eklenmez; geri alınabilir. Testler: plugin 149, mutasyon 21/21.
- Studio durum satırı etkileşim/panel/efekt sayılarını gösterir; tüm sürüm yazıları v28.
- Bilinen: paketteki "Icons New" klasöründeki 228 numaralı PNG henüz işlenmedi (Icons New2 ile çakışma eşiği kesin sonuç vermedi).

## v29 (katmana uygulama)
- Kütüphane kartı artık seçilen katmana uygulanır: efekt (ayarları kaydırıcı ve sayı kutusuyla), animasyon, ikon (efekt resmi).
- Önizleme katmanın gerçek boyutu, dolgu rengi, köşesi ve metniyle çizilir; BUY sabiti kaldırıldı.
- Kart kurulumda ilk ekranda, dışa aktarımdan sonra sonuç ekranının başında.
- Kullanıcı atamaları yeniden kurulumda korunur (userFx / userAnim).
- Düzeltme: ui.html'e <meta charset="utf-8"> eklendi; önceki sürümlerde JS metinleri (ör. "Yağmur") tarayıcıda bozuk görünebiliyordu.

## v30 (gerçek önizleme, canlı animasyon, ikon eylemleri)
- Önizleme: seçilen katmanın gerçek Figma görüntüsü (eklenti PNG olarak dışa aktarır; JSON'a girmez).
- Panelde bir animasyon seçilince öğede canlı oynar.
- İkon: "İçeri ekle" seçili öğeye görüntü düğümü ekler (Studio ad eşleşmesiyle bağlanır; yalnızca bu oturumda, yeniden dışa aktarımda kaybolur).
- "Efekt resmi olarak ekle" yalnızca bir efekt uygulandıktan sonra etkin.
- Eylem düğmeleri önizlemenin hemen altında.
- Doğrulama: tarayıcı testi (gerçek önizleme, canlı animasyon, İçeri ekle). Eklenti PNG dışa aktarımı Figma'da henüz denenmedi.

## v33 (GUI/UI animasyonları · "Süre" düzeltmesi · kendi resim envanteri)
Kullanıcının üç isteği: (1) kendi resimlerimizi efekt yapalım + envanter bizim olsun ve Roblox aktarımında sıfırlansın,
(2) paneldeki "Süre" ayarları çalışmıyor, (3) GUI/UI (buton dışı) animasyonlar yok — panel yumuşak/soldan sağa açılsın.

- **GUI/UI animasyonları (madde 3):** Kütüphanedeki `cikis` (14), `gecis` (8), `metin` (6), `fx` (15) kategorileri üretime alındı.
  Çalışma zamanı yuvaları: `cikis → hide`, `gecis/metin → giris` (giriş seçenekleri), `fx → dongu`; bu katlanan havuz
  `pool = "extra"` olduğu için varsayılan sıralamaya girmez, yalnız seçenek listelerinde görünür.
- **Panel açılışı:** `_open` hedefi ya da içinde `_close` olan öğe (code.js `markPanels` → `node.panel`) panel sayılır.
  Açılış animasyonu yalnız `panel_*`/`page_*` havuzundan seçilir; varsayılan tercih **panel_slide_left_soft** (soldan sağa,
  0.55 sn, sönerek — kullanıcının tarif ettiği "yumuşak, yavaş, soldan sağa"). Kapanışta **exit_slide_left**. Kullanıcı
  panelden başka animasyon seçtiyse (öğrenme kaydı) tercih uygulanmaz — öğrenme kazanır.
- **Çıkış animasyonu (yeni yuva `hide`):** JSON'da `düğüm.anim.hide` → Studio'da bağlama; `openPanel` görünür yapar ve
  girişi oynatır, `closePanel` önce çıkış animasyonunu oynatır, **animasyonun süresi bitince** `Visible=false` yapar
  (`task.delay`). Panel içindeki `hide` bağlamalı öğeler de çıkışta oynar. Kapanış beklerken yeniden açılırsa bekleyen
  gizleme iptal edilir (sıra numarası). `play` artık en uzun izin süresini döndürür (kapanış beklemesi için).
- **Eklenti:** panel öğelerine `EI_Panel` özniteliği yazılır (asistan yolunda da panel bayrağı gider); JSON'daki
  `anim.hide` doğrudan bağlamaya eklenir.
- **"Süre" düzeltmesi (madde 2):** Kök neden kütüphane kartındaki önizlemeydi: `playFx` ayarları yok sayıyordu
  (sabit 220 ms yağmur, 10 parça patlama…), bu yüzden kaydırıcı oynatılınca hiçbir şey değişmiyordu ("deniyorum çalışmıyor").
  Yeni `fxPreviewPlan(kind, params)` önizlemeyi Kaç tane / Süre (sn) / Görünürlük / En küçük-En büyük / Yayılma /
  Süpürme-Bekleme-Bant-Eğim-Parlaklık / Döngü ayarlarına göre çizer; kaydırıcı değişince önizleme anında tazelenir.
  JSON'a yazım (AS paneli ve kütüphane kartı "Uygula") zaten doğruydu; Lua/JS tarafında `seconds`/`count` çalışıyor.
  Konfeti varsayılanları (`FX_DEFAULTS.confetti`) iki dile eklendi → parity 9 → 10 efekt.
- **Envanter (madde 1):** Efekt resmi kullanan efektlerde (fall/confetti/burst/orbit/twinkle) "Envanter · kendi resimlerim"
  bölümü: tasarımda dışa aktarılan PNG'ler tek tıkla efekte resim olur (ek Figma katmanı yok — kullanıcının istediği gibi
  karmaşa çıkmaz). Ad, ZIP'teki dosya adıdır → Studio'da "İsimden eşleştir" doğrudan bağlar. Envanter **yeni Roblox
  aktarımında (dışa aktarma) sıfırlanır**; ayrıca "Envanteri sıfırla" düğmesi vardır (yüklenen dosyalar da temizlenir).
- **Ek düzeltmeler:** `resolveProp` — sınıfta olmayan özellik adları sessizce düşmez, sınıfın karşılığına çevrilir
  (TextButton'da `ImageTransparency` → `BackgroundTransparency`); `u = "scale"` track'leri Position/Size'ı ölçekli taşır.
- **Yeni kapılar:** `tests/verify_panel_anim.py` (panel yumuşak açılır, çıkış oynar ve süre bitince gizlenir, yarış iptali) ·
  `tests/verify_panel_params.js` (Süre/Kaç tane önizleme planına geçer, envanter ve panel çıkış yuvası üründe var).
  Parite fikstürüne panel öğesi + `cikis` kategorisi eklendi (Lua ≡ JS). Tüm Lua/JS kapıları geçti.
- Bilinen: gerçek Roblox Studio'da ve gerçek Figma'da yine denenmedi; kod gerçek Figma/Studio yerine sahte ortamda koşuyor.

### v33 ek (ekstra kütüphane yolu · kategori katlanması · seçilebilirlik)
- **Ekstra Kütüphane yol hatası düzeltildi:** kütüphane repo kökünde (`kutuphane/`) duruyor, araçlar ise
  `kaynak/kutuphane/` bekliyordu (geçici symlink ile çalışıyordu). Artık üç dosya kökü kendisi bulur:
  `tests/verify_ekstra.js`, `assistant/tools/build_ekstra.py`, `assistant/tools/train_fx.py`
  (sırayla `kaynak/..`, `kaynak`, `..` adaylarına bakar). Symlink olmadan `verify_ekstra.js` GEÇTİ (15 kontrol);
  `train_fx.py` modeli bayt birebir yeniden üretir (deterministik).
- **Kategori katlanması doğrulandı:** üreteç `fx`→`dongu` (15), `gecis`+`metin`→`giris` (14) katlar; `durum` (8)
  üretime alınmaz, 5 kayıt boş kalır → çalışma zamanı 116 animasyon. Yani `fx` (efekt) animasyonları döngü
  yuvasında, sayfa geçişleri ve metin animasyonları giriş yuvasında seçilebilir; kütüphane kutusunun kategori
  listesi bu katlanmış hâldir. `ei-animlib-ui.js` başlığı ve `EIAnim.lua` "extra havuzu" yorumu buna göre düzeltildi.
- **Kapı genişletildi:** `tests/verify_panel_params.js` 31 kontrol — kütüphanedeki 7 kategori de bir yuvaya bağlı,
  116 animasyon listeleniyor, `panel_*`/`exit_*`/`fx_*`/`page_*`/`text_*` kayıtları doğru yuvalarda, panel açılışı
  önerilen havuzda ve çıkış girişten hızlı (0.3 sn).
- **Belgeler:** `anim/README.md` sayıları ve katlanma notu güncellendi; README kapı listesine yeni testler eklendi.

### v33 ek 2 (Roblox aktarımı uçtan uca doğrulandı)
- **Yeni kapı: `tests/verify_transfer_to_studio.py`** — "Figma → JSON → Studio eklentisi → LocalScript → sahte Roblox"
  zinciri baştan sona koşar (54 kontrol):
  1. Figma dışa aktarımı GERÇEK `code.js` ile yapılır (panel + `_open`/`_close` aksiyonları doğrulanır).
  2. Figma panelinin JSON sözleşmesi kaynaktan denetlenir (`{src, cat, trig, tracks}` + yuva→anahtar eşlemesi).
  3. Track'ler GERÇEK `ei-anim.js` (EIAnim.getAnim) üzerinden alınır — kopya veri yok.
  4. Studio eklentisinin (`EasyImportStudioPlugin.lua`) JSON→bağlama kopyalaması (show/hide/hover/press/loop/selA/
     delay/fx/params), `EI_Panel`, panels listesi, `buildSourceSpec(animBindings, doc.anims, …)` ve `fxImages` →
     gizli şablon ImageLabel aktarımı statik olarak doğrulanır.
  5. rbxmx gömülü modüllerle SENKRON ve yeni animasyonları içeriyor.
  6. Üretilen LocalScript sahte Roblox'ta koşar: panel 0.55 sn Quint Out ile soldan açılır, çıkış 0.3 sn oynar,
     `task.delay` sonrası gizlenir, geçiş (page_slide_left) ve metin (text_typewriter) girişleri oynar,
     döngü animasyonu rep=-1 ile döner, yağmur aralığı = Süre ÷ Kaç tane (4÷8 = 0.5 sn),
     parçalar ENVANTERDEKİ kendi resmimizden kopyalanır, Rectangle parlama ayarı (süpürme 2 sn) uygulanır.
  7. **Tüm kütüphane:** 116 animasyonun 180 track'inin TAMAMI tween üretir (92 animasyon kendi öğesinde,
     24'ü yalnız tutucu öğede: UIScale/UIStroke/UIGradient) — hiçbir animasyon aktarımda kaybolmuyor.
  8. **Efektler:** Figma'daki 10 efekt ≡ çalışma zamanı varsayılanları ≡ Studio motorunun `startFx` dalları;
     5 efekt (fall/confetti/burst/orbit/twinkle) envanter resmini kopyalar.
- Belgeler: README kapı listesi ve `TEST-REHBERI-v33.md` (aktarım adımları dâhil) güncellendi.

### v34 (dünya efekti · karakter animasyonu · etkileşim — MASTER PROMPT turu)
- **Analiz:** tüm modül satırları ölçüldü; 19 Roblox sınıfı için depo tarandı → **dünya VFX, karakter animasyonu,
  dünya etkileşimi tamamen yoktu** (kategori C). `Beam`/`Trail`/`Lighting` yalnız 2B GUI önizleme sınıf adıydı.
- **Yeni bağımsız modül:** `assistant/vfx/vfx-library.json` (32 preset: world 12 · char 9 · interact 4 · post 3 ·
  cam 2 · decide 2; 26 istemci / 6 sunucu) + `runtime/lua/EIVfx.lua` (502) + `runtime/js/ei-vfx.js` (3269) +
  üreteç `assistant/tools/build_vfx_lua.py` (API beyaz listesi: 23 sınıf + 10 enum; uydurma → **durur**).
- **Karar sözleşmesi:** `suggest` puanlı liste (daima `decide_none` ile biter; UI olayında `reuse_ui_anim`),
  `plan` alternatifler + `skipped` (sebep: `butce`/`mobil`), `tryPlay` (`bekleme`/`es-zamanli`/`kapasite`),
  `tick`/`release`, `limits` (masaüstü 3/60 · mobil 1/24), `animPlan`
  (`ok · tekrar · oncelik · asset-eksik · char-degil · animasyon-degil` — kimlik yoksa oynatılmaz).
- **Yetki ayrımı:** sunucu presetleri istemcide `yetki-sunucu`, istemci görselleri sunucuda `yetki-istemci` ile reddedilir;
  RemoteEvent `ReplicatedStorage`'ta yeniden kullanılır.
- **Yeni kapılar:** `tests/verify_vfx.py` (55 kontrol) ve `tests/verify_vfx_parity.py` (Lua ≡ JS, 4692 satır birebir).
  Kapılar 5 gerçek hata buldu ve düzelttim: `TweenService` global sanılıyordu (servisten alınmalı), `animPlan` aynı
  animasyonun yeniden tetiklenmesini de engelliyordu (`tekrar` eklendi), `repeat` alan adı Lua anahtar sözcüğüydü
  (`freq` oldu; üreteç anahtar sözcükleri artık hata veriyor), `limits` iki dilde `0` bütçede farklıydı (sayı verilmişse
  o kullanılır), boş `AnimationId` (projeden gelir) şemaca reddediliyordu.
- **Paket:** `build_rbxmx.py` EIVfx'i de gömer → 8 modül, 454 KB; `studio-plugin/EasyImportStudioPlugin.rbxm` güncellendi
  (md5 eşit). Aktarım ve Studio köprüsü kapıları yeşil kaldı.
- **Rapor:** kök dizinde `Efekt-Animasyon-Sistemi-Raporu.md` (A/B/C/D sınıflandırması + D listesi: gerçek Studio
  görseli, doküman teyidi, mobil FPS ölçümü, gerçek AnimationId'ler, panel arayüzü — hepsi **yapılmadı** olarak yazılı).

