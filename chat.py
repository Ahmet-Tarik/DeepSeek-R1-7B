import sys
import ollama
import json
from PyQt5.QtWidgets import QApplication, QTextEdit, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor, QFont, QTextBlockFormat
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class ChatWorker(QThread):
    """DeepSeek API ile arka planda mesaj işleyen iş parçacığı"""
    finished = pyqtSignal(str)

    def __init__(self, chat_history):
        super().__init__()
        self.chat_history = chat_history

    def run(self):
        """DeepSeek'e mesaj gönder ve cevabı al"""
        response = ollama.chat(model="deepseek-r1", messages=self.chat_history)
        bot_response = response['message']['content']
        self.finished.emit(bot_response)

class ChatApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DeepSeek Chat")
        self.resize(500, 600)
        self.layout = QVBoxLayout()
        self.setStyleSheet("""
            background-color: #282828; 
            color: white; 
            padding: 10px;
        """)

        # Chat ekranı
        self.chatbox = QTextEdit()
        self.chatbox.setReadOnly(True)
        self.chatbox.setStyleSheet("""
            background-color: #3a3a3a;
            color: white;
            font-size: 16px;
            padding: 10px;
            border-radius: 5px;
            border: none;
        """)
        self.layout.addWidget(self.chatbox)

        # Kullanıcı giriş alanı
        self.inputbox = QTextEdit()
        self.inputbox.setStyleSheet("""
            background-color: #505050;
            color: white;
            font-size: 16px;
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #606060;
        """)
        self.inputbox.installEventFilter(self)
        self.layout.addWidget(self.inputbox)

        # Gönder butonu
        self.send_button = QPushButton("➤ Send")
        self.send_button.setStyleSheet("""
            background-color: #0078D7;
            color: white;
            font-size: 18px;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        """)
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        self.setLayout(self.layout)

        # Hafıza yönetimi
        self.chat_history = self.load_chat_history()
        self.user_name = self.load_user_name()
        self.think_button = None
        self.think_content = ""
        self.think_visible = False

    def eventFilter(self, obj, event):
        if obj == self.inputbox and event.type() == event.KeyPress:
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
        except FileNotFoundError:
            return []

    def load_user_name(self):
        try:
            with open("user_name.json", "r", encoding="utf-8") as file:
                return json.load(file).get("name", None)
        except FileNotFoundError:
            return None

    def send_message(self):
        user_input = self.inputbox.toPlainText().strip()
        if not user_input:
            return

        self.inputbox.clear()
        self.display_message("You", user_input, QColor("white"), align_right=True)
        self.display_message("DeepSeek 🤖", "AI is thinking...", QColor("#FFD700"), align_right=False)
        self.chat_history.append({"role": "user", "content": user_input})

        self.worker = ChatWorker(self.chat_history)
        self.worker.finished.connect(self.handle_response)
        self.worker.start()

    def handle_response(self, bot_response):
        self.chatbox.setText(self.chatbox.toPlainText().replace("AI is thinking...\n", ""))

        if "<think>" in bot_response and "</think>" in bot_response:
            think_start = bot_response.find("<think>") + 7
            think_end = bot_response.find("</think>")
            self.think_content = bot_response[think_start:think_end].strip()
            bot_response = bot_response[:think_start-7] + bot_response[think_end+8:].strip()

            if self.think_button:
                self.layout.removeWidget(self.think_button)
                self.think_button.deleteLater()
                self.think_button = None

            self.think_button = QPushButton("Show Thought 🤔")
            self.think_button.setStyleSheet("""
                background-color: #444444;
                color: white;
                font-size: 14px;
                padding: 5px;
                border-radius: 5px;
            """)
            self.think_button.clicked.connect(self.toggle_think)
            self.layout.addWidget(self.think_button)

        self.display_message("DeepSeek 🤖", bot_response, QColor("#AAAAAA"), align_right=False)
        self.chat_history.append({"role": "assistant", "content": bot_response})

    def toggle_think(self):
        if self.think_visible:
            self.think_visible = False
            self.think_button.setText("Show Thought 🤔")
            self.chatbox.setText(self.chatbox.toPlainText().replace(f"🤖 DeepSeek's Thought:\n🧠 {self.think_content}\n", "").strip())
        else:
            self.think_visible = True
            self.think_button.setText("Hide Thought 🔽")
            self.display_message("🤖 DeepSeek's Thought", f"🧠 {self.think_content}", QColor("#888888"), align_right=False)

    def display_message(self, sender, message, text_color, align_right=False):
        cursor = self.chatbox.textCursor()
        cursor.movePosition(QTextCursor.End)

        format = QTextCharFormat()
        format.setForeground(text_color)
        format.setFontPointSize(14)
        format.setFont(QFont("Arial", 14))

        block_format = QTextBlockFormat()
        block_format.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        cursor.mergeBlockFormat(block_format)

        cursor.insertText(f"{sender}: ", format)
        format.setForeground(QColor("white"))
        cursor.insertText(f"{message}\n\n", format)

        self.chatbox.setTextCursor(cursor)
        self.chatbox.ensureCursorVisible()

app = QApplication(sys.argv)
window = ChatApp()
window.show()
sys.exit(app.exec_())
