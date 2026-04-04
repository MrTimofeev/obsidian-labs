import json
import random
from datetime import date
from dotenv import load_dotenv
from core.utils import get_vault_path, get_data_dir
from core.parser import find_notes_by_tags
from core.sm2 import get_next_review_date

load_dotenv()

class SRSManager:
    def __init__(self):
        self.vault = get_vault_path("VAULT_CODING")
        self.data_dir = get_data_dir()
        self.reviews_file = self.data_dir / "reviews.json"
        self.review_list_file = self.data_dir / "Повторение.md"
        self.today = date.today()
        
        self.notes = self.load_reviews()

    def load_reviews(self):
        if not self.reviews_file.exists():
            return []
        try:
            with open(self.reviews_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_reviews(self):
        with open(self.reviews_file, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def scan_for_new_notes(self):
        """Ищет заметки с тегом #повторить"""
        existing_files = {note["file_name"] for note in self.notes}
        
        new_files = find_notes_by_tags(
            include_tags=["#повторить"],
            exclude_tags=["#архив", "#черновик"], 
            vault_path=self.vault
        )
        
        new_count = 0
        for file_path in new_files:
            if file_path.name not in existing_files:
                rel_path = file_path.relative_to(self.vault)
                self.notes.append({
                    "file_name": file_path.name,
                    "relative_path": str(rel_path),
                    "date_for_repeat": str(self.today),
                    "number_of_repetitions": 0,
                    "interval_days": 0,
                    "is_random": False
                })
                new_count += 1
        
        if new_count > 0:
            self.save_reviews()
            print(f"🆕 Найдено новых заметок: {new_count}")

    def run_daily_review(self):
        print("🔍 Поиск новых заметок...")
        self.scan_for_new_notes()

        today_notes = []
        future_notes = []
        
        for note in self.notes:
            try:
                d = date.fromisoformat(note["date_for_repeat"])
                if d <= self.today:
                    today_notes.append(note)
                else:
                    future_notes.append(note)
            except ValueError:
                today_notes.append(note) # Битая дата = пора повторять

        # Если пусто, берем 5 случайных
        if not today_notes and future_notes:
            print("📅 Нет запланированных, выбираю 5 случайных...")
            random.shuffle(future_notes)
            today_notes = future_notes[:5]
            for n in today_notes: n["is_random"] = True

        if not today_notes:
            print("📭 На сегодня всё чисто!")
            return

        # Генерация списка ссылок
        content = f"# 📅 Повторение на {self.today}\n\n"
        for note in today_notes:
            status = " (случайная)" if note.get("is_random") else ""
            content += f"- [[{note['file_name']}]]{status} (Повторений: {note['number_of_repetitions']})\n"
        
        with open(self.review_list_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"\n📄 Список создан: {self.review_list_file}")
        print("Прочитай заметки, затем вернись сюда.")

        # Запрос оценок
        print("\n👉 Введи оценки (Формат: 'ИмяФайла:Оценка', через запятую)")
        print("   0=Забыл, 1=Трудно, 2=Легко")
        user_input = input("> ").strip()

        updates = {}
        if user_input:
            for part in user_input.split(","):
                if ":" in part:
                    name, score_str = part.strip().split(":")
                    try:
                        updates[name.strip()] = int(score_str.strip())
                    except ValueError:
                        pass

        # Обновление дат через core.sm2
        for note in today_notes:
            if note["file_name"] in updates:
                quality = updates[note["file_name"]]
                sm2_quality = 0 if quality == 0 else (3 if quality == 1 else 5)
                
                last_interval = note.get("interval_days", 0)
                last_reps = note.get("number_of_repetitions", 0)
                
                next_date, new_interval, new_reps = get_next_review_date(
                    sm2_quality, last_interval, last_reps
                )
                
                note["date_for_repeat"] = str(next_date)
                note["interval_days"] = new_interval
                note["number_of_repetitions"] = new_reps
                note["is_random"] = False
                
                print(f"   ✅ {note['file_name']} -> след: {next_date}")

        self.save_reviews()
        print("\n🎉 Готово!")

if __name__ == "__main__":
    SRSManager().run_daily_review()