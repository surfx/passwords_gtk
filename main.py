import sys
import os
import subprocess
import glob
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QPlainTextEdit, QMessageBox, QTabWidget,
    QInputDialog
)
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor, QShortcut, QKeySequence, QFont, QIcon
from PyQt6.QtCore import Qt

class CustomPlainTextEdit(QPlainTextEdit):
    def focusNextPrevChild(self, next):
        # Impede que o Tab ou Shift+Tab mude o foco para outros botões
        return False

    def keyPressEvent(self, event):
        # No Qt, Shift+Tab muitas vezes é reportado como Key_Backtab
        if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            is_shift = (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) or (event.key() == Qt.Key.Key_Backtab)
            if self.handle_tab(backwards=is_shift):
                return
        
        super().keyPressEvent(event)

    def handle_tab(self, backwards=False):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            if backwards:
                self.indent_selection(backwards=True)
                return True
            return False
        self.indent_selection(backwards=backwards)
        return True

    def indent_selection(self, backwards=False):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(start)
        line_start = cursor.blockNumber()
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        line_end = cursor.blockNumber()

        cursor.beginEditBlock()
        for i in range(line_start, line_end + 1):
            cursor.setPosition(self.document().findBlockByNumber(i).position())
            
            if not backwards:
                cursor.insertText("    ")
            else:
                line_text = cursor.block().text()
                if line_text.startswith("\t"):
                    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
                elif line_text.startswith(" "):
                    spaces_to_remove = 0
                    while spaces_to_remove < 4 and spaces_to_remove < len(line_text) and line_text[spaces_to_remove] == " ":
                        spaces_to_remove += 1
                    if spaces_to_remove > 0:
                        cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, spaces_to_remove)
                        cursor.removeSelectedText()
        cursor.endEditBlock()

class TabContent(QWidget):
    def __init__(self, file_name, app_font, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.file_name = file_name
        self.passphrase = "root"
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(self.base_dir, "arquivos", f"{file_name}.gpg")
        self._original_text = ""
        self.matches = []
        self.current_match_index = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.text_edit = CustomPlainTextEdit()
        self.text_edit.setFont(app_font)
        self.text_edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_edit)

    def on_text_changed(self):
        current_text = self.text_edit.toPlainText()
        has_changed = current_text != self._original_text
        self.parent_app.update_tab_visuals(self, has_changed)
        self.parent_app.update_save_button_state(has_changed)

    def is_modified(self):
        return self.text_edit.toPlainText() != self._original_text

class SearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pwd")
        self.resize(1000, 800)
        self.setWindowIcon(QIcon.fromTheme("system-lock-screen", QIcon.fromTheme("lock")))

        self.app_font = QFont("FiraCode Nerd Font", 10)
        self.app_font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(self.app_font)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, "arquivos")
        
        self.init_ui()
        self.scan_and_load_tabs()
        self.setup_shortcuts()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar (Search)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setFont(self.app_font)
        self.search_input.setPlaceholderText("Digite para buscar...")
        self.search_input.textChanged.connect(self.on_search_changed)
        
        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedWidth(50)
        self.btn_up.clicked.connect(self.prev_match)
        
        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedWidth(50)
        self.btn_down.clicked.connect(self.next_match)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_up)
        search_layout.addWidget(self.btn_down)
        main_layout.addLayout(search_layout)

        # Tabs Control Bar (+ / -)
        tabs_control_layout = QHBoxLayout()
        self.btn_add_tab = QPushButton("+")
        self.btn_add_tab.setFixedWidth(40)
        self.btn_add_tab.clicked.connect(self.add_new_tab_dialog)
        
        self.btn_remove_tab = QPushButton("-")
        self.btn_remove_tab.setFixedWidth(40)
        self.btn_remove_tab.clicked.connect(self.remove_current_tab)
        
        tabs_control_layout.addWidget(self.btn_add_tab)
        tabs_control_layout.addWidget(self.btn_remove_tab)
        tabs_control_layout.addStretch()
        main_layout.addLayout(tabs_control_layout)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.app_font)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)

        # Save Button
        self.btn_save = QPushButton("Salvar Aba Atual")
        self.btn_save.setFont(self.app_font)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_current_tab)
        main_layout.addWidget(self.btn_save)

    def setup_shortcuts(self):
        self.shortcut_f3 = QShortcut(QKeySequence("F3"), self)
        self.shortcut_f3.activated.connect(self.next_match)
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_current_tab)
        self.shortcut_new_tab = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new_tab.activated.connect(self.add_new_tab_dialog)
        self.shortcut_next_tab = QShortcut(QKeySequence("Ctrl+PgDown"), self)
        self.shortcut_next_tab.activated.connect(self.next_tab)
        self.shortcut_prev_tab = QShortcut(QKeySequence("Ctrl+PgUp"), self)
        self.shortcut_prev_tab.activated.connect(self.prev_tab)

    def next_tab(self):
        current = self.tab_widget.currentIndex()
        count = self.tab_widget.count()
        if count > 0:
            self.tab_widget.setCurrentIndex((current + 1) % count)

    def prev_tab(self):
        current = self.tab_widget.currentIndex()
        count = self.tab_widget.count()
        if count > 0:
            self.tab_widget.setCurrentIndex((current - 1) % count)

    def scan_and_load_tabs(self):
        os.makedirs(self.data_dir, exist_ok=True)
        gpg_files = glob.glob(os.path.join(self.data_dir, "*.gpg"))
        if not gpg_files:
            self.add_tab("Principal")
        else:
            gpg_files.sort()
            for file_path in gpg_files:
                tab_name = os.path.splitext(os.path.basename(file_path))[0]
                self.add_tab(tab_name)

    def add_tab(self, name):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i).replace(" *", "") == name:
                return
        tab = TabContent(name, self.app_font, self)
        self.tab_widget.addTab(tab, name)
        self.load_tab_data(tab)

    def add_new_tab_dialog(self):
        name, ok = QInputDialog.getText(self, "Nova Aba", "Nome da aba:")
        if ok and name:
            self.add_tab(name)
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

    def remove_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx == -1: return
        tab = self.tab_widget.widget(idx)
        res = QMessageBox.question(self, "Remover Aba", f"Deseja remover a aba '{tab.file_name}'?\n\nIsso deletará o arquivo físico criptografado permanentemente.",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            if os.path.exists(tab.file_path):
                try:
                    os.remove(tab.file_path)
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Não foi possível deletar o arquivo: {e}")
                    return
            self.tab_widget.removeTab(idx)
            if self.tab_widget.count() == 0:
                self.add_tab("Principal")

    def load_tab_data(self, tab):
        if not os.path.exists(tab.file_path):
            content = ""
        else:
            try:
                cmd = ["gpg", "--batch", "--yes", "--passphrase", tab.passphrase, "-d", tab.file_path]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                content = result.stdout
            except:
                content = ""
        tab.text_edit.blockSignals(True)
        tab.text_edit.setPlainText(content)
        tab.text_edit.blockSignals(False)
        tab._original_text = content

    def update_tab_visuals(self, tab, is_modified):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i) == tab:
                if is_modified:
                    self.tab_widget.setTabText(i, f"{tab.file_name} *")
                    font = self.tab_widget.tabBar().font()
                    font.setItalic(True)
                    self.tab_widget.tabBar().setFont(font)
                else:
                    self.tab_widget.setTabText(i, tab.file_name)
                    any_modified = any(self.tab_widget.widget(j).is_modified() for j in range(self.tab_widget.count()))
                    if not any_modified:
                        font = self.tab_widget.tabBar().font()
                        font.setItalic(False)
                        self.tab_widget.tabBar().setFont(font)

    def save_current_tab(self):
        tab = self.tab_widget.currentWidget()
        if not tab: return
        content = tab.text_edit.toPlainText()
        try:
            cmd = ["gpg", "--batch", "--yes", "--passphrase", tab.passphrase, "-c", "-o", tab.file_path]
            subprocess.run(cmd, input=content, text=True, check=True)
            tab._original_text = content
            self.update_save_button_state(False)
            self.update_tab_visuals(tab, False)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {e}")

    def on_tab_changed(self):
        tab = self.tab_widget.currentWidget()
        if tab:
            self.update_save_button_state(tab.is_modified())
            self.on_search_changed()

    def update_save_button_state(self, enabled):
        self.btn_save.setEnabled(enabled)

    def on_search_changed(self):
        tab = self.tab_widget.currentWidget()
        if not tab: return
        query = self.search_input.text()
        self.clear_highlights(tab)
        tab.matches = []
        tab.current_match_index = -1
        if not query: return
        doc = tab.text_edit.document()
        cursor = QTextCursor(doc)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#2d5a88"))
        fmt.setForeground(QColor("white"))
        while True:
            cursor = doc.find(query, cursor)
            if cursor.isNull(): break
            tab.matches.append(QTextCursor(cursor))
            cursor.mergeCharFormat(fmt)
        if tab.matches:
            tab.current_match_index = 0
            self.scroll_to_match(tab, 0)

    def clear_highlights(self, tab):
        cursor = tab.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())

    def scroll_to_match(self, tab, index):
        if 0 <= index < len(tab.matches):
            cursor = tab.matches[index]
            tab.text_edit.setTextCursor(cursor)
            tab.text_edit.ensureCursorVisible()

    def next_match(self):
        tab = self.tab_widget.currentWidget()
        if not tab or not tab.matches: return
        tab.current_match_index = (tab.current_match_index + 1) % len(tab.matches)
        self.scroll_to_match(tab, tab.current_match_index)

    def prev_match(self):
        tab = self.tab_widget.currentWidget()
        if not tab or not tab.matches: return
        tab.current_match_index = (tab.current_match_index - 1) % len(tab.matches)
        self.scroll_to_match(tab, tab.current_match_index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SearchApp()
    window.show()
    sys.exit(app.exec())
