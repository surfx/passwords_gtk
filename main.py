import sys
import os
import subprocess
import glob
import secrets
import pickle
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QPlainTextEdit, QMessageBox, QTabWidget,
    QInputDialog, QDialog, QLabel, QFileDialog
)
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor, QShortcut, QKeySequence, QFont, QIcon
from PyQt6.QtCore import Qt

class LoginDialog(QDialog):
    def __init__(self, vault_path, parent=None):
        super().__init__(parent)
        self.vault_path = vault_path
        self.master_password = None
        self.vault_data = None
        self.setWindowTitle("Login - Password")
        self.setFixedSize(300, 150)
        self.setWindowIcon(QIcon.fromTheme("system-lock-screen", QIcon.fromTheme("lock")))
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Digite a Senha Mestre:"))
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        self.btn_login = QPushButton("Desbloquear")
        self.btn_login.clicked.connect(self.attempt_login)
        layout.addWidget(self.btn_login)
        
        self.password_input.returnPressed.connect(self.attempt_login)

    def attempt_login(self):
        password = self.password_input.text()
        if not password:
            return
            
        try:
            cmd = ["gpg", "--batch", "--yes", "--passphrase", password, "-d", self.vault_path]
            result = subprocess.run(cmd, capture_output=True, check=True)
            self.vault_data = pickle.loads(result.stdout)
            self.master_password = password
            self.accept()
        except Exception:
            QMessageBox.critical(self, "Erro", "Senha incorreta ou erro ao ler o cofre.")
            self.password_input.clear()

class InitialSetupDialog(QDialog):
    def __init__(self, vault_path, parent=None):
        super().__init__(parent)
        self.vault_path = vault_path
        self.master_password = None
        self.setWindowTitle("Configuração Inicial - password")
        self.setFixedSize(350, 200)
        self.setWindowIcon(QIcon.fromTheme("system-lock-screen", QIcon.fromTheme("lock")))
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Defina sua Senha Mestre:"))
        
        self.pass1 = QLineEdit()
        self.pass1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass1.setPlaceholderText("Nova Senha")
        layout.addWidget(self.pass1)
        
        layout.addWidget(QLabel("Confirme a Senha:"))
        self.pass2 = QLineEdit()
        self.pass2.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass2.setPlaceholderText("Confirmar Senha")
        layout.addWidget(self.pass2)
        
        self.btn_create = QPushButton("Criar Cofre")
        self.btn_create.clicked.connect(self.create_vault)
        layout.addWidget(self.btn_create)

    def create_vault(self):
        p1 = self.pass1.text()
        p2 = self.pass2.text()
        
        if not p1:
            QMessageBox.warning(self, "Aviso", "A senha não pode ser vazia.")
            return
        if p1 != p2:
            QMessageBox.warning(self, "Aviso", "As senhas não coincidem.")
            return
            
        try:
            empty_vault = {}
            data = pickle.dumps(empty_vault)
            cmd = ["gpg", "--batch", "--yes", "--passphrase", p1, "-c", "-o", self.vault_path]
            subprocess.run(cmd, input=data, check=True)
            self.master_password = p1
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao criar cofre: {e}")

class CustomPlainTextEdit(QPlainTextEdit):
    def focusNextPrevChild(self, next):
        return False

    def keyPressEvent(self, event):
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
    def __init__(self, file_name, passphrase, app_font, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.file_name = file_name
        self.passphrase = passphrase
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
    def __init__(self, master_password, vault_data):
        super().__init__()
        self.master_password = master_password
        self.vault_data = vault_data
        self.setWindowTitle("password")
        self.resize(1000, 800)
        self.setWindowIcon(QIcon.fromTheme("system-lock-screen", QIcon.fromTheme("lock")))

        self.app_font = QFont("FiraCode Nerd Font", 10)
        self.app_font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(self.app_font)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, "arquivos")
        self.vault_path = os.path.join(self.data_dir, ".vault.gpg")
        
        self.init_ui()
        self.scan_and_load_tabs()
        self.setup_shortcuts()

    def save_vault(self):
        try:
            data = pickle.dumps(self.vault_data)
            cmd = ["gpg", "--batch", "--yes", "--passphrase", self.master_password, "-c", "-o", self.vault_path]
            subprocess.run(cmd, input=data, check=True)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao atualizar o cofre: {e}")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar (Search apenas com Input e botões de navegação ▲ ▼)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setFont(self.app_font)
        self.search_input.setPlaceholderText("Digite para buscar...")
        self.search_input.textChanged.connect(self.on_search_changed)
        
        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedWidth(40)
        self.btn_up.clicked.connect(self.prev_match)
        
        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedWidth(40)
        self.btn_down.clicked.connect(self.next_match)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_up)
        search_layout.addWidget(self.btn_down)
        main_layout.addLayout(search_layout)

        # Barra de Controles e Abas (+ / - / R / Exportar / Importar / Ver Senha Mestra)
        tabs_control_layout = QHBoxLayout()
        self.btn_add_tab = QPushButton("+")
        self.btn_add_tab.setFixedWidth(40)
        self.btn_add_tab.clicked.connect(self.add_new_tab_dialog)
        
        self.btn_remove_tab = QPushButton("-")
        self.btn_remove_tab.setFixedWidth(40)
        self.btn_remove_tab.clicked.connect(self.remove_current_tab)

        self.btn_rename_tab = QPushButton("R")
        self.btn_rename_tab.setFixedWidth(40)
        self.btn_rename_tab.setToolTip("Renomear Aba Atual")
        self.btn_rename_tab.clicked.connect(self.rename_current_tab)

        self.btn_export = QPushButton("Exportar")
        self.btn_export.clicked.connect(self.export_vault_data)
        
        self.btn_import = QPushButton("Importar")
        self.btn_import.clicked.connect(self.import_vault_data)

        # self.btn_show_master = QPushButton("Ver Senha Mestra")
        # self.btn_show_master.clicked.connect(self.show_master_password_dialog)
        
        tabs_control_layout.addWidget(self.btn_add_tab)
        tabs_control_layout.addWidget(self.btn_remove_tab)
        tabs_control_layout.addWidget(self.btn_rename_tab)
        tabs_control_layout.addWidget(self.btn_export)
        tabs_control_layout.addWidget(self.btn_import)
        # tabs_control_layout.addWidget(self.btn_show_master)
        tabs_control_layout.addStretch()
        main_layout.addLayout(tabs_control_layout)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.app_font)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBar().tabMoved.connect(self.on_tabs_reordered)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)

        # Save Button
        self.btn_save = QPushButton("Salvar Aba Atual")
        self.btn_save.setFont(self.app_font)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_current_tab)
        main_layout.addWidget(self.btn_save)

    # def show_master_password_dialog(self):
    #     QMessageBox.information(
    #         self,
    #         "Senha Mestra",
    #         f"A sua senha mestre atual é:\n\n{self.master_password}"
    #     )

    def export_vault_data(self):
        """Exporta todas as abas para um arquivo estruturado em JSON e criptografado com a senha mestre."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Senhas Criptografadas", "backup_senhas.json.gpg", "Arquivos Criptografados (*.gpg *.json)")
        if not file_path:
            return

        try:
            export_data = {}
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                export_data[tab.file_name] = tab.text_edit.toPlainText()

            json_str = json.dumps(export_data, ensure_ascii=False, indent=4)

            cmd = ["gpg", "--batch", "--yes", "--passphrase", self.master_password, "-c", "-o", file_path]
            subprocess.run(cmd, input=json_str, text=True, check=True)
            QMessageBox.information(self, "Sucesso", f"Dados exportados e criptografados com sucesso em:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar dados: {e}")

    def import_vault_data(self):
        """Importa dados de um arquivo JSON criptografado, restaurando abas e conteúdos perfeitamente."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Importar Senhas Criptografadas", "", "Arquivos Criptografados (*.gpg *.json)")
        if not file_path:
            return

        try:
            cmd = ["gpg", "--batch", "--yes", "--passphrase", self.master_password, "-d", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            imported_data = json.loads(result.stdout)

            if not isinstance(imported_data, dict):
                raise ValueError("O formato do arquivo importado é inválido.")

            res = QMessageBox.question(
                self, "Confirmar Importação",
                "Isso irá atualizar as abas existentes com o conteúdo do arquivo e sobrescrevê-las se necessário. Deseja continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res != QMessageBox.StandardButton.Yes:
                return

            for tab_name, content in imported_data.items():
                found = False
                for i in range(self.tab_widget.count()):
                    tab = self.tab_widget.widget(i)
                    if tab.file_name == tab_name:
                        tab.text_edit.setPlainText(content)
                        self.save_current_tab_explicit(tab)
                        found = True
                        break
                
                if not found:
                    self.add_tab(tab_name)
                    for i in range(self.tab_widget.count()):
                        tab = self.tab_widget.widget(i)
                        if tab.file_name == tab_name:
                            tab.text_edit.setPlainText(content)
                            self.save_current_tab_explicit(tab)
                            break

            QMessageBox.information(self, "Sucesso", "Importação concluída com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao importar cofre (senha incorreta ou arquivo inválido): {e}")

    def save_current_tab_explicit(self, tab):
        try:
            content = tab.text_edit.toPlainText()
            cmd = ["gpg", "--batch", "--yes", "--passphrase", tab.passphrase, "-c", "-o", tab.file_path]
            subprocess.run(cmd, input=content, text=True, check=True)
            tab._original_text = content
            self.update_tab_visuals(tab, False)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar aba {tab.file_name}: {e}")

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

    def closeEvent(self, event):
        modified_tabs = []
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if tab.is_modified():
                modified_tabs.append(tab.file_name)
        
        if modified_tabs:
            msg = "As seguintes abas possuem alterações não salvas:\n\n"
            msg += "\n".join(f"- {name}" for name in modified_tabs)
            msg += "\n\nDeseja salvar tudo antes de sair?"
            
            res = QMessageBox.question(
                self, "Alterações não Salvas", msg,
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if res == QMessageBox.StandardButton.Save:
                for i in range(self.tab_widget.count()):
                    tab = self.tab_widget.widget(i)
                    if tab.is_modified():
                        self.tab_widget.setCurrentWidget(tab)
                        self.save_current_tab()
                event.accept()
            elif res == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

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
        gpg_files = [f for f in gpg_files if not os.path.basename(f).startswith(".")]
        existing_names = [os.path.splitext(os.path.basename(f))[0] for f in gpg_files]
        saved_order = self.vault_data.get("__order__", [])
        
        loaded_names = []
        for name in saved_order:
            if name in existing_names:
                self.add_tab(name)
                loaded_names.append(name)
        
        for name in sorted(existing_names):
            if name not in loaded_names:
                self.add_tab(name)

        if not gpg_files and self.tab_widget.count() == 0:
            self.add_tab("Principal")

    def on_tabs_reordered(self, from_idx, to_idx):
        new_order = []
        for i in range(self.tab_widget.count()):
            name = self.tab_widget.tabText(i).replace(" *", "")
            new_order.append(name)
        self.vault_data["__order__"] = new_order
        self.save_vault()

    def add_tab(self, name):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i).replace(" *", "") == name:
                return
        
        if name not in self.vault_data:
            self.vault_data[name] = secrets.token_urlsafe(32)
            self.update_order_in_vault()
            self.save_vault()
            
        passphrase = self.vault_data[name]
        tab = TabContent(name, passphrase, self.app_font, self)
        self.tab_widget.addTab(tab, name)
        self.load_tab_data(tab)

    def update_order_in_vault(self):
        new_order = []
        for i in range(self.tab_widget.count()):
            name = self.tab_widget.tabText(i).replace(" *", "")
            new_order.append(name)
        self.vault_data["__order__"] = new_order

    def add_new_tab_dialog(self):
        name, ok = QInputDialog.getText(self, "Nova Aba", "Nome da aba:")
        if ok and name:
            self.add_tab(name)
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
            self.update_order_in_vault()
            self.save_vault()

    def rename_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx == -1: return
        tab = self.tab_widget.widget(idx)
        old_name = tab.file_name
        
        new_name, ok = QInputDialog.getText(self, "Renomear Aba", "Novo nome da aba:", text=old_name)
        if not ok or not new_name or new_name == old_name:
            return

        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i).replace(" *", "") == new_name:
                QMessageBox.warning(self, "Aviso", "Já existe uma aba com este nome.")
                return

        new_file_path = os.path.join(self.data_dir, f"{new_name}.gpg")
        if os.path.exists(tab.file_path):
            try:
                os.rename(tab.file_path, new_file_path)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao renomear arquivo: {e}")
                return
        
        if old_name in self.vault_data:
            self.vault_data[new_name] = self.vault_data.pop(old_name)
            if "__order__" in self.vault_data:
                self.vault_data["__order__"] = [new_name if n == old_name else n for n in self.vault_data["__order__"]]
            self.save_vault()

        tab.file_name = new_name
        tab.file_path = new_file_path
        self.update_tab_visuals(tab, tab.is_modified())

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
            
            if tab.file_name in self.vault_data:
                del self.vault_data[tab.file_name]
                
            self.tab_widget.removeTab(idx)
            self.update_order_in_vault()
            self.save_vault()
            
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
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "arquivos")
    os.makedirs(data_dir, exist_ok=True)
    vault_path = os.path.join(data_dir, ".vault.gpg")
    
    master_password = None
    vault_data = {}
    
    if not os.path.exists(vault_path):
        setup = InitialSetupDialog(vault_path)
        if setup.exec() == QDialog.DialogCode.Accepted:
            master_password = setup.master_password
            vault_data = {}
        else:
            sys.exit()
    else:
        login = LoginDialog(vault_path)
        if login.exec() == QDialog.DialogCode.Accepted:
            master_password = login.master_password
            vault_data = login.vault_data
        else:
            sys.exit()
            
    window = SearchApp(master_password, vault_data)
    window.show()
    sys.exit(app.exec())