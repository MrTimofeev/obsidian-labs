from datetime import date

from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static
from textual.containers import Container, Horizontal
from textual.app import ComposeResult

from core.models import SrsCard, SrsReviewLog
from core.database import get_session
from core.sm2 import calculate_sm2_interval

from apps.repeter.screens.summary import SummaryScreen

class ReviewScreen(Screen):
    """Экран показа карточки."""

    BINDINGS = [
        Binding("space", "toggle_answer", "Показать ответ"),
        Binding("1", "rate_again", "1: Again"),
        Binding("2", "rate_hard", "2: Hard"),
        Binding("3", "rate_good", "3: Good"),
        Binding("4", "rate_easy", "4: Easy"),
        Binding("q", "quit_app", "Выход"),
    ]

    def __init__(self, cards_to_review: list[SrsCard]):
        super().__init__()
        self.cards = cards_to_review
        self.current_index = 0
        self.session = get_session()
        self.results = []  # Для статистики сессии

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="card-container"):
            yield Static(f"Карточка {self.current_index + 1} из {len(self.cards)}", id="counter")
            yield Static("", id="question-box")
            yield Static("", id="answer-box")
            with Horizontal(id="controls"):
                yield Static("[SPACE] Показать ответ | [1-4] Оценка | [Q] Выход", classes="hint")
        yield Footer()

    def on_mount(self) -> None:
        self.show_question()

    def show_question(self):
        if self.current_index >= len(self.cards):
        
            self.app.push_screen(SummaryScreen(self.results))
            return

        card = self.cards[self.current_index]
        self.query_one("#question-box", Static).update(str(card.question))
        self.query_one("#answer-box", Static).update("")
        self.query_one("#answer-box", Static).add_class("hidden")
        self.query_one("#counter", Static).update(
            f"Карточка {self.current_index + 1} из {len(self.cards)}")

    def action_toggle_answer(self):
        answer_box = self.query_one("#answer-box", Static)
        if answer_box.has_class("hidden"):
            card = self.cards[self.current_index]
            answer_box.update(str(card.answer))
            answer_box.remove_class("hidden")
        else:
            # Если ответ уже показан, переходим к оценке?
            # Или просто ждем нажатия цифр. Оставим как есть.
            pass

    def _rate_card(self, quality: int):
        """Обрабатывает оценку и переходит к следующей."""
        answer_box = self.query_one("#answer-box")
        if answer_box.has_class("hidden"):
            return  # Нельзя оценить, не увидев ответ

        card = self.cards[self.current_index]

        # 1. Сохраняем лог
        log = SrsReviewLog(
            card_hash=card.card_hash,
            review_date=date.today(),
            quality=quality,
            was_correct=(quality >= 3)
        )
        self.session.add(log)

        # 2. Обновляем параметры карточки (SM-2)
        new_interval, new_reps = calculate_sm2_interval(
            quality=quality,
            repetitions=card.repetitions,
            interval=card.interval
        )

        card.interval = new_interval
        card.repetitions = new_reps
        card.last_reviewed = date.today()

        self.session.commit()

        self.results.append({
            'question': card.question,
            'quality': quality,
            'correct': quality >= 3
        })

        # Переход к следующей
        self.current_index += 1
        self.show_question()

    def action_rate_again(self): self._rate_card(0)
    def action_rate_hard(self): self._rate_card(3)
    def action_rate_good(self): self._rate_card(4)
    def action_rate_easy(self): self._rate_card(5)

    def action_quit_app(self):
        self.session.close()
        self.app.exit()

    def on_unmount(self):
        self.session.close()
