import sys
import os
import json
import shutil
import calendar
from datetime import datetime, date
from io import StringIO
from contextlib import redirect_stdout

# --- IMPORTY ---
try:
    import google.generativeai as genai
    from bs4 import BeautifulSoup
    HAS_AI = True
except ImportError:
    HAS_AI = False

HAS_DATA = False 

from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize, QTimer, QDate, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette, QPainter, QLinearGradient
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QFileDialog, QInputDialog, QLabel, 
                             QStackedWidget, QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect)
from PyQt5.QtWebEngineWidgets import QWebEngineView

# --- MODERN UI ---
from qfluentwidgets import (FluentWindow, NavigationItemPosition, FluentIcon, 
                            SubtitleLabel, TitleLabel, BodyLabel, PrimaryPushButton, 
                            PushButton, LineEdit, TextEdit, CardWidget, SimpleCardWidget,
                            InfoBar, InfoBarPosition, ScrollArea, SearchLineEdit, 
                            setTheme, Theme, StrongBodyLabel, CaptionLabel, TransparentToolButton,
                            SegmentedWidget, MessageBox, ComboBox, IndeterminateProgressRing,
                            ProgressBar, CalendarPicker)

# --- KONFIGURACJA ---
APP_NAME = "Neuralka"
DATA_FILE = "study_data.json"
NOTES_DIR = "notes_library"

# Kolory - Enhanced palette
C_BG_MAIN = "#0f0f14"        # Deeper background
C_BG_CARD = "#1a1a24"        # Card background
C_BG_ELEVATED = "#232333"     # Elevated elements
C_ACCENT = "#6366f1"          # Indigo accent
C_ACCENT_LIGHT = "#818cf8"    # Light indigo
C_NEON_CYAN = "#22d3ee"       # Cyan for subjects
C_NEON_PURPLE = "#a78bfa"     # Purple accent
C_TEXT_MAIN = "#f8fafc"       
C_TEXT_SUB = "#cbd5e1"
C_TEXT_MUTED = "#94a3b8"
C_SUCCESS = "#10b981"
C_WARNING = "#f59e0b"

# --- WORKERS ---
class AIWorker(QThread):
    finished = pyqtSignal(str)
    def __init__(self, key, prompt, ctx=""): super().__init__(); self.key=key; self.prompt=prompt; self.ctx=ctx
    def run(self):
        if not HAS_AI: return self.finished.emit("Brak bibliotek AI")
        try:
            genai.configure(api_key=self.key)
            model = genai.GenerativeModel('gemini-flash-latest')
            resp = model.generate_content(f"CTX:{self.ctx[:10000]} TASK:{self.prompt}")
            self.finished.emit(resp.text)
        except Exception as e: self.finished.emit(str(e))

class HTMLGenWorker(QThread):
    finished = pyqtSignal(str, str)
    def __init__(self, key, content, title): super().__init__(); self.key=key; self.c=content; self.t=title
    def run(self):
        try:
            genai.configure(api_key=self.key)
            model = genai.GenerativeModel('gemini-flash-latest')
            prompt = (f"You are a strict teacher. Generate a HTML5 Exercise Sheet based on the text below.\n"
                      f"RULES:\n"
                      f"1. Do NOT summarize the text. I do not want notes.\n"
                      f"2. Create EXACTLY 3 distinct, practical problems/tasks (Zadanie 1, Zadanie 2, Zadanie 3).\n"
                      f"3. For each task, provide the correct solution/answer HIDDEN inside a <details> tag.\n"
                      f"4. The <summary> tag must display text: 'Kliknij, aby sprawdzić rozwiązanie'.\n"
                      f"5. Use strictly HTML tags. No markdown formatting (no ```html).\n"
                      f"6. Make sure the text color is contrastive (white/light gray) because background is dark.\n\n"
                      f"SOURCE TEXT: {self.c[:7000]}")
            resp = model.generate_content(prompt)
            clean = resp.text.replace("```html","").replace("```","").strip()
            clean_title = self.t.replace(".html", "")
            self.finished.emit(f"CWICZENIA_{clean_title}.html".replace(" ","_"), clean)
        except: pass

# --- ENHANCED UI COMPONENTS ---

class AnimatedCard(CardWidget):
    """Card with hover animation and shadow"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        self._default_style = ""
        self._hover_style = ""
        
    def enterEvent(self, event):
        super().enterEvent(event)
        # Subtle scale effect would need QPropertyAnimation with geometry
        
    def leaveEvent(self, event):
        super().leaveEvent(event)

class StatCard(AnimatedCard):
    def __init__(self, icon, title, value, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setStyleSheet(f"""
            CardWidget {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C_BG_CARD}, stop:1 {C_BG_ELEVATED});
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
            }}
            CardWidget:hover {{
                border: 1px solid {C_ACCENT}40;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C_BG_ELEVATED}, stop:1 {C_BG_CARD});
            }}
        """)
        
        h = QHBoxLayout(self)
        h.setContentsMargins(24, 20, 24, 20)
        h.setSpacing(18)
        
        # Icon with gradient background
        icon_container = QWidget()
        icon_container.setFixedSize(56, 56)
        icon_container.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C_ACCENT}, stop:1 {C_ACCENT_LIGHT});
                border-radius: 14px;
            }}
        """)
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        self.icon_lbl = QLabel()
        if isinstance(icon, FluentIcon):
            self.icon_lbl.setPixmap(icon.icon(color=QColor("white")).pixmap(28, 28))
        icon_layout.addWidget(self.icon_lbl)
        
        v = QVBoxLayout()
        v.setSpacing(4)
        v.setAlignment(Qt.AlignVCenter)
        
        self.val_lbl = QLabel(str(value), self)
        self.val_lbl.setStyleSheet(f"""
            font-size: 32px; 
            color: {C_TEXT_MAIN}; 
            font-weight: 900; 
            border: none; 
            background: transparent;
            letter-spacing: -1px;
        """)
        
        self.title_lbl = QLabel(title, self)
        self.title_lbl.setStyleSheet(f"""
            color: {C_TEXT_MUTED}; 
            font-size: 12px; 
            font-weight: 600; 
            text-transform: uppercase; 
            border: none; 
            background: transparent;
            letter-spacing: 0.5px;
        """)
        
        v.addWidget(self.val_lbl)
        v.addWidget(self.title_lbl)
        
        h.addWidget(icon_container)
        h.addLayout(v)
        h.addStretch()

    def set_value(self, val):
        self.val_lbl.setText(str(val))

class PomodoroCard(AnimatedCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(380, 460)
        self.setStyleSheet(f"""
            CardWidget {{ 
                background-color: {C_BG_CARD}; 
                border: 1px solid rgba(255, 255, 255, 0.05); 
                border-radius: 20px; 
            }}
        """)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.time_left = 25 * 60
        self.is_running = False
        
        l = QVBoxLayout(self)
        l.setContentsMargins(32, 32, 32, 32)
        l.setSpacing(24)
        
        header = QLabel("⏱️ Sesja Skupienia", self)
        header.setStyleSheet(f"color: {C_TEXT_MAIN}; font-size: 20px; font-weight: 700; background: transparent;")
        l.addWidget(header)
        
        # Circular progress container
        progress_container = QWidget()
        progress_container.setFixedSize(260, 260)
        pc_layout = QVBoxLayout(progress_container)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setAlignment(Qt.AlignCenter)
        
        self.lcd = QLabel("25:00", self)
        self.lcd.setAlignment(Qt.AlignCenter)
        self.lcd.setStyleSheet(f"""
            font-size: 72px; 
            font-weight: 800; 
            color: {C_ACCENT};
            background: transparent;
            letter-spacing: -2px;
        """)
        pc_layout.addWidget(self.lcd)
        
        l.addWidget(progress_container, 0, Qt.AlignCenter)
        
        self.prog = ProgressBar(self)
        self.prog.setRange(0, 25*60)
        self.prog.setValue(0)
        self.prog.setFixedHeight(6)
        self.prog.setStyleSheet(f"""
            ProgressBar {{
                background-color: {C_BG_ELEVATED};
                border-radius: 3px;
            }}
        """)
        l.addWidget(self.prog)
        
        l.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_start = PrimaryPushButton("Start", self)
        self.btn_start.setIcon(FluentIcon.PLAY)
        self.btn_start.setFixedHeight(48)
        self.btn_start.clicked.connect(self.toggle_timer)
        
        self.btn_reset = PushButton("Reset", self)
        self.btn_reset.setIcon(FluentIcon.SYNC)
        self.btn_reset.setFixedHeight(48)
        self.btn_reset.clicked.connect(self.reset_timer)
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_reset)
        l.addLayout(btn_layout)

    def toggle_timer(self):
        if self.is_running:
            self.timer.stop()
            self.btn_start.setText("Start")
            self.btn_start.setIcon(FluentIcon.PLAY)
            self.is_running = False
        else:
            self.timer.start(1000)
            self.btn_start.setText("Pauza")
            self.btn_start.setIcon(FluentIcon.PAUSE)
            self.is_running = True

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.time_left = 25 * 60
        self.update_display()
        self.btn_start.setText("Start")
        self.btn_start.setIcon(FluentIcon.PLAY)
        self.prog.setValue(0)

    def update_timer(self):
        self.time_left -= 1
        self.update_display()
        elapsed = (25*60) - self.time_left
        self.prog.setValue(elapsed)
        
        if self.time_left <= 0:
            self.reset_timer()
            InfoBar.success("Koniec!", "Dobra robota! Czas na przerwę.", parent=self.window())

    def update_display(self):
        m = self.time_left // 60
        s = self.time_left % 60
        self.lcd.setText(f"{m:02d}:{s:02d}")

class InteractiveCalendar(AnimatedCard):
    def __init__(self, parent_app, parent=None):
        super().__init__(parent)
        self.parent_app = parent_app
        self.setFixedSize(520, 460)
        self.setObjectName("CalendarCard")
        self.setStyleSheet(f"""
            CardWidget {{ 
                background-color: {C_BG_CARD}; 
                border: 1px solid rgba(255, 255, 255, 0.05); 
                border-radius: 20px; 
            }}
            QPushButton#DayBtn {{ 
                background: transparent; 
                border-radius: 8px; 
                color: {C_TEXT_SUB}; 
                font-weight: 600; 
                font-size: 14px;
            }}
            QPushButton#DayBtn:hover {{ 
                background-color: {C_BG_ELEVATED}; 
                color: {C_TEXT_MAIN};
            }}
            QPushButton#DayBtn[hasNote="true"] {{ 
                background-color: {C_ACCENT}20;
                border: 2px solid {C_ACCENT}; 
                color: {C_ACCENT};
            }}
            QPushButton#DayBtn[isToday="true"] {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C_ACCENT}, stop:1 {C_ACCENT_LIGHT});
                color: white;
                font-weight: 800;
            }}
            QLabel {{ background: transparent; color: {C_TEXT_MAIN}; }}
        """)
        
        self.current_date = date.today()
        self.displayed_date = self.current_date
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header = QHBoxLayout()
        self.lbl_month = QLabel()
        self.lbl_month.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C_TEXT_MAIN};")
        
        btn_prev = TransparentToolButton(FluentIcon.LEFT_ARROW, self)
        btn_prev.clicked.connect(self.prev_month)
        
        btn_next = TransparentToolButton(FluentIcon.RIGHT_ARROW, self)
        btn_next.clicked.connect(self.next_month)
        
        header.addWidget(self.lbl_month)
        header.addStretch()
        header.addWidget(btn_prev)
        header.addWidget(btn_next)
        
        layout.addLayout(header)
        
        days_layout = QHBoxLayout()
        for d in ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]:
            l = QLabel(d)
            l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;")
            days_layout.addWidget(l)
        layout.addLayout(days_layout)
        
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        layout.addLayout(self.grid)
        
        self.refresh_calendar()

    def refresh_calendar(self):
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)
            
        month_names = ["", "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", 
                       "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
        self.lbl_month.setText(f"{month_names[self.displayed_date.month]} {self.displayed_date.year}")
        
        cal = calendar.monthcalendar(self.displayed_date.year, self.displayed_date.month)
        calendar_notes = self.parent_app.data.get("calendar_notes", {})
        
        for row, week in enumerate(cal):
            for col, day in enumerate(week):
                if day != 0:
                    btn = QPushButton(str(day))
                    btn.setObjectName("DayBtn")
                    btn.setFixedSize(48, 48)
                    btn.setCursor(Qt.PointingHandCursor)
                    
                    is_today = (day == self.current_date.day and 
                                self.displayed_date.month == self.current_date.month and 
                                self.displayed_date.year == self.current_date.year)
                    btn.setProperty("isToday", is_today)
                    
                    note_key = f"{self.displayed_date.year}-{self.displayed_date.month:02d}-{day:02d}"
                    has_note = note_key in calendar_notes
                    btn.setProperty("hasNote", has_note)
                    if has_note:
                        btn.setToolTip(f"📝 {calendar_notes[note_key]}")
                    
                    btn.clicked.connect(lambda _, d=day: self.on_day_clicked(d))
                    
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)
                    
                    self.grid.addWidget(btn, row, col)

    def prev_month(self):
        month = self.displayed_date.month - 1
        year = self.displayed_date.year
        if month == 0:
            month = 12
            year -= 1
        self.displayed_date = date(year, month, 1)
        self.refresh_calendar()

    def next_month(self):
        month = self.displayed_date.month + 1
        year = self.displayed_date.year
        if month == 13:
            month = 1
            year += 1
        self.displayed_date = date(year, month, 1)
        self.refresh_calendar()

    def on_day_clicked(self, day):
        note_key = f"{self.displayed_date.year}-{self.displayed_date.month:02d}-{day:02d}"
        notes = self.parent_app.data.get("calendar_notes", {})
        current_note = notes.get(note_key, "")
        
        text, ok = QInputDialog.getText(self, f"Notatka: {day}/{self.displayed_date.month}", 
                                      "Wpisz wydarzenie/zadanie:", text=current_note)
        if ok:
            if "calendar_notes" not in self.parent_app.data:
                self.parent_app.data["calendar_notes"] = {}
                
            if text.strip():
                self.parent_app.data["calendar_notes"][note_key] = text
            else:
                if note_key in self.parent_app.data["calendar_notes"]:
                    del self.parent_app.data["calendar_notes"][note_key]
            
            self.parent_app.save_data()
            self.refresh_calendar()

class NoteListItem(AnimatedCard):
    note_clicked = pyqtSignal(str, str, str)
    delete_clicked = pyqtSignal(str, str, str)
    
    def __init__(self, name, subj, path, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setCursor(Qt.PointingHandCursor)
        self.path = path; self.subj = subj; self.name = name
        
        self.setStyleSheet(f"""
            CardWidget {{ 
                background-color: {C_BG_CARD}; 
                border: 1px solid rgba(255, 255, 255, 0.05); 
                border-radius: 12px; 
            }}
            CardWidget:hover {{ 
                background-color: {C_BG_ELEVATED}; 
                border: 1px solid {C_ACCENT}40; 
                transform: translateY(-2px);
            }}
        """)
        
        l = QHBoxLayout(self)
        l.setContentsMargins(24, 16, 24, 16)
        l.setSpacing(20)
        
        icn_char = "📝"
        if "fiz" in subj.lower(): icn_char = "⚛️"
        elif "mat" in subj.lower(): icn_char = "📐"
        elif "py" in subj.lower(): icn_char = "🐍"
        elif "sys" in subj.lower() or "os" in subj.lower() or "linux" in subj.lower(): icn_char = "🐧"
        elif "prog" in subj.lower() or "dev" in subj.lower() or "cpp" in subj.lower() or "java" in subj.lower(): icn_char = "🚀"
        elif "baz" in subj.lower() or "sql" in subj.lower() or "data" in subj.lower(): icn_char = "🗄️"
        elif "siec" in subj.lower() or "net" in subj.lower(): icn_char = "🌐"
        elif "machine" in subj.lower() or "learn" in subj.lower() or "ai" in subj.lower(): icn_char = "🧠"
        
        if "CWICZENIA" in name: icn_char = "🏋️"
        
        # Icon with background
        icon_container = QWidget()
        icon_container.setFixedSize(56, 56)
        icon_container.setStyleSheet(f"""
            QWidget {{
                background-color: {C_BG_ELEVATED};
                border-radius: 12px;
            }}
        """)
        
        ic_layout = QVBoxLayout(icon_container)
        ic_layout.setContentsMargins(0, 0, 0, 0)
        ic_layout.setAlignment(Qt.AlignCenter)
        
        lbl_icn = QLabel(icn_char)
        lbl_icn.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        ic_layout.addWidget(lbl_icn)
        
        txt_lay = QVBoxLayout()
        txt_lay.setAlignment(Qt.AlignVCenter)
        txt_lay.setSpacing(6)
        
        display_name = name.replace("CWICZENIA_", "Ćw: ").replace(".html", "")
        t = QLabel(display_name, self)
        t.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {C_TEXT_MAIN}; background: transparent; border: none;")
        
        s = QLabel(subj.upper(), self)
        s.setStyleSheet(f"color: {C_NEON_CYAN}; font-weight: 700; font-size: 11px; letter-spacing: 1px; background: transparent; border: none;")
        
        txt_lay.addWidget(t)
        txt_lay.addWidget(s)
        
        btn_del = TransparentToolButton(FluentIcon.DELETE, self)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("background: transparent; border: none;")
        btn_del.clicked.connect(self._emit_delete)
        
        arrow = QLabel("›")
        arrow.setStyleSheet(f"font-size: 28px; color: {C_ACCENT}; font-weight: 300; background: transparent; border: none;")
        
        l.addWidget(icon_container)
        l.addLayout(txt_lay, 1)
        l.addWidget(btn_del)
        l.addSpacing(10)
        l.addWidget(arrow)

    def mouseReleaseEvent(self, e):
        if not self.childAt(e.pos()) or not isinstance(self.childAt(e.pos()), TransparentToolButton):
            super().mouseReleaseEvent(e)
            self.note_clicked.emit(self.path, self.subj, self.name)

    def _emit_delete(self):
        self.delete_clicked.emit(self.path, self.subj, self.name)

# --- ZAKŁADKI ---

class DashboardInterface(ScrollArea):
    def __init__(self, parent_app):
        super().__init__()
        self.view = QWidget()
        self.view.setObjectName("DashboardView")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.parent_app = parent_app
        self.setObjectName("Dashboard")
        
        self.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} QWidget#DashboardView {{ background-color: {C_BG_MAIN}; }}")
        
        l = QVBoxLayout(self.view)
        l.setContentsMargins(48, 48, 48, 48)
        l.setSpacing(40)
        
        # Enhanced Banner with gradient
        self.banner = CardWidget(self)
        self.banner.setFixedHeight(180)
        self.banner.setStyleSheet(f"""
            CardWidget {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C_ACCENT}, stop:0.5 {C_ACCENT_LIGHT}, stop:1 {C_NEON_PURPLE});
                border: none; 
                border-radius: 20px; 
            }}
        """)
        
        # Add subtle shadow
        banner_shadow = QGraphicsDropShadowEffect(self.banner)
        banner_shadow.setBlurRadius(30)
        banner_shadow.setColor(QColor(99, 102, 241, 100))
        banner_shadow.setOffset(0, 8)
        self.banner.setGraphicsEffect(banner_shadow)
        
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(48, 0, 48, 0)
        
        cap_icon = FluentIcon.EDUCATION.icon(color=QColor("white"))
        img_lbl = QLabel()
        img_lbl.setPixmap(cap_icon.pixmap(72, 72))
        img_lbl.setStyleSheet("background: transparent; border: none;")
        
        txt = QVBoxLayout(); txt.setAlignment(Qt.AlignVCenter); txt.setSpacing(8)
        w = QLabel("Witaj Inżynierze!", self.banner)
        w.setStyleSheet("color: white; font-size: 36px; font-weight: 900; background: transparent; border: none; letter-spacing: -1px;")
        d = QLabel("Twoje Centrum Nauki jest gotowe. Otwórz notatki i zacznij działać.", self.banner)
        d.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-size: 16px; background: transparent; border: none; font-weight: 500;")
        txt.addWidget(w); txt.addWidget(d)
        
        bl.addWidget(img_lbl); bl.addSpacing(28); bl.addLayout(txt); bl.addStretch()
        l.addWidget(self.banner)
        
        # Enhanced Stats
        stats_lay = QHBoxLayout()
        stats_lay.setSpacing(24)
        
        self.stat_notes = StatCard(FluentIcon.LIBRARY, "Materiały", 0)
        self.stat_subjs = StatCard(FluentIcon.FOLDER, "Przedmioty", 0)
        self.stat_exer = StatCard(FluentIcon.EDIT, "Ćwiczenia", 0)
        
        stats_lay.addWidget(self.stat_notes)
        stats_lay.addWidget(self.stat_subjs)
        stats_lay.addWidget(self.stat_exer)
        l.addLayout(stats_lay)
        
        # Content with better spacing
        content = QHBoxLayout()
        content.setSpacing(32)
        
        list_con = QVBoxLayout()
        list_con.setSpacing(20)
        list_con.setAlignment(Qt.AlignTop) 
        
        st = QLabel("📅 Kalendarz", self)
        st.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C_TEXT_MAIN}; margin-bottom: 8px;")
        list_con.addWidget(st)
        
        self.calendar = InteractiveCalendar(self.parent_app)
        list_con.addWidget(self.calendar)
        
        chart_con = QVBoxLayout()
        chart_con.setAlignment(Qt.AlignTop)
        chart_con.setSpacing(20)
        
        pom_label = QLabel("⏱️ Produktywność", self)
        pom_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C_TEXT_MAIN}; margin-bottom: 8px;")
        chart_con.addWidget(pom_label)
        
        self.pomodoro = PomodoroCard()
        chart_con.addWidget(self.pomodoro)
        
        content.addLayout(list_con, 55)
        content.addLayout(chart_con, 45)
        l.addLayout(content)

    def refresh(self):
        data = self.parent_app.data.get("subjects", {})
        
        n_notes = 0
        n_exer = 0
        for s, notes in data.items():
            for n in notes:
                if "CWICZENIA_" in n: n_exer += 1
                else: n_notes += 1
                
        self.stat_notes.set_value(n_notes)
        self.stat_subjs.set_value(len(data))
        self.stat_exer.set_value(n_exer)
        
        self.calendar.refresh_calendar()

class NotesInterface(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.setObjectName("Notes")
        
        l = QVBoxLayout(self)
        l.setContentsMargins(48, 48, 48, 48)
        l.setSpacing(32)
        
        # Enhanced Header
        top_bar = QHBoxLayout()
        tl = TitleLabel("Biblioteka", self)
        tl.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {C_TEXT_MAIN}; letter-spacing: -1px;")
        
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("notes", "📚 Notatki")
        self.pivot.addItem("exercises", "🏋️ Ćwiczenia")
        self.pivot.setCurrentItem("notes")
        self.pivot.setFixedHeight(36) 
        self.pivot.setFixedWidth(240)
        self.pivot.currentItemChanged.connect(lambda k: self.refresh()) 
        
        top_bar.addWidget(tl)
        top_bar.addSpacing(40)
        top_bar.addWidget(self.pivot)
        top_bar.addStretch()
        
        self.search = SearchLineEdit(self)
        self.search.setPlaceholderText("🔍 Szukaj...")
        self.search.setFixedWidth(280)
        self.search.setFixedHeight(40)
        self.search.textChanged.connect(self.filter_list)
        
        btn_add = PrimaryPushButton("Importuj", self)
        btn_add.setIcon(FluentIcon.ADD)
        btn_add.setFixedHeight(40)
        btn_add.clicked.connect(self.parent_app.import_file)
        
        top_bar.addWidget(self.search)
        top_bar.addSpacing(12)
        top_bar.addWidget(btn_add)
        
        l.addLayout(top_bar)
        
        # Enhanced Generator Card
        self.gen_card = AnimatedCard()
        self.gen_card.setFixedHeight(100)
        self.gen_card.setStyleSheet(f"""
            CardWidget {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C_BG_CARD}, stop:1 {C_BG_ELEVATED});
                border: 1px solid rgba(255, 255, 255, 0.05); 
                border-radius: 16px; 
            }}
        """)
        gc_layout = QHBoxLayout(self.gen_card)
        gc_layout.setContentsMargins(28, 16, 28, 16)
        gc_layout.setSpacing(16)
        
        # Icon for generator
        gen_icon_container = QWidget()
        gen_icon_container.setFixedSize(56, 56)
        gen_icon_container.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C_NEON_PURPLE}, stop:1 {C_ACCENT_LIGHT});
                border-radius: 14px;
            }}
        """)
        
        gen_icon_layout = QVBoxLayout(gen_icon_container)
        gen_icon_layout.setContentsMargins(0, 0, 0, 0)
        gen_icon_layout.setAlignment(Qt.AlignCenter)
        
        gen_icon_lbl = QLabel("🤖")
        gen_icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        gen_icon_layout.addWidget(gen_icon_lbl)
        
        gen_text = QVBoxLayout()
        gen_text.setSpacing(4)
        
        gc_lbl = StrongBodyLabel("Generator Ćwiczeń", self.gen_card)
        gc_lbl.setStyleSheet(f"color: {C_TEXT_MAIN}; font-size: 16px; font-weight: 700;")
        
        gc_sub = CaptionLabel("Automatycznie twórz zadania z notatek", self.gen_card)
        gc_sub.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        
        gen_text.addWidget(gc_lbl)
        gen_text.addWidget(gc_sub)
        
        self.note_combo = ComboBox()
        self.note_combo.setPlaceholderText("Wybierz notatkę źródłową...")
        self.note_combo.setFixedWidth(320)
        self.note_combo.setFixedHeight(40)
        
        self.btn_gen = PrimaryPushButton("Generuj", self.gen_card)
        self.btn_gen.setIcon(FluentIcon.ROBOT)
        self.btn_gen.setFixedHeight(40)
        self.btn_gen.clicked.connect(self.start_generation)
        
        self.progress_ring = IndeterminateProgressRing(self.gen_card)
        self.progress_ring.setFixedSize(28, 28)
        self.progress_ring.setVisible(False)
        
        self.status_lbl = CaptionLabel("", self.gen_card)
        self.status_lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        
        gc_layout.addWidget(gen_icon_container)
        gc_layout.addLayout(gen_text)
        gc_layout.addSpacing(16)
        gc_layout.addWidget(self.note_combo)
        gc_layout.addSpacing(12)
        gc_layout.addWidget(self.btn_gen)
        gc_layout.addSpacing(12)
        gc_layout.addWidget(self.progress_ring)
        gc_layout.addWidget(self.status_lbl)
        gc_layout.addStretch()
        
        l.addWidget(self.gen_card)
        
        # Enhanced List
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.con = QWidget()
        self.con.setObjectName("NotesContainer")
        self.con.setStyleSheet(f"QWidget#NotesContainer {{ background-color: {C_BG_MAIN}; }}")
        self.notes_layout = QVBoxLayout(self.con)
        self.notes_layout.setSpacing(14)
        self.notes_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.con)
        l.addWidget(self.scroll)
        
    def populate_combo(self):
        self.note_combo.clear()
        data = self.parent_app.data.get("subjects", {})
        for s, notes in data.items():
            for n, m in notes.items():
                if "CWICZENIA_" not in n: 
                    self.note_combo.addItem(f"{s}: {n}", userData=m["path"])

    def start_generation(self):
        if not self.note_combo.currentText():
            InfoBar.warning("Błąd", "Wybierz notatkę z listy!", parent=self)
            return
            
        path = self.note_combo.itemData(self.note_combo.currentIndex())
        name = self.note_combo.currentText().split(": ")[1]
        
        if not os.path.exists(path): return
        
        self.btn_gen.setDisabled(True)
        self.progress_ring.setVisible(True)
        self.progress_ring.start()
        self.status_lbl.setText("Analizuję i tworzę zadania...")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = BeautifulSoup(f.read(), "html.parser").get_text()
        except:
            content = ""
            
        key = self.parent_app.data.get("api_key")
        self.worker = HTMLGenWorker(key, content, name)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.start()
        
    def on_generation_finished(self, name, html):
        p = os.path.join(NOTES_DIR, name)
        with open(p, 'w', encoding='utf-8') as f: f.write(html)
        
        if "Inne" not in self.parent_app.data["subjects"]: self.parent_app.data["subjects"]["Inne"] = {}
        self.parent_app.data["subjects"]["Inne"][name] = {"path": p}
        self.parent_app.save_data()
        
        self.btn_gen.setDisabled(False)
        self.progress_ring.stop()
        self.progress_ring.setVisible(False)
        self.status_lbl.setText("")
        
        self.pivot.setCurrentItem("exercises")
        self.refresh()
        
        InfoBar.success("Gotowe!", "Ćwiczenia zostały wygenerowane.", parent=self)

    def refresh(self):
        self.populate_combo()
        
        for i in reversed(range(self.notes_layout.count())): 
            if self.notes_layout.itemAt(i).widget(): self.notes_layout.itemAt(i).widget().setParent(None)
            
        data = self.parent_app.data.get("subjects", {})
        show_exercises = (self.pivot.currentItem().text() == "🏋️ Ćwiczenia")
        
        found_any = False
        
        for s, notes in data.items():
            filtered_notes = {}
            for n, m in notes.items():
                is_exercise = "CWICZENIA_" in n
                if show_exercises and is_exercise:
                    filtered_notes[n] = m
                elif not show_exercises and not is_exercise:
                    filtered_notes[n] = m
            
            if not filtered_notes: continue
            
            found_any = True
            lbl = QLabel(s.upper(), self)
            lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; margin-top: 32px; margin-bottom: 12px; font-size: 13px; font-weight: 700; letter-spacing: 1.5px;")
            self.notes_layout.addWidget(lbl)
            
            for n, m in filtered_notes.items():
                item = NoteListItem(n, s, m["path"])
                item.note_clicked.connect(self.parent_app.open_note)
                item.delete_clicked.connect(self.parent_app.delete_note)
                self.notes_layout.addWidget(item)
        
        if not found_any:
            empty_container = QWidget()
            empty_container.setFixedHeight(200)
            empty_layout = QVBoxLayout(empty_container)
            empty_layout.setAlignment(Qt.AlignCenter)
            
            empty = QLabel("🗂️", self)
            empty.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 64px;")
            empty.setAlignment(Qt.AlignCenter)
            
            empty_text = QLabel("Brak elementów w tej sekcji", self)
            empty_text.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 16px; font-weight: 600;")
            empty_text.setAlignment(Qt.AlignCenter)
            
            empty_layout.addWidget(empty)
            empty_layout.addWidget(empty_text)
            
            self.notes_layout.addWidget(empty_container)
                
    def filter_list(self, txt):
        txt = txt.lower()
        for i in range(self.notes_layout.count()):
            w = self.notes_layout.itemAt(i).widget()
            if isinstance(w, NoteListItem):
                w.setVisible(txt in w.name.lower() or txt in w.subj.lower())

class ViewerInterface(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        l = QVBoxLayout(self)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)
        
        # Enhanced top bar
        bar = QFrame()
        bar.setStyleSheet(f"background: {C_BG_CARD}; border-bottom: 1px solid rgba(255, 255, 255, 0.05);")
        bar.setFixedHeight(72)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(32,0,32,0)
        
        btn_back = PushButton("← Wróć", self)
        btn_back.setIcon(FluentIcon.RETURN)
        btn_back.setFixedHeight(40)
        btn_back.clicked.connect(lambda: self.parent_app.switchTo(self.parent_app.notes_interface))
        
        self.lbl_title = QLabel("Podgląd", self)
        self.lbl_title.setStyleSheet(f"font-size: 20px; color: {C_TEXT_MAIN}; font-weight: 700;")
        
        bl.addWidget(btn_back); bl.addSpacing(24); bl.addWidget(self.lbl_title); bl.addStretch()
        l.addWidget(bar)
        
        self.web = QWebEngineView()
        self.web.page().setBackgroundColor(QColor(C_BG_MAIN))
        l.addWidget(self.web)
        
    def load(self, path, title):
        self.lbl_title.setText(title)
        self.web.setUrl(QUrl.fromLocalFile(os.path.abspath(path)))
        
        css = f"""
        * {{ color: {C_TEXT_MAIN} !important; }}
        body, html {{ 
            background-color: {C_BG_MAIN} !important; 
            font-family: 'Segoe UI', -apple-system, sans-serif !important;
            padding: 48px !important;
            max-width: 900px !important;
            margin: 0 auto !important;
            line-height: 1.7 !important;
        }}
        div, p, span, table, tr, td, th, section, article, aside, li, ul {{
            background-color: {C_BG_CARD} !important; 
            border-color: rgba(255, 255, 255, 0.05) !important;
        }}
        h1, h2, h3, h4 {{ 
            color: {C_ACCENT_LIGHT} !important; 
            background-color: transparent !important; 
            margin-top: 32px !important;
            margin-bottom: 16px !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px !important;
        }}
        h1 {{ font-size: 36px !important; }}
        h2 {{ font-size: 28px !important; }}
        h3 {{ font-size: 22px !important; }}
        a {{ color: {C_NEON_CYAN} !important; text-decoration: none !important; }}
        a:hover {{ text-decoration: underline !important; }}
        code, pre {{ 
            background-color: #000000 !important; 
            color: {C_SUCCESS} !important; 
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding: 2px 6px !important;
            border-radius: 6px !important;
            font-family: 'Consolas', monospace !important;
        }}
        pre {{ 
            padding: 16px !important; 
            margin: 16px 0 !important;
            overflow-x: auto !important;
        }}
        img {{ border-radius: 12px; opacity: 0.95; max-width: 100% !important; }}
        
        details {{
            background-color: {C_BG_ELEVATED} !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding: 20px !important;
            border-radius: 12px !important;
            margin-top: 20px !important;
        }}
        summary {{
            cursor: pointer !important;
            color: {C_ACCENT_LIGHT} !important;
            font-weight: 700 !important;
            outline: none !important;
            font-size: 16px !important;
            padding: 4px 0 !important;
        }}
        summary:hover {{
            color: {C_ACCENT} !important;
        }}
        table {{
            border-collapse: collapse !important;
            width: 100% !important;
            margin: 20px 0 !important;
        }}
        th, td {{
            padding: 12px !important;
            text-align: left !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        th {{
            background-color: {C_BG_ELEVATED} !important;
            font-weight: 700 !important;
        }}
        """
        js = f"var style = document.createElement('style'); style.innerHTML = `{css}`; document.head.appendChild(style);"
        self.web.loadFinished.connect(lambda: self.web.page().runJavaScript(js))

class AIInterface(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.setObjectName("AI")
        l = QVBoxLayout(self)
        l.setContentsMargins(48,48,48,48)
        l.setSpacing(32)
        
        # Header
        header = QHBoxLayout()
        tl = TitleLabel("AI Studio", self)
        tl.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {C_TEXT_MAIN}; letter-spacing: -1px;")
        
        subtitle = CaptionLabel("Zadawaj pytania o swoje notatki", self)
        subtitle.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 14px; margin-left: 4px;")
        
        header.addWidget(tl)
        header.addSpacing(16)
        header.addWidget(subtitle, 0, Qt.AlignBottom)
        header.addStretch()
        l.addLayout(header)
        
        chat_box = AnimatedCard()
        chat_box.setStyleSheet(f"""
            CardWidget {{ 
                background-color: {C_BG_CARD}; 
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 20px;
            }}
        """)
        cl = QVBoxLayout(chat_box); 
        cl.setContentsMargins(32,32,32,32)
        cl.setSpacing(20)
        
        st = QLabel("🤖 Asystent Notatek", self)
        st.setStyleSheet(f"color: {C_TEXT_MAIN}; font-size: 20px; font-weight: 700;")
        cl.addWidget(st)
        
        self.out = TextEdit()
        self.out.setReadOnly(True)
        self.out.setStyleSheet(f"""
            background: {C_BG_MAIN}; 
            border: 1px solid rgba(255, 255, 255, 0.05); 
            font-size: 15px; 
            padding: 20px; 
            border-radius: 12px; 
            color: {C_TEXT_MAIN};
            line-height: 1.6;
        """)
        
        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        
        self.inp = LineEdit()
        self.inp.setPlaceholderText("💬 Zapytaj o treść notatki...")
        self.inp.setFixedHeight(48)
        self.inp.setStyleSheet(f"""
            LineEdit {{
                font-size: 15px;
                padding: 0 16px;
            }}
        """)
        
        btn = PrimaryPushButton("Wyślij", self)
        btn.setIcon(FluentIcon.SEND)
        btn.setFixedHeight(48)
        btn.setFixedWidth(120)
        btn.clicked.connect(self.ask)
        
        input_row.addWidget(self.inp)
        input_row.addWidget(btn)
        
        cl.addWidget(self.out, 1)
        cl.addLayout(input_row)
        l.addWidget(chat_box)

    def ask(self):
        ctx = self.parent_app.get_current_text()
        if not ctx: return InfoBar.warning("Błąd", "Najpierw otwórz notatkę", parent=self)
        key = self.parent_app.data.get("api_key")
        if not key: return InfoBar.error("Błąd", "Brak klucza API", parent=self)
        
        self.worker = AIWorker(key, self.inp.text(), ctx)
        self.worker.finished.connect(lambda t: self.out.append(f"\n🤖 AI: {t}\n"))
        self.worker.start()
        self.out.append(f"👤 Ty: {self.inp.text()}")
        self.inp.clear()

class PythonInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Python")
        l = QVBoxLayout(self)
        l.setContentsMargins(48,48,48,48)
        l.setSpacing(32)
        
        header = QHBoxLayout()
        tl = TitleLabel("Python Playground", self)
        tl.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {C_TEXT_MAIN}; letter-spacing: -1px;")
        
        subtitle = CaptionLabel("🐍 Testuj kod w czasie rzeczywistym", self)
        subtitle.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 14px; margin-left: 4px;")
        
        header.addWidget(tl)
        header.addSpacing(16)
        header.addWidget(subtitle, 0, Qt.AlignBottom)
        header.addStretch()
        l.addLayout(header)
        
        code_label = QLabel("📝 Kod Źródłowy", self)
        code_label.setStyleSheet(f"color: {C_TEXT_SUB}; font-size: 14px; font-weight: 600;")
        l.addWidget(code_label)
        
        self.code = TextEdit()
        self.code.setPlainText("import math\nprint(f'Hello Inżynier! Pi={math.pi:.2f}')")
        self.code.setStyleSheet(f"""
            font-family: 'Consolas', 'Courier New', monospace; 
            font-size: 15px; 
            color: {C_TEXT_MAIN}; 
            background: {C_BG_CARD};
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 16px;
        """)
        
        btn_container = QHBoxLayout()
        btn = PrimaryPushButton("▶ Uruchom", self)
        btn.setIcon(FluentIcon.PLAY)
        btn.setFixedHeight(48)
        btn.setFixedWidth(160)
        btn.clicked.connect(self.run_code)
        btn_container.addWidget(btn)
        btn_container.addStretch()
        
        output_label = QLabel("📊 Wynik", self)
        output_label.setStyleSheet(f"color: {C_TEXT_SUB}; font-size: 14px; font-weight: 600; margin-top: 8px;")
        
        self.out = TextEdit()
        self.out.setReadOnly(True)
        self.out.setStyleSheet(f"""
            font-family: 'Consolas', 'Courier New', monospace; 
            color: {C_SUCCESS}; 
            background: #000000;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 16px;
            font-size: 14px;
        """)
        
        l.addWidget(self.code, 2)
        l.addLayout(btn_container)
        l.addWidget(output_label)
        l.addWidget(self.out, 1)

    def run_code(self):
        f = StringIO()
        try:
            with redirect_stdout(f): exec(self.code.toPlainText(), globals())
            self.out.setText(f.getvalue())
        except Exception as e: 
            self.out.setText(f"❌ Error: {str(e)}")

class SettingsInterface(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.setObjectName("Settings")
        l = QVBoxLayout(self)
        l.setContentsMargins(48,48,48,48)
        l.setSpacing(32)
        
        header = QHBoxLayout()
        tl = TitleLabel("Ustawienia", self)
        tl.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {C_TEXT_MAIN}; letter-spacing: -1px;")
        
        subtitle = CaptionLabel("⚙️ Konfiguracja aplikacji", self)
        subtitle.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 14px; margin-left: 4px;")
        
        header.addWidget(tl)
        header.addSpacing(16)
        header.addWidget(subtitle, 0, Qt.AlignBottom)
        header.addStretch()
        l.addLayout(header)
        
        card = AnimatedCard()
        card.setStyleSheet(f"""
            CardWidget {{ 
                background-color: {C_BG_CARD}; 
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
            }}
        """)
        cl = QVBoxLayout(card); 
        cl.setContentsMargins(32,32,32,32)
        cl.setSpacing(16)
        
        st = StrongBodyLabel("🔑 Klucz API Google Gemini", self)
        st.setStyleSheet(f"color: {C_TEXT_MAIN}; font-size: 16px; font-weight: 700;")
        cl.addWidget(st)
        
        desc = CaptionLabel("Wymagany do funkcji AI i generatora ćwiczeń", self)
        desc.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")
        cl.addWidget(desc)
        
        cl.addSpacing(8)
        
        self.inp = LineEdit()
        self.inp.setEchoMode(LineEdit.Password)
        self.inp.setFixedHeight(44)
        self.inp.setPlaceholderText("Wklej swój klucz API...")
        if "api_key" in parent_app.data: self.inp.setText(parent_app.data["api_key"])
        self.inp.textChanged.connect(self.save)
        
        cl.addWidget(self.inp)
        
        info = CaptionLabel("💡 Pobierz klucz z: https://makersuite.google.com/app/apikey", self)
        info.setStyleSheet(f"color: {C_NEON_CYAN}; font-size: 12px; margin-top: 8px;")
        cl.addWidget(info)
        
        l.addWidget(card)
        l.addStretch()
        self.parent_app = parent_app
        
    def save(self):
        self.parent_app.data["api_key"] = self.inp.text()
        self.parent_app.save_data()

# --- GŁÓWNE OKNO ---

class MainWindow(FluentWindow):
    def __init__(self):
        setTheme(Theme.DARK)
        super().__init__()
        self.setWindowTitle(f"🎓 {APP_NAME}")
        self.resize(1280, 900)
        
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {C_BG_MAIN}; }}
            QWidget {{ color: {C_TEXT_MAIN}; }}
        """)
        
        self.data = self.load_data()
        self.ensure_dirs()
        self.current_note_path = None
        
        self.dash_interface = DashboardInterface(self)
        self.notes_interface = NotesInterface(self)
        self.ai_interface = AIInterface(self)
        self.py_interface = PythonInterface()
        self.sett_interface = SettingsInterface(self)
        self.viewer_interface = ViewerInterface(self)
        
        self.addSubInterface(self.dash_interface, FluentIcon.HOME, "Pulpit")
        self.addSubInterface(self.notes_interface, FluentIcon.LIBRARY, "Notatki")
        self.addSubInterface(self.ai_interface, FluentIcon.ROBOT, "AI Studio") 
        self.addSubInterface(self.py_interface, FluentIcon.CODE, "Python")
        
        self.stackedWidget.addWidget(self.viewer_interface)
        
        self.addSubInterface(self.sett_interface, FluentIcon.SETTING, "Ustawienia", NavigationItemPosition.BOTTOM)
        
        self.dash_interface.refresh()
        self.notes_interface.refresh()

    def load_data(self):
        if os.path.exists(DATA_FILE): return json.load(open(DATA_FILE))
        return {"subjects": {}}

    def save_data(self): json.dump(self.data, open(DATA_FILE, 'w'), indent=4)
    def ensure_dirs(self): os.makedirs(NOTES_DIR, exist_ok=True)

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik")
        if not path: return
        
        subs = list(self.data["subjects"].keys())
        if not subs: subs = ["Ogólne"]
        item, ok = QInputDialog.getItem(self, "Przedmiot", "Wybierz:", subs, 0, True)
        if not ok or not item: return
        
        if item not in self.data["subjects"]: self.data["subjects"][item] = {}
        
        fname = os.path.basename(path)
        dest = os.path.join(NOTES_DIR, f"{item}_{fname}")
        shutil.copy2(path, dest)
        
        self.data["subjects"][item][fname] = {"path": dest}
        self.save_data()
        
        self.dash_interface.refresh()
        self.notes_interface.refresh()
        InfoBar.success("Sukces", "Notatka dodana", parent=self)
        
    def delete_note(self, path, subj, name):
        w = MessageBox("Usuń element", f"Czy na pewno chcesz usunąć: {name}?", self)
        if w.exec():
            if os.path.exists(path):
                os.remove(path)
            
            if subj in self.data["subjects"] and name in self.data["subjects"][subj]:
                del self.data["subjects"][subj][name]
                self.save_data()
            
            self.notes_interface.refresh()
            self.dash_interface.refresh()
            InfoBar.success("Usunięto", "Plik został pomyślnie usunięty", parent=self)

    def open_note(self, path, subj, name):
        self.current_note_path = path
        self.viewer_interface.load(path, name)
        self.stackedWidget.setCurrentWidget(self.viewer_interface)

    def get_current_text(self):
        if self.current_note_path:
            try: 
                with open(self.current_note_path, encoding='utf-8') as f:
                    return BeautifulSoup(f.read(), "html.parser").get_text()
            except: return None
        return None

    def gen_html(self):
        self.switchTo(self.notes_interface)
        InfoBar.info("Generator", "Użyj panelu generatora w zakładce Notatki", parent=self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())