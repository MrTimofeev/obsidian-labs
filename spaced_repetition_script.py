import os
import json
import random
from datetime import date, timedelta

"""
Это срипт для интервального повторения
Он выбирает все файлы из твоей базы в которых есть: 
#повторить
После этого он собирает эти файлы в json, который состоит из такой структуры:
[
    {
        file_name: "Название файла", # нужно для поиска файла
        date_for_repeat: "Дата для повторения", # Сравнивается с текущей, и если совпадает выдает чтобы ты прочитал
        number_of_repetitions: "количество повторений" # количество Coroutines VS Threads VS Processes.mdкоторое влияет на то, на сколько дата для повторения сдвинется
    }
]
И выдает файлы которые нужно повторить сегодня.
Если на текущую дату нет файлов для повторения, берет случайные 5 файлов.

После того как ты прочел что писал тебе предложиться отметить файлы и дать им оценку, как ты их помнишь, на основе оценки будет 
перерасчитываться дата следующего повторения

Это все нужно для того чтобы постоянно актуализировать информацию в своей памяти, и если что редактировать их данные в случает устаревания.
"""


class SRSManager:
    def __init__(self, flag=True):
        if flag:
            self.base_dir = "D:\\База Знаний\\pc\\Programming"
            self.reviews_file = os.path.join(
                "D:\\База Знаний\\pc\\Programming\\08. Повторение", "reviews.json")
            self.review_list_file = os.path.join(
                "D:\\База Знаний\\pc\\Programming\\08. Повторение", "Повторение.md")
        else:
            self.base_dir = "D:\\База Знаний\\pc\\Logs_of_my_Life"
            self.reviews_file = os.path.join(
                "D:\\База Знаний\\pc\\Logs_of_my_Life\\08. Повторение", "reviews.json")
            self.review_list_file = os.path.join(
                "D:\\База Знаний\\pc\\Logs_of_my_Life\\08. Повторение", "Повторение.md")
        self.today = date.today()
        self.notes = self.load_reviews()

    def load_reviews(self):
        """Загружает или создаёт reviews.json"""
        if not os.path.exists(self.reviews_file):
            print("🔄 Создаю новый reviews.json...")
            return []
        try:
            with open(self.reviews_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Ошибка чтения {self.reviews_file}: {e}")
            return []

    def save_reviews(self):
        """Сохраняет текущие данные в reviews.json"""
        with open(self.reviews_file, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)
        print(f"✅ Сохранено в {self.reviews_file}")

    def scan_for_new_notes(self):
        """Находит все .md с '#повторить', которых ещё нет в reviews.json"""
        existing_files = {note["file_name"] for note in self.notes}
        new_notes = []

        for root, dirs, files in os.walk(self.base_dir):
            if "05. Шаблоны" in root.split(os.sep):
                continue
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "#повторить" in content and file not in existing_files:
                                relative_path = os.path.relpath(
                                    file_path, self.base_dir)
                                new_notes.append({
                                    "file_name": file,
                                    "relative_path": relative_path,
                                    "date_for_repeat": str(self.today),
                                    "number_of_repetitions": 0
                                })
                                print(f"🆕 Новая заметка добавлена: {file}")
                    except Exception as e:
                        print(f"⚠️ Ошибка чтения {file}: {e}")

        if new_notes:
            self.notes.extend(new_notes)
            self.save_reviews()

    def sm2_evaluate(self, score, repetitions, interval_days):
        """Алгоритм SM-2 (Anki-style) — возвращает (новый_интервал, новые_повторения)"""
        if score == 0:  # Не помню — сброс
            return 0, 0
        elif score == 1:  # Трудно — 1 день
            return 1, repetitions + 1
        elif score == 2:  # Легко — растущий интервал
            if repetitions == 0:
                new_interval = 1
            elif repetitions == 1:
                new_interval = 6
            else:
                # Экспоненциальный рост
                new_interval = int(interval_days * 2.5)
            return new_interval, repetitions + 1

    def get_notes_for_today(self):
        """Возвращает список заметок на сегодня + случайные, если пусто"""
        today_notes = []
        future_notes = []

        for note in self.notes:
            repeat_date = date.fromisoformat(note["date_for_repeat"])
            if repeat_date <= self.today:
                today_notes.append(note)
            else:
                future_notes.append(note)

        # Если ничего на сегодня — выбираем 5 случайных
        if not today_notes and future_notes:
            print("📅 Сегодня нет запланированных заметок — выбираю 5 случайных...")
            random.shuffle(future_notes)
            today_notes = future_notes[:5]
            for n in today_notes:
                n["is_random"] = True

        return today_notes

    def generate_review_list(self, notes):
        """Генерирует файл Повторение.md с гиперссылками"""
        content = f"# 📅 Повторение на {self.today}\n\n"
        for note in notes:
            link = f"[[{note['file_name']}]]"
            reps = note["number_of_repetitions"]
            next_date = note["date_for_repeat"]
            status = " (случайная)" if note.get("is_random") else ""
            content += f"- {link}{status} · Повторений: {reps} · Следующий: {next_date}\n"

        with open(self.review_list_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 Создан/обновлён файл '{self.review_list_file}'")

    def run_daily_review(self):
        """Главный цикл"""
        print("🔍 Поиск новых заметок...")
        self.scan_for_new_notes()  # Добавляем новые

        print("\n=== 📌 ПОЛУЧЕНИЕ ЗАМЕТОК НА СЕГОДНЯ ===")
        today_notes = self.get_notes_for_today()

        if not today_notes:
            print("📭 Нет заметок для повторения сегодня.")
            return

        # ✅ ПЕРВЫЙ ШАГ: ГЕНЕРИРУЕМ ССЫЛКИ — ДО того, как спрашиваем оценку!
        self.generate_review_list(today_notes)

        # Выводим в консоль (для справки)
        for note in today_notes:
            status = "(случайная)" if note.get("is_random") else ""
            print(f"   • {note['file_name']} {status}")

        print("\n✨ Открой файл:")
        print(f"   {self.review_list_file}")
        print("   Прочитай заметки — затем вернись сюда и введи оценки.")

        # ✅ ВТОРОЙ ШАГ: ЗАПРОС ОЦЕНОК — ПОСЛЕ того, как ты прочитал
        print("\n👉 Введите оценку для каждой заметки (0=не помню, 1=трудно, 2=легко)")
        print("   Формат: 'имя_файла:оценка' (например: Важно.md:2)")
        print("   Нажми Enter, если ничего не менять.")

        updates = {}
        user_input = input("> ").strip()
        if user_input:
            for entry in user_input.split(","):
                if ":" in entry:
                    fname, score_str = entry.strip().split(":", 1)
                    try:
                        score = int(score_str.strip())
                        if score in [0, 1, 2]:
                            updates[fname] = score
                    except ValueError:
                        pass

        # Обновляем заметки
        for note in today_notes:
            if note["file_name"] in updates:
                score = updates[note["file_name"]]
                old_interval = note["number_of_repetitions"]
                new_interval_days, new_repetitions = self.sm2_evaluate(
                    score, old_interval, old_interval)

                next_date = self.today + timedelta(days=new_interval_days)
                note["date_for_repeat"] = str(next_date)
                note["number_of_repetitions"] = new_repetitions

                print(
                    f"   ✅ Обновлено: {note['file_name']} → следующее: {next_date} ({new_interval_days} дней)")

        # Сохраняем изменения
        self.save_reviews()

        print(f"\n🎉 Готово! Все обновления сохранены. До завтра!")


# ==========================
# 🚀 ЗАПУСК СИСТЕМЫ
# ==========================
if __name__ == "__main__":
    srs = SRSManager()
    srs.run_daily_review()
