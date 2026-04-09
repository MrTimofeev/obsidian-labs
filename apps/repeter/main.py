import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from textual.app import App
from core.database import init_db
from apps.repeter.screens.menu import MainMenu
from apps.repeter.screens.review import ReviewScreen
from apps.repeter.screens.summary import SummaryScreen

class SRSApp(App):
    """Главное приложение."""
    TITLE = "Obsidian SRS Repeter"
    
    SCREENS = {
        "main": MainMenu,
        "review": ReviewScreen,
        "summary": SummaryScreen,
    }

    def on_mount(self) -> None:
        init_db()
        self.push_screen("main")

if __name__ == "__main__":
    app = SRSApp()
    app.run()