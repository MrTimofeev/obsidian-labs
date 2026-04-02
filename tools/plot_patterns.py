import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def calculate_max_streak(series, threshold=1):
    """Вычисляет максимальную серию подряд, где значение >= порога."""
    if series.empty or series.isna().all():
        return 0
    
    # Булева маска: True если условие выполнено
    mask = series >= threshold
    
    current_streak = 0
    max_streak = 0
    
    for val in mask:
        if val:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    return max_streak

def run_pattern_analysis():
    # 1. Конфигурация путей
    input_file_str = os.getenv("STATS_INPUT_FILE", ".data/stats_daily.json")
    output_image_str = os.getenv("ANALYTICS_PATTERNS_IMAGE", ".data/patterns_report.png")
    
    input_path = Path(input_file_str)
    output_path = Path(output_image_str)

    if not input_path.exists():
        print(f"❌ Ошибка: Файл '{input_path}' не найден.")
        return

    print("🔍 Поиск паттернов, серий и сравнение режимов...")

    # --- ЗАГРУЗКА ДАННЫХ ---
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data_source = json.load(f)
    except json.JSONDecodeError:
        print("❌ Ошибка: Неверный формат JSON.")
        return

    if not data_source:
        print("⚠️ Файл пуст.")
        return

    # Парсинг
    flat_data = []
    for entry in data_source:
        row = {"date_str": entry.get("дата", entry.get("date"))}
        if "данные" in entry:
            row.update(entry["данные"])
        flat_data.append(row)

    df = pd.DataFrame(flat_data)
    
    if df.empty or 'date_str' not in df.columns:
        print("❌ Нет данных или даты.")
        return

    # Парсинг даты с обработкой ошибок
    df['date_obj'] = pd.to_datetime(df['date_str'], format='%d.%m.%y', errors='coerce')
    if df['date_obj'].isna().all():
        # Пробуем автоматический формат если стандартный не подошел
        df['date_obj'] = pd.to_datetime(df['date_str'], errors='coerce')
        
    df = df.dropna(subset=['date_obj'])
    df = df.sort_values('date_obj').reset_index(drop=True)
    
    if df.empty:
        print("❌ Не удалось распарсить ни одной даты.")
        return

    df['day_of_week'] = df['date_obj'].dt.day_name()
    df['is_weekend'] = df['day_of_week'].isin(['Saturday', 'Sunday'])
    df['week_num'] = df['date_obj'].dt.isocalendar().week
    df['weekday_num'] = df['date_obj'].dt.dayofweek

    # Маппинг числовых колонок
    numeric_map = {
        "Отжимания": "pushups",
        "Подтягивания": "pullups",
        "Приседания": "squats",
        "КоличествоСнаЧ": "sleep",
        "ВодаСтаканов": "water"
    }

    for orig, short in numeric_map.items():
        if orig in df.columns:
            df[short] = pd.to_numeric(df[orig], errors='coerce')

    # Маппинг привычек
    habit_map = {
        "Тренировка": "hab_workout",
        "Английский": "hab_english",
        "Бег": "hab_run",
        "ХолодныйДуш": "hab_cold"
    }

    for orig, short in habit_map.items():
        if orig in df.columns:
            df[short] = df[orig].map(lambda x: 1 if str(x).lower() == 'да' else 0)

    # --- ВИЗУАЛИЗАЦИЯ ---
    fig, axs = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('🔥 Паттерны, Серии и Режимы', fontsize=18, fontweight='bold')
    plt.subplots_adjust(hspace=0.35, wspace=0.3)

    # === ГРАФИК 1: МАКСИМАЛЬНЫЕ СЕРИИ (STREAKS) ===
    ax1 = axs[0, 0]
    streaks_data = {}

    # Числовые серии (порог > 0)
    for short, label in zip(numeric_map.values(), numeric_map.keys()):
        if short in df.columns:
            streaks_data[label] = calculate_max_streak(df[short], threshold=1)

    # Привычки (порог == 1)
    for short, label in zip(habit_map.values(), habit_map.keys()):
        if short in df.columns:
            streaks_data[label] = calculate_max_streak(df[short], threshold=1)

    if streaks_data:
        sorted_streaks = dict(sorted(streaks_data.items(), key=lambda x: x[1], reverse=True)[:10])
        labels = list(sorted_streaks.keys())
        values = list(sorted_streaks.values())
        colors = ['#27ae60' if v >= 7 else '#f39c12' for v in values]

        bars = ax1.barh(labels, values, color=colors, edgecolor='black')
        ax1.set_title('🏆 Самые длинные серии подряд', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Дней подряд')
        ax1.grid(axis='x', alpha=0.3, linestyle='--')

        for bar, val in zip(bars, values):
            ax1.text(val + 0.2, bar.get_y() + bar.get_height()/2, str(val), va='center', fontsize=11, fontweight='bold')
    else:
        ax1.text(0.5, 0.5, 'Нет данных для анализа серий', ha='center', va='center')
        ax1.set_title('Серии')
        ax1.axis('off')
        sorted_streaks = {} # Для вывода в консоль

    # === ГРАФИК 2: БУДНИ ПРОТИВ ВЫХОДНЫХ ===
    ax2 = axs[0, 1]
    metrics_compare = ['sleep', 'pushups', 'squats', 'water']
    compare_labels = ['Сон', 'Отжимания', 'Приседания', 'Вода']
    
    # Фильтруем только те метрики, что есть в данных
    existing_metrics = [(m, l) for m, l in zip(metrics_compare, compare_labels) if m in df.columns]
    
    if existing_metrics:
        real_metrics, real_labels = zip(*existing_metrics)
        x = np.arange(len(real_metrics))
        width = 0.35
        
        means_weekday = [df[df['is_weekend'] == False][m].mean() for m in real_metrics]
        means_weekend = [df[df['is_weekend'] == True][m].mean() for m in real_metrics]

        ax2.bar(x - width/2, means_weekday, width, label='Будни', color='#3498db', edgecolor='black')
        ax2.bar(x + width/2, means_weekend, width, label='Выходные', color='#e74c3c', edgecolor='black')

        ax2.set_title('📅 Будни vs Выходные', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(real_labels, rotation=15)
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
    else:
        ax2.text(0.5, 0.5, 'Нет общих метрик\nдля сравнения', ha='center', va='center')
        ax2.set_title('Режимы')
        ax2.axis('off')

    # === ГРАФИК 3: ИДЕАЛЬНЫЕ ДНИ ===
    ax3 = axs[1, 0]
    
    # Динамическое построение условий для "Идеального дня"
    conditions = []
    if 'sleep' in df.columns: conditions.append(df['sleep'] >= 7)
    if 'pushups' in df.columns: conditions.append(df['pushups'] >= 20)
    if 'hab_workout' in df.columns: conditions.append(df['hab_workout'] == 1)
    
    if conditions:
        perfect_mask = np.logical_and.reduce(conditions)
        perfect_count = perfect_mask.sum()
        total = len(df)
        ordinary_count = total - perfect_count
        
        sizes = [perfect_count, ordinary_count]
        labels_pie = ['Идеальные дни', 'Обычные дни']
        colors_pie = ['#2ecc71', '#ecf0f1']
        
        if total > 0:
            ax3.pie(sizes, labels=labels_pie, autopct='%1.1f%%', startangle=90, colors=colors_pie, explode=(0.05, 0))
            ax3.set_title('🌟 Процент "Идеальных дней"', fontsize=14, fontweight='bold')
        else:
            ax3.text(0.5, 0.5, 'Нет данных', ha='center', va='center')
            ax3.axis('off')
    else:
        ax3.text(0.5, 0.5, 'Недостаточно критериев\nдля определения идеала', ha='center', va='center')
        ax3.set_title('Идеальные дни')
        ax3.axis('off')

    # === ГРАФИК 4: КАЛЕНДАРЬ АКТИВНОСТИ (GitHub Style) ===
    ax4 = axs[1, 1]
    
    # Определяем колонки активности
    activity_cols = ['pushups', 'squats', 'pullups']
    existing_act_cols = [c for c in activity_cols if c in df.columns]
    
    if existing_act_cols:
        df['total_activity'] = df[existing_act_cols].sum(axis=1)
        
        # Берем последние 12 недель с данными
        unique_weeks = sorted(df['week_num'].unique())
        last_weeks = unique_weeks[-12:] if len(unique_weeks) >= 12 else unique_weeks
        
        if last_weeks:
            df_recent = df[df['week_num'].isin(last_weeks)]
            
            pivot_cal = df_recent.pivot_table(
                values='total_activity', 
                index='weekday_num', 
                columns='week_num', 
                aggfunc='sum', 
                fill_value=0
            )
            
            # Реиндекс по дням недели (0-Пн ... 6-Вс)
            pivot_cal = pivot_cal.reindex([0,1,2,3,4,5,6], fill_value=0)
            
            im4 = ax4.imshow(pivot_cal.values, cmap='Greens', aspect='auto', interpolation='nearest')
            ax4.set_yticks(range(7))
            ax4.set_yticklabels(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'])
            ax4.set_xticks(range(len(last_weeks)))
            ax4.set_xticklabels([f'W{w}' for w in last_weeks], rotation=45, ha='right')
            ax4.set_title('📅 Активность (последние недели)', fontsize=14, fontweight='bold')
            
            plt.colorbar(im4, ax=ax4, shrink=0.8, label='Сумма повторений')
        else:
            ax4.text(0.5, 0.5, 'Нет данных о неделях', ha='center', va='center')
            ax4.set_title('Календарь')
            ax4.axis('off')
    else:
        ax4.text(0.5, 0.5, 'Нет данных об активности\n(отжимания/приседания)', ha='center', va='center')
        ax4.set_title('Календарь')
        ax4.axis('off')

    # --- СОХРАНЕНИЕ И ВЫВОД ---
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Анализ паттернов завершен! Отчет: {output_path.resolve()}")
        
        if sorted_streaks:
            print("\n--- 🏆 Ваши рекорды ---")
            for label, val in sorted_streaks.items():
                if val > 0:
                    print(f"Максимальная серия '{label}': {val} дн.")
        else:
            print("\n⚠️ Рекорды не найдены.")
            
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        import traceback
        traceback.print_exc()
    finally:
        plt.close()

if __name__ == "__main__":
    run_pattern_analysis()