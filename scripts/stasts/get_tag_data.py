import json
import os
import pprint

"""
Скрит который пробегается по всем файлам в твоей базе и забирае из нее все теги с текстом
(Примечание, только те теги которые указываются в тексте, а не в загловке файла)

И сохраняет их в Json с такой структурой:
[
    {
        "file": "Название файла",
        "тег": "данные с этим тегом"
    }
]
"""


# Совет: при проверке изменить значение переменной directory
DIRECTORY = "Путь до вашей базы"

def get_data_teg(directory, tag):
    result = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    flag = False
                    thought_lines = []
                    for line in f:
                        if tag in line:
                            flag = True
                            continue

                        if flag:
                            if line.strip() == "":
                                flag = False
                                if thought_lines:
                                    result.append({
                                        "file": file,
                                        tag: " ".join(thought_lines).strip()
                                    })
                                    thought_lines = []
                            else:
                                thought_lines.append(line.strip())
    return result

# Получаем данные
data = get_data_teg(DIRECTORY, "#мысль")

# Выводим данные в консоль
pprint.pprint(data)

# Записываем данные в JSON файл
with open("tags.json", "w", encoding="utf-8") as json_file:
    json.dump(data, json_file, ensure_ascii=False, indent=4)