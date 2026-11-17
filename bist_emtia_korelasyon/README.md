# BIST hisseleri – emtia / dış etken korelasyonları

Borsa İstanbul'daki her hisse, iş modeline göre ilgili emtiayla (ör. Tüpraş → Brent ve
rafineri marjı, Ülker → kakao, Ereğli → çelik) ya da emtiası olmayan şirketlerde en yakın
dış etkenle (Dolar/TL, küresel sektör hisseleri vb.) eşleştirildi ve bu ilişkinin fiyatlara
gerçekten yansıyıp yansımadığı ölçüldü.

* **Kapsam:** 614 BIST sembolü (597'sinde yeterli veri), 67 emtia/etken, 523 hafta
  (2016-11-14 – 2026-11-16).
* **İnteraktif rapor:** `rapor.html` (tarayıcıda açılır; aranabilir tablo, sektör özeti,
  kayan korelasyon grafikleri).

## Öne çıkan bulgular

| Hisse | En güçlü ilgili etken | Ham kor. | Kısmi kor. (BIST100'den arındırılmış) | Sonuç |
|---|---|---|---|---|
| DOCO | Küresel havayolları (JETS) | 0,53 | 0,51 | Güçlü |
| TUPRS | Brent petrol | 0,30 | 0,42 | Güçlü |
| EREGL | Küresel çelik üreticileri (SLX) | 0,34 | 0,28 | Orta |
| THYAO | Küresel havayolları (JETS) | 0,31 | 0,26 | Orta |
| TRENJ | Altın | 0,22 | 0,25 | Orta |
| AYGAZ | Brent petrol | 0,15 | 0,22 | Orta |
| KRDMD / KRDMA / KRDMB | Demir cevheri | 0,16–0,17 | 0,20–0,22 | Orta |
| PETKM | Brent petrol | 0,13 | 0,22 | Orta |
| PGSUS | Motorin / jet yakıtı (ters) | −0,14 | −0,21 | Orta |
| AEFES | Buğday (ters, maliyet) | −0,18 | −0,21 | Orta |
| TRMET / TRALT | Altın / altın madencileri | 0,18–0,20 | 0,18–0,19 | Orta |
| ASELS | Savunma hisseleri (ITA) | 0,26 | 0,18 | Orta |

1. **Gerçek emtia bağı az sayıda hissede var.** 597 hissenin yalnızca 18'inde ilgili
   emtia/etkenle piyasadan bağımsız, istatistiksel olarak sağlam bir bağ çıktı. Hisselerin
   çoğu asıl olarak BIST geneliyle hareket ediyor (BIST 100 ile medyan haftalık korelasyon 0,48).
2. **Tüpraş en net örnek:** Brent ile kısmi korelasyon 0,42 (t = 7,4); 52 haftalık kayan
   korelasyon dönemin %94'ünde pozitif; son 1 yılda Brent ile 0,52, motorinle 0,63.
3. **Havayolları** küresel havayolu hisseleriyle birlikte, yakıtla ters hareket ediyor;
   son 1 yılda Brent ile ham korelasyon THY'de −0,58, Pegasus'ta −0,54.
4. **Çelikte doğru referans ABD HRC vadelisi değil**, küresel çelik üreticileri (SLX) ve demir
   cevheri. Ereğli–ABD HRC korelasyonu 0,01, Ereğli–SLX 0,34.
5. **Beklenen ama veride görünmeyen ilişkiler:** Ülker–kakao (−0,05; son 1 yıl 0,01),
   Gübretaş–gübre (−0,03), Sarkuysan–bakır (kısmi 0,07), şeker fabrikaları–şeker (~0),
   Banvit–yem (~0), Sasa–petrol (0,00), bankalar–küresel bankalar (piyasadan arındırınca ~0).
6. **2026 enerji şoku:** 2 Mart 2026 haftasında Brent %25, Avrupa gazı (TTF) %51 yükseldi.
   Son 1 yılda emtia korelasyonları belirgin şekilde yüksek (beklenen yönde ≥ 0,30 olan
   hisse–etken çifti 1 yılda 148, 5 yılda 64). Kısa dönem korelasyonu kalıcı sanmamak gerekir.
7. **İsim tuzakları ilişkisiz:** SILVR–gümüş −0,05, ALTNY–altın 0,04, PETUN–petrol 0,01.

## Yöntem

* **Veri:** Haftalık kapanışlar (Yahoo Finance, hissebilanco.com proxy'si üzerinden), en fazla
  10 yıl. Hisseler temettü/bölünme düzeltmeli. Emtialar vadeli kontratların sürekli serisi.
  Vadelisi olmayan ürünler için küresel sektör lideri vekil: gübre → CF Industries / Nutrien,
  selüloz → Suzano, petrokimya → LyondellBasell, navlun → BDRY, havayolu → JETS vb.
* **USD bazlı getiriler:** TL hisse fiyatları Dolar/TL ile USD'ye çevrildi; korelasyonlar fiyat
  seviyesi yerine haftalık log getiriler üzerinden. (TL fiyat ile USD emtia fiyatı kur nedeniyle
  "birlikte artıyor" görünür; bu sahte korelasyondur.) Kur etkenleri için hissenin TL getirisi
  kullanıldı.
* **Ham ve kısmi korelasyon:** `r_hisse = a + b_piyasa·r_BIST100(USD) + b_etken·r_etken`.
  Kısmi korelasyon ve beta, BIST 100'ün etkisi çıkarıldıktan sonra kalan şirkete özgü bağı ölçer.
* **Pencereler:** son 1, 3, 5 yıl ve tüm dönem; birincil pencere 5 yıl (daha kısa geçmişli
  hisselerde tüm veri). Ayrıca son 5 yılın iki yarısı ayrı ayrı (istikrar kontrolü).
* **Sağlamlık:** 52 haftalık kayan korelasyonun işaret istikrarı, 1 hafta gecikmeli korelasyon,
  4 haftalık getirilerle korelasyon, 3 yıllık USD fiyat seviyesi korelasyonu (yalnızca bilgi).
  BIST'in ±%10 günlük limiti nedeniyle haftada %+65 / %−43'ü aşan hareketler (düzeltilmemiş
  bedelsiz vb.) veri dışı bırakıldı.
* **Çoklu test:** ~1.000 önceden belirlenmiş hisse–etken hipotezi ve ~34 bin veri taraması testi
  için Benjamini–Hochberg yanlış keşif oranı (q-değeri). Ayrıca bir bağ ancak ham ve kısmi
  korelasyon aynı işaretli ve |ham| ≥ 0,10 ise kabul edilir: BIST 100'ün kendisi bazı küresel
  faktörlerle korele olduğundan, piyasa kontrol edilince ilişkisiz hisseler mekanik olarak
  negatif kısmi korelasyon alabilir.
* **Sonuç etiketleri:** Güçlü (kısmi ≥ 0,30, q < 0,05, iki yarıda aynı yön) · Orta (≥ 0,15,
  q < 0,10) · Zayıf (yön doğru, |t| ≥ 2, düzeltmeyi geçemedi) · Ters yönde (|t| ≥ 3,3, beklenenin
  tersi) · Zayıf / anlamsız.

Korelasyon nedensellik değildir. Türkiye'de fiyatı düzenlenen ürünlerde (şeker, süt, elektrik,
doğalgaz) küresel fiyat bağlantısı zayıftır; fındık, çay, zeytinyağı, çinko gibi ürünlerin likit
vadelisi yoktur. Bu çalışma yatırım tavsiyesi değildir.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `rapor.html` | İnteraktif rapor |
| `sonuclar/hisse_ozet.csv` | Hisse başına özet: sektör, temel etkenler ve gerekçe, en güçlü ilgili etken, 1/3/5/10 yıl korelasyonlar, kısmi kor., beta, t, q, sonuç, veri taramasının ilk 3 etkeni, Dolar/TL duyarlılığı |
| `sonuclar/hisse_etken_detay.csv` | Her hisse × ilgili etken çifti için tüm pencereler ve sağlamlık ölçüleri |
| `sonuclar/sektor_ozet.csv` | Ana sektör bazında özet |
| `sonuclar/matris_{ham,kismi}_kor_{1y,5y}.csv` | Tüm hisseler × 67 etken korelasyon matrisleri |
| `sonuclar/kayan_korelasyon_52h.csv` | 52 haftalık kayan korelasyon serileri (2 haftada bir) |
| `sonuclar/bist_emtia_korelasyon.xlsx` | Yukarıdakilerin Excel çalışma kitabı + eşleştirme ve etken listesi |
| `sonuclar/veri_haftalik_bist_kapanis_try.csv` | Veri seti: haftalık düzeltilmiş kapanışlar (TL) |
| `sonuclar/veri_haftalik_emtia_etken.csv` | Veri seti: haftalık emtia/etken fiyatları |
| `scripts/mapping.py` | Hisse → emtia/etken eşleştirmesi, beklenen yön, gerekçe, güven |
| `scripts/fetch_prices.py`, `analyze.py`, `build_report.py` | Veri indirme, analiz, rapor üretimi |

## Yeniden üretme

```bash
cd bist_emtia_korelasyon/scripts
# 1) sembol listeleri (factors.txt, bist_syms.txt) ile fiyatları indir
python fetch_prices.py ../_ham/factors @factors.txt   # OJ=F (portakal suyu) bozuk, kullanılmadı
python fetch_prices.py ../_ham/bist @bist_syms.txt
# 2) analiz (universe.json: [{"ticker": "...", "name": "..."}])
python analyze.py ../_ham ../sonuclar universe.json
# 3) rapor
python build_report.py ../sonuclar report_template.html bulgular.html ../rapor.html
```
