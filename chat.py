import json
from html import escape
import sys

import ollama
from PyQt5.QtCore import QEvent, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

MODEL_NAME = "deepseek-r1:7b"


class ChatWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, chat_history):
        super().__init__()
        self.chat_history = chat_history.copy()

    def run(self):
        try:
            response = ollama.chat(model=MODEL_NAME, messages=self.chat_history)
            bot_response = response["message"]["content"]
            self.finished.emit(bot_response)
        except Exception as error:
            self.error.emit(str(error))


class ChatApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DeepSeek R1 Chat")
        self.resize(720, 780)
        self.setObjectName("mainWindow")

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(22, 22, 22, 22)
        self.layout.setSpacing(14)

        self.setStyleSheet("""
            QWidget#mainWindow {
                background-color: #111111;
                color: #f3f4f6;
            }

            QLabel#titleLabel {
                color: #ffffff;
                font-size: 25px;
                font-weight: 800;
            }

            QLabel#subtitleLabel {
                color: #a3a3a3;
                font-size: 13px;
            }

            QFrame#chatPanel {
                background-color: #1a1a1a;
                border: 1px solid #2f2f2f;
                border-radius: 18px;
            }

            QTextEdit#chatBox {
                background-color: transparent;
                color: #f3f4f6;
                border: none;
                padding: 16px;
                font-size: 15px;
                selection-background-color: #404040;
            }

            QLabel#statusLabel {
                color: #a3a3a3;
                font-size: 13px;
                padding-left: 4px;
            }

            QTextEdit#inputBox {
                background-color: #181818;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 16px;
                padding: 13px;
                font-size: 15px;
                selection-background-color: #404040;
            }

            QTextEdit#inputBox:focus {
                border: 1px solid #6b7280;
            }

            QPushButton#sendButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 14px;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#sendButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton#sendButton:pressed {
                background-color: #1e40af;
            }

            QPushButton#sendButton:disabled {
                background-color: #2f2f2f;
                color: #8a8a8a;
            }
        """)

        self.title_label = QLabel("DeepSeek R1 Chat")
        self.title_label.setObjectName("titleLabel")
        self.layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Local AI chat powered by Ollama")
        self.subtitle_label.setObjectName("subtitleLabel")
        self.layout.addWidget(self.subtitle_label)

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("chatPanel")
        self.chat_panel_layout = QVBoxLayout()
        self.chat_panel_layout.setContentsMargins(0, 0, 0, 0)

        self.chatbox = QTextEdit()
        self.chatbox.setObjectName("chatBox")
        self.chatbox.setReadOnly(True)
        self.chat_panel_layout.addWidget(self.chatbox)
        self.chat_panel.setLayout(self.chat_panel_layout)
        self.layout.addWidget(self.chat_panel)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.layout.addWidget(self.status_label)

        self.inputbox = QTextEdit()
        self.inputbox.setObjectName("inputBox")
        self.inputbox.setPlaceholderText("Type your message...  Shift + Enter for new line")
        self.inputbox.setFixedHeight(115)
        self.inputbox.installEventFilter(self)
        self.layout.addWidget(self.inputbox)

        self.send_button = QPushButton("Send Message")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        self.setLayout(self.layout)

        self.chat_history = self.load_chat_history()
        self.load_previous_messages()

    def eventFilter(self, obj, event):
        if obj == self.inputbox and event.type() == QEvent.KeyPress:
            if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
                if event.modifiers() == Qt.ShiftModifier:
                    return False
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def load_chat_history(self):
        try:
            with open("chat_history.json", "r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_chat_history(self):
        with open("chat_history.json", "w", encoding="utf-8") as file:
            json.dump(self.chat_history, file, indent=4, ensure_ascii=False)

    def load_previous_messages(self):
        for message in self.chat_history:
            if message["role"] == "user":
                self.display_message("You", message["content"], QColor("#f5f5f5"), align_right=True)
            else:
                self.display_message("DeepSeek", message["content"], QColor("#d4d4d4"), align_right=False)

    def send_message(self):
        user_input = self.inputbox.toPlainText().strip()
        if not user_input:
            return

        self.inputbox.clear()
        self.display_message("You", user_input, QColor("#f5f5f5"), align_right=True)

        self.chat_history.append({"role": "user", "content": user_input})
        self.save_chat_history()

        self.status_label.setText("DeepSeek is thinking...")
        self.send_button.setDisabled(True)
        self.inputbox.setDisabled(True)

        self.worker = ChatWorker(self.chat_history)
        self.worker.finished.connect(self.handle_response)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_response(self, bot_response):
        bot_response = self.clean_thoughts(bot_response)
        self.display_message("DeepSeek", bot_response, QColor("#d4d4d4"), align_right=False)

        self.chat_history.append({"role": "assistant", "content": bot_response})
        self.save_chat_history()

        self.reset_input_state()

    def handle_error(self, error_message):
        self.display_message("System", f"Error: {error_message}", QColor("#fca5a5"), align_right=False)
        self.reset_input_state()

    def reset_input_state(self):
        self.status_label.setText("")
        self.send_button.setDisabled(False)
        self.inputbox.setDisabled(False)
        self.inputbox.setFocus()

    def clean_thoughts(self, text):
        while "<think>" in text and "</think>" in text:
            start = text.find("<think>")
            end = text.find("</think>") + len("</think>")
            text = text[:start] + text[end:]
        return text.strip()

    def display_message(self, sender, message, text_color, align_right=False):
        cursor = self.chatbox.textCursor()
        cursor.movePosition(QTextCursor.End)

        safe_sender = escape(sender)
        safe_message = escape(message).replace("\n", "<br>")

        if align_right:
            bubble_color = "#242424"
            border_color = "#3a3a3a"
            sender_color = "#cfcfcf"
            text_color_hex = "#ffffff"
            outer_align = "right"
        else:
            bubble_color = "#181818"
            border_color = "#333333"
            sender_color = "#9ca3af"
            text_color_hex = "#d4d4d4"
            outer_align = "left"

        html = f'''
        <table width="100%" cellspacing="0" cellpadding="0" style="margin-top: 12px; margin-bottom: 12px;">
            <tr>
                <td align="{outer_align}">
                    <table width="82%" cellspacing="0" cellpadding="10" bgcolor="{bubble_color}" style="border: 1px solid {border_color}; border-radius: 12px;">
                        <tr>
                            <td>
                                <div style="color: {sender_color}; font-size: 13px; font-weight: bold; margin-bottom: 6px;">
                                    {safe_sender}
                                </div>
                                <div style="color: {text_color_hex}; font-size: 14px; line-height: 1.45;">
                                    {safe_message}
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        '''

        cursor.insertHtml(html)
        cursor.insertBlock()

        self.chatbox.setTextCursor(cursor)
        self.chatbox.ensureCursorVisible()


app = QApplication(sys.argv)
window = ChatApp()
window.show()
sys.exit(app.exec_())
