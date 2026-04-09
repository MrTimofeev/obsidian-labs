from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static, Button
from textual.binding import Binding

class SummaryScreen(Screen):
    """Экран с итогами сессии."""
    
    CSS_PATH = "../styles.tcss"

    BINDINGS = [
        Binding("enter", "go_to_menu", "В меню"),
        Binding("q", "quit_app", "Выход"),
    ]

    def __init__(self, results: list[dict]):
        super().__init__()
        self.results = results or []

    def compose(self):
        yield Header()
        with Container(id="menu-container"): # Используем тот же стиль контейнера
            yield Static("🏁 Сессия завершена!", classes="title")
            
            total = len(self.results)
            correct = sum(1 for r in self.results if r['correct'])
            percentage = int((correct / total * 100) if total > 0 else 0)
            
            # Формируем текст отчета
            report = f"""
Всего карточек: {total}
Верных ответов: {correct}
Точность: {percentage}%
            """
            yield Static(report, id="stats-content")
            
            yield Button("🏠 Вернуться в меню", id="btn-menu", variant="primary")
            
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-menu":
            self.app.switch_screen("main") 

    def action_go_to_menu(self):
        self.app.switch_screen("main")

    def action_quit_app(self):
        self.app.exit()