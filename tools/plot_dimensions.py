import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Попытка импорта sklearn (может отсутствовать, если не установлен)
try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ Библиотека scikit-learn не найдена. Кластеризация будет пропущена.")
    print("💡 Установите: pip install scikit-learn")

# Загружаем переменные окружения
load_dotenv()

def run_dimensional_analysis():
    # 1. Конфигурация путей
    input_file_str = os.getenv("STATS_INPUT_FILE", ".data/stats_daily.json")
    output_image_str = os.getenv("ANALYTICS_3D_IMAGE", ".data/dimensions_report.png")
    
    input_path = Path(input_file_str)
    output_path = Path(output_image_str)

    if not input_path.exists():
        print(f"❌ Ошибка: Файл '{input_path}' не найден.")
        return

    print("🌌 Построение многомерных моделей...")

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

    # Парсинг в DataFrame
    flat_data = []
    for entry in data_source:
        row = {"date_str": entry.get('дата', entry.get('date'))}
        if 'данные' in entry:
            row.update(entry['данные'])
        else:
            # Fallback для плоской структуры
            row.update({k: v for k, v in entry.items() if k not in ['дата', 'date']})
        flat_data.append(row)

    df = pd.DataFrame(flat_data)
    if df.empty or 'date_str' not in df.columns:
        print("❌ Нет данных или отсутствует колонка даты.")
        return

    df = df.dropna(subset=['date_str'])

    # Маппинг колонок (Оригинал -> Стандартное имя)
    numeric_map = {
        "КоличествоСнаЧ": "Sleep",
        "Настроение1_10": "Mood",
        "Отжимания": "Pushups",
        "Подтягивания": "Pullups",
        "Приседания": "Squats",
        "Стресс1_10": "Stress",
        "Самочувствие1_10": "Wellbeing",
        "ВодаСтаканов": "Water"
    }

    model_df = pd.DataFrame()
    model_df['date_str'] = df['date_str']

    # Создаем числовые колонки, игнорируя отсутствующие
    for orig, new in numeric_map.items():
        if orig in df.columns:
            model_df[new] = pd.to_numeric(df[orig], errors='coerce')
    
    # Удаляем строки, где нет ни одного числового значения
    num_cols = model_df.select_dtypes(include=[np.number]).columns
    if len(num_cols) == 0:
        print("❌ Нет числовых данных для анализа.")
        return
        
    model_df = model_df.dropna(subset=num_cols, how='all')

    if len(model_df) < 5:
        print(f"⚠️ Мало данных ({len(model_df)} записей). Для 3D и кластеризации нужно минимум 5.")
        # Можно продолжить, но графики будут пустыми

    # --- ВИЗУАЛИЗАЦИЯ ---
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('🌌 Многомерный анализ привычек', fontsize=18, fontweight='bold')

    cols = list(model_df.select_dtypes(include=[np.number]).columns)
    
    # === ГРАФИК 1: 3D СКАТТЕР ===
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    
    # Выбор осей с проверкой существования
    x_col = 'Sleep' if 'Sleep' in cols else (cols[0] if len(cols) > 0 else None)
    y_col = 'Pushups' if 'Pushups' in cols else (cols[1] if len(cols) > 1 else cols[0])
    z_col = 'Mood' if 'Mood' in cols else (cols[2] if len(cols) > 2 else (cols[0] if len(cols) > 0 else None))

    if x_col and y_col and z_col:
        x = model_df[x_col]
        y = model_df[y_col]
        z = model_df[z_col]
        
        # Цвет по настроению, если оно есть и не является одной из осей, или просто по Z
        color_col = 'Mood' if 'Mood' in cols else z_col
        c = model_df[color_col]

        scatter = ax1.scatter(x, y, z, c=c, cmap='viridis', s=50, alpha=0.8, edgecolors='w', linewidth=0.5)
        ax1.set_xlabel(x_col)
        ax1.set_ylabel(y_col)
        ax1.set_zlabel(z_col)
        ax1.set_title(f'3D Облако: {x_col} vs {y_col} vs {z_col}', fontsize=12, fontweight='bold')
        plt.colorbar(scatter, ax=ax1, shrink=0.5, label=color_col)
    else:
        ax1.text(0.5, 0.5, 'Недостаточно данных\nдля 3D графика', ha='center', va='center', transform=ax1.transAxes)
        ax1.set_title('3D Анализ')
        ax1.axis('off')

    # === ГРАФИК 2: КЛАСТЕРИЗАЦИЯ (K-Means) ===
    ax2 = fig.add_subplot(2, 2, 2)
    
    if SKLEARN_AVAILABLE and len(model_df) >= 5 and len(cols) >= 2:
        data_for_cluster = model_df[cols].dropna()
        if len(data_for_cluster) >= 5:
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data_for_cluster)
            
            n_clusters = min(3, len(data_for_cluster))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            model_df.loc[data_for_cluster.index, 'Cluster'] = kmeans.fit_predict(scaled_data)
            
            cluster_moods = model_df.dropna(subset=['Cluster']).groupby('Cluster')['Mood'].mean().sort_values(ascending=False) if 'Mood' in cols else None
            
            cluster_labels_map = {}
            if cluster_moods is not None:
                names = ["🌟 Дни Успеха", "😐 Обычные дни", "🔋 Дни Восстановления"]
                for i, idx in enumerate(cluster_moods.index):
                    cluster_labels_map[idx] = names[i] if i < len(names) else f"Кластер {i}"
            else:
                cluster_labels_map = {i: f"Кластер {i}" for i in range(n_clusters)}

            colors_clusters = ['#2ecc71', '#f1c40f', '#e74c3c']
            
            has_plot_data = False
            for cid in model_df['Cluster'].dropna().unique():
                subset = model_df[model_df['Cluster'] == cid]
                if 'Mood' in subset.columns and subset['Mood'].notna().any():
                    ax2.scatter(subset.index, subset['Mood'], c=[colors_clusters[int(cid) % 3]], 
                                label=cluster_labels_map.get(int(cid), f"Grp {int(cid)}"), alpha=0.7, s=60, edgecolors='black')
                    has_plot_data = True
            
            if has_plot_data:
                ax2.set_title('🧩 Типы дней (K-Means)', fontsize=12, fontweight='bold')
                ax2.set_xlabel('Индекс дня')
                ax2.set_ylabel('Настроение')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
            else:
                ax2.text(0.5, 0.5, 'Нет данных о настроении\nдля кластеров', ha='center', va='center', transform=ax2.transAxes)
        else:
            ax2.text(0.5, 0.5, 'Мало данных\nдля кластеризации', ha='center', va='center', transform=ax2.transAxes)
    else:
        reason = "Нет sklearn" if not SKLEARN_AVAILABLE else "Мало данных"
        ax2.text(0.5, 0.5, f'Кластеризация недоступна\n({reason})', ha='center', va='center', transform=ax2.transAxes)
    
    ax2.set_title('🧩 Кластеризация дней')
    if ax2.lines == [] and ax2.collections == []:
         ax2.axis('off')

    # === ГРАФИК 3: ПАРАЛЛЕЛЬНЫЕ КООРДИНАТЫ ===
    ax3 = fig.add_subplot(2, 2, 3)
    plot_cols = [c for c in ['Sleep', 'Pushups', 'Mood', 'Stress', 'Water'] if c in model_df.columns]
    
    if len(plot_cols) >= 2 and 'Mood' in model_df.columns and model_df['Mood'].notna().any():
        valid_df = model_df.dropna(subset=plot_cols + ['Mood'])
        if len(valid_df) >= 5:
            top_good = valid_df.nlargest(5, 'Mood')
            top_bad = valid_df.nsmallest(5, 'Mood')
            plot_df = pd.concat([top_good, top_bad]).drop_duplicates()

            norm_df = (plot_df[plot_cols] - plot_df[plot_cols].min()) / (plot_df[plot_cols].max() - plot_df[plot_cols].min() + 1e-9)
            
            for idx, row in norm_df.iterrows():
                original_mood = plot_df.loc[idx, 'Mood']
                color = '#2ecc71' if idx in top_good.index else '#e74c3c'
                ax3.plot(plot_cols, row.values, color=color, alpha=0.5, linewidth=2, marker='o', markersize=4)

            ax3.set_title('🌈 Лучшие vs Худшие дни', fontsize=12, fontweight='bold')
            ax3.set_xticklabels(plot_cols, rotation=45, ha='right')
            ax3.grid(True, alpha=0.3)
            
            from matplotlib.lines import Line2D
            custom_lines = [Line2D([0], [0], color='#2ecc71', lw=2), Line2D([0], [0], color='#e74c3c', lw=2)]
            ax3.legend(custom_lines, ['Лучшие дни', 'Худшие дни'])
        else:
            ax3.text(0.5, 0.5, 'Мало данных', ha='center', va='center', transform=ax3.transAxes)
    else:
        ax3.text(0.5, 0.5, 'Нет данных\nдля сравнения', ha='center', va='center', transform=ax3.transAxes)
        ax3.axis('off')

    # === ГРАФИК 4: ТЕПЛОВАЯ КАРТА (Дни недели) ===
    ax4 = fig.add_subplot(2, 2, 4)
    
    if 'Mood' in model_df.columns:
        try:
            # Пробуем распарсить дату. Формат может быть разным, пробуем несколько
            model_df['DateObj'] = pd.to_datetime(model_df['date_str'], format='%d.%m.%y', errors='coerce')
            if model_df['DateObj'].isna().all():
                 model_df['DateObj'] = pd.to_datetime(model_df['date_str'], errors='coerce')
            
            valid_dates = model_df.dropna(subset=['DateObj'])
            
            if not valid_dates.empty:
                valid_dates = valid_dates.copy()
                valid_dates['DayOfWeek'] = valid_dates['DateObj'].dt.day_name()
                
                pivot = valid_dates.pivot_table(values='Mood', index='DayOfWeek', aggfunc='mean')
                order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                # Фильтруем только те дни, что есть в данных
                order = [d for d in order if d in pivot.index]
                pivot = pivot.reindex(order)
                
                ru_names = {'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср', 'Thursday': 'Чт', 
                            'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'}
                pivot.index = [ru_names.get(d, d) for d in pivot.index]

                im = ax4.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=0, vmax=10)
                ax4.set_yticks(range(len(pivot)))
                ax4.set_yticklabels(pivot.index)
                ax4.set_xticks([])
                ax4.set_title('📅 Настроение по дням недели', fontsize=12, fontweight='bold')

                for i in range(len(pivot)):
                    for j in range(1):
                        val = pivot.iloc[i, j]
                        if not np.isnan(val):
                            ax4.text(j, i, f'{val:.1f}', ha='center', va='center', color='white' if val > 5 else 'black', fontweight='bold')

                plt.colorbar(im, ax=ax4, shrink=0.8, label='Настроение')
            else:
                ax4.text(0.5, 0.5, 'Не удалось\nраспознать даты', ha='center', va='center', transform=ax4.transAxes)
        except Exception:
            ax4.text(0.5, 0.5, 'Ошибка дат', ha='center', va='center', transform=ax4.transAxes)
    else:
        ax4.text(0.5, 0.5, 'Нет данных\nо настроении', ha='center', va='center', transform=ax4.transAxes)
        ax4.axis('off')

    # --- СОХРАНЕНИЕ ---
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ 3D отчет сохранен: {output_path.resolve()}")
        
        if 'Cluster' in model_df.columns and SKLEARN_AVAILABLE:
            print("\n--- 🧬 Анализ кластеров ---")
            valid_clusters = model_df.dropna(subset=['Cluster'])
            if not valid_clusters.empty and 'Mood' in valid_clusters.columns:
                for cid in valid_clusters['Cluster'].unique():
                    subset = valid_clusters[valid_clusters['Cluster'] == cid]
                    count = len(subset)
                    avg_mood = subset['Mood'].mean()
                    pct = count / len(valid_clusters) * 100
                    print(f"Кластер {int(cid)}: {count} дней ({pct:.1f}%). Ср. настроение: {avg_mood:.1f}")
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        import traceback
        traceback.print_exc()
    finally:
        plt.close()

if __name__ == "__main__":
    run_dimensional_analysis()