import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import os
from .utils import get_vault_path

# Макркеры для блоков кароточке Anki
ANKI_START = "<!-- ANKI_START ->"
ANKI_END = "<- ANKI_END --!>"

def parse_markdown_file(file_path: Path, remove_anki_blocks: bool = True) -> Tuple[str, Dict]:
    """
    Парсит заметку возвращает текст и метаданные
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    metadata = {}
    content_lines = []
    in_header = True
    
    for line in lines:
        if in_header:
            stripped = line.strip()
            # Разделитель шаблона
            if stripped == '---':
                in_header = False
                continue
            
            # Парсинг полей шапки
            if '::' in stripped:
                
                key, value = stripped.split('::', 1)
                key = key.strip()
                value = value.strip()
                
                if key == "Дата":
                    metadata["Дата"] = value
                elif key == "Теги":
                    metadata["Теги"] = value
            # Игнорируем пустые строки в шапке
        else:
            content_lines.append(line)
    
    # Собираем тело заметки
    content = "".join(content_lines)

    # Удаление блоков Anki
    if remove_anki_blocks:
        pattern = re.escape(ANKI_START) + r'.*?' + re.escape(ANKI_END)
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    return content.strip(), metadata

def find_notes_by_tags(
    include_tags: List[str], 
    exclude_tags: Optional[List[str]] = None,
    vault_path: Optional[Path] = None
) -> List[Path]:
    """
    Быстрый поиск по тегам.
    Проверяет ТОЛЬКО шапку файла (первые строки до '---').
    Игнорирует вхождения тегов в теле заметки.
    """
    if vault_path is None:
        vault_path = get_vault_path()
        
    if exclude_tags is None:
        exclude_tags = []

    found_files = []
    
    # Нормализуем теги для поиска (убираем решетку для сравнения, если нужно)
    # Но будем искать именно подстроку "#тег" в строке "Теги: #тег #другой"
    
    for root, _, files in os.walk(vault_path):
        # Пропуск служебных папок
        if any(x in root for x in ['.git', '.obsidian', 'node_modules', '__pycache__', '.data']):
            continue
            
        for file in files:
            if not file.endswith('.md'):
                continue
                
            file_path = Path(root) / file
            
            try:
                # Читаем только первые 20 строк (шапка обычно короче)
                # Это дает огромный прирост скорости
                with open(file_path, 'r', encoding='utf-8') as f:
                    header_found = False
                    file_tags_str = ""
                    
                    for _ in range(20):
                        line = f.readline()
                        if not line:
                            break
                        stripped = line.strip()
                        
                        if stripped == '---':
                            header_found = True
                            break
                        
                        if stripped.startswith("Теги:"):
                            file_tags_str = stripped
                    
                    # Если шапка не найдена корректно, пропускаем файл
                    if not header_found:
                        continue
                    
                    # Проверка тегов
                    # Функция проверки наличия тега в строке "Теги: #tag1 #tag2"
                    def has_tag_in_line(tags_line: str, target_tag: str) -> bool:
                        # target_tag ожидаем с # или без, приведем к виду с #
                        if not target_tag.startswith('#'):
                            target_tag = '#' + target_tag
                        # Простая проверка вхождения слова с границами
                        # Используем regex для точности, чтобы #python не нашелся в #cpython
                        pattern = rf'(?:^|\s|,){re.escape(target_tag)}(?:\s|$|,)'
                        return bool(re.search(pattern, tags_line))

                    # Логика исключений
                    is_excluded = any(has_tag_in_line(file_tags_str, t) for t in exclude_tags)
                    if is_excluded:
                        continue

                    # Логика включений (хотя бы один тег должен совпасть)
                    is_included = any(has_tag_in_line(file_tags_str, t) for t in include_tags)
                    
                    if is_included:
                        found_files.append(file_path)
                    
            except Exception:
                continue 

    return found_files

def extract_cards_from_file(file_path: Path) -> List[Dict[str, str]]:
    """Извлекает карточки из блока комментариев."""
    cards = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        start_idx = content.find(ANKI_START)
        end_idx = content.find(ANKI_END)
        
        if start_idx == -1 or end_idx == -1:
            return cards
            
        block = content[start_idx + len(ANKI_START):end_idx]
        
        current_q = None
        current_a_lines = []
        
        for line in block.split('\n'):
            s_line = line.strip()
            if not s_line: continue
            
            if s_line.startswith('Q:'):
                if current_q and current_a_lines:
                    cards.append({'question': current_q, 'answer': '\n'.join(current_a_lines).strip()})
                current_q = s_line[2:].strip()
                current_a_lines = []
            elif s_line.startswith('A:'):
                current_a_lines.append(s_line[2:].strip())
            elif current_a_lines:
                current_a_lines.append(s_line)
        
        if current_q and current_a_lines:
            cards.append({'question': current_q, 'answer': '\n'.join(current_a_lines).strip()})
            
    except Exception:
        pass
        
    return cards