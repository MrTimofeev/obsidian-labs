import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("❌ Библиотека scikit-learn не найдена. Прогнозирование невозможно.")
    print("💡 Установите: pip install scikit-learn")
    sys.exit(1)

# Загружаем переменные окружения
load_dotenv()

def run_forecast_analysis():
    # 1. Конфигурация путей
    input_file_str = os.getenv("STATS_INPUT_FILE", ".data/stats_daily.json")
    output_image_str = os.getenv("ANALYTICS_FORECAST_IMAGE", ".data/forecast_report.png")
    
    input_path = Path(input_file_str)
    output_path = Path(output_image_str)

    if not input_path.exists():
        print(f"❌ Ошибка: Файл '{input_path}' не найден.")
        return

    print("🔮 Запуск модуля предсказания и симуляции...")

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
        row = {"date_str": entry.get('дата', entry.get('date'))}
        if 'данные' in entry:
            row.update(entry['данные'])
        else:
            row.update({k: v for k, v in entry.items() if k not in ['дата', 'date']})
        flat_data.append(row)

    df = pd.DataFrame(flat_data)
    if df.empty or 'date_str' not in df.columns:
        print("❌ Нет данных или даты.")
        return
    
    df = df.dropna(subset=['date_str'])

    # Маппинг
    numeric_map = {
        "КоличествоСнаЧ": "Sleep",
        "КачествоСна1_5": "SleepQual",
        "Настроение1_10": "Mood",       # Target
        "Самочувствие1_10": "Wellbeing",
        "Стресс1_10": "Stress",
        "Отжимания": "Pushups",
        "Подтягивания": "Pullups",
        "Приседания": "Squats",
        "ВодаСтаканов": "Water",
        "Тренировка": "Workout",
        "Английский": "English",
        "Бег": "Run",
        "ХолодныйДуш": "ColdShower"
    }

    model_df = pd.DataFrame()
    for orig, new in numeric_map.items():
        if orig in df.columns:
            if orig in ["Тренировка", "Английский", "Бег", "ХолодныйДуш"]:
                model_df[new] = df[orig].map(lambda x: 1 if str(x).lower() == 'да' else 0)
            else:
                model_df[new] = pd.to_numeric(df[orig], errors='coerce')

    # Удаляем строки, где нет целевой переменной (Настроение)
    if 'Mood' not in model_df.columns:
        print("❌ Нет данных о настроении ('Настроение1_10'). Невозможно построить модель.")
        return

    model_df = model_df.dropna(subset=['Mood'])
    

    feature_cols = [c for c in model_df.columns if c != 'Mood']
    if not feature_cols:
        print("❌ Нет числовых факторов для анализа.")
        return
        
    model_df = model_df.dropna(subset=feature_cols, how='all')
    model_df = model_df.fillna(model_df.mean(numeric_only=True)) # Заполняем остальные пропуски средним

    if len(model_df) < 10:
        print(f"⚠️ Мало данных ({len(model_df)} записей). Для надежной регрессии нужно минимум 10-15.")
        # Продолжаем, но с предупреждением

    # Разделение X и y
    X = model_df[feature_cols]
    y = model_df['Mood']

    # Обучение
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)

    print(f"✅ Модель обучена! Точность (R²): {r2:.2f}")
    if r2 < 0.3:
        print("⚠️ Внимание: Точность низкая. Настроение может зависеть от скрытых факторов.")

    # --- ВИЗУАЛИЗАЦИЯ ---
    fig, axs = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('🔮 Прогноз и Формула Счастья', fontsize=18, fontweight='bold')
    plt.subplots_adjust(hspace=0.3, wspace=0.3)

    days = range(len(y))

    # === ГРАФИК 1: РЕАЛЬНОСТЬ vs МОДЕЛЬ ===
    ax1 = axs[0, 0]
    ax1.plot(days, y, 'o-', label='Реальность', color='#3498db', alpha=0.6)
    ax1.plot(days, y_pred, 's--', label='Модель', color='#e74c3c', linewidth=2)
    ax1.fill_between(days, y, y_pred, color='gray', alpha=0.1)
    ax1.set_title('📈 Реальность vs Предсказание', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Дни')
    ax1.set_ylabel('Настроение')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.text(0.05, 0.95, f'R²: {r2:.2f}', transform=ax1.transAxes, fontsize=12, fontweight='bold', 
             bbox=dict(facecolor='white', alpha=0.8))

    # === ГРАФИК 2: ВАЖНОСТЬ ФАКТОРОВ ===
    ax2 = axs[0, 1]
    coefficients = pd.Series(model.coef_, index=X.columns)
    sorted_coeffs = coefficients.abs().sort_values(ascending=False)

    if not sorted_coeffs.empty:
        colors = ['#2ecc71' if coefficients[idx] > 0 else '#e74c3c' for idx in sorted_coeffs.index]
        bars = ax2.barh(sorted_coeffs.index, sorted_coeffs.values, color=colors, edgecolor='black')
        ax2.set_title('⚖️ Сила влияния на настроение', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Абсолютное значение коэффициента')
        ax2.grid(axis='x', alpha=0.3, linestyle='--')

        for bar, val, name in zip(bars, sorted_coeffs.values, sorted_coeffs.index):
            sign = "+" if coefficients[name] > 0 else "-"
            ax2.text(val + 0.05, bar.get_y() + bar.get_height()/2, f'{sign}{val:.2f}', va='center', fontsize=10)
    else:
        ax2.text(0.5, 0.5, 'Нет данных', ha='center', va='center')
        ax2.set_title('Влияние факторов')
        ax2.axis('off')

    # === ГРАФИК 3: СИМУЛЯТОР ===
    ax3 = axs[1, 0]
    base_scenario = X.mean().to_dict()
    base_mood = model.predict([list(base_scenario.values())])[0]

    scenarios = []
    labels_sim = ['Текущее\nсреднее']
    values_sim = [base_mood]
    colors_sim = ['#95a5a6']

    # Сценарий Сон
    if 'Sleep' in base_scenario:
        s_sleep = base_scenario.copy()
        s_sleep['Sleep'] += 1
        m_sleep = model.predict([list(s_sleep.values())])[0]
        scenarios.append(m_sleep)
        labels_sim.append('+1 час\nсна')
        colors_sim.append('#3498db')

    # Сценарий Спорт
    sport_added = False
    s_sport = base_scenario.copy()
    if 'Pushups' in s_sport:
        s_sport['Pushups'] += 20
        sport_added = True
    if 'Squats' in s_sport:
        s_sport['Squats'] += 20
        sport_added = True
    
    if sport_added:
        m_sport = model.predict([list(s_sport.values())])[0]
        scenarios.append(m_sport)
        labels_sim.append('+20 повторений\nспорта')
        colors_sim.append('#f1c40f')

    # Сценарий Без стресса
    if 'Stress' in base_scenario:
        s_stress = base_scenario.copy()
        s_stress['Stress'] = 0
        m_stress = model.predict([list(s_stress.values())])[0]
        scenarios.append(m_stress)
        labels_sim.append('Стресс = 0')
        colors_sim.append('#e74c3c')

    values_sim.extend(scenarios)
    
    if len(labels_sim) > 1:
        bars_sim = ax3.bar(labels_sim, values_sim, color=colors_sim, edgecolor='black')
        ax3.set_title('🧪 Симулятор: Что поднимет настроение?', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Прогноз настроения')
        ax3.set_ylim(0, 10)
        ax3.grid(axis='y', alpha=0.3, linestyle='--')

        for bar, val in zip(bars_sim, values_sim):
            diff = val - base_mood
            sign = "+" if diff > 0 else ""
            color_text = 'green' if diff > 0 else 'red'
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, 
                     f'{val:.1f}\n({sign}{diff:.1f})', ha='center', va='bottom', fontsize=10, fontweight='bold', color=color_text)
    else:
        ax3.text(0.5, 0.5, 'Недостаточно факторов\nдля симуляции', ha='center', va='center')
        ax3.set_title('Симулятор')
        ax3.axis('off')

    # === ГРАФИК 4: ТРЕНД ===
    ax4 = axs[1, 1]
    X_index = np.arange(len(y)).reshape(-1, 1)
    trend_model = LinearRegression()
    trend_model.fit(X_index, y)

    future_days = np.arange(len(y), len(y) + 10).reshape(-1, 1)
    future_pred = trend_model.predict(future_days)

    ax4.plot(X_index, y, 'o', label='История', color='#34495e', alpha=0.6)
    ax4.plot(X_index, trend_model.predict(X_index), '-', label='Тренд', color='#2c3e50', linewidth=2)
    ax4.plot(future_days, future_pred, '--', label='Прогноз (10 дней)', color='#e74c3c', linewidth=2)

    ax4.set_title('📉 Прогноз тренда', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Дни')
    ax4.set_ylabel('Настроение')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    slope = trend_model.coef_[0]
    if slope > 0.05:
        msg, col = "Тренд растет! 🚀", 'green'
    elif slope < -0.05:
        msg, col = "Осторожно, спад! ⚠️", 'red'
    else:
        msg, col = "Стабильность.", 'blue'
    
    ax4.text(0.05, 0.95, msg, transform=ax4.transAxes, fontsize=14, fontweight='bold', color=col, 
             bbox=dict(facecolor='white', alpha=0.8))

    # --- СОХРАНЕНИЕ И ВЫВОД ---
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Отчет сохранен: {output_path.resolve()}")
        
        print("\n--- 🧙‍♂️ ТВОЯ ФОРМУЛА СЧАСТЬЯ ---")
        formula_parts = [f"{model.intercept_:.2f}"]
        for feat, coef in zip(X.columns, model.coef_):
            sign = "+" if coef > 0 else "-"
            formula_parts.append(f"{sign} {abs(coef):.2f}*{feat}")
        
        print("Настроение = " + " ".join(formula_parts))
        
        print("\n💡 Главные рычаги:")
        if not coefficients.empty:
            top_pos = coefficients.idxmax()
            top_neg = coefficients.idxmin()
            
            print(f"🚀 Стимулятор: '{top_pos}' (+{coefficients[top_pos]:.2f} за единицу)")
            if coefficients[top_neg] < -0.1:
                print(f"🛑 Враг: '{top_neg}' ({coefficients[top_neg]:.2f} за единицу)")
        
        print("\n🔮 Прогноз:")
        if slope > 0.05:
            print("Настроение растет. Продолжай!")
        elif slope < -0.05:
            print("Внимание на спад. Используй симулятор для коррекции.")
        else:
            print("Стабильное состояние.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        plt.close()

if __name__ == "__main__":
    run_forecast_analysis()