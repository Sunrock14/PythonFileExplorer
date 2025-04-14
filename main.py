import os
import sys
import fnmatch
import sqlite3
import json
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QListWidget, 
                             QLabel, QComboBox, QFileDialog, QMessageBox, 
                             QProgressBar, QStatusBar, QInputDialog, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Veritabanı yönetim sınıfı
class DatabaseManager:
    def __init__(self, db_file='file_explorer.db'):
        self.db_file = db_file
        self.init_db()
        
    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Yapılandırma tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        # Tarama yapılan klasörler tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS watch_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            last_scan TEXT
        )
        ''')
        
        # Dosya verileri tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            filename TEXT,
            extension TEXT,
            size INTEGER,
            modified TEXT,
            last_seen TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_watch_path(self, path):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            cursor.execute("INSERT OR REPLACE INTO watch_paths (path, last_scan) VALUES (?, ?)", 
                        (path, now))
            conn.commit()
        except:
            pass
        finally:
            conn.close()
    
    def get_watch_paths(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT path FROM watch_paths")
        paths = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return paths
    
    def add_file(self, file_path):
        if not os.path.exists(file_path):
            return False
            
        filename = os.path.basename(file_path)
        extension = os.path.splitext(filename)[1].lower()
        
        try:
            size = os.path.getsize(file_path)
            modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        except:
            size = 0
            modified = datetime.now().isoformat()
            
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO files 
            (path, filename, extension, size, modified, last_seen) 
            VALUES (?, ?, ?, ?, ?, ?)
            """, (file_path, filename, extension, size, modified, now))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()
    
    def remove_file(self, file_path):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM files WHERE path = ?", (file_path,))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()
    
    def update_file_last_seen(self, file_path):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE files SET last_seen = ? WHERE path = ?", (now, file_path))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()
    
    def get_all_files(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT path, filename, extension FROM files ORDER BY filename")
        files = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return files
    
    def clear_old_records(self, days=30):
        # Belirli bir süreden daha eski kayıtları temizle
        threshold = (datetime.now() - datetime.timedelta(days=days)).isoformat()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM files WHERE last_seen < ?", (threshold,))
            conn.commit()
        except:
            pass
        finally:
            conn.close()
    
    def set_config(self, key, value):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", 
                        (key, value))
            conn.commit()
        except:
            pass
        finally:
            conn.close()
    
    def get_config(self, key, default=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return default


class FileScanner(QThread):
    """Dosyaları arkaplanda tarayan sınıf"""
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    progress_signal = pyqtSignal(int)
    
    def __init__(self, path, db_manager, file_extensions=None):
        super().__init__()
        self.path = path
        self.db_manager = db_manager
        self.file_extensions = file_extensions
        self.files = []
        self.running = True
        
    def run(self):
        self.scan_files()
        
    def scan_files(self):
        self.files = []
        total_items = 0
        scanned_items = 0
        
        # Önce toplam dosya sayısını bulalım (ilerleme çubuğu için)
        for root, _, files in os.walk(self.path):
            total_items += len(files)
        
        # Dosyaları tarayalım
        for root, _, files in os.walk(self.path):
            if not self.running:
                break
                
            for file in files:
                if not self.running:
                    break
                
                file_path = os.path.join(root, file)
                
                # Eğer uzantı filtresi varsa kontrol et
                if self.file_extensions:
                    if any(file.lower().endswith(ext.lower()) for ext in self.file_extensions):
                        self.files.append(file_path)
                        # Veritabanına ekle veya güncelle
                        self.db_manager.add_file(file_path)
                        self.update_signal.emit(file_path)
                else:
                    self.files.append(file_path)
                    # Veritabanına ekle veya güncelle
                    self.db_manager.add_file(file_path)
                    self.update_signal.emit(file_path)
                
                scanned_items += 1
                progress = int((scanned_items / total_items) * 100) if total_items > 0 else 0
                self.progress_signal.emit(progress)
                time.sleep(0.001)  # CPU kullanımını azaltmak için
        
        # Tarama tamamlandığında, izleme yolunu veritabanına ekle
        self.db_manager.add_watch_path(self.path)
        self.finished_signal.emit(self.files)
    
    def stop(self):
        self.running = False


class FileSystemWatcher(FileSystemEventHandler):
    """Dosya sistemi değişikliklerini izleyen sınıf"""
    
    def __init__(self, app, db_manager):
        self.app = app
        self.db_manager = db_manager
        
    def on_created(self, event):
        if not event.is_directory:
            # Dosya oluşturulduğunda, veritabanına ekle
            self.db_manager.add_file(event.src_path)
            self.app.handle_file_change(event.src_path, "added")
    
    def on_deleted(self, event):
        if not event.is_directory:
            # Dosya silindiğinde, veritabanından kaldır
            self.db_manager.remove_file(event.src_path)
            self.app.handle_file_change(event.src_path, "deleted")
    
    def on_modified(self, event):
        if not event.is_directory:
            # Dosya değiştirildiğinde, veritabanını güncelle
            self.db_manager.add_file(event.src_path)
            self.app.handle_file_change(event.src_path, "modified")
    
    def on_moved(self, event):
        if not event.is_directory:
            # Eski dosyayı kaldır, yeni dosyayı ekle
            self.db_manager.remove_file(event.src_path)
            self.db_manager.add_file(event.dest_path)
            self.app.handle_file_change(event.dest_path, "moved")


class FileExplorer(QMainWindow):
    """Ana uygulama penceresi"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.scanner = None
        self.observer = None
        self.watch_paths = []
        self.all_files = []
        self.filtered_files = []
        self.auto_scan_timer = QTimer(self)
        self.auto_scan_timer.timeout.connect(self.auto_scan)
        self.init_ui()
        self.load_saved_data()
        
        # Uygulama başlangıcında tarama işlemi
        QTimer.singleShot(1000, self.auto_scan)
        
        # Periyodik tarama ayarı (varsayılan olarak her 1 saat)
        scan_interval = int(self.db_manager.get_config("scan_interval", "3600")) * 1000
        self.auto_scan_timer.start(scan_interval)
        
    def init_ui(self):
        # Ana pencere ayarları
        self.setWindowTitle("Dosya Tarayıcı")
        self.setGeometry(100, 100, 800, 600)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Üst panel - Klasör seçme
        top_panel = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Taranacak klasör yolu")
        browse_button = QPushButton("Gözat")
        browse_button.clicked.connect(self.browse_folder)
        scan_button = QPushButton("Tara")
        scan_button.clicked.connect(self.start_scan)
        
        top_panel.addWidget(self.path_input)
        top_panel.addWidget(browse_button)
        top_panel.addWidget(scan_button)
        
        # Orta panel - Arama ve filtreleme
        middle_panel = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.textChanged.connect(self.filter_files)
        
        self.extension_combo = QComboBox()
        self.extension_combo.addItem("Tüm Dosyalar")
        common_extensions = ["txt", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", 
                           "jpg", "jpeg", "png", "gif", "mp3", "mp4", "zip", "rar", "py", "exe"]
        
        for ext in common_extensions:
            self.extension_combo.addItem(f".{ext}")
        
        self.extension_combo.currentTextChanged.connect(self.filter_files)
        
        # Otomatik tarama onay kutusu
        self.auto_scan_checkbox = QCheckBox("Otomatik Tarama")
        self.auto_scan_checkbox.setChecked(True)
        
        middle_panel.addWidget(QLabel("Arama:"))
        middle_panel.addWidget(self.search_input)
        middle_panel.addWidget(QLabel("Uzantı:"))
        middle_panel.addWidget(self.extension_combo)
        middle_panel.addWidget(self.auto_scan_checkbox)
        
        # Dosya listesi
        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.open_file)
        
        # İlerleme çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Durum çubuğu
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Hazır")
        
        # Ana düzene widget'ları ekleme
        main_layout.addLayout(top_panel)
        main_layout.addLayout(middle_panel)
        main_layout.addWidget(self.file_list)
        main_layout.addWidget(self.progress_bar)
        
    def load_saved_data(self):
        # Veritabanından dosya listesini yükle
        saved_files = self.db_manager.get_all_files()
        self.all_files = [file['path'] for file in saved_files]
        
        # Kayıtlı izleme yollarını yükle
        self.watch_paths = self.db_manager.get_watch_paths()
        
        # İzleme yollarını aktif et
        for path in self.watch_paths:
            if os.path.exists(path):
                self.start_file_watcher(path)
        
        # Görünümü güncelle
        self.filter_files()
        
        # Son izlenen klasörü göster
        if self.watch_paths and os.path.exists(self.watch_paths[-1]):
            self.path_input.setText(self.watch_paths[-1])
            
        self.statusBar.showMessage(f"Veritabanından {len(self.all_files)} dosya yüklendi")
    
    def auto_scan(self):
        # Otomatik tarama kontrolü
        if not self.auto_scan_checkbox.isChecked():
            return
            
        # Aktif izleme yollarını tara
        for path in self.watch_paths:
            if os.path.exists(path):
                self.start_scan(path, silent=True)
        
        # Eğer hiç tarama yolu yoksa ve input'ta geçerli bir yol varsa onu tara
        if not self.watch_paths:
            path = self.path_input.text()
            if path and os.path.exists(path):
                self.start_scan(path, silent=True)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if folder:
            self.path_input.setText(folder)
            # Klasör seçildiğinde otomatik taramayı başlat
            self.start_scan(folder)
    
    def start_scan(self, custom_path=None, silent=False):
        path = custom_path if custom_path else self.path_input.text()
        
        if not path or not os.path.exists(path):
            if not silent:
                QMessageBox.warning(self, "Hata", "Lütfen geçerli bir klasör yolu girin.")
            return
        
        # Önceki taramayı durdur
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
        
        if not silent:
            # Dosya listesini temizle
            self.file_list.clear()
            self.filtered_files = []
            
            # İlerleme çubuğunu görünür hale getir
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
        
        # Uzantı filtresi
        extension_filter = None
        selected_extension = self.extension_combo.currentText()
        if selected_extension != "Tüm Dosyalar":
            extension_filter = [selected_extension]
        
        # Yeni taramayı başlat
        self.scanner = FileScanner(path, self.db_manager, extension_filter)
        self.scanner.update_signal.connect(self.update_file_list)
        self.scanner.finished_signal.connect(lambda files: self.scan_finished(files, silent))
        self.scanner.progress_signal.connect(self.update_progress)
        self.scanner.start()
        
        # Dosya sistemi izleyicisini başlat
        self.start_file_watcher(path)
        
        if not silent:
            self.statusBar.showMessage(f"Taranıyor: {path}")
    
    def update_file_list(self, file_path):
        if file_path not in self.all_files:
            self.all_files.append(file_path)
        
        # Eğer filtreleme yoksa veya dosya filtreye uyuyorsa listeye ekle
        if self.should_display_file(file_path):
            self.filtered_files.append(file_path)
            self.file_list.addItem(os.path.basename(file_path))
    
    def scan_finished(self, files, silent=False):
        if not silent:
            self.progress_bar.setVisible(False)
            self.filter_files()
            self.statusBar.showMessage(f"Tarama tamamlandı. {len(files)} dosya bulundu.")
        else:
            self.statusBar.showMessage(f"Arkaplan taraması tamamlandı. {len(files)} dosya güncellendi.")
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def filter_files(self):
        search_text = self.search_input.text().lower()
        extension = self.extension_combo.currentText()
        
        self.file_list.clear()
        self.filtered_files = []
        
        for file_path in self.all_files:
            if self.should_display_file(file_path, search_text, extension):
                self.filtered_files.append(file_path)
                if os.path.exists(file_path):  # Sadece varolan dosyaları göster
                    self.file_list.addItem(os.path.basename(file_path))
        
        self.statusBar.showMessage(f"{len(self.filtered_files)} dosya gösteriliyor")
    
    def should_display_file(self, file_path, search_text="", extension=""):
        if not os.path.exists(file_path):
            return False
            
        file_name = os.path.basename(file_path).lower()
        
        # Arama metnine göre filtrele
        if search_text and search_text not in file_name:
            return False
        
        # Uzantıya göre filtrele
        if extension and extension != "Tüm Dosyalar":
            if not file_name.endswith(extension.lower()):
                return False
        
        return True
    
    def open_file(self, item):
        index = self.file_list.row(item)
        if index >= 0 and index < len(self.filtered_files):
            file_path = self.filtered_files[index]
            try:
                # Windows işletim sistemi için dosyayı açma
                os.startfile(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Dosya açılamadı: {str(e)}")
    
    def start_file_watcher(self, path):
        # Path'in izleme listesinde olup olmadığını kontrol et
        if path in self.watch_paths:
            return
            
        # Dosya sistemi izleyicisini başlat
        if not self.observer:
            self.observer = Observer()
            event_handler = FileSystemWatcher(self, self.db_manager)
            self.observer.schedule(event_handler, path, recursive=True)
            self.observer.start()
        else:
            # Mevcut izleyiciye yeni yol ekle
            event_handler = FileSystemWatcher(self, self.db_manager)
            self.observer.schedule(event_handler, path, recursive=True)
        
        self.watch_paths.append(path)
        self.db_manager.add_watch_path(path)
        
    def handle_file_change(self, file_path, change_type):
        # Dosya sisteminde değişiklik olduğunda yapılacaklar
        if change_type == "added":
            if file_path not in self.all_files:
                self.all_files.append(file_path)
                if self.should_display_file(file_path):
                    self.filtered_files.append(file_path)
                    self.file_list.addItem(os.path.basename(file_path))
        
        elif change_type == "deleted":
            if file_path in self.all_files:
                self.all_files.remove(file_path)
                if file_path in self.filtered_files:
                    self.filtered_files.remove(file_path)
                    self.filter_files()  # Listeyi yeniden oluştur
        
        elif change_type in ["modified", "moved"]:
            self.filter_files()  # Listeyi yeniden oluştur
    
    def closeEvent(self, event):
        # Uygulamadan çıkmadan önce izleyiciyi ve tarayıcıyı durdur
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        # Otomatik tarama ayarını kaydet
        self.db_manager.set_config("auto_scan", "1" if self.auto_scan_checkbox.isChecked() else "0")
        
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = FileExplorer()
    ex.show()
    sys.exit(app.exec_()) 