import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_vault_path(vault_key: str = None) -> Path:
    """Возвращает путь к корню базы знаний Obsidian."""
    if vault_key is None:
        vault_key = os.getenv("DEFAULT_VAULT_KEY")
        if not vault_key:
            vault_key = "OBSIDIAN_VAULT_PATH"
            
    path_str = os.getenv(vault_key)
    
    if not path_str:
        raise ValueError("Переменая окружения OBSDIAN_VAULT_PATH не найдена в .env")

    return Path(path_str)

def get_congig_path(config_name: str) -> Path:
    """Возвращает полный путь к файлу конфигурации в папке config/."""
    # ПРоверяем, есьт ли полный путь в env, иначе строим относительно проекта
    env_var = f"CONFIG_{config_name.upper().replace('.','_')}"
    custom_path = os.getenv(env_var)
    
    if custom_path:
        return Path(custom_path)
    
    # По умолчанию ищем в папке config/ рядом со скриптом или в корне проекта
    # Для простоты предполагаем, что скрипт запускается из корня или мы идем вверх
    base_dir = Path(__file__).parent.parent
    config_dir = base_dir / "config"
    return config_dir / config_name

def load_json_config(config_name: str) -> dict:
    """Загружаем JSON конфиг по имени файла."""
    path = get_congig_path(config_name)
    if not path.exists():
        # Пробуем добавить .example если файл не найден (для обратной совместимости)
        if not path.with_suffix(".json").exists():
            # Если это вызов без расширения, добавим его
            if not path.suffix:
                path = path.with_suffix('.json')
        
        if not path.exists():
            raise FileNotFoundError(f"Файл конфигурации не найден: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def ensure_dir(directory: Path) -> None:
    """Создает директорию, если она не существует."""
    directory.mkdir(parents=True, exist_ok=True)

def get_data_dir() -> Path:
    """Возвращает путь к папке .data для временных файлов"""
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / ".data"
    ensure_dir(data_dir)
    return data_dir