import json
import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

def get_stats_from_vault():
    # 1. Получаем путь к базе знаний
    vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path_str:
        raise ValueError("Ошибка: Не найдена переменная OBSIDIAN_VAULT_PATH в .env")
    
    base_dir = Path(vault_path_str)
    
    # 2. Получаем относительный путь к папке логов
    daily_logs_relative = os.getenv("DAILY_LOGS_PATH", "01. Ежедневное")
    target_dir = base_dir / daily_logs_relative
    
    if not target_dir.exists():
        raise FileNotFoundError(f"Папка логов не найдена: {target_dir}")
    
    result = []
    file_processed = 0
    
    print(f"Сканирование папки: {target_dir}")

    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith(".md"):
                continue
            
            file_path = Path(root) / file
            file_processed += 1
            
            data_entry = {}
            date_val = None
            try: 
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "::" in line:
                            parts = line.split("::", 1)
                            if len(parts) == 2:
                                key = parts[0].replace('-', "").strip()
                                value = parts[1].strip()
                                
                                if key == "Дата":
                                    date_val = value
                                else:
                                    data_entry[key] = value
                                
                if date_val:
                    result.append({
                        "дата": date_val,
                        "данные": data_entry
                    })
            except Exception as e:
                print(f"Ошибка чтения файла {file}: {e}")
                    
    print(f"Обработано файлов: {file_processed}")
    print(f"Найдено записей с датой: {len(result)}")
    return result


def save_data_json():
    try:
        
        # Получаем данные
        data = get_stats_from_vault()
        
        output_filename = os.getenv("STATS_OUTPUT_FILE", "stats_daily.json")
        
        output_path = Path(output_filename)
        
        data_dir = Path(".data")
        data_dir.mkdir(exist_ok=True)
        output_path = data_dir / output_filename


        # Записываем данные в JSON файл
        with open("stats.json", "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        
        print(f"Данные сохранены в файл: {output_path.resolve()}")
    except Exception as e:
        print(f"Критическая ошибка при сохранении: {e}")
        
if __name__ == "__main__":
    save_data_json()