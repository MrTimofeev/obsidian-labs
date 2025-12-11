import json
import os
import pprint

"""
Скрит который пробегается по всем файлам в твоей базе и собирает всю статистику

И сохраняет их в Json с такой структурой:
[
    {
        "дата": "дата из заголовка файла"
        "данные": {
            "название_статистики": "значение"
        }
    }
]
"""


# Совет: при проверке изменить значение переменной directory
DIRECTORY = "путь до вашей базы"


def get_data_teg(directory):
    result = []

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".md"):
                continue
            
            file_path = os.path.join(root, file)
            
            if "Ежедневное" not in file_path:
                continue
            
            data = {}
            date = None
            
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "::" in line:
                        key, value = line.split("::", 1)
                        key = key.replace("-", "").strip()
                        value = value.strip()
                        
                        if key == "Дата":
                            date = value
                        else:
                            data[key] = value
                            
            if date is not None:
                if data:
                    result.append({
                        "дата": date,
                        "данные": data
                    })
    return result


def save_data_json(directory):
    # Получаем данные
    data = get_data_teg(directory)


    # Записываем данные в JSON файл
    with open("stats.json", "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

save_data_json(DIRECTORY)