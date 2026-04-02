import json
import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


def progress_to_goal(completed, goal):
    """Считает % выполнения цели."""
    if goal == 0:
        return {"goal": goal, "progress_pct": 0.0, "completed": 0}
    ratio_pct = round(completed / goal * 100, 2)
    return {
        "goal": goal,
        "completed": completed,
        "progress_pct": ratio_pct
    }

def aggregate_data(data, rules, year_filter=None):
    result = {}
    num_days = 0
    field_values = defaultdict(list)

    for entry in data:
        entry_year = None
        if "дата" in entry:
            # Ожидаем формат ДД.ММ.ГГ
            date_parts = entry["дата"].split('.')
            if len(date_parts) == 3:
                entry_year = date_parts[-1] # Последние две цифры года
        
        # Фильтрация по году
        if year_filter:
            if entry_year != year_filter:
                continue
        
        # Если фильтр не задан или год совпал
        if "данные" in entry:
            for field, value in entry["данные"].items():
                field_values[field].append(value)
            num_days += 1

    if num_days == 0:
        print("⚠️ Нет данных для анализа за выбранный период.")
        return {"error": "No data found", "total_days": 0}

    # Агрегация по правилам
    for field, rule in rules.items():
        values = field_values.get(field, [])
        if not values:
            continue

        agg_type = rule.get("type")
        agg_methods = rule.get("agg", [])
        if isinstance(agg_methods, str):
            agg_methods = [agg_methods]

        field_result = {}

        try:
            if agg_type == "numeric":
                numeric_vals = [float(v) for v in values if v not in ['', None]]
                
                for method in agg_methods:
                    if method == "sum":
                        field_result["sum"] = sum(numeric_vals)
                    elif method == "mean":
                        field_result["mean"] = round(sum(numeric_vals) / len(numeric_vals), 2) if numeric_vals else 0
                    elif method == "max":
                        field_result["max"] = max(numeric_vals) if numeric_vals else 0
                    elif method == "min":
                        field_result["min"] = min(numeric_vals) if numeric_vals else 0
                    elif isinstance(method, dict) and "progress_to_goal" in method:
                        goal = method["progress_to_goal"]
                        total_sum = sum(numeric_vals)
                        field_result["progress_to_goal"] = progress_to_goal(total_sum, goal)

            elif agg_type == "ordinal":
                numeric_vals = [int(v) for v in values if v not in ['', None]]
                
                for method in agg_methods:
                    if method == "mean":
                        field_result["mean"] = round(sum(numeric_vals) / len(numeric_vals), 2) if numeric_vals else 0
                    elif method == "max":
                        field_result["max"] = max(numeric_vals) if numeric_vals else 0
                    elif method == "min":
                        field_result["min"] = min(numeric_vals) if numeric_vals else 0

            elif agg_type == "binary":
                count_days = len(values)
                yes_count = sum(1 for v in values if str(v).lower() in ("да", "yes", "1", "true"))

                for method in agg_methods:
                    if method == "count_yes":
                        field_result.update({
                            "total_records": count_days,
                            "days_yes": yes_count,
                            "days_no": count_days - yes_count,
                            "ratio_yes": round(yes_count / count_days, 2) if count_days > 0 else 0
                        })
                    elif isinstance(method, dict) and "progress_to_goal" in method:
                        goal = method["progress_to_goal"]
                        field_result["progress_to_goal"] = progress_to_goal(yes_count, goal)
            
            if field_result:
                result[field] = field_result
                
        except ValueError as e:
            print(f"⚠️ Ошибка обработки поля '{field}': возможно, данные не соответствуют типу '{agg_type}'. {e}")

    result["meta"] = {
        "total_days": num_days,
        "year_filter": year_filter or "all"
    }
    
    return result

def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Анализ статистики Obsidian")
    parser.add_argument("--year", type=str, help="Год для анализа (например, 25, 26). По умолчанию все годы.")
    parser.add_argument("--config", type=str, help="Путь к файлу конфигурации правил.")
    parser.add_argument("--input", type=str, help="Путь к входному JSON файлу со статистикой.")
    parser.add_argument("--output", type=str, help="Путь к выходному файлу.")
    args = parser.parse_args()

    # 1. Определение путей
    input_file_str = args.input or os.getenv("STATS_INPUT_FILE", ".data/stats_daily.json")
    output_file_str = args.output or os.getenv("STATS_ANALYSIS_OUTPUT", ".data/analysis_summary.json")
    config_file_str = args.config or os.getenv("STATS_RULES_FILE", "config/stats_rules.json")
    year_filter = args.year or os.getenv("DEFAULT_ANALYSIS_YEAR")

    input_path = Path(input_file_str)
    output_path = Path(output_file_str)
    config_path = Path(config_file_str)

    # Проверка существования файлов
    if not input_path.exists():
        print(f"❌ Ошибка: Входной файл '{input_path}' не найден. Запустите сначала сборщик статистики.")
        sys.exit(1)
    
    if not config_path.exists():
        print(f"❌ Ошибка: Файл конфигурации правил '{config_path}' не найден.")
        print("💡 Создайте файл на основе config/stats_rules.example.json")
        sys.exit(1)

    print(f"🔍 Загрузка данных из {input_path}...")
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        with open(config_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка JSON: {e}")
        sys.exit(1)

    print(f"📊 Анализ данных... {'за ' + year_filter if year_filter else 'за все время'}")
    analysis = aggregate_data(data, rules, year_filter=year_filter)

    # Сохранение результата
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Анализ завершён! Результат сохранён в: {output_path.resolve()}")
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()