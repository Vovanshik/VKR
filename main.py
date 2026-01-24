

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from gostcrypto import gosthash
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import sys
import socket
import os

from traits.trait_types import false

# Настройки подключения к БД
DB_CONFIG = {
    'dbname': 'auth_db',
    'user': 'postgres',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def hash_password(password):
    return gosthash.new('streebog512', data=password.encode()).hexdigest()

def get_pc_name():
    try:
        return socket.gethostname()
    except:
        return "Unknown"

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Создание таблицы пользователей (users)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Создание таблицы журнала входов (login_audit)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_audit (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            pc_name TEXT,
            login_time TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Создание учетных записей по умолчани

    conn.commit()
    cur.close()
    conn.close()

def log_login(username, role, success):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO login_audit (username, role, success, pc_name) VALUES (%s, %s, %s, %s)",
        (username, role, success, get_pc_name())
    )
    conn.commit()
    cur.close()
    conn.close()


def check_db(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    db_status = cur.fetchall()

    # Если БД пустая, создаём первого админа
    if not db_status:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, hash_password(password), 'admin')
        )
        conn.commit()

    cur.close()
    conn.close()


class LoginWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Авторизация')
        self.setFixedSize(450, 550)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
            }
            QWidget#centralWidget {
                background: white;
                border-radius: 15px;
            }
            QLabel#titleLabel {
                font-size: 28px;
                font-weight: bold;
                color: #333;
                padding: 10px;
            }
            QLabel#subtitleLabel {
                font-size: 13px;
                color: #666;
                padding: 5px;
            }
            QLabel {
                font-size: 14px;
                color: #333;
                font-weight: 500;
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
            QPushButton#loginButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton#loginButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568d3, stop:1 #6a3f8f);
            }
            QPushButton#loginButton:pressed {
                background: #5568d3;
            }
            QGroupBox {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                margin-top: 10px;
            }
            QGroupBox::title {
                color: #333;
                font-weight: bold;
            }
        """)

        # Центральный виджет
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel('Авторизация')
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel('Защищено ГОСТ Стрибог-512')
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Поле логина
        username_label = QLabel('Имя пользователя')
        layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Введите имя пользователя')
        layout.addWidget(self.username_input)

        # Поле пароля
        password_label = QLabel('Пароль')
        layout.addWidget(password_label)

        # Контейнер для поля пароля и кнопки показа
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(0)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Введите пароль')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.login)
        password_layout.addWidget(self.password_input)

        # Кнопка показа/скрытия пароля
        self.toggle_password_btn = QPushButton('👁')
        self.toggle_password_btn.setFixedSize(40, 40)
        self.toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        self.toggle_password_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        font-size: 20px;
                        padding: 0;
                    }
                    QPushButton:hover {
                        background: rgba(102, 126, 234, 0.1);
                        border-radius: 4px;
                    }
                """)
        password_layout.addWidget(self.toggle_password_btn)

        layout.addWidget(password_container)

        layout.addSpacing(10)

        # Кнопка входа
        login_btn = QPushButton('Войти')
        login_btn.setObjectName("loginButton")
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)

        # Информация о тестовых учетках

        layout.addStretch()

        central_widget.setLayout(layout)

        # Центрирование окна
        self.center()

    def center(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_btn.setText('🙈')
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_btn.setText('👁')

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, 'Ошибка', 'Заполните все поля!')
            return

        password_hash = hash_password(password)
        check_db(username,password)
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and user['password_hash'] == password_hash:
                log_login(username, user['role'], True)
                cur.close()
                conn.close()
                self.main_window = MainWindow(user)
                self.main_window.show()
                self.close()
            elif not user:
                cur.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (username, password_hash, 'user')
                )
                conn.commit()
                cur.close()
                conn.close()
                QMessageBox.information(self,'Успех','Ваша учетная запись была зарегистрирована\n Используйте введенные данные для входа')
                self.password_input.clear()
            else:
                role = user['role'] if user else 'unknown'
                log_login(username, role, False)
                cur.close()
                conn.close()
                QMessageBox.critical(self, 'Ошибка', 'Неверное имя пользователя или пароль!')
                self.password_input.clear()

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка БД', f'Ошибка подключения к базе данных:\n{str(e)}')


class MainWindow(QMainWindow):
    #Окно после авторизации

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'Панель управления - {self.user["username"]}')
        self.setMinimumSize(1100, 700)

        self.setStyleSheet("""
            QMainWindow {
                background: #f5f7fa;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #e0e0e0;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                color: #667eea;
            }
            QTableWidget {
                border: none;
                background: white;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #f8f9fa;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: bold;
                color: #333;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568d3, stop:1 #6a3f8f);
            }
            QLabel#statsLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border-radius: 10px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
            }
        """)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Шапка
        header = QWidget()
        header_layout = QHBoxLayout()

        welcome_label = QLabel(f'Добро пожаловать, {self.user["username"]}!')
        welcome_label.setStyleSheet('font-size: 20px; font-weight: bold; color: #333;')
        header_layout.addWidget(welcome_label)

        role_badge = QLabel(f'{self.user["role"].upper()}')
        role_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #667eea, stop:1 #764ba2);
            color: white;
            padding: 8px 16px;
            border-radius: 15px;
            font-weight: bold;
        """)
        header_layout.addWidget(role_badge)

        header_layout.addStretch()

        logout_btn = QPushButton('Выйти')
        logout_btn.clicked.connect(self.logout)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(logout_btn)

        header.setLayout(header_layout)
        main_layout.addWidget(header)

        # Вкладки
        tabs = QTabWidget()

        # Вкладка "Главная"
        home_tab = self.create_home_tab()
        tabs.addTab(home_tab, 'Главная')

        # Вкладка "Журнал входов"
        logs_tab = self.create_logs_tab()
        tabs.addTab(logs_tab, 'Журнал входов')

        if self.user['role'] == 'admin':
            # Вкладка "Статистика" только для админа
            stats_tab = self.create_stats_tab()
            tabs.addTab(stats_tab, 'Статистика')

        main_layout.addWidget(tabs)
        central_widget.setLayout(main_layout)

        # Центрирование окна
        self.center()

    def center(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def create_home_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Приветственное сообщение
        welcome = QLabel(f'Добро пожаловать в систему, {self.user["username"]}!')
        welcome.setStyleSheet('font-size: 18px; font-weight: bold; color: #333; padding: 20px;')
        layout.addWidget(welcome)

        # Информация о пользователе
        info_group = QGroupBox('👤 Информация о пользователе')
        info_layout = QVBoxLayout()

        username_info = QLabel(f'Логин: {self.user["username"]}')
        username_info.setStyleSheet('font-size: 14px; padding: 5px;')
        info_layout.addWidget(username_info)

        role_info = QLabel(f'Роль: {self.user["role"]}')
        role_info.setStyleSheet('font-size: 14px; padding: 5px;')
        info_layout.addWidget(role_info)

        created_info = QLabel(f'Дата создания: {self.user["created_at"].strftime("%d.%m.%Y %H:%M")}')
        created_info.setStyleSheet('font-size: 14px; padding: 5px;')
        info_layout.addWidget(created_info)

        pc_info = QLabel(f'Компьютер: {get_pc_name()}')
        pc_info.setStyleSheet('font-size: 14px; padding: 5px;')
        info_layout.addWidget(pc_info)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        app_group = QGroupBox('Функционал программы')
        app_layout = QVBoxLayout()

        desc_label = QLabel('Сканер ПДН')
        desc_label.setStyleSheet('font-size: 14px; color: #666; padding: 10px;')
        app_layout.addWidget(desc_label)

        # Кнопка запуска сканера ПДН
        btn_scanner = QPushButton('Сканер персональных данных')
        if self.user['role'] == 'admin':
            btn_scanner.clicked.connect(self.open_pdn_scanner)
        else:
            btn_scanner.clicked.connect(self.open_pdn_scanner_user)
        btn_scanner.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #28a745, stop:1 #20c997);
                padding: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #218838, stop:1 #1aa179);
            }
        """)
        app_layout.addWidget(btn_scanner)
        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_logs_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Кнопка обновления
        refresh_btn = QPushButton('🔄 Обновить')
        refresh_btn.clicked.connect(lambda: self.load_logs(table))
        refresh_btn.setMaximumWidth(150)
        layout.addWidget(refresh_btn)

        # Таблица журнала
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['Пользователь', 'Роль', 'Время входа', 'Компьютер', 'Статус'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(table)
        widget.setLayout(layout)
        self.load_logs(table)
        return widget

    def load_logs(self, table):
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            if self.user['role'] == 'admin':
                cur.execute("SELECT * FROM login_audit ORDER BY login_time DESC LIMIT 100")
            else:
                cur.execute(
                    "SELECT * FROM login_audit WHERE username = %s ORDER BY login_time DESC LIMIT 50",
                    (self.user['username'],)
                )

            logs = cur.fetchall()
            cur.close()
            conn.close()

            table.setRowCount(len(logs))

            for i, log in enumerate(logs):
                table.setItem(i, 0, QTableWidgetItem(log['username']))
                table.setItem(i, 1, QTableWidgetItem(log['role']))
                table.setItem(i, 2, QTableWidgetItem(log['login_time'].strftime('%d.%m.%Y %H:%M:%S')))
                table.setItem(i, 3, QTableWidgetItem(log['pc_name'] or 'Unknown'))

                status_item = QTableWidgetItem('✓ Успешно' if log['success'] else '✗ Неудачно')
                if log['success']:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item.setForeground(Qt.GlobalColor.red)
                table.setItem(i, 4, status_item)

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка загрузки журнала:\n{str(e)}')

    def create_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Получение статистики
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) as count FROM users")
            total_users = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM login_audit")
            total_logins = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM login_audit WHERE success = TRUE")
            successful_logins = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM login_audit WHERE success = FALSE")
            failed_logins = cur.fetchone()['count']

            cur.close()
            conn.close()

            #Карточки статистики
            stats_layout = QHBoxLayout()

            stats = [
                ('Всего пользователей', total_users),
                ('Всего попыток', total_logins),
                ('Успешных входов', successful_logins),
                ('Неудачных попыток', failed_logins),
            ]

            for title, value in stats:
                stat_label = QLabel(f'{title}\n\n{value}')
                stat_label.setObjectName("statsLabel")
                stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                stat_label.setMinimumHeight(100)
                stats_layout.addWidget(stat_label)

            layout.addLayout(stats_layout)

            #Таблица последних входов
            recent_group = QGroupBox('Последние попытки входа')
            recent_layout = QVBoxLayout()

            recent_table = QTableWidget()
            recent_table.setColumnCount(5)
            recent_table.setHorizontalHeaderLabels(['Пользователь', 'Роль', 'Время', 'Компьютер', 'Статус'])
            recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            recent_table.setMaximumHeight(300)

            # Загрузка последних записей
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM login_audit ORDER BY login_time DESC LIMIT 10")
            recent_logs = cur.fetchall()
            cur.close()
            conn.close()

            recent_table.setRowCount(len(recent_logs))
            for i, log in enumerate(recent_logs):
                recent_table.setItem(i, 0, QTableWidgetItem(log['username']))
                recent_table.setItem(i, 1, QTableWidgetItem(log['role']))
                recent_table.setItem(i, 2, QTableWidgetItem(log['login_time'].strftime('%d.%m.%Y %H:%M:%S')))
                recent_table.setItem(i, 3, QTableWidgetItem(log['pc_name'] or 'Unknown'))

                status_item = QTableWidgetItem('✓ Успешно' if log['success'] else '✗ Неудачно')
                if log['success']:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item.setForeground(Qt.GlobalColor.red)
                recent_table.setItem(i, 4, status_item)

            recent_layout.addWidget(recent_table)
            recent_group.setLayout(recent_layout)
            layout.addWidget(recent_group)

        except Exception as e:
            error_label = QLabel(f'Ошибка загрузки статистики:\n{str(e)}')
            error_label.setStyleSheet('color: red; padding: 20px;')
            layout.addWidget(error_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def open_pdn_scanner(self):
        try:
            import subprocess
            scanner_path = "main_gui_dir_search_2.py"

            if os.path.exists(scanner_path):
                subprocess.Popen([sys.executable, scanner_path])
                QMessageBox.information(
                    self,
                    'Запуск',
                    'Сканер персональных данных запущен в отдельном окне!'
                )
            else:
                QMessageBox.warning(
                    self,
                    'Ошибка',
                    f'Файл {scanner_path} не найден!\n\n'
                    f'Убедитесь, что файл находится в той же папке, что и программа авторизации.'
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                'Ошибка запуска',
                f'Не удалось запустить сканер:\n{str(e)}'
            )
    def open_pdn_scanner_user(self):
        try:
            import subprocess
            scanner_path = "main_gui_dir_search_2_user.py"

            if os.path.exists(scanner_path):
                subprocess.Popen([sys.executable, scanner_path])
                QMessageBox.information(
                    self,
                    'Запуск',
                    'Сканер персональных данных запущен в отдельном окне!'
                )
            else:
                QMessageBox.warning(
                    self,
                    'Ошибка',
                    f'Файл {scanner_path} не найден!\n\n'
                    f'Убедитесь, что файл находится в той же папке, что и программа авторизации.'
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                'Ошибка запуска',
                f'Не удалось запустить сканер:\n{str(e)}'
            )

    def logout(self):
        reply = QMessageBox.question(
            self, 'Выход',
            'Вы действительно хотите выйти?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            login_window = LoginWindow()
            login_window.show()


def main():
    # Инициализация БД
    try:
        print("Инициализация базы данных...")
        init_db()
        print("✓ База данных готова к работе")
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")
        print("Проверьте настройки подключения к PostgreSQL в DB_CONFIG")
        return

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()