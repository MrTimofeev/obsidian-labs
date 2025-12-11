import os
import json
from tqdm import tqdm
import paramiko
from stat import S_ISDIR


"""
Это вторая версия скрипта, которая позволит быстро и безболезненно синхронизировать мои заметки с компа на телефон
Проблема первой версии в том, что я пытался сделать сихронизацию двухсторонней, что добавляло некоторое количество проблем. 
Поэтому я решил изменить подход для синхронизации. 

Теперь при каждой синхронизации на телефоне будет полностью удаляться вся текущая база, а после копироваться обновленная (основная)
с ПК. Выбор такого подхода связан с тем что заметки на телефоне я почти не делаю. А если и буду делать то они заносятся в другое место,
А после переносятся уже в основую базу. 

В дальнейшем можно создать отдельную папку которая не будет затронута при синхронизации и скорее будет переноситься наоборот с телефона на пк.
По такому же принципу. Удаление и полная замена. В данному случае в с телефона и определнной папки (например 09.Телефон).

Для того чтобы произвести синхронизацию, запусти на телефоне термукс, и введи команду sshd, затем запусти скрипт, после завершения синхронизации
закрой ссерисю в термукс.
Для закрытия достаточно написать exit и закрыть termux
"""


def remove_remote_directory(sftp, remote_path):
    """Рекурсивно удаляет удалённую директорию (включая файлы и подпапки)."""
    try:
        files = sftp.listdir_attr(remote_path)
    except FileNotFoundError:
        return  # Нечего удалять

    for item in files:
        remote_item_path = os.path.join(remote_path, item.filename).replace("\\", "/")
        if S_ISDIR(item.st_mode):
            remove_remote_directory(sftp, remote_item_path)
        else:
            sftp.remove(remote_item_path)
    sftp.rmdir(remote_path)


def upload_directory(sftp, local_dir, remote_dir):
    """Рекурсивно загружает локальную директорию на удалённый сервер."""
    # Создаём удалённую директорию
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)

    # Собираем все файлы и папки для отображения прогресса
    all_items = []
    for root, dirs, files in os.walk(local_dir):
        for name in files:
            all_items.append(os.path.join(root, name))
        for name in dirs:
            all_items.append(os.path.join(root, name))

    with tqdm(total=len(all_items), desc="Загрузка файлов", unit="item") as pbar:
        _upload_recursive(sftp, local_dir, remote_dir, pbar)


def _upload_recursive(sftp, local_dir, remote_dir, pbar):
    """Вспомогательная рекурсивная функция для загрузки."""
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = os.path.join(remote_dir, item).replace("\\", "/")

        if os.path.isdir(local_path):
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                sftp.mkdir(remote_path)
            _upload_recursive(sftp, local_path, remote_path, pbar)
        else:
            sftp.put(local_path, remote_path)
        pbar.update(1)


def load_config(file_path):
    """Загружает конфигурацию из JSON-файла."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    config = load_config("config.json")

    source = config["source_dir"]
    remote = config["remote_dir"]
    ssh_config = config["ssh"]

    if not os.path.isdir(source):
        raise FileNotFoundError(f"Локальная папка не найдена: {source}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print("Подключение к телефону...")
        ssh.connect(
            hostname=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            password=ssh_config["password"],
            timeout=10
        )
        sftp = ssh.open_sftp()

        print(f"Удаление старой базы на телефоне: {remote}")
        remove_remote_directory(sftp, remote)

        print(f"Создание новой папки: {remote}")
        sftp.mkdir(remote)

        print("Загрузка новой базы...")
        upload_directory(sftp, source, remote)

        print("✅ Синхронизация завершена!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if 'sftp' in locals():
            sftp.close()
        ssh.close()