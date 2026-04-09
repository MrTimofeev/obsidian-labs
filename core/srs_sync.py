import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
import os
from datetime import datetime, timezone

from .models import SrsCard, SrsTag, SrsReviewLog
from .parser import extract_anki_data_from_file
from .utils import get_vault_path

def generate_card_hash(question: str) -> str:
    """Генерирует уникальный хэш для вопроса."""
    normalized = " ".join(question.lower().split())
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def sync_srs_cards(session: Session, vault_path: Path = None):
    """
    Сканирует базу знаний и обновляет карточки в БД.
    """
    if vault_path is None:
        vault_path = get_vault_path("VAULT_CODING")
        
    print("🔍 Сканирование карточек в базе знаний...")
    
    # Ищем все файлы с тегами, которые могут содержать карточки
    # Например, ищем файлы с тегом #повторить или просто все .md в определенной папке
    # Для надежности найдем все .md файлы, а парсер сам проверит наличие блоков
    all_md_files = []
    for root, _, files in os.walk(vault_path):
        if any(x in root for x in ['.git', '.obsidian', '__pycache__']):
            continue
        for f in files:
            if f.endswith('.md'):
                all_md_files.append(Path(root) / f)
                
    print(f"📂 Найдено файлов: {len(all_md_files)}")
    
    processed_hashes = set()
    new_cards_count = 0
    updated_cards_count = 0
    
    for file_path in all_md_files:
        try:
            cards_data = extract_anki_data_from_file(file_path)
            
            for data in cards_data:
                q_hash = generate_card_hash(data['question'])
                processed_hashes.add(q_hash)
                
                # Проверяем, есть ли карточка
                card = session.query(SrsCard).filter_by(card_hash=q_hash).first()
                
                if card:
                    # Карточка существует
                    if card.is_archived:
                        card.is_archived = False # Разархивируем, если вернулась
                    
                    # Проверяем, изменился ли текст
                    if card.question != data['question'] or card.answer != data['answer']:
                        card.question = data['question']
                        card.answer = data['answer']
                        card.updated_at = datetime.now(timezone.utc)
                        updated_cards_count += 1
                        
                else:
                    # Новая карточка
                    new_card = SrsCard(
                        card_hash=q_hash,
                        question=data['question'],
                        answer=data['answer'],
                        source_file=str(file_path.relative_to(vault_path)),
                        is_archived=False
                    )
                    
                    # Добавляем теги
                    for tag_name in data['tags']:
                        tag = session.query(SrsTag).filter_by(name=tag_name).first()
                        if not tag:
                            tag = SrsTag(name=tag_name)
                            session.add(tag)
                        new_card.tags.append(tag)
                        
                    session.add(new_card)
                    new_cards_count += 1
                    
        except Exception as e:
            print(f"⚠️ Ошибка обработки файла {file_path}: {e}")

    # Архивируем карточки, которых нет в файлах
    all_known_hashes = {c.card_hash for c in session.query(SrsCard.card_hash).filter_by(is_archived=False).all()}
    to_archive = all_known_hashes - processed_hashes
    
    archived_count = 0
    for hash_val in to_archive:
        card = session.query(SrsCard).filter_by(card_hash=hash_val).first()
        if card:
            card.is_archived = True
            archived_count += 1
            
    session.commit()
    print(f"✅ Синхронизация завершена.")
    print(f"   🆕 Новых: {new_cards_count}")
    print(f"   🔄 Обновлено: {updated_cards_count}")
    print(f"   🗑 Архивировано: {archived_count}")
