import os
import json
import getpass
from pathlib import Path
from dotenv import load_dotenv
import paramiko
from stat import S_ISDIR
from tqdm import tqdm

# Загружаем переменные окружения
load_dotenv()

def remove_remote_directory(sftp, remote_path):
    """Рекурсивно удаляет удалённую директорию."""
    # Защита от удаления корня или важных системных папок
    if not remote_path or remote_path == "/" or remote_path == ".":
        raise ValueError(f"⛔ Попытка удалить опасный путь: {remote_path}")
        
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
    """Рекурсивно загружает локальную директорию с прогресс-баром."""
    # Создаём удалённую директорию, если нет
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)

    # Сбор всех файлов для точного подсчета прогресса (только файлы, т.к. папки создаются на лету)
    all_files = []
    for root, _, files in os.walk(local_dir):
        for name in files:
            all_files.append(os.path.join(root, name))

    with tqdm(total=len(all_files), desc="📤 Загрузка файлов", unit="file") as pbar:
        _upload_recursive(sftp, local_dir, remote_dir, pbar)

def _upload_recursive(sftp, local_dir, remote_dir, pbar):
    """Вспомогательная рекурсивная функция."""
    try:
        items = os.listdir(local_dir)
    except PermissionError:
        print(f"⚠️ Нет доступа к папке: {local_dir}")
        return

    for item in items:
        local_path = os.path.join(local_dir, item)
        remote_path = os.path.join(remote_dir, item).replace("\\", "/")

        if os.path.isdir(local_path):
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                sftp.mkdir(remote_path)
            _upload_recursive(sftp, local_path, remote_path, pbar)
        else:
            # Пропускаем временные файлы и системный мусор
            if item.startswith(".") or item.endswith("~"):
                pbar.update(1)
                continue
                
            try:
                sftp.put(local_path, remote_path)
            except Exception as e:
                print(f"\n⚠️ Ошибка загрузки {item}: {e}")
        pbar.update(1)

def main():
    print("📱 Синхронизация Obsidian с телефоном (Wipe & Replace)")
    
    # 1. Получение конфигурации
    config_file_str = os.getenv("SYNC_CONFIG_FILE", "config/config_sync.json")
    config_path = Path(config_file_str)
    
    if not config_path.exists():
        print(f"❌ Файл конфигурации не найден: {config_path}")
        print("💡 Скопируйте config/config_sync.example.json в config/config_sync.json и заполните его.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Читаем пути из конфига, но проверяем переменные окружения для переопределения
    source_dir = os.getenv("SYNC_SOURCE_DIR") or config.get("source_dir")
    remote_dir = os.getenv("SYNC_REMOTE_DIR") or config.get("remote_dir")
    ssh_host = config.get("ssh", {}).get("host")
    ssh_port = config.get("ssh", {}).get("port", 8022) # Стандартный порт Termux SSH
    ssh_user = config.get("ssh", {}).get("username")
    
    # Пароль берем ТОЛЬКО из env или запрашиваем вручную. НИКОГДА из файла!
    ssh_password = os.getenv("SSH_PASSWORD")

    if not all([source_dir, remote_dir, ssh_host, ssh_user]):
        print("❌ Ошибка: Не все параметры конфигурации заполнены.")
        return

    if not os.path.isdir(source_dir):
        print(f"❌ Локальная папка не найдена: {source_dir}")
        return

    # Безопасный запрос пароля, если нет в env
    if not ssh_password:
        print("🔒 Пароль не найден в переменной окружения SSH_PASSWORD.")
        ssh_password = getpass.getpass("Введите пароль SSH для телефона: ")

    # Подключение
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # В продакшене лучше использовать KnownHostsFile

    sftp = None
    try:
        print(f"🔌 Подключение к {ssh_user}@{ssh_host}:{ssh_port}...")
        ssh.connect(
            hostname=ssh_host,
            port=ssh_port,
            username=ssh_user,
            password=ssh_password,
            timeout=15,
            allow_agent=False,
            look_for_keys=False
        )
        sftp = ssh.open_sftp()
        print("✅ Подключение успешно!")

        # Проверка существования удаленной папки перед удалением
        try:
            sftp.stat(remote_dir)
            print(f"🗑️ Удаление старой базы: {remote_dir}")
            remove_remote_directory(sftp, remote_dir)
        except FileNotFoundError:
            print(f"ℹ️ Папка {remote_dir} не найдена, создадим новую.")

        print(f"📂 Создание папки: {remote_dir}")
        sftp.mkdir(remote_dir)

        print("🚀 Начало загрузки...")
        upload_directory(sftp, source_dir, remote_dir)

        print("\n🎉 Синхронизация завершена успешно!")
        print("💡 Не забудьте выполнить 'exit' в Termux на телефоне.")

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        if "Authentication failed" in str(e):
            print("💡 Проверьте правильность пароля и пользователя.")
        elif "Connection refused" in str(e):
            print("💡 Убедитесь, что на телефоне запущен SSH (команда 'sshd' в Termux).")
    finally:
        if sftp:
            sftp.close()
        ssh.close()
        print("🔌 Соединение закрыто.")

if __name__ == "__main__":
    main()