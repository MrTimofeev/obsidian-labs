import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def run_dashboard_plotter():
    # 1. Конфигурация путей
    input_file_str = os.getenv("STATS_INPUT_FILE", ".data/stats_daily.json")
    output_image_str = os.getenv("ANALYTICS_DASHBOARD_IMAGE", ".data/my_stats_dashboard.png")
    
    input_path = Path(input_file_str)
    output_path = Path(output_image_str)

    if not input_path.exists():
        print(f"❌ Ошибка: Файл '{input_path}' не найден.")
        print("💡 Запустите сначала скрипт сбора статистики.")
        return

    print(f"📊 Построение главного дашборда...")

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

    print(f"✅ Загружено {len(data_source)} записей. Обработка...")

    # --- ПРЕОБРАЗОВАНИЕ ---
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

    df['date_obj'] = pd.to_datetime(df['date_str'], format='%d.%m.%y', errors='coerce')
    if df['date_obj'].isna().all():
        df['date_obj'] = pd.to_datetime(df['date_str'], errors='coerce')
        
    df = df.dropna(subset=['date_obj'])
    df = df.sort_values('date_obj').reset_index(drop=True)
    
    days_count = len(df)
    if days_count == 0:
        print("⚠️ Нет валидных дат для построения графика.")
        return

    # Числовые колонки
    numeric_cols = [
        "КоличествоСнаЧ", "КачествоСна1_5", "Отжимания", "Подтягивания", 
        "Приседания", "ВодаСтаканов", "ЧайСтаканов", "Настроение1_10", 
        "Самочувствие1_10", "Стресс1_10"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- НАСТРОЙКА ВИЗУАЛИЗАЦИИ ---
    
    # ОГРАНИЧЕНИЕ РАЗМЕРА: Чтобы не создать файл на 100 МБ при большом объеме данных
    # Максимальная ширина 24 дюйма (полный экран широкоформатного монитора)
    calculated_width = min(24, max(14, days_count * 0.15))
    # Высота тоже ограничим, чтобы влезло в экран, скролл лучше чем гигантская картинка
    calculated_height = min(16, max(10, days_count * 0.04)) 

    fig, axs = plt.subplots(4, 1, figsize=(calculated_width, calculated_height))
    fig.suptitle(f'📊 Дашборд прогресса ({days_count} дней)', fontsize=20, fontweight='bold', y=0.995)

    plt.subplots_adjust(hspace=0.25, left=0.05, right=0.98, top=0.96, bottom=0.05)

    # === ГРАФИК 1: Эмоции и Сон ===
    ax1 = axs[0]
    has_data_1 = False
    
    if 'Настроение1_10' in df.columns and df['Настроение1_10'].notna().any():
        ax1.plot(df['date_obj'], df['Настроение1_10'], label='Настроение', color='#2ecc71', linewidth=2)
        ax1.fill_between(df['date_obj'], df['Настроение1_10'], alpha=0.15, color='#2ecc71')
        has_data_1 = True
        
    if 'КоличествоСнаЧ' in df.columns and df['КоличествоСнаЧ'].notna().any():
        ax1.plot(df['date_obj'], df['КоличествоСнаЧ'], label='Сон (ч)', color='#3498db', linewidth=2, linestyle='--')
        has_data_1 = True
        
    if 'Стресс1_10' in df.columns and df['Стресс1_10'].notna().any():
        ax1.plot(df['date_obj'], df['Стресс1_10'], label='Стресс', color='#e74c3c', linewidth=2, linestyle=':')
        has_data_1 = True

    ax1.set_title('Эмоциональное состояние и Сон', fontsize=14, loc='left', fontweight='bold')
    if has_data_1:
        ax1.legend(loc='upper right', ncol=3, framealpha=0.9)
        ax1.set_ylim(0, 12)
    ax1.grid(True, axis='y', alpha=0.3, linestyle='--')

    # === ГРАФИК 2: СПОРТ (Многослойный) ===
    ax2 = axs[1]
    base_width = 0.6
    has_data_2 = False

    # Приседания (Фон)
    if 'Приседания' in df.columns and df['Приседания'].notna().any() and df['Приседания'].max() > 0:
        ax2.bar(df['date_obj'], df['Приседания'], width=base_width, label='Приседания', 
                color='#8e44ad', alpha=0.4, edgecolor='#8e44ad', linewidth=2.5)
        has_data_2 = True

    # Отжимания (Средний)
    if 'Отжимания' in df.columns and df['Отжимания'].notna().any() and df['Отжимания'].max() > 0:
        ax2.bar(df['date_obj'], df['Отжимания'], width=base_width * 0.75, label='Отжимания', 
                color='#d35400', alpha=0.8, edgecolor='#d35400', linewidth=2.0)
        has_data_2 = True

    # Подтягивания (Центр)
    if 'Подтягивания' in df.columns and df['Подтягивания'].notna().any() and df['Подтягивания'].max() > 0:
        ax2.bar(df['date_obj'], df['Подтягивания'], width=base_width * 0.5, label='Подтягивания', 
                color='#f1c40f', alpha=1.0, edgecolor='white', linewidth=1.5)
        has_data_2 = True

    ax2.set_title('Физическая активность', fontsize=14, loc='left', fontweight='bold')
    if has_data_2:
        ax2.legend(loc='upper right', framealpha=0.9)
        ax2.set_ylim(bottom=0)
    ax2.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax2.set_axisbelow(True)

    # === ГРАФИК 3: Привычки ===
    ax3 = axs[2]
    habit_cols = ["Тренировка", "Английский", "Бег", "ХолодныйДуш", "ЧиталСегодня", "Планка"]
    existing_habits = [c for c in habit_cols if c in df.columns]

    if existing_habits:
        # Конвертируем в 0/1 безопасно
        habit_df = df[existing_habits].map(lambda x: 1 if str(x).lower() == 'да' else 0)
        
        ax3.set_yticks(range(len(existing_habits)))
        ax3.set_yticklabels(existing_habits, fontsize=12, fontweight='bold')
        ax3.set_title('Трекер привычек', fontsize=14, loc='left', fontweight='bold')
        
        for i, habit in enumerate(existing_habits):
            mask = habit_df[habit] == 1
            dates_done = df.loc[mask, 'date_obj']
            if not dates_done.empty:
                ax3.scatter(dates_done, [i]*len(dates_done), color='#27ae60', s=100, marker='|', linewidths=2.5)
        
        ax3.set_xlim(df['date_obj'].min(), df['date_obj'].max())
        ax3.set_ylim(-0.5, len(existing_habits) - 0.5)
        ax3.grid(True, axis='x', alpha=0.3, linestyle='--')
        ax3.set_axisbelow(True)
    else:
        ax3.text(0.5, 0.5, 'Нет данных о привычках', ha='center', va='center', transform=ax3.transAxes)
        ax3.set_title('Трекер привычек', fontsize=14, loc='left', fontweight='bold')
        ax3.axis('off')

    # === ГРАФИК 4: Жидкость ===
    ax4 = axs[3]
    has_data_4 = False
    
    if 'ВодаСтаканов' in df.columns and df['ВодаСтаканов'].notna().any():
        ax4.fill_between(df['date_obj'], df['ВодаСтаканов'], alpha=0.4, color='#3498db', label='Вода')
        has_data_4 = True
        
        if 'ЧайСтаканов' in df.columns and df['ЧайСтаканов'].notna().any():
            # Безопасное сложение с заполнением пропусков нулем
            tea_series = df['ЧайСтаканов'].fillna(0)
            water_series = df['ВодаСтаканов'].fillna(0)
            total_series = water_series + tea_series
            
            ax4.fill_between(df['date_obj'], water_series, total_series, alpha=0.4, color='#d35400', label='Чай')
            
    ax4.set_title('Потребление жидкости', fontsize=14, loc='left', fontweight='bold')
    if has_data_4:
        ax4.legend(loc='upper right', framealpha=0.9)
        ax4.set_ylim(bottom=0)
    ax4.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax4.set_axisbelow(True)

    # === УМНАЯ ОСЬ ВРЕМЕНИ ===
    for ax in [ax1, ax2, ax3, ax4]:
        if days_count > 100:
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        elif days_count > 30:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        else:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)

    # --- СОХРАНЕНИЕ ---
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Готово! Дашборд сохранен: {output_path.resolve()}")
        print(f"   Размер: {calculated_width:.1f}x{calculated_height:.1f} дюймов")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        import traceback
        traceback.print_exc()
    finally:
        plt.close()

if __name__ == "__main__":
    run_dashboard_plotter()