import os
import re
from datetime import datetime

# Укажите путь к папке с вашими ежедневными заметками
notes_folder = "/путь/к/вашей/папке"

# Регулярное выражение для поиска файлов вида DD.MM.YYYY.md
date_pattern = re.compile(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})\.md$')

def rename_daily_notes(folder_path, recursive=True):
    renamed = 0
    skipped = 0
    errors = 0

    def process_folder(current_folder):
        nonlocal renamed, skipped, errors
        try:
            for filename in os.listdir(current_folder):
                full_path = os.path.join(current_folder, filename)
                if os.path.isfile(full_path):
                    match = date_pattern.match(filename)
                    if match:
                        day, month, year = match.groups()
                        try:
                            # Приводим к целым числам и проверяем корректность даты
                            day = int(day)
                            month = int(month)
                            year = int(year)
                            # Создаём дату — это проверит, существует ли такая дата
                            date_obj = datetime(year, month, day)
                            # Формируем новое имя в формате YYYY-MM-DD.md
                            new_name = date_obj.strftime('%Y-%m-%d.md')
                            new_path = os.path.join(current_folder, new_name)
                            
                            if full_path == new_path:
                                skipped += 1
                                continue
                            
                            if os.path.exists(new_path):
                                print(f"⚠️  Пропущено (файл уже существует): {new_path}")
                                skipped += 1
                                continue
                            
                            os.rename(full_path, new_path)
                            print(f"✅ Переименовано: {filename} → {new_name}")
                            renamed += 1
                            
                        except ValueError as e:
                            print(f"❌ Некорректная дата в имени файла: {filename} — {e}")
                            errors += 1
                elif os.path.isdir(full_path) and recursive:
                    process_folder(full_path)
                    
        except Exception as e:
            print(f"Ошибка при обработке папки {current_folder}: {e}")

    process_folder(folder_path)
    
    print("\n=== Итог ===")
    print(f"Переименовано: {renamed}")
    print(f"Пропущено (уже в правильном формате или дубликат): {skipped}")
    print(f"Ошибок (некорректные даты): {errors}")

# Запуск
if __name__ == "__main__":
    if notes_folder == "/путь/к/вашей/папке":
        print("❌ Пожалуйста, укажите правильный путь к папке с заметками в переменной 'notes_folder'!")
    else:
        rename_daily_notes(notes_folder, recursive=True)