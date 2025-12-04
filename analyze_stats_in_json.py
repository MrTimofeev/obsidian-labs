import json
from collections import defaultdict
from all_stats_in_json import save_data_json

"""
Скрипт который анализует статистику из базы зананий
Я спросил у ИИ как это можно сделать по проще, при этом с возможностью масштабирования и получил код ниже

Создали словарь-конфиг, где для каждого поля укажем:
 - тип (numeric, binary, ordinal, categorical)
 - как агрегировать (mean, sum, count_yes, max, min, и т.д.)
 
Типы: 
 - numeric — числа, можно считать сумму, среднее
 - ordinal — числовые оценки (1–10), но не для суммирования, а для среднего/макс/мин
 - binary — "да"/"нет", считаем сколько раз "да"

"""
def progress_to_goal(completed, goal):
    """
    Считает % выполнения цели по тренировка.
    goal: цель
    yes_count: количетво выполнений
    """
    ratio_pct = round(completed / goal * 100, 2)
    return {
        "goal": goal,
        "progress_pct": ratio_pct
    }
    

def aggregate_data(data, rules):
    # Инициализация результатов
    result = {}
    num_days = len(data)

    # Собираем все значения по полям
    field_values = defaultdict(list)
    for entry in data:
        for field, value in entry["данные"].items():
            field_values[field].append(value)

    # Агрегация по правилам
    for field, rule in rules.items():
        values = field_values.get(field, [])
        if not values:
            continue

        agg_type = rule["type"]
        agg_methods = rule["agg"]
        if isinstance(agg_methods, str):
            agg_methods = [agg_methods]

        field_result = {}

        if agg_type == "numeric":
            try:
                numeric_vals = [float(v) for v in values]
            except ValueError:
                continue  # пропускаем, если не число

            for method in agg_methods:
                if method == "sum":
                    field_result["sum"] = sum(numeric_vals)
                elif method == "mean":
                    field_result["mean"] = round(sum(numeric_vals) / len(numeric_vals), 2)
                elif method == "max":
                    field_result["max"] = max(numeric_vals)
                elif method == "min":
                    field_result["min"] = min(numeric_vals)
                elif isinstance(method, dict) and "progress_to_goal" in method:
                    goal = method["progress_to_goal"]
                    field_result["progress_to_goal"] = progress_to_goal(sum(numeric_vals), goal)

        elif agg_type == "ordinal":
            try:
                numeric_vals = [int(v) for v in values]
            except ValueError:
                continue

            for method in agg_methods:
                if method == "mean":
                    field_result["mean"] = round(sum(numeric_vals) / len(numeric_vals), 2)
                elif method == "max":
                    field_result["max"] = max(numeric_vals)
                elif method == "min":
                    field_result["min"] = min(numeric_vals)

        elif agg_type == "binary":
            count_days = len(values)
            yes_count = sum(1 for v in values if str(v).lower() in ("да"))
            
            for method in agg_methods:
                if method == "count_yes":
                    field_result.update({
                        "total_records": count_days,
                        "days_yes": yes_count,
                        "days_no": count_days - yes_count,
                        "ratio_yes": round(yes_count / num_days, 2) if num_days > 0 else 0
                    })
                elif isinstance(method, dict) and "progress_to_goal" in method:
                    goal = method["progress_to_goal"]
                    field_result["progress_to_goal"] = progress_to_goal(yes_count, goal)
                
                    

        if field_result:
            result[field] = field_result

    result["total_days"] = num_days
    return result


def main():
    # Совет: при проверке изменить значение переменной directory
    DIRECTORY_BASE = "D:\\База Знаний\\pc\\Logs_of_my_Life"
    DIRECTORY = "stats.json"
    OUTPUT_FILE = "analayz_stats.json"
    CONFIG_ANALYZE_FILE = "analyz_config.json"

    save_data_json(DIRECTORY_BASE)

    with open(DIRECTORY, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(CONFIG_ANALYZE_FILE, 'r', encoding="utf-8") as f:
        AGGREGATION_RULES = json.load(f)

    analysis = aggregate_data(data, AGGREGATION_RULES)

    # Сохраняем
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=4)

    print("✅ Анализ завершён. Результат в:", OUTPUT_FILE)
    print(json.dumps(analysis, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()