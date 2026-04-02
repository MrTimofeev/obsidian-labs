import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import json
import os
import sys
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def run_efficiency_analysis():
    # 1. Конфигурация путей
    input_file_str = os.getenv("STATS_INPUT_FILE", ".data/stats_daily.json")
    output_image_str = os.getenv("ANALYTICS_EFFICIENCY_IMAGE", ".data/efficiency_report.png")
    
    input_path = Path(input_file_str)
    output_path = Path(output_image_str)

    if not input_path.exists():
        print(f"❌ Ошибка: Файл '{input_path}' не найден.")
        print("💡 Запустите сначала скрипт сбора статистики.")
        return

    print("🧠 Расчет эффективности и скрытых связей...")

    # --- ЗАГРУЗКА ДАННЫХ ---
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data_source = json.load(f)
    except json.JSONDecodeError:
        print("❌ Ошибка: Файл поврежден или не является valid JSON.")
        return

    if not data_source:
        print("⚠️ Файл пуст.")
        return

    # --- ПОДГОТОВКА ДАННЫХ ---
    flat_data = []
    date_key_found = None
    possible_date_keys = ['дата', 'date', 'Дата', 'Date', 'datum']

    for entry in data_source:
        if date_key_found is None:
            for key in possible_date_keys:
                if key in entry:
                    date_key_found = key
                    break
        
        row = {}
        if date_key_found and date_key_found in entry:
            row['date_str'] = entry[date_key_found]
        else:
            row['date_str'] = None
            
        if 'данные' in entry:
            row.update(entry['данные'])
        
        flat_data.append(row)

    if date_key_found is None:
        print("❌ Критическая ошибка: Не удалось найти колонку с датой.")
        return

    df = pd.DataFrame(flat_data)
    df = df.dropna(subset=['date_str'])

    if df.empty:
        print("⚠️ Нет данных с корректной датой.")
        return

    # Маппинг имен
    col_map = {
        "КоличествоСнаЧ": "Сон",
        "КачествоСна1_5": "Кач. сна",
        "Настроение1_10": "Настроение",
        "Самочувствие1_10": "Самочувствие",
        "Стресс1_10": "Стресс",
        "Отжимания": "Отжимания",
        "Подтягивания": "Подтягивания",
        "Приседания": "Приседания",
        "ВодаСтаканов": "Вода",
        "Тренировка": "Тренировка (да/нет)",
        "Английский": "Английский (да/нет)",
        "ХолодныйДуш": "Хол. душ (да/нет)"
    }

    df_clean = pd.DataFrame()
    df_clean['date_str'] = df['date_str']

    for orig, new in col_map.items():
        if orig in df.columns:
            if 'да/нет' in new:
                df_clean[new] = df[orig].map(lambda x: 1 if str(x).lower() == 'да' else 0)
            else:
                df_clean[new] = pd.to_numeric(df[orig], errors='coerce')

    # Фильтрация
    required_for_analysis = ['Настроение', 'Сон', 'Стресс', 'Самочувствие']
    existing_req = [c for c in required_for_analysis if c in df_clean.columns]

    if existing_req:
        df_clean = df_clean.dropna(subset=existing_req, how='all')
    
    if df_clean.empty:
        print("⚠️ Недостаточно данных для анализа после очистки.")
        return

    # Парсинг даты
    try:
        df_clean['DateObj'] = pd.to_datetime(df_clean['date_str'], format='%d.%m.%y', errors='coerce')
        if df_clean['DateObj'].isna().all():
            df_clean['DateObj'] = pd.to_datetime(df_clean['date_str'], errors='coerce')
    except Exception:
        print("⚠️ Не удалось распарсить даты.")
        df_clean['DateObj'] = pd.to_datetime('2000-01-01')

    # --- ВИЗУАЛИЗАЦИЯ ---
    sns.set_theme(style="whitegrid")
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    fig.suptitle('⚡ Эффективность и Баланс', fontsize=20, fontweight='bold')

    numeric_df = df_clean.select_dtypes(include=[np.number])
    # Исключаем служебные колонки если попали
    numeric_df = numeric_df.loc[:, ~numeric_df.columns.str.contains('DateObj|date_str', regex=False)]

    # === ГРАФИК 1: КОРРЕЛЯЦИИ ===
    ax1 = fig.add_subplot(gs[0, 0])
    if numeric_df.shape[1] < 2:
        ax1.text(0.5, 0.5, "Мало числовых данных\nдля корреляции", ha='center', va='center', transform=ax1.transAxes)
        ax1.set_title('🔗 Корреляции')
        ax1.axis('off')
    else:
        corr_matrix = numeric_df.corr()
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap='coolwarm', 
                    center=0, square=True, linewidths=.5, ax=ax1, cbar_kws={"shrink": .8})
        ax1.set_title('🔗 Матрица связей', fontsize=14, fontweight='bold', pad=10)

    # === ГРАФИК 2: РАДАР ===
    ax2 = fig.add_subplot(gs[0, 1], projection='polar')
    categories = ['Сон', 'Настроение', 'Спорт', 'Вода', 'Дисциплина']
    values = []

    # Сон (норма 8ч)
    values.append(min(df_clean['Сон'].mean() / 8.0, 1.0) if 'Сон' in df_clean.columns else 0)
    # Настроение (норма 10)
    values.append(df_clean['Настроение'].mean() / 10.0 if 'Настроение' in df_clean.columns else 0)
    # Спорт (сумма упражнений, норма 100)
    sport_cols = [c for c in ['Отжимания', 'Подтягивания', 'Приседания'] if c in df_clean.columns]
    if sport_cols:
        values.append(min(df_clean[sport_cols].sum(axis=1).mean() / 100.0, 1.0))
    else:
        values.append(0)
    # Вода (норма 8 стаканов)
    values.append(min(df_clean['Вода'].mean() / 8.0, 1.0) if 'Вода' in df_clean.columns else 0)
    # Дисциплина (среднее по привычкам)
    habit_cols = [c for c in df_clean.columns if 'да/нет' in c]
    if habit_cols:
        values.append(df_clean[habit_cols].mean().mean())
    else:
        values.append(0)

    values += values[:1]
    angles = [n / float(len(categories)) * 2 * np.pi for n in range(len(categories))]
    angles += angles[:1]

    ax2.plot(angles, values, 'o-', linewidth=2, color='#8e44ad', label='Вы')
    ax2.fill(angles, values, alpha=0.25, color='#8e44ad')
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(categories, fontsize=11, fontweight='bold')
    ax2.set_ylim(0, 1)
    ax2.set_title('⚖️ Баланс жизни', fontsize=14, fontweight='bold', pad=20)
    ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

    # === ГРАФИК 3: ТОП-5 ДНЕЙ ===
    ax3 = fig.add_subplot(gs[1, 0])
    score_df = df_clean.copy()
    score_df['Score'] = 0

    if 'Настроение' in score_df: score_df['Score'] += score_df['Настроение']
    if 'Самочувствие' in score_df: score_df['Score'] += score_df['Самочувствие']
    if 'Стресс' in score_df: score_df['Score'] -= score_df['Стресс']
    if 'Отжимания' in score_df: score_df['Score'] += score_df['Отжимания'] / 10
    if 'Подтягивания' in score_df: score_df['Score'] += score_df['Подтягивания'] / 5

    top_5 = score_df.nlargest(5, 'Score')

    if len(top_5) > 0 and 'DateObj' in top_5.columns:
        y_labels = top_5['DateObj'].dt.strftime('%d.%m.%y')
        bars = ax3.barh(y_labels, top_5['Score'], color='#27ae60', edgecolor='black')
        ax3.set_title('🏆 Топ-5 лучших дней', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Баллы эффективности')
        ax3.grid(axis='x', alpha=0.3, linestyle='--')
        
        for bar, val in zip(bars, top_5['Score']):
            ax3.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{val:.1f}', va='center', fontsize=11)
    else:
        ax3.text(0.5, 0.5, "Нет данных для рейтинга", ha='center', va='center')
        ax3.set_title('🏆 Топ дней')
        ax3.axis('off')

    # === ГРАФИК 4: ВЛИЯНИЕ ПРИВЫЧЕК ===
    ax4 = fig.add_subplot(gs[1, 1])
    target = 'Настроение' 

    if target in df_clean.columns:
        habit_cols_check = [c for c in df_clean.columns if 'да/нет' in c]
        x_labels, y_yes, y_no = [], [], []
        
        for col in habit_cols_check:
            name = col.replace(' (да/нет)', '')
            avg_yes = df_clean[df_clean[col] == 1][target].mean()
            avg_no = df_clean[df_clean[col] == 0][target].mean()
            
            if not np.isnan(avg_yes) and not np.isnan(avg_no):
                x_labels.append(name)
                y_yes.append(avg_yes)
                y_no.append(avg_no)
        
        if x_labels:
            x = np.arange(len(x_labels))
            width = 0.35
            ax4.bar(x - width/2, y_yes, width, label='С привычкой', color='#2ecc71')
            ax4.bar(x + width/2, y_no, width, label='Без привычки', color='#e74c3c', alpha=0.6)
            ax4.set_title(f'Влияние привычек на "{target}"', fontsize=14, fontweight='bold')
            ax4.set_xticks(x)
            ax4.set_xticklabels(x_labels, rotation=45, ha='right')
            ax4.legend()
            ax4.grid(axis='y', alpha=0.3, linestyle='--')
        else:
            ax4.text(0.5, 0.5, "Нет бинарных привычек", ha='center', va='center')
            ax4.set_title('Влияние привычек')
            ax4.axis('off')
    else:
        ax4.text(0.5, 0.5, "Нет данных о настроении", ha='center', va='center')
        ax4.set_title('Влияние привычек')
        ax4.axis('off')

    # --- СОХРАНЕНИЕ И ИНСАЙТЫ ---
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Отчет готов: {output_path.resolve()}")
        
        # Инсайты
        if 'Настроение' in numeric_df.columns and len(numeric_df.columns) > 1:
            corr_matrix = numeric_df.corr()
            mood_corr_series = corr_matrix['Настроение'].drop('Настроение', errors='ignore').dropna()
            
            if len(mood_corr_series) > 0:
                sorted_factors = mood_corr_series.reindex(mood_corr_series.abs().sort_values(ascending=False).index)
                
                print("\n--- 💡 Топ-3 фактора настроения ---")
                for i, (factor, val) in enumerate(sorted_factors.items()):
                    if i >= 3: break
                    sign = "📈" if val > 0 else "📉"
                    print(f"{i+1}. {factor}: {val:.2f} {sign}")
                
                best = sorted_factors.index[0]
                val = sorted_factors.iloc[0]
                print(f"\n🏆 Главный инсайт: На настроение сильнее всего влияет «{best}» ({val:.2f}).")
            else:
                print("\n⚠️ Мало данных для инсайтов.")
        else:
            print("\n⚠️ Нет данных о настроении для инсайтов.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        plt.close()

if __name__ == "__main__":
    run_efficiency_analysis()