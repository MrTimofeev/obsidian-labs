import json
import os
from pathlib import Path
from dotenv import load_dotenv
from core.utils import get_vault_path, get_data_dir
from core.parser import parse_personal_note


load_dotenv()


def collect_daily_stats():
    print("Сбор статистики из ежедневных заметок")

    vault = get_vault_path("VAULT_PERSONAL")
    data_dir = get_data_dir()

    # Путь к папке ежедневных заметок
    daily_subfolder = os.getenv("DAILY_LOGS_SUBFOLDER", "01. Ежедневное")
    target_dir = vault / daily_subfolder

    if not target_dir.exists():
        print(f"Папка ежедневных заметок не найдена: {target_dir}")
        return

    all_data = []
    files_processed = 0

    print(f"Сканирование: {target_dir}")

    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith(".md"):
                continue

            file_path = Path(root) / file
            files_processed += 1

            try:
                content, metadata, entry_data = parse_personal_note(
                    file_path=file_path)

                date_val = metadata.get("Дата")

                if not date_val:
                    continue

                if entry_data:
                    all_data.append({
                        "дата": date_val,
                        "данные": entry_data
                    })

            except Exception as e:
                print(f" Ошибка чтения {file}: {e}")

    output_file = data_dir / "stats_daily.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    print(f"Готово! Обработано файлов: {files_processed}")
    print(f"Данные сохранены: {output_file}")
    print(f"Найдено записей: {len(all_data)}")


if __name__ == "__main__":
    collect_daily_stats()
