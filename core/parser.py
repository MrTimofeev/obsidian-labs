import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import os
import json
import pandas as pd
from .utils import get_vault_path, get_data_dir

# Макркеры для блоков кароточке Anki
ANKI_START = "<!-- ANKI_START ->"
ANKI_END = "<- ANKI_END --!>"

# ==============================================================================
# 1. ИНСТРУМЕНТЫ ДЛЯ ЛИЧНОЙ БАЗЫ (Ежедневник, Трекинг)
# ==============================================================================


def parse_personal_note(file_path: Path) -> Tuple[str, Dict, Dict]:
    """
    Парсит заметку из личной базы и возвращает метаданные, текст и статистику
    Returns:
        (clean_body_text, metadata_dict, stats_dict)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    metadata = {}
    body_lines = []
    stats = {}

    state = 'HEADER'  # HEADER, BODY, STATS

    for line in lines:
        stripped = line.strip()

        # Детектор разделителей
        if stripped == '---':
            if state == 'HEADER':
                state = 'BODY'
                continue
            elif state == 'BODY':
                state = 'STATS'
                continue

        # Логика по состояниям
        if state == 'HEADER':
            if '::' in stripped:
                key, val = stripped.split('::', 1)
                metadata[key.strip()] = val.strip()

        elif state == 'BODY':
            body_lines.append(line)

        elif state == 'STATS':
            if '::' in stripped:
                key, val = stripped.split('::', 1)
                k = key.strip().replace("-", "")
                v = val.strip()
                if k and v:  # Игнорируем пустые
                    stats[k] = v

    clean_body = "".join(body_lines).strip()

    return clean_body, metadata, stats


# ==============================================================================
# 2. ИНСТРУМЕНТЫ ДЛЯ БАЗЫ ЗНАНИЙ (Programming, Notes, SRS)
# ==============================================================================

def parse_knowledge_note(file_path: Path, remove_anki_blocks: bool = True) -> Tuple[str, Dict]:
    """
    Парсит заметку из базы знаний и возвращает весь текст без Anki блоков если указано и метаданные
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    metadata = {}

    # 1. Попытка извлечь YAML (если есть)
    yaml_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if yaml_match:
        # Простой парсинг YAML
        for line in yaml_match.group(1).split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                metadata[k.strip()] = v.strip()
        content = content[yaml_match.end():]

    # 2. Удаление Anki блоков
    if remove_anki_blocks:
        pattern = re.escape(ANKI_START) + r'.*?' + re.escape(ANKI_END)
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    return content.strip(), metadata

def extract_anki_data_from_file(file_path: Path) -> List[Dict]:
    """
    Извлекает карточки Anki и связывает их с тегами из метаданных файла.
    Returns:
        Список словарей: 
        {
            'question': str, 
            'answer': str, 
            'tags': ['#tag1', '#tag2'], 
            'source_file': str
        }
    """
    cards = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Извлекаем теги
        file_tags = []
        for line in content.split('\n'):
            if line.strip().startswith("Теги::"):
                tags_str = line.split("::", 1)[1].strip()
                file_tags = [t.strip() for t in tags_str.split() if t.startswith('#')]
                break
        
        # 2. Ищем блоки Anki
        start_idx = 0
        while True:
            start_idx = content.find(ANKI_START, start_idx)
            if start_idx == -1: break
            
            end_idx = content.find(ANKI_END, start_idx + len(ANKI_START))
            if end_idx == -1: break
            
            block = content[start_idx + len(ANKI_START):end_idx]
            
            # Парсим Q: и A: внутри блока
            current_q = None
            current_a_lines = []
            
            for line in block.split('\n'):
                s_line = line.strip()
                if not s_line: continue
                
                if s_line.startswith('Q:'):
                    if current_q and current_a_lines:
                        cards.append({
                            'question': current_q,
                            'answer': '\n'.join(current_a_lines).strip(),
                            'tags': file_tags,
                            'source_file': str(file_path)
                        })
                    current_q = s_line[2:].strip()
                    current_a_lines = []
                elif s_line.startswith('A:'):
                    current_a_lines.append(s_line[2:].strip())
                elif current_a_lines:
                    current_a_lines.append(s_line)
            
            # Добавляем последнюю карточку в блоке
            if current_q and current_a_lines:
                cards.append({
                    'question': current_q,
                    'answer': '\n'.join(current_a_lines).strip(),
                    'tags': file_tags,
                    'source_file': str(file_path)
                })
                
            start_idx = end_idx + len(ANKI_END)
            
    except Exception as e:
        print(f"Error parsing Anki in {file_path}: {e}")
        
    return cards
            
def find_notes_by_tags(
    include_tags: List[str],
    exclude_tags: Optional[List[str]] = None,
    vault_path: Optional[Path] = None
) -> List[Path]:
    """
    Поиск заметок в Базе Знаний по тегам в шапке или теле.
    """
    if vault_path is None:
        # По умолчанию база кодинга
        vault_path = get_vault_path("VAULT_CODING")

    if exclude_tags is None:
        exclude_tags = []

    found_files = []

    def has_tag(text: str, tag: str) -> bool:
        safe_tag = re.escape(tag.lstrip('#'))
        pattern = rf'(?:^|\s|,|:)#{safe_tag}(?:\s|$|,)'
        return bool(re.search(pattern, text, re.IGNORECASE))

    for root, _, files in os.walk(vault_path):
        if any(x in root for x in ['.git', '.obsidian', 'node_modules', '__pycache__', '.data']):
            continue

        for file in files:
            if not file.endswith('.md'):
                continue

            file_path = Path(root) / file

            try:
                # Читаем только начало для скорости
                with open(file_path, 'r', encoding='utf-8') as f:
                    header_snippet = f.read(1000)

                if any(has_tag(header_snippet, t) for t in exclude_tags):
                    continue

                if any(has_tag(header_snippet, t) for t in include_tags):
                    found_files.append(file_path)

            except Exception:
                continue

    return found_files
