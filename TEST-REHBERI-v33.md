# Test Rehberi — v33 (ne denemeli, nereye bakmalı)

Bu sürümde üç isteğin için yapılanlar ve **nasıl test edileceği** aşağıda. Tüm testler sahte ortamda
(jsdom + sahte Figma/Studio) otomatik koşuyor; gerçek Figma/Studio'da denemeyi sen yapacaksın.

## Kurulum (teste başlamadan)

| Dosya | Nereye |
|---|---|
| `figma-plugin/` (manifest.json + code.js + ui.html) | Figma → Plugins → Development → Import plugin from manifest |
| `studio-plugin/EasyImportStudioPlugin.rbxm` | Studio'ya sürükle (veya `kaynak/roblox-studio-plugin/EasyImportStudioPlugin.rbxmx`) |

Not: `figma-plugin/ui.html` ve `studio-plugin/EasyImportStudioPlugin.rbxm` bu turda yeniden üretildi
(`kaynak/` kaynaklarından), ikisi de kaynakla birebir aynı.

## 1) "Süre" ayarları (madde 2 — artık çalışıyor)

1. Figma panelini aç → **Kütüphane ve önizleme** kartı → **Efektler** sekmesi.
2. Yağmur / Konfeti / Patlama… seç → önizlemede oynar.
3. **Süre (sn)**, **Kaç tane** kaydırıcılarını oynat → önizleme **anında** değişir.
   - Doğrulandı: `Kaç tane=30` → 1,5 sn'de ~5 parça; `Kaç tane=3` → aynı sürede 0–1 parça (aralık = süre ÷ sayı).
   - Yörünge: `Kaç tane=3` → 3 parça, `=8` → 8 parça (anında).
   - **Döngü** düğmesi de önizlemeyi değiştirir: "Açık: sürekli oynar" ↔ "Kapalı: bir kez oynar".
4. **Uygula** → JSON'a yazılır; Studio'da aynı sayılar geçerli olur (Lua tarafı zaten okuyordu).

## 2) Animasyonlar ve efektler (madde 3)

Kütüphanede **129 animasyon kaydı** var; **116'sı** üretime giriyor (kategori katlanması: fx→döngü,
geçiş+metin→giriş; **durum** kategorisi kapsam dışı). Yeni eklenenler:

- **Panel açılışı (8):** Panel: Soldan / Sağdan / Yukarıdan / Aşağıdan Yumuşak Açılış · Yumuşak Beliriş ·
  Katlanarak Açılma · Yumuşak Zoom · Yavaş Yükselme — **varsayılan: soldan, 0,55 sn, sönerek** (senin tarifin).
- **Çıkış (4 yeni, toplam 14):** Sola/Sağa Kayarak Çıkış · Yumuşak Sönerek Çıkış · Ölçekli Sönerek Çıkış.
  Panel kapanışı **exit_slide_left** (0,3 sn) ile oynar, **animasyon bitince** panel gizlenir.
- **Efekt animasyonları (15):** Aura Dönüş + Nefes, Işık Huzmesi Dönüşü, Toz Süzülmesi, Cam Parlaması,
  Yıldız Parıltısı, Halka Pingi… → **döngü** yuvasında seçilebilir.
- **Sayfa geçişleri (8) ve metin animasyonları (6):** giriş yuvasında seçilebilir (Daktilo, Sayı Sayma…).

Nasıl test edilir:
1. **Panel otomatiği:** katman adına `_panel` + bir kapatma butonuna `_close` yaz (ya da bir butona `_open:PanelAdı`).
   → Panel açılışta soldan yumuşak açılır; `_close` ile kapanırken çıkış animasyonu oynar, bitince gizlenir.
2. **Asistan sekmeleri:** Sonuç ekranında her öğenin yuvaları listelenir (giriş 40 seçenek, çıkış 14,
   hover 12, basma 11). Bir animasyon seçince öğede **anında canlı oynar**.
3. **Kütüphane kartı:** Animasyonlar sekmesinde kategori seç → öğeye **Uygula**. Örnek doğrulama (jsdom):
   - `Geçiş: Sayfa Soldan` → JSON `anim.show = page_slide_left`
   - `Metin: Daktilo` → `anim.show = text_typewriter`
   - `FX: Aura Dönüş + Nefes` → `anim.loop = fx_aura_rotate_pulse`
   - `Sola Kayarak Çıkış` → `anim.hide = exit_slide_left`

## 3) Envanter (madde 1)

- Efekt resmi kullanan efektlerde (Yağmur/Konfeti/Patlama/Yörünge/Parıltı) **"Envanter · kendi resimlerim"**
  bölümü: tasarımda dışa aktardığın PNG'ler tek tıkla efekte resim olur (Figma'ya ek katman **açılmaz**).
- Tıkla → eklenir, tekrar tıkla → çıkar. **"Envanteri sıfırla"** düğmesi hepsini temizler.
- **Roblox'a aktarımda (yeni dışa aktarma) envanter sıfırlanır** (doğrulandı).
- Studio'da "İsimden eşleştir" ile ZIP'teki dosya adı Decal adına bağlanır.

## 4) Ekstra Kütüphane (bu turda düzeltildi)

Kütüphane deposu kökünde (`kutuphane/`), araçlar ise `kaynak/kutuphane/` bekliyordu (geçici symlink ile
çalışıyordu). Artık araçlar kökü **kendisi buluyor**:

- `kaynak/tests/verify_ekstra.js` → symlink olmadan **GEÇTİ (15 kontrol)**
- `kaynak/assistant/tools/build_ekstra.py` ve `train_fx.py` → kök: `EasyImport32v/kutuphane`
- `train_fx.py` modeli **bayt birebir** yeniden üretir (deterministik)

Senin test edebileceğin yer: Figma paneli → Kütüphane kartı → **İkonlar** (1022 simge, kategori/arama,
ızgara) ve efekt simgesi sıralaması (kabul/red ile öğrenir).

## 5) Roblox eklentisine aktarma (senin uyardığın adım) — doğrulandı

Aktarım zinciri: **Figma → JSON kopyala → Studio eklentisine yapıştır → içe aktar → LocalScript + EIAnim**.

Bu turda baştan sona test edildi (`kaynak/tests/verify_transfer_to_studio.py`, 54 kontrol, GEÇTİ):

- **Panel:** 0,55 sn Quint Out ile soldan açılır (ölçek −1 → 0) · çıkış animasyonu 0,3 sn oynar · **animasyon
  bitince** `Visible=false` (task.delay) · sönerek gelme (Transparency 0,3 → 0) uygulanır.
- **Geçiş ve metin:** `page_slide_left` butonda, `text_typewriter` yazıda oynar.
- **Döngü:** `fx_aura_rotate_pulse` 360°, 8 sn, `rep = −1` (sonsuz) döner.
- **Efekt ayarları:** yağmur aralığı = **Süre ÷ Kaç tane** (4÷8 = 0,5 sn) — "Süre" gerçekten Studio'ya geçiyor.
- **Envanter:** yağmur parçaları **kendi resmimizden** kopyalanır (Hazine_Kart_1-9) — 8 parça; parça adı ZIP
  dosya adıyla aynı olduğu için Studio'da "İsimden eşleştir" doğrudan bağlar.
- **Rectangle parlama:** süpürme 2 sn ayarı uygulanır.
- **Tüm kütüphane:** 116 animasyonun **180 track'inin tamamı** tween üretir (aktarımda hiçbir animasyon kaybolmaz).
- **Efektler:** Figma'daki 10 efekt = çalışma zamanı varsayılanları = Studio motorunun tanıdığı dallar.

Senin elle test akışın:
1. Figma'da panel aç → animasyon/efekt/ikon seç → **Kopyala** (JSON).
2. Studio'da eklentiyi aç → JSON'u yapıştır → **İçe aktar**.
3. Ekranda `EI_Animator` LocalScript'i oluşur; `_open` butonuna bas → panel soldan yumuşak açılır; `_close` → çıkış
   animasyonu oynar ve panel gizlenir.
4. Görseller: **Tümünü indir** (ZIP) → Asset Manager'a toplu yükle → **İsimden eşleştir** (envanter adları ZIP
   dosya adlarıyla birebir aynıdır).

## Kapılar (bu turda koşuldu, hepsi yeşil)

- Python: 13 `tests/verify_*.py` (yeni: `verify_transfer_to_studio.py` — Roblox aktarımı) + `verify_anim`,
  `verify_learn`, `verify_merge`, `verify_anim_parity` (Lua ≡ JS birebir) + `build_anim_lua.py --check` (senkron)
- Node: `verify_export_tags`, `verify_figma_merge`, `verify_fxmodel`, `verify_learn_channel`,
  `verify_ekstra` (15), `verify_panel_params` (31)
- UI Tools: çekirdek 135 · plugin 149 · mutasyon 21/21

### Bakım dışı (temel sürümde de başarısız — bu turda değişmedi)

Şu 6 eski kapı, veri dosyaları eksik olduğu için `HEAD`'de de aynı hatayı veriyor (benim değişikliklerimden
bağımsız, ayrı ayrı doğrulandı): `verify_generalization`, `verify_model` (`effect-icons-human.jsonl` içinde
`feat` alanı boş) · `verify_plugin_v9` (`-- <<ASSIST_BEGIN>>` işareti eklentide yok) · `verify_real_dataset`,
`verify_real_run` (`designs/`, `designs-export/` yok — ham Figma verisi depoda değil) · `verify_teacher`.

## Bilinen sınırlar

- Gerçek Figma ve gerçek Roblox Studio'da **hâlâ denenmedi**; tüm doğrulama jsdom + sahte Roblox.
- `durum` kategorisi (8 animasyon) bilinçli olarak üretime alınmadı.
- Otomatik döngü yuvası yalnız CTA/ikon rollerinde (en fazla 3 öğe); diğer öğelere döngü animasyonu
  kütüphane kartından uygulanır.
