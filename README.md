# Dosya Tarayıcı Uygulaması

Bu uygulama, disk üzerindeki dosyaları tarayarak kullanıcıya kolay erişim sağlayan bir masaüstü uygulamasıdır. PyQt5 ve watchdog kütüphanelerini kullanarak geliştirilmiştir.

## Özellikler

- Belirtilen klasörü ve alt klasörlerini otomatik tarama
- Dosya adına göre arama yapabilme
- Dosya uzantısına göre filtreleme
- Gerçek zamanlı dosya sistemi izleme (yeni dosya eklendiğinde, silindiğinde veya değiştirildiğinde otomatik güncelleme)
- Çift tıklama ile dosyaları açabilme
- İlerleme çubuğu ile tarama durumunu görebilme
- Veritabanı desteği ile uygulama kapatıldığında tarama sonuçlarını saklama
- Otomatik periyodik tarama
- Uygulama başlatıldığında otomatik tarama

## Gereksinimler

- Python 3.6 veya üzeri
- PyQt5: Grafiksel kullanıcı arayüzü için
- watchdog: Dosya sistemi değişikliklerini izlemek için
- sqlite3: Tarama sonuçlarını ve ayarları saklamak için (Python standart kütüphanesinde mevcuttur)

## Kurulum

Gereksinimleri yüklemek için:

```
pip install PyQt5 watchdog
```

## Kullanım

Uygulamayı çalıştırmak için:

```
python file_explorer.py
```

### Temel Kullanım Adımları

1. Uygulama başlatıldığında, önceden taranmış dosyalar veritabanından otomatik olarak yüklenir
2. Yeni bir klasör taramak için "Gözat" düğmesine tıklayıp klasörü seçin (otomatik tarama başlayacaktır)
3. Arama kutusunu kullanarak dosya adına göre arama yapabilirsiniz
4. Uzantı açılır menüsünden dosya türüne göre filtreleme yapabilirsiniz
5. Listedeki bir dosyaya çift tıklayarak dosyayı açabilirsiniz
6. "Otomatik Tarama" onay kutusunu işaretli tutarak düzenli aralıklarla taramanın yapılmasını sağlayabilirsiniz

## Proje Yapısı ve Kodun Açıklaması

Uygulama üç ana sınıftan oluşur:

### 1. DatabaseManager Sınıfı

Veritabanı işlemlerini yönetir ve aşağıdaki amaçlar için tasarlanmıştır:

- **init_db()**: Veritabanı yapısını oluşturur. Üç temel tablo kurar:
  - `config`: Uygulama yapılandırma ayarlarını saklar
  - `watch_paths`: İzlenen klasör yollarını ve son tarama zamanlarını saklar
  - `files`: Taranan dosyaların bilgilerini (konum, ad, uzantı, boyut, değiştirilme tarihi) saklar

- **add_watch_path()**: İzlenen klasör yollarını veritabanına kaydeder. Bu, uygulamanın yeniden başlatıldığında hangi klasörleri izlemesi gerektiğini hatırlaması için önemlidir.

- **get_watch_paths()**: Veritabanından kayıtlı izleme yollarını alır.

- **add_file()**: Taranan dosyaların bilgilerini veritabanına ekler veya günceller.

- **remove_file()**: Silinen dosyaları veritabanından kaldırır.

- **update_file_last_seen()**: Dosyanın son görülme zamanını günceller, böylece artık mevcut olmayan eski dosyaları belirleyebiliriz.

- **get_all_files()**: Tüm kayıtlı dosyaların listesini veritabanından getirir.

- **clear_old_records()**: Belirli bir süreden daha eski kayıtları temizler.

- **set_config()** ve **get_config()**: Uygulama yapılandırma ayarlarını saklar ve alır.

### 2. FileScanner Sınıfı (QThread'den türetilmiş)

Dosyaları arkaplanda taramak için QThread kullanılarak oluşturulmuş bir sınıftır:

- **run()**: QThread'in temel metodu, tarama işlemini başlatır.

- **scan_files()**: Belirtilen klasörü ve alt klasörlerini rekursif olarak tarar. Şu işlemleri gerçekleştirir:
  - Toplam dosya sayısını hesaplar (ilerleme çubuğu için)
  - Dosyaları tarar ve filtreleri uygular
  - Bulunan dosyaları veritabanına ekler/günceller
  - İlerleme durumunu güncelleyerek kullanıcıya bildirir

- **stop()**: Tarama işlemini güvenli bir şekilde durdurur.

Bu sınıf, arayüzün donmasını önlemek için tarama işlemini ayrı bir iş parçacığında (thread) yürütür.

### 3. FileSystemWatcher Sınıfı (FileSystemEventHandler'dan türetilmiş)

watchdog kütüphanesini kullanarak dosya sistemi değişikliklerini takip eder:

- **on_created()**: Yeni dosya oluşturulduğunda tetiklenir.

- **on_deleted()**: Dosya silindiğinde tetiklenir.

- **on_modified()**: Dosya değiştirildiğinde tetiklenir.

- **on_moved()**: Dosya taşındığında tetiklenir.

Bu metotlar, değişiklikleri hem veritabanında hem de arayüzde güncelleyerek sistemin her zaman güncel kalmasını sağlar.

### 4. FileExplorer Sınıfı (QMainWindow'dan türetilmiş)

Ana uygulama penceresini ve kullanıcı arayüzünü yönetir:

- **init_ui()**: Kullanıcı arayüzü elemanlarını oluşturur ve düzenler.

- **load_saved_data()**: Uygulama başlatıldığında veritabanından dosya listesini ve izleme yollarını yükler.

- **auto_scan()**: Otomatik periyodik taramayı gerçekleştirir.

- **browse_folder()**: Kullanıcının klasör seçmesini sağlar.

- **start_scan()**: Tarama işlemini başlatır.

- **filter_files()**: Kullanıcının arama veya uzantı filtresine göre dosya listesini filtreler.

- **should_display_file()**: Bir dosyanın gösterilip gösterilmeyeceğini belirler.

- **open_file()**: Seçilen dosyayı açar.

- **start_file_watcher()**: Belirtilen klasörü izlemek için dosya sistemi izleyicisini başlatır.

- **handle_file_change()**: Dosya sistemi değişikliklerini işler ve arayüzü günceller.

## Uygulama Mantığı ve Tasarım Kararları

1. **Veritabanı Kullanımı**: Uygulama kapatıldığında tarama sonuçlarının kaybedilmemesi için SQLite veritabanı entegre edilmiştir. Bu, büyük klasörlerin tekrar taranması gerekmeden hızlı erişim sağlar.

2. **İş Parçacığı (Thread) Kullanımı**: Tarama işleminin arayüzü bloke etmemesi için QThread kullanılmıştır. Böylece kullanıcı, tarama devam ederken bile uygulamayı kullanabilir.

3. **Gerçek Zamanlı İzleme**: watchdog kütüphanesi kullanılarak, dosya sistemindeki değişikliklerin anında takip edilmesi sağlanmıştır. Bu, uygulama çalışırken eklenen, silinen veya değiştirilen dosyaların otomatik olarak güncellenmesini sağlar.

4. **Otomatik Tarama**: Uygulama başlatıldığında ve belirli aralıklarla otomatik tarama yapılması, dosya listesinin her zaman güncel kalmasını sağlar.

5. **Kullanıcı Dostu Arayüz**: Basit ve kullanımı kolay bir arayüz tasarlanmıştır. Arama, filtreleme ve dosya açma işlemleri hızlı ve kolay bir şekilde gerçekleştirilebilir.

## Performans Düşünceleri

- Büyük klasörler için tarama işlemi zaman alabilir, bu nedenle arkaplanda yürütülür.
- Veritabanı kullanımı, tekrarlanan taramaları azaltarak performansı artırır.
- Tarama sırasında CPU kullanımını azaltmak için küçük gecikmeler eklenmiştir.
- Var olmayan dosyalar filtrelenerek sadece mevcut dosyalar gösterilir.

## Gelecek Geliştirmeler

- Daha gelişmiş filtreleme seçenekleri (boyut, değiştirilme tarihi vb.)
- Dosya önizlemesi ve detaylı bilgi görüntüleme
- Sık kullanılan dosyalar listesi
- Dosya etiketleme ve kategorileme
- Çoklu dil desteği 