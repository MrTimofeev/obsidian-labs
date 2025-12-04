import os
import time
import json
from tqdm import tqdm
import paramiko
from stat import S_ISDIR

# Логирование изменений
def log_changes(message):
    with open("sync_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Получение всех файлов с датой последнего изменения (локально)
def get_all_files(directory):
    files = {}
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for filename in filenames:
            if filename.startswith('.'):
                continue
            file_path = os.path.join(root, filename)
            last_modified = os.path.getmtime(file_path)
            relative_path = os.path.relpath(file_path, directory)
            files[relative_path] = last_modified
    return files

# Получение всех файлов с датой последнего изменения (удаленно)
def get_remote_files(sftp, remote_directory):
    files = {}
    

    def walk_remote_dir(path):
        for item in sftp.listdir_attr(path):
            if ".obsidian" in path or ".trash" in path:
                continue
            item_path = f"{path}/{item.filename}"
            if item.longname.startswith('d'):
                walk_remote_dir(item_path)
            else:
                relative_path = os.path.relpath(item_path, remote_directory)
                files[relative_path] = item.st_mtime

    walk_remote_dir(remote_directory)
    return files

# Функция для создания директорий на удаленной стороне, если их нет
def create_remote_directory(sftp, remote_file_path):
    remote_dir = os.path.dirname(remote_file_path)
    try:
        sftp.stat(remote_dir)  # Проверка существования директории
    except FileNotFoundError:
        # Директория не существует, создаем её
        create_remote_directory(sftp, remote_dir)  # Рекурсивный вызов
        sftp.mkdir(remote_dir)  # Создание текущей директории


# Синхронизация файлов
def sync_directories(source_dir, remote_dir, sftp):
    source_files = get_all_files(source_dir)
    remote_files = get_remote_files(sftp, remote_dir)

    all_files = set(source_files.keys()).union(remote_files.keys())
    with tqdm(total=len(all_files), desc="Синхронизация файлов") as pbar:
        for relative_path in all_files:
            source_modified = source_files.get(relative_path)
            remote_modified = remote_files.get(relative_path)
            linux_path = relative_path.replace("\\", "/")
            file_name = os.path.basename(relative_path)

            # Создание удаленной директории, если её нет
            create_remote_directory(sftp, f"{remote_dir}/{linux_path}")


            if source_modified and remote_modified:
                if source_modified > remote_modified:
                    sftp.put(os.path.join(source_dir, relative_path), f"{remote_dir}/{linux_path}")
                    log_changes(f"Копирование | из ПК - телефон | {file_name} ")
                elif remote_modified > source_modified:
                    sftp.get(f"{remote_dir}/{linux_path}", os.path.join(source_dir, relative_path))
                    log_changes(f"Копирование | из телефон - ПК | {file_name} ")
            elif source_modified and not remote_modified:
                sftp.put(os.path.join(source_dir, relative_path), f"{remote_dir}/{linux_path}")
                log_changes(f"Копирование | из ПК - телефон (только в ПК) | {file_name} ")
            elif not source_modified and remote_modified:
                sftp.get(f"{remote_dir}/{linux_path}", os.path.join(source_dir, relative_path))
                log_changes(f"Копирование | из телефон - ПК (только в телефон) | {file_name} ")

            pbar.update(1)

# Загрузка конфигурации из JSON-файла
def load_config(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

if __name__ == "__main__":
    config = load_config("config.json")
    
    source = config["source_dir"]
    remote = config["remote_dir"]
    ssh_config = config["ssh"]

    # Подключение через Paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            hostname=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            password=ssh_config["password"]
        )
        # Создание SFTP-соединения
        sftp = ssh.open_sftp()

        # Создание удаленной директории, если ее нет
        try:
            sftp.stat(remote)
        except FileNotFoundError:
            sftp.mkdir(remote)

        # Выполнение синхронизации
        sync_directories(source, remote, sftp)

    finally:
        # Закрытие соединений
        if 'sftp' in locals():
            sftp.close()
        ssh.close()
