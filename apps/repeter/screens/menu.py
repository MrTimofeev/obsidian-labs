from datetime import date

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, Button

from sqlalchemy.orm import Session
from core.database import get_session
from core.models import SrsCard
from apps.repeter.screens.review import ReviewScreen

class MainMenu(Screen):
    """Главное меню приложения."""
    CSS_PATH = "../styles.tcss"   

    BINDINGS = [
        Binding("q", "quit_app", "Выход"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="menu-container"):
            yield Static("🧠 Obsidian SRS Repeter", classes="title")
            yield Button("🔄 Начать повторение", id="btn-repeat", variant="primary")
            yield Button("📥 Синхронизировать базу", id="btn-sync")
            yield Static("", id="status-msg")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        session = get_session()
        try:
            if event.button.id == "btn-repeat":
                self.start_review(session)
            elif event.button.id == "btn-sync":
                self.do_sync(session)
        finally:
            session.close()

    def start_review(self, session: Session):
        today = date.today()
        cards = session.query(SrsCard).filter(
            SrsCard.is_archived == False,
            (SrsCard.last_reviewed == None) | (SrsCard.last_reviewed < today)
        ).order_by(SrsCard.last_reviewed.asc()).limit(50).all() # Лимит 50 за раз
        
        if not cards:
            self.query_one("#status-msg", Static).update("✅ На сегодня карточек нет!")
            return
            
        self.app.push_screen(ReviewScreen(cards))

    def do_sync(self, session: Session):
        self.query_one("#status-msg", Static).update("⏳ Синхронизация...")
        try:
            from core.srs_sync import sync_srs_cards
            from core.utils import get_vault_path
            
            vault = get_vault_path("VAULT_CODING")
            sync_srs_cards(session, vault)
            
            self.query_one("#status-msg", Static).update("✅ Синхронизация завершена!")
        except Exception as e:
            self.query_one("#status-msg", Static).update(f"❌ Ошибка: {str(e)}")

    def action_quit_app(self):
        self.app.exit()

