import os
import json
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def load_validation_rules(config_path):
    """Загружает правила валидации из JSON файла."""
    if not os.path.exists(config_path):
        print(f"❌ Файл правил не найден: {config_path}")
        print("💡 Создайте файл на основе примера и укажите путь в .env")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка JSON в файле правил: {e}")
        return None

def validate_value(key, value, rule):
    """Проверяет одно значение по правилу. Возвращает сообщение об ошибке или None."""
    rule_type = rule.get("type")
    
    if rule_type == "boolean":
        allowed = rule.get("values", ["да", "нет"])
        if value not in allowed:
            return f"Ожидается один из {allowed}, получено: '{value}'"
    
    elif rule_type == "positive":
        try:
            num_val = float(value) # Используем float для универсальности
            if num_val < 0:
                return f"Число не может быть отрицательным: {value}"
        except ValueError:
            return f"Не является числом: '{value}'"

    elif rule_type == "range":
        try:
            num_val = float(value)
            min_v = rule.get("min", 0)
            max_v = rule.get("max", 100)
            if not (min_v <= num_val <= max_v):
                return f"Число вне диапазона [{min_v}-{max_v}]: {value}"
        except ValueError:
            return f"Не является числом: '{value}'"
            
    return None

def validate_file(file_path, rules, show_unknown=False):
    """Проверяет файл на соответствие правилам."""
    errors_found = False
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if "::" not in line:
                    continue

                parts = line.split("::", 1)
                if len(parts) != 2:
                    continue
                
                raw_key, value = parts
                key = raw_key.replace("-", "").strip()
                value = value.strip()

                # Пропускаем дату и пустые значения
                if key == "Дата" or not value:
                    continue

                if key not in rules:
                    if show_unknown:
                        print(f"[WARN] Неизвестный параметр '{key}' в файле {os.path.basename(file_path)}")
                    continue

                rule = rules[key]
                error_msg = validate_value(key, value, rule)

                if error_msg:
                    print(f"❌ ОШИБКА в файле: {os.path.basename(file_path)}")
                    print(f"   Строка ~{line_num}: {key} :: {value}")
                    print(f"   Проблема: {error_msg}")
                    print("-" * 30)
                    errors_found = True
                    
    except Exception as e:
        print(f"⚠️ Не удалось прочитать файл {file_path}: {e}")

    return errors_found

def main():
    parser = argparse.ArgumentParser(description="Валидация статистики Obsidian")
    parser.add_argument("--unknown", action="store_true", help="Показывать предупреждения о неизвестных полях")
    args = parser.parse_args()

    # 1. Конфигурация путей
    vault_path_str = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path_str:
        print("❌ Ошибка: Не найдена переменная OBSIDIAN_VAULT_PATH в .env")
        return

    base_dir = Path(vault_path_str)
    daily_logs_relative = os.getenv("DAILY_LOGS_SUBFOLDER", "01. Ежедневное")
    target_dir = base_dir / daily_logs_relative
    
    rules_file_str = os.getenv("STATS_VALIDATION_RULES", "config/validation_rules.json")
    rules_path = Path(rules_file_str)

    if not target_dir.exists():
        print(f"❌ Папка логов не найдена: {target_dir}")
        return

    print(f"🔍 Начинаю проверку папки: {target_dir}")
    print(f"📜 Правила загружаются из: {rules_path}\n")

    # Загрузка правил
    rules = load_validation_rules(rules_path)
    if rules is None:
        return

    total_errors = 0
    files_checked = 0
    files_with_errors = 0

    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith(".md"):
                continue

            file_path = Path(root) / file
            files_checked += 1
            
            if validate_file(file_path, rules, show_unknown=args.unknown):
                files_with_errors += 1
                total_errors += 1 # Можно считать количество ошибок, а не файлов

    print("\n" + "="*30)
    if files_with_errors == 0:
        print("✅ Все данные валидны! Ошибок не найдено.")
    else:
        print(f"📊 Проверено файлов: {files_checked}")
        print(f"🔥 Найдено файлов с ошибками: {files_with_errors}")
        print("\n💡 Исправьте ошибки в заметках, чтобы аналитика была точной.")

if __name__ == "__main__":
    main()