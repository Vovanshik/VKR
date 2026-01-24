import sys
import os
import getpass
import subprocess
from datetime import datetime


from Dir_search_2_1_1 import main_scanner, faceless_text, archive_files_with_zip,generate_report,load_keywords_from_file,secure_delete_file, get_file_owner   # важно!
from PyQt5 import QtCore, QtGui, QtWidgets


def is_document_older_than_years(file_path: str, years: int = 40) -> bool:
    try:
        created_ts = os.path.getctime(file_path)
        created_dt = datetime.fromtimestamp(created_ts)
        now = datetime.now()

        age_years = (now - created_dt).days / 365.25
        return age_years >= years
    except Exception:
        return False



class PDNScannerGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Сканер персональных данных")
        self.setGeometry(200, 100, 1100, 650)

        #Основная панель
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)


        #верхняя панель
        top_panel = QtWidgets.QHBoxLayout()

        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("Выберите директорию для сканирования...")
        top_panel.addWidget(self.path_edit)

        browse_btn = QtWidgets.QPushButton("Обзор…")
        browse_btn.clicked.connect(self.choose_directory)
        top_panel.addWidget(browse_btn)

        scan_btn = QtWidgets.QPushButton("Сканировать")
        scan_btn.clicked.connect(self.start_scan)
        top_panel.addWidget(scan_btn)



        self.chk_pdn_and_keywords = QtWidgets.QCheckBox("Искать ПДн + пользовательские слова")
        self.chk_only_keywords = QtWidgets.QCheckBox("Искать только пользовательские слова")
        self.chk_pdn_and_keywords.setEnabled(False)
        self.chk_only_keywords.setEnabled(False)
        self.chk_highlight_old = QtWidgets.QCheckBox(
            "Подсвечивать документы старше 40 лет"
        )
        self.chk_highlight_old.stateChanged.connect(self.update_old_highlighting)

        layout.addWidget(self.chk_highlight_old)


        layout.addWidget(self.chk_pdn_and_keywords)
        layout.addWidget(self.chk_only_keywords)

        layout.addLayout(top_panel)

        #таблица
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["✔", "Полный путь", "Имя файла", "Типы ПДн", "Срок документа"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.table.cellDoubleClicked.connect(self.open_folder_for_row)

        layout.addWidget(self.table)

        #нижняя панель
        self.table.setSortingEnabled(True)
        bottom_panel = QtWidgets.QHBoxLayout()

        mask_btn = QtWidgets.QPushButton("Обезличить выбранные")
        mask_btn.clicked.connect(self.mask_selected)
        bottom_panel.addWidget(mask_btn)

        zip_btn = QtWidgets.QPushButton("Заархивировать выбранные")
        zip_btn.clicked.connect(self.archive_selected)
        bottom_panel.addWidget(zip_btn)

        report_btn = QtWidgets.QPushButton("Экспорт отчёта")
        report_btn.clicked.connect(self.export_report)
        bottom_panel.addWidget(report_btn)

        keywords_btn = QtWidgets.QPushButton("Загрузить пользов. слова")
        keywords_btn.clicked.connect(self.load_keywords)
        bottom_panel.addWidget(keywords_btn)

        self.btn_destroy = QtWidgets.QPushButton("Уничтожить файлы")
        self.btn_destroy.clicked.connect(self.destroy_selected_files)
        bottom_panel.addWidget(self.btn_destroy)

        self.status_label = QtWidgets.QLabel("Готов к работе.")
        bottom_panel.addWidget(self.status_label)



        layout.addLayout(bottom_panel)
        self.scan_results = []
        self.custom_keywords = []
        self.apply_styles()

    # =======================================================================
    #                           СТИЛИ ОФОРМЛЕНИЯ
    # =======================================================================
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f4f4f6;
            }
            QPushButton {
                background-color: #4682B4;
                color: white;
                padding: 6px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5A9BD5;
            }
            QTableWidget {
                background: white;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #D0D7E5;
                font-weight: bold;
                padding: 4px;
            }
        """)


    def choose_directory(self):
        start_dir = self.path_edit.text() or os.path.expanduser("~/Desktop")

        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку",start_dir)
        if directory:
            self.path_edit.setText(directory)


    def start_scan(self):
        mode = "pdn"

        if self.chk_only_keywords.isChecked():
            mode = "keywords"
        elif self.chk_pdn_and_keywords.isChecked():
            mode = "pdn+keywords"
        print(mode)
        directory = self.path_edit.text().strip()
        if not os.path.isdir(directory):
            self.status_label.setText("Ошибка: выберите корректную папку.")
            return
        if mode in ("keywords", "pdn+keywords") and not self.custom_keywords:
            QtWidgets.QMessageBox.warning(
                self,
                "Пользовательские слова не загружены",
                "Вы выбрали поиск по Пользовательским словам,\n"
                "но не загрузили файл с пользовательскими словами.\n\n"
                "Загрузите файл и повторите попытку."
            )
            return
        self.status_label.setText("Сканирование...")

        results = main_scanner(directory,keywords=self.custom_keywords,mode=mode)
        self.scan_results = results

        self.fill_table(results)
        self.status_label.setText(f"Найдено {len(results)} файлов с ПДн.")

    def update_old_highlighting(self):
        highlight = self.chk_highlight_old.isChecked()

        for row in range(self.table.rowCount()):
            file_item = self.table.item(row, 1)  # колонка с путём
            if not file_item:
                continue

            file_path = file_item.text()

            is_old = is_document_older_than_years(file_path, 0)

            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if not item:
                    continue

                if highlight and is_old:
                    item.setBackground(QtGui.QColor("#FFE4E1"))
                else:
                    item.setBackground(QtGui.QBrush())



    #Содержимое таблицы
    def fill_table(self, results):
        self.table.setRowCount(0)
        self.update_old_highlighting()

        for item in results:
            file_path = item["file"]
            filename = os.path.basename(file_path)
            owner = get_file_owner(file_path)
            owner_pc = os.getlogin()
            if owner_pc not in owner:
                continue

            types_list = ", ".join(sorted(set(f["type"] for f in item["findings"])))
            age = item['file_time_creat']
            row = self.table.rowCount()
            self.table.insertRow(row)

            #чекбокс
            checkbox = QtWidgets.QTableWidgetItem()
            checkbox.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            checkbox.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row, 0, checkbox)

            #Полный путь
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(file_path))

            #Имя файла
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(filename))

            #Тип пдн
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(types_list))

            #Возраст
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(age))

        self.table.resizeColumnsToContents()


    def open_folder_for_row(self, row: int, column: int):
        path_item = self.table.item(row, 1)
        if not path_item:
            return

        file_path = path_item.text()
        folder = os.path.dirname(file_path)

        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])


    def get_selected_files(self):
        selected = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.item(row, 0)
            if checkbox.checkState() == QtCore.Qt.Checked:
                selected.append(self.table.item(row, 1).text())
        return selected


    #Обезличивание
    def mask_selected(self):
        selected = self.get_selected_files()
        if not selected:
            self.status_label.setText("Нет выбранных файлов.")
            return

        items = [res for res in self.scan_results if res["file"] in selected]

        faceless_text(items)

        self.status_label.setText(f"Обезличено файлов: {len(items)}")
        password, ok = QtWidgets.QInputDialog.getText(
            self,
            "Пароль архива",
            "Введите пароль:",
            QtWidgets.QLineEdit.EchoMode.Password
        )

        archive_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить архив",
            "secure_archive.zip",
            "ZIP архив (*.zip)"
        )

        if not archive_path:
            return

        if not archive_path.lower().endswith(".zip"):
            archive_path += ".zip"

        # Архивация
        archive_files_with_zip(selected, archive_path, password)

        self.status_label.setText(
            f"Файлы заархивированы: {len(selected)} → {archive_path}"
        )

    #архивирование
    def archive_selected(self):
        selected = self.get_selected_files()
        if not selected:
            self.status_label.setText("Нет выбранных файлов.")
            return

        password, ok = QtWidgets.QInputDialog.getText(
            self, "Пароль", "Введите пароль для архива:", echo=QtWidgets.QLineEdit.Password
        )

        if not ok or not password:
            return

        archive_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить архив",
            "secure_archive.zip",
            "ZIP архив (*.zip)"
        )

        if not archive_path:
            return

        if not archive_path.lower().endswith(".zip"):
            archive_path += ".zip"

        # Архивация
        archive_files_with_zip(selected, archive_path, password)

        self.status_label.setText(
            f"Файлы заархивированы: {len(selected)} → {archive_path}"
        )

    def export_report(self):
        if not self.scan_results:
            self.status_label.setText("Нет данных для отчёта.")
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт",
            "~/Desktop/pdn_report.xlsx",
            "Excel (*.xlsx)"
        )

        if not path:
            return

        try:
            generate_report(self.scan_results, path)
            self.status_label.setText(f"Отчёт сохранён: {path}")
        except Exception as e:
            self.status_label.setText(f"Ошибка сохранения отчёта: {e}")

    def load_keywords(self):
        QtWidgets.QMessageBox.warning(
            self,
            "!",
            "Для загрузки используйте файл формата (.txt)\n"
            "Каждое слово или фраза для поиска должна находиться"
            "на отдельной строке.\n В конце каждого слова или фразы "
            "должен стоять разделитель ';'. \nПример:\n"
            "Владимир;\n"
            "Вышел погулять;\n"
            "Высокозеро;\n"
        )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Файл с пользовательскими словами", "", "Text files (*.txt)"
        )
        if not path:
            return
        self.custom_keywords = load_keywords_from_file(path)

        if not self.custom_keywords:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Файл не содержит пользовательских слов."
            )
            return
        self.chk_pdn_and_keywords.setEnabled(True)
        self.chk_only_keywords.setEnabled(True)

        self.status_label.setText(
            f"Загружено слов пользователя: {len(self.custom_keywords)}"
        )

    def destroy_selected_files(self):
        checked = self.get_selected_files()

        if not checked:
            QtWidgets.QMessageBox.information(
                self,
                "Нет файлов",
                "Не выбрано ни одного файла для уничтожения."
            )
            return
        QtWidgets.QMessageBox.warning(
            self,
            "ВНИМАНИЕ",
            "Данное действие эффективно только для жестких дисков (HDD)."
        )
        reply = QtWidgets.QMessageBox.warning(
            self,
            "Подтверждение уничтожения",
            "Вы действительно хотите БЕЗВОЗВРАТНО уничтожить выбранные файлы?",
            QtWidgets.QMessageBox.StandardButton.Yes |
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        destroyed_files = []

        for file_path in checked:
            if secure_delete_file(file_path, passes=3):
                destroyed_files.append(file_path)

        self.refresh_after_destruction(destroyed_files)

        QtWidgets.QMessageBox.information(
            self,
            "Готово",
            f"Уничтожено файлов: {len(destroyed_files)}"
        )

    def refresh_after_destruction(self, destroyed_files):
        rows_to_remove = []

        for row in range(self.table.rowCount()):
            path_item = self.table.item(row, 1)
            if path_item and path_item.text() in destroyed_files:
                rows_to_remove.append(row)

        QtCore.QTimer.singleShot(
            0,
            lambda: self.remove_rows_safe(rows_to_remove)
        )

    def remove_rows_safe(self, rows):
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    gui = PDNScannerGUI()
    gui.show()
    sys.exit(app.exec_())
