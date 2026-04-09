import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from core.utils import get_vault_path
from core.parser import parse_personal_note
from core.database import init_db, get_session
from core.models import DailyMetric, DailyNote

load_dotenv()


def sync_obsidian_to_db():
    print("🔄 Синхронизация Личной Базы -> SQLite DB...")
    init_db()

    vault = get_vault_path("VAULT_PERSONAL")
    daily_subfolder = os.getenv("DAILY_LOGS_SUBFOLDER", "01. Ежедневное")
    target_dir = vault / daily_subfolder

    if not target_dir.exists():
        print(f"❌ Папка не найдена: {target_dir}")
        return

    session = get_session()
    files_processed = 0

    try:
        for root, _, files in os.walk(target_dir):
            for file in files:
                if not file.endswith(".md"):
                    continue

                file_path = Path(root) / file
                files_processed += 1

                try:
                    # 1. Парсим личную заметку
                    body_text, metadata, stats_raw = parse_personal_note(
                        file_path)

                    date_str = metadata.get("Дата")
                    if not date_str:
                        continue

                    try:
                        log_date = datetime.strptime(
                            date_str, "%d.%m.%y").date()
                    except ValueError:
                        continue

                    # 2. Сохраняем ТОЛЬКО ТЕЛО ЗАМЕТКИ (Дневник)
                    note = session.query(DailyNote).filter_by(
                        log_date=log_date).first()
                    if note:
                        note.content_text = body_text
                        note.file_name = file
                        note.relative_path = str(file_path.relative_to(vault))
                    else:
                        note = DailyNote(
                            log_date=log_date,
                            file_name=file,
                            relative_path=str(file_path.relative_to(vault)),
                            content_text=body_text
                        )
                        session.add(note)

                    # 3. Сохраняем СТАТИСТИКУ
                    for key, raw_value in stats_raw.items():
                        m_type, m_value = _determine_type(raw_value)

                        existing = session.query(DailyMetric).filter_by(
                            log_date=log_date, metric_name=key
                        ).first()

                        if existing:
                            setattr(existing, f'value_{m_type}', m_value)
                            if m_type != 'num':
                                existing.value_num = None
                            if m_type != 'bool':
                                existing.value_bool = None
                            if m_type != 'text':
                                existing.value_text = None
                        else:
                            new_m = DailyMetric(
                                log_date=log_date, metric_name=key)
                            setattr(new_m, f'value_{m_type}', m_value)
                            session.add(new_m)

                except Exception as e:
                    print(f"⚠️ Ошибка {file}: {e}")

        session.commit()
        print(f"✅ Готово! Файлов: {files_processed}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()


def _determine_type(value: str):
    if value.lower() in ['да', 'нет', 'true', 'false']:
        return 'bool', value.lower() in ['да', 'true']
    try:
        return 'num', float(value)
    except:
        return 'text', value


if __name__ == "__main__":
    sync_obsidian_to_db()
