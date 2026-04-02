import matplotlib.pyplot as plt
import pandas as pd
import json
import os
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def run_analytics():
    # 1. Получаем пути из конфига
    input_file_str = os.getenv("STATS_INPUT_FILE", "stats.json")
    output_image_str = os.getenv("ANALYTICS_OUTPUT_IMAGE", "analysis_report.png")
    
    input_path = Path(input_file_str)
    output_path = Path(output_image_str)

    # Проверка входного файла
    if not input_path.exists():
        print(f"❌ Ошибка: Файл '{input_path}' не найден.")
        print("💡 Совет: Запустите сначала скрипт сбора статистики (stats_collector.py).")
        return

    print(f"🔍 Анализ данных из {input_path}...")

    # --- ЗАГРУЗКА И ПОДГОТОВКА ---
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data_source = json.load(f)
    except json.JSONDecodeError:
        print("❌ Ошибка: Файл поврежден или не является валидным JSON.")
        return

    if not data_source:
        print("⚠️ Файл пуст. Нечего анализировать.")
        return

    # Распаковка данных
    flat_data = []
    for entry in data_source:
        row = {"date_str": entry.get("дата")}
        if "данные" in entry:
            row.update(entry["данные"])
        flat_data.append(row)

    df = pd.DataFrame(flat_data)
    if df.empty:
        print("⚠️ Данные отсутствуют после обработки.")
        return

    # Маппинг колонок (Оригинал -> Короткое имя)
    numeric_cols_map = {
        "КоличествоСнаЧ": "sleep",
        "КачествоСна1_5": "sleep_quality",
        "Настроение1_10": "mood",
        "Стресс1_10": "stress",
        "Самочувствие1_10": "wellbeing",
        "Отжимания": "pushups",
        "Подтягивания": "pullups",
        "Приседания": "squats",
        "ВодаСтаканов": "water",
        "ЧайСтаканов": "tea"
    }

    # Создаем числовые колонки
    for orig_name, short_name in numeric_cols_map.items():
        if orig_name in df.columns:
            df[short_name] = pd.to_numeric(df[orig_name], errors='coerce')
        else:
            # Создаем пустую колонку, чтобы скрипт не падал, если данных нет
            df[short_name] = np.nan

    # Обработка привычек (да/нет -> 1/0)
    habit_cols_map = {
        "Тренировка": "hab_workout",
        "Английский": "hab_english",
        "Бег": "hab_run",
        "ХолодныйДуш": "hab_cold_shower",
        "ЧиталСегодня": "hab_read",
        "Планка": "hab_plank"
    }

    for orig_name, short_name in habit_cols_map.items():
        if orig_name in df.columns:
            df[short_name] = df[orig_name].map(lambda x: 1 if str(x).lower() == 'да' else 0)
        else:
            df[short_name] = np.nan

    # Очистка данных для корреляций (нужны sleep, mood, stress)
    required_for_corr = ['sleep', 'mood', 'stress']
    df_clean = df.dropna(subset=required_for_corr) 

    if len(df_clean) < 2:
        print("⚠️ Недостаточно данных для построения корреляций (нужно минимум 2 записи с полным набором).")
        # Не выходим, пробуем построить хотя бы гистограммы если есть данные

    # --- НАСТРОЙКА ГРАФИКОВ ---
    # Проверяем, есть ли хоть какие-то данные для графиков
    has_corr_data = not df_clean.empty and all(col in df_clean.columns for col in required_for_corr)
    has_activity_data = any(col in df.columns for col in ['pushups', 'pullups', 'squats'])
    has_habit_data = any(col in df.columns for col in habit_cols_map.values())
    has_sleep_data = 'sleep' in df.columns and df['sleep'].notna().any()

    if not any([has_corr_data, has_activity_data, has_habit_data, has_sleep_data]):
        print("⚠️ Нет подходящих данных для построения ни одного графика.")
        return

    fig, axs = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('🧠 Анализ статистики', fontsize=18, fontweight='bold')
    plt.subplots_adjust(hspace=0.3, wspace=0.3)

    # === ГРАФИК 1: КОРРЕЛЯЦИЯ ===
    ax1 = axs[0, 0]
    if has_corr_data:
        scatter = ax1.scatter(df_clean['sleep'], df_clean['mood'], 
                              c=df_clean['stress'], cmap='RdYlGn_r', 
                              s=100, alpha=0.7, edgecolors='black', linewidth=0.5)
        ax1.set_title('☁️ Сон vs Настроение (цвет = Стресс)', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Часов сна')
        ax1.set_ylabel('Настроение (1-10)')
        ax1.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax1, label='Стресс')
    else:
        ax1.text(0.5, 0.5, 'Нет данных\nдля корреляции', ha='center', va='center', transform=ax1.transAxes, fontsize=15, color='gray')
        ax1.set_title('☁️ Корреляция', fontsize=14)
        ax1.axis('off')

    # === ГРАФИК 2: АКТИВНОСТЬ ===
    ax2 = axs[0, 1]
    if has_activity_data:
        activity_metrics = ['pushups', 'pullups', 'squats']
        activity_labels = ['Отжимания', 'Подтягивания', 'Приседания']
        activity_colors = ['#f1c40f', '#e67e22', '#8e44ad']
        
        means = [df[m].mean() if m in df.columns and df[m].notna().any() else 0 for m in activity_metrics]
        
        bars = ax2.bar(activity_labels, means, color=activity_colors, edgecolor='black')
        ax2.set_title('📈 Средняя активность', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Раз (среднее)')
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        
        for bar, val in zip(bars, means):
            if val > 0:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{val:.1f}', ha='center', va='bottom', fontsize=10)
    else:
        ax2.text(0.5, 0.5, 'Нет данных\nоб активности', ha='center', va='center', transform=ax2.transAxes, fontsize=15, color='gray')
        ax2.set_title('📈 Активность', fontsize=14)
        ax2.axis('off')

    # === ГРАФИК 3: РАСПРЕДЕЛЕНИЕ СНА ===
    ax3 = axs[1, 0]
    if has_sleep_data:
        ax3.hist(df['sleep'].dropna(), bins=range(0, 15), color='#3498db', edgecolor='white', alpha=0.8)
        ax3.set_title('💤 Распределение сна', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Часов')
        ax3.set_ylabel('Дней')
        ax3.grid(axis='y', alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'Нет данных\nо сне', ha='center', va='center', transform=ax3.transAxes, fontsize=15, color='gray')
        ax3.set_title('💤 Сон', fontsize=14)
        ax3.axis('off')

    # === ГРАФИК 4: ПРИВЫЧКИ ===
    ax4 = axs[1, 1]
    if has_habit_data:
        habits_data = {}
        for short_name, label in zip(habit_cols_map.values(), habit_cols_map.keys()):
            if short_name in df.columns and df[short_name].notna().any():
                percent = (df[short_name].sum() / len(df)) * 100
                habits_data[label] = percent
        
        if habits_data:
            sorted_habits = dict(sorted(habits_data.items(), key=lambda item: item[1], reverse=True))
            labels = list(sorted_habits.keys())
            values = list(sorted_habits.values())
            colors = ['#2ecc71' if v > 50 else '#e74c3c' for v in values]
            
            bars_h = ax4.barh(labels, values, color=colors, edgecolor='black')
            ax4.set_title('✅ Выполнение привычек', fontsize=14, fontweight='bold')
            ax4.set_xlabel('% дней')
            ax4.set_xlim(0, 100)
            ax4.grid(axis='x', alpha=0.3, linestyle='--')
            
            for bar, val in zip(bars_h, values):
                ax4.text(val + 2, bar.get_y() + bar.get_height()/2, f'{val:.1f}%', va='center', fontsize=10)
            ax4.axvline(50, color='gray', linestyle=':', linewidth=1)
        else:
             ax4.text(0.5, 0.5, 'Нет данных\nо привычках', ha='center', va='center', transform=ax4.transAxes, fontsize=15, color='gray')
             ax4.axis('off')
    else:
        ax4.text(0.5, 0.5, 'Нет данных\nо привычках', ha='center', va='center', transform=ax4.transAxes, fontsize=15, color='gray')
        ax4.set_title('✅ Привычки', fontsize=14)
        ax4.axis('off')

    # --- СОХРАНЕНИЕ ---
    try:
        # Создаем директорию если нет
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Анализ завершен! Отчет сохранен в: {output_path.resolve()}")
        
        # Краткая сводка
        print("\n--- Краткая сводка ---")
        if 'sleep' in df.columns:
            print(f"Средний сон: {df['sleep'].mean():.1f} ч.")
        if 'mood' in df.columns:
            print(f"Среднее настроение: {df['mood'].mean():.1f}/10")
        if 'hab_workout' in df.columns:
            print(f"Тренировки: {(df['hab_workout'].mean()*100):.1f}% дней")
            
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
    finally:
        plt.close() # Освобождаем память

if __name__ == "__main__":
    run_analytics()