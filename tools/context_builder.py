import os
from pathlib import Path
from dotenv import load_dotenv
from core.utils import get_vault_path, get_data_dir
from core.parser import find_notes_by_tags, parse_knowledge_note


load_dotenv()

def build_notebooklm_context():
    print("Подготовка контекста для NotebookLM")
    
    vault = get_vault_path("VAULT_CODING")
    data_dir = get_data_dir()
    
    tags_str = os.getenv("NOTEBOOKLM_INCLUDE_TAGS", "#python,#идея,#теория")
    include_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    
    exclude_tags_str = os.getenv("NOTEBOOKLM_EXCLUDE_TAGS", "#черновик,#архив")
    exclude_tags = [t.strip() for t in exclude_tags_str.split(",") if t.strip()]
    
    print(f"Включаем теги: {include_tags}")
    print(f"Исключаем теги: {exclude_tags}")
    
    files = find_notes_by_tags(include_tags, exclude_tags, vault)
    
    if not files:
        print("Заметки не найдены")
        return
    
    output_content = []
    output_content.append("#Контекст базы знаний Obsdian\n")
    output_content.append(f"Сгенериованно автоматическию Всего заметок: {len(files)}\n")
    output_content.append("---\n\n")
    
    for file_path in files:
        try:
            # Парсим с удалением блоков Anki и meta
            text, meta = parse_knowledge_note(file_path, remove_anki_blocks=True)
            
            if not text.strip():
                continue
            
            title = file_path.stem
            output_content.append(f"# ТЕМА: {title}\n")
            output_content.append(text)
            output_content.append("\n\n---\n\n")
            
        except Exception as e:
            print(f"Ошибка обработки {file_path.name}: {e}")
    
    output_file = data_dir / "notebooklm_content.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(output_content))
        
    print(f"Готово! Файл контекста: {output_file}")
    print(f'Загрузи этот файт в Notebooklm как источник.')
    
if __name__ == "__main__":
    build_notebooklm_context()
    