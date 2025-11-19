import os
import sys
import json
import shutil
import sqlite3
import uuid
from colorama import Fore, Style, init
from typing import Optional
import configparser
import traceback
from datetime import datetime

# 初始化 colorama
init()

# 定义表情符号常量
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "WARNING": "⚠️",
}

class ConfigError(Exception):
    """配置错误异常"""
    pass

class SimpleTranslator:
    """Простой класс для перевода сообщений"""
    def __init__(self):
        self.translations = {
            'reset.current_file_not_found': 'Текущий файл не найден',
            'reset.current_backup_created': 'Создана резервная копия текущего файла',
            'reset.storage_updated': 'Файл storage.json обновлен',
            'reset.update_failed': 'Ошибка обновления: {error}',
            'reset.sqlite_not_found': 'SQLite база данных не найдена',
            'reset.updating_sqlite': 'Обновление SQLite базы данных',
            'reset.updating_pair': 'Обновление пары',
            'reset.sqlite_updated': 'SQLite база данных обновлена',
            'reset.sqlite_update_failed': 'Ошибка обновления SQLite: {error}',
            'reset.machine_id_backup_created': 'Создана резервная копия machineId файла',
            'reset.backup_creation_failed': 'Не удалось создать резервную копию: {error}',
            'reset.machine_id_updated': 'Файл machineId обновлен',
            'reset.machine_id_update_failed': 'Ошибка обновления machineId: {error}',
            'reset.updating_system_ids': 'Обновление системных ID',
            'reset.system_ids_update_failed': 'Ошибка обновления системных ID: {error}',
            'reset.windows_machine_guid_updated': 'Windows MachineGuid обновлен',
            'reset.permission_denied': 'Доступ запрещен. Запустите от имени администратора',
            'reset.update_windows_machine_guid_failed': 'Ошибка обновления MachineGuid: {error}',
            'reset.windows_machine_id_updated': 'Windows MachineId обновлен',
            'reset.sqm_client_key_not_found': 'Ключ SQMClient не найден',
            'reset.update_windows_machine_id_failed': 'Ошибка обновления MachineId: {error}',
            'reset.update_windows_system_ids_failed': 'Ошибка обновления системных ID Windows: {error}',
            'reset.macos_platform_uuid_updated': 'macOS Platform UUID обновлен',
            'reset.failed_to_execute_plutil_command': 'Не удалось выполнить команду plutil',
            'reset.update_macos_system_ids_failed': 'Ошибка обновления системных ID macOS: {error}',
            'reset.starting': 'Начало сброса Machine ID',
            'reset.ids_to_reset': 'Новые ID для установки',
            'reset.confirm': 'Подтвердите сброс Machine ID. Это действие нельзя отменить! (y/n)',
            'reset.operation_cancelled': 'Операция отменена',
            'reset.success': 'Сброс Machine ID завершен успешно',
            'reset.process_error': 'Ошибка процесса: {error}',
            'reset.title': 'Сброс Machine ID',
            'reset.press_enter': 'Нажмите Enter для продолжения',
            'reset.generating_new_ids': 'Генерация новых Machine ID...',
            'reset.backing_up_current': 'Создание резервной копии текущих ID...',
        }
    
    def get(self, key: str, **kwargs) -> str:
        """Получить переведенное сообщение"""
        msg = self.translations.get(key, key)
        if kwargs:
            try:
                return msg.format(**kwargs)
            except KeyError:
                return msg
        return msg

def is_arch_linux() -> bool:
    """Проверить, является ли система Arch Linux"""
    if sys.platform != "linux":
        return False
    # Проверяем наличие файла /etc/arch-release (стандартный способ определения Arch Linux)
    return os.path.exists("/etc/arch-release")

def get_user_documents_path() -> str:
    """Получить путь к папке Documents пользователя"""
    if sys.platform == "win32":
        # Windows
        documents = os.path.join(os.path.expanduser("~"), "Documents")
    elif sys.platform == "darwin":
        # macOS
        documents = os.path.expanduser("~/Documents")
    else:
        # Linux (включая Arch Linux)
        documents = os.path.expanduser("~/Documents")
    
    return documents

def get_cursor_machine_id_path(translator=None) -> str:
    """Получить путь к файлу machineId Cursor"""
    if sys.platform == "win32":
        # Windows: %APPDATA%\Cursor\User\machineId
        appdata = os.getenv("APPDATA")
        if appdata:
            return os.path.join(appdata, "Cursor", "User", "machineId")
        else:
            return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Cursor", "User", "machineId")
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/Cursor/User/machineId
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Cursor", "User", "machineId")
    else:
        # Linux: ~/.config/Cursor/User/machineId
        return os.path.join(os.path.expanduser("~"), ".config", "Cursor", "User", "machineId")

def get_config(translator=None) -> Optional[configparser.ConfigParser]:
    """Получить конфигурацию из файла config.ini"""
    try:
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        
        if not os.path.exists(config_file):
            print(f"{Fore.YELLOW}⚠️  Файл конфигурации не найден: {config_file}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}ℹ️  Создание файла конфигурации с настройками по умолчанию...{Style.RESET_ALL}")
            
            # Создать директорию если не существует
            os.makedirs(config_dir, exist_ok=True)
            
            # Создать конфигурацию по умолчанию
            config = configparser.ConfigParser()
            
            # Windows пути по умолчанию
            if sys.platform == "win32":
                appdata = os.getenv("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
                config.add_section('WindowsPaths')
                config.set('WindowsPaths', 'storage_path', 
                          os.path.join(appdata, "Cursor", "User", "globalStorage", "storage.json"))
                config.set('WindowsPaths', 'sqlite_path', 
                          os.path.join(appdata, "Cursor", "User", "globalStorage", "state.vscdb"))
            
            # macOS пути по умолчанию
            elif sys.platform == "darwin":
                config.add_section('MacPaths')
                config.set('MacPaths', 'storage_path', 
                          os.path.join(os.path.expanduser("~"), "Library", "Application Support", 
                                      "Cursor", "User", "globalStorage", "storage.json"))
                config.set('MacPaths', 'sqlite_path', 
                          os.path.join(os.path.expanduser("~"), "Library", "Application Support", 
                                      "Cursor", "User", "globalStorage", "state.vscdb"))
            
            # Arch Linux пути по умолчанию
            elif is_arch_linux():
                config.add_section('ArchPaths')
                config.set('ArchPaths', 'storage_path', 
                          os.path.join(os.path.expanduser("~"), ".config", "Cursor", "User", 
                                      "globalStorage", "storage.json"))
                config.set('ArchPaths', 'sqlite_path', 
                          os.path.join(os.path.expanduser("~"), ".config", "Cursor", "User", 
                                      "globalStorage", "state.vscdb"))
            
            # Linux пути по умолчанию (для других дистрибутивов)
            else:
                config.add_section('LinuxPaths')
                config.set('LinuxPaths', 'storage_path', 
                          os.path.join(os.path.expanduser("~"), ".config", "Cursor", "User", 
                                      "globalStorage", "storage.json"))
                config.set('LinuxPaths', 'sqlite_path', 
                          os.path.join(os.path.expanduser("~"), ".config", "Cursor", "User", 
                                      "globalStorage", "state.vscdb"))
            
            # Сохранить конфигурацию
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            print(f"{Fore.GREEN}✅ Файл конфигурации создан: {config_file}{Style.RESET_ALL}")
            return config
        else:
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            return config
    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка при чтении конфигурации: {e}{Style.RESET_ALL}")
        return None

class MachineIDResetter:
    def __init__(self, translator=None, config=None):
        self.translator = translator if translator else SimpleTranslator()
        
        # Получить конфигурацию
        if config is None:
            config = get_config(self.translator)
        
        if config is None:
            raise ConfigError("Не удалось загрузить конфигурацию")
        
        # 根据操作系统获取路径
        if sys.platform == "win32":  # Windows
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("APPDATA Environment Variable Not Set")
            
            if not config.has_section('WindowsPaths'):
                raise ConfigError("WindowsPaths section not found in config")
                
            self.db_path = config.get('WindowsPaths', 'storage_path')
            self.sqlite_path = config.get('WindowsPaths', 'sqlite_path')
            
        elif sys.platform == "darwin":  # macOS
            if not config.has_section('MacPaths'):
                raise ConfigError("MacPaths section not found in config")
                
            self.db_path = config.get('MacPaths', 'storage_path')
            self.sqlite_path = config.get('MacPaths', 'sqlite_path')
            
        elif is_arch_linux():  # Arch Linux
            if not config.has_section('ArchPaths'):
                raise ConfigError("ArchPaths section not found in config")
                
            self.db_path = config.get('ArchPaths', 'storage_path')
            self.sqlite_path = config.get('ArchPaths', 'sqlite_path')
            
        elif sys.platform == "linux":  # Linux (другие дистрибутивы)
            if not config.has_section('LinuxPaths'):
                raise ConfigError("LinuxPaths section not found in config")
                
            self.db_path = config.get('LinuxPaths', 'storage_path')
            self.sqlite_path = config.get('LinuxPaths', 'sqlite_path')
            
        else:
            raise NotImplementedError(f"Not Supported OS: {sys.platform}")
    
    def generate_new_ids(self):
        """Генерация новых Machine ID"""
        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.generating_new_ids')}{Style.RESET_ALL}")
        
        # Генерируем новые UUID для всех типов ID
        new_ids = {
            "telemetry.devDeviceId": str(uuid.uuid4()),
            "telemetry.macMachineId": str(uuid.uuid4()),
            "telemetry.machineId": str(uuid.uuid4()),
            "telemetry.sqmId": str(uuid.uuid4()),
            "storage.serviceMachineId": str(uuid.uuid4())
        }
        
        return new_ids
    
    def backup_current_ids(self):
        """Создание резервной копии текущих ID"""
        print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.backing_up_current')}{Style.RESET_ALL}")
        
        try:
            current_ids = {}
            
            # Читаем текущие ID из storage.json
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        storage_data = json.load(f)
                        current_ids.update({
                            "telemetry.devDeviceId": storage_data.get("telemetry.devDeviceId", ""),
                            "telemetry.macMachineId": storage_data.get("telemetry.macMachineId", ""),
                            "telemetry.machineId": storage_data.get("telemetry.machineId", ""),
                            "telemetry.sqmId": storage_data.get("telemetry.sqmId", ""),
                            "storage.serviceMachineId": storage_data.get("storage.serviceMachineId", "")
                        })
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} Не удалось прочитать текущие ID из storage.json: {e}{Style.RESET_ALL}")
            
            # Читаем текущие ID из SQLite
            if os.path.exists(self.sqlite_path):
                try:
                    conn = sqlite3.connect(self.sqlite_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS ItemTable (
                            key TEXT PRIMARY KEY,
                            value TEXT
                        )
                    """)
                    
                    keys = ["telemetry.devDeviceId", "telemetry.macMachineId", 
                           "telemetry.machineId", "telemetry.sqmId", "storage.serviceMachineId"]
                    for key in keys:
                        cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                        result = cursor.fetchone()
                        if result and not current_ids.get(key):
                            current_ids[key] = result[0]
                    
                    conn.close()
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} Не удалось прочитать текущие ID из SQLite: {e}{Style.RESET_ALL}")
            
            # Сохраняем резервную копию
            if current_ids:
                backup_dir = os.path.dirname(self.db_path)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(backup_dir, f"storage.json.bak.{timestamp}")
                
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(current_ids, f, indent=4)
                
                print(f"{Fore.GREEN}{EMOJI['BACKUP']} Резервная копия сохранена: {backup_file}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} Не найдено текущих ID для резервного копирования{Style.RESET_ALL}")
                return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} Ошибка при создании резервной копии: {e}{Style.RESET_ALL}")
            return False
    
    def update_current_file(self, ids):
        """更新当前的storage.json文件"""
        try:
            if not os.path.exists(self.db_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.current_file_not_found')}: {self.db_path}{Style.RESET_ALL}")
                return False
            
            # 读取当前文件
            with open(self.db_path, "r", encoding="utf-8") as f:
                current_data = json.load(f)
            
            # 创建当前文件的备份
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.restore_bak.{timestamp}"
            shutil.copy2(self.db_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.current_backup_created')}: {backup_path}{Style.RESET_ALL}")
            
            # 更新ID
            current_data.update(ids)
            
            # 保存更新后的文件
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=4)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.storage_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def update_sqlite_db(self, ids):
        """更新SQLite数据库中的ID"""
        try:
            if not os.path.exists(self.sqlite_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_not_found')}: {self.sqlite_path}{Style.RESET_ALL}")
                return False
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_sqlite')}...{Style.RESET_ALL}")
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            for key, value in ids.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('reset.updating_pair')}: {key}{Style.RESET_ALL}")
            
            conn.commit()
            conn.close()
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.sqlite_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def update_machine_id_file(self, dev_device_id):
        """更新machineId文件"""
        try:
            machine_id_path = get_cursor_machine_id_path(self.translator)
            
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
            
            # 备份当前文件（如果存在）
            if os.path.exists(machine_id_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{machine_id_path}.restore_bak.{timestamp}"
                try:
                    shutil.copy2(machine_id_path, backup_path)
                    print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('reset.machine_id_backup_created')}: {backup_path}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_creation_failed', error=str(e))}{Style.RESET_ALL}")
            
            # 写入新的ID
            with open(machine_id_path, "w", encoding="utf-8") as f:
                f.write(dev_device_id)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.machine_id_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.machine_id_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def update_system_ids(self, ids):
        """更新系统级ID（特定于操作系统）"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_system_ids')}...{Style.RESET_ALL}")
            
            if sys.platform.startswith("win"):
                self._update_windows_system_ids(ids)
            elif sys.platform == "darwin":
                self._update_macos_system_ids(ids)
            
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.system_ids_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    def _update_windows_system_ids(self, ids):
        """更新Windows系统ID"""
        try:
            import winreg
            
            # 更新MachineGuid
            guid = ids.get("telemetry.devDeviceId", "")
            if guid:
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        "SOFTWARE\\Microsoft\\Cryptography",
                        0,
                        winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                    )
                    winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, guid)
                    winreg.CloseKey(key)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_guid_updated')}{Style.RESET_ALL}")
                except PermissionError:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied')}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_guid_failed', error=str(e))}{Style.RESET_ALL}")
            
            # 更新SQMClient MachineId
            sqm_id = ids.get("telemetry.sqmId", "")
            if sqm_id:
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\SQMClient",
                        0,
                        winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                    )
                    winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, sqm_id)
                    winreg.CloseKey(key)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_id_updated')}{Style.RESET_ALL}")
                except FileNotFoundError:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.sqm_client_key_not_found')}{Style.RESET_ALL}")
                except PermissionError:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied')}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_id_failed', error=str(e))}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_system_ids_failed', error=str(e))}{Style.RESET_ALL}")
    
    def _update_macos_system_ids(self, ids):
        """更新macOS系统ID"""
        try:
            uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
            if os.path.exists(uuid_file):
                mac_id = ids.get("telemetry.macMachineId", "")
                if mac_id:
                    cmd = f'sudo plutil -replace "UUID" -string "{mac_id}" "{uuid_file}"'
                    result = os.system(cmd)
                    if result == 0:
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.macos_platform_uuid_updated')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.failed_to_execute_plutil_command')}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_macos_system_ids_failed', error=str(e))}{Style.RESET_ALL}")
    
    def check_cursor_running(self):
        """Проверка, запущен ли Cursor"""
        try:
            if sys.platform == "win32":
                # Используем tasklist для проверки процессов на Windows
                try:
                    import subprocess
                    result = subprocess.run(
                        ['tasklist', '/FI', 'IMAGENAME eq Cursor.exe', '/FO', 'CSV'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if 'Cursor.exe' in result.stdout:
                        # Пытаемся извлечь PID из вывода
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:  # Есть заголовок и данные
                            # Формат CSV: "Image Name","PID","Session Name",...
                            parts = lines[1].split('","')
                            if len(parts) > 1:
                                try:
                                    pid = int(parts[1].strip('"'))
                                    return True, pid
                                except (ValueError, IndexError):
                                    return True, None
                        return True, None
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                    # Если tasklist не работает, пробуем через wmic
                    try:
                        result = subprocess.run(
                            ['wmic', 'process', 'where', 'name="Cursor.exe"', 'get', 'ProcessId'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if 'ProcessId' in result.stdout and result.stdout.strip() != 'ProcessId':
                            # Есть процессы
                            return True, None
                    except Exception:
                        pass
                return False, None
            elif sys.platform == "darwin":
                # Используем pgrep на macOS
                try:
                    import subprocess
                    result = subprocess.run(
                        ['pgrep', '-i', 'cursor'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        if pids:
                            try:
                                return True, int(pids[0])
                            except ValueError:
                                return True, None
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                    pass
                return False, None
            else:  # Linux
                # Используем pgrep на Linux
                try:
                    import subprocess
                    result = subprocess.run(
                        ['pgrep', '-i', 'cursor'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        if pids:
                            try:
                                return True, int(pids[0])
                            except ValueError:
                                return True, None
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                    pass
                return False, None
        except Exception:
            # Если что-то пошло не так, возвращаем None (неизвестно)
            return None, None
    
    def reset_machine_ids(self):
        """Сброс Machine ID для Cursor - генерация новых ID"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.starting')} для Cursor...{Style.RESET_ALL}")
            
            # Проверяем, запущен ли Cursor
            cursor_running, pid = self.check_cursor_running()
            if cursor_running is True:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} Внимание: Cursor запущен (PID: {pid})!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}⚠️  Рекомендуется закрыть Cursor перед изменением Machine ID.{Style.RESET_ALL}")
                continue_anyway = input(f"{Fore.YELLOW}Продолжить в любом случае? (y/n): {Style.RESET_ALL}")
                if continue_anyway.lower() != 'y':
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.operation_cancelled')}{Style.RESET_ALL}")
                    return False
            
            # Проверяем существование файлов Cursor
            machine_id_path = get_cursor_machine_id_path(self.translator)
            if not os.path.exists(self.db_path) and not os.path.exists(self.sqlite_path) and not os.path.exists(machine_id_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} Файлы Cursor не найдены. Убедитесь, что Cursor установлен.{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Ожидаемые пути:{Style.RESET_ALL}")
                print(f"  - storage.json: {self.db_path}")
                print(f"  - state.vscdb: {self.sqlite_path}")
                print(f"  - machineId: {machine_id_path}")
                return False
            
            # Создаем резервную копию текущих ID
            self.backup_current_ids()
            
            # Генерируем новые ID
            new_ids = self.generate_new_ids()
            
            # Показываем новые ID
            print(f"\n{Fore.CYAN}{self.translator.get('reset.ids_to_reset')} для Cursor:{Style.RESET_ALL}")
            for key, value in new_ids.items():
                print(f"{EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")
            
            # Подтверждение
            confirm = input(f"\n{EMOJI['WARNING']} {self.translator.get('reset.confirm')}: ")
            if confirm.lower() != 'y':
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.operation_cancelled')}{Style.RESET_ALL}")
                return False
            
            # Обновляем файлы Cursor
            if not self.update_current_file(new_ids):
                return False
            
            # Обновляем SQLite базу данных Cursor
            self.update_sqlite_db(new_ids)
            
            # Обновляем machineId файл Cursor
            self.update_machine_id_file(new_ids.get("telemetry.devDeviceId", ""))
            
            # Обновляем системные ID
            self.update_system_ids(new_ids)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.success')} для Cursor!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}ℹ️  Перезапустите Cursor, чтобы изменения вступили в силу.{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.process_error', error=str(e))}{Style.RESET_ALL}")
            traceback.print_exc()
            return False

def run(translator=None):
    """Сброс machine ID для Cursor - главная функция"""
    if translator is None:
        translator = SimpleTranslator()
    
    config = get_config(translator)
    if not config:
        return False
    
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title')} для Cursor{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    try:
        resetter = MachineIDResetter(translator, config)
        resetter.reset_machine_ids()
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Ошибка: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        return False
    
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('reset.press_enter')}...")
    return True

if __name__ == "__main__":
    run() 