#!/usr/bin/env python3
"""
Тестовый скрипт для создания новых локальных проектов Odoo.

Создает проекты для различных версий Odoo, измеряет время выполнения и логирует результаты.
"""

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from secure_delete import DEFAULT_PROTECTED, delete_paths, is_root

# Добавляем корень проекта в path для импорта логгера
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dev_project.inside_docker_app.logger import get_module_logger

# Инициализируем логгер из проекта
_logger = get_module_logger(__name__)

# Версии Odoo для тестирования
ODOO_VERSIONS = ["19.0"]

# Пути для тестов
TEST_BASE_DIR = Path("/tmp/odoo_test_projects")
BACKUP_DIR = Path("/tmp/odoo_backups")
ODOO_PROJECTS_DIR = Path("/tmp/odoo_projects")


def setup_logging():
    """Настройка логирования на основе конфигурации проекта."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cleanup_directory(directory: Path):
    """
    Удаляет содержимое директории с повышенными привилегиями.

    Args:
        directory: Путь к директории для очистки
    """
    if directory.exists():
        _logger.info(f"Очистка директории: {directory}")
        try:
            # Попытка удалить через shutil
            shutil.rmtree(directory)
        except PermissionError:
            # Если не получилось, используем sudo
            _logger.warning(f"Требуется sudo для удаления {directory}")
            subprocess.run(
                ["sudo", "rm", "-rf", str(directory)],
                check=True,
                capture_output=True,
            )
        _logger.info(f"Директория {directory} успешно очищена")


def create_test_environment(version: str) -> Path:
    """
    Создает каталог для тестирования указанной версии Odoo.

    Args:
        version: Версия Odoo

    Returns:
        Путь к созданной директории
    """
    version_dir = Path(os.path.join(str(TEST_BASE_DIR), f"test-{version}"))
    cleanup_directory(version_dir)
    version_dir.mkdir(parents=True, exist_ok=True)
    _logger.info(f"Создана директория для версии {version}: {version_dir}")
    return version_dir


def create_env_file(work_dir: Path, port_offset: int = 0):
    """
    Создает файл .env с необходимыми параметрами.

    Args:
        work_dir: Рабочая директория
        version: Версия Odoo
        port_offset: Смещение для портов (чтобы избежать конфликтов)
    """
    env_content = f"""BACKUP_DIR={BACKUP_DIR}
ODOO_PROJECTS_DIR={ODOO_PROJECTS_DIR}
PATH_TO_SSH_KEY=
ODOO_PORT={9069 + port_offset}
POSTGRES_PORT={6432 + port_offset}
DEBUGGER_PORT={6678 + port_offset}
GEVENT_PORT={9072 + port_offset}
ODPM_SCENARIO=developer
"""
    env_file = work_dir / ".env"
    env_file.write_text(env_content)
    _logger.info(f"Создан файл .env в {work_dir}")


def run_odpm_script(work_dir: Path, version: str) -> tuple[bool, float]:
    """
    Запускает скрипт odpm.py для создания проекта.

    Args:
        work_dir: Рабочая директория
        version: Версия Odoo

    Returns:
        Кортеж (успех, время_выполнения)
    """
    odpm_script = PROJECT_ROOT / "odpm.py"

    # Проверяем существование скрипта
    if not odpm_script.exists():
        _logger.error(f"Скрипт odpm.py не найден: {odpm_script}")
        return False, 0.0

    # Переходим в рабочую директорию
    os.chdir(work_dir)
    _logger.info(f"Переход в рабочую директорию: {work_dir}")

    # Замеряем время начала
    start_time = time.time()
    _logger.info(f"Начало выполнения для версии {version}")
    # Формируем команду
    cmd = [
        "python3",
        str(odpm_script),
        "--init",
        ".",
        "--odoo-version",
        version,
        "-d",
        "test_db",
        "--odoo-bin",
        "--stop-after-init",
    ]

    _logger.info(f"Выполняемая команда: {' '.join(cmd)}")

    try:
        os.system(f"""{" ".join(cmd)}""")
        elapsed_time = time.time() - start_time
        return True, elapsed_time
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        _logger.error(f"Версия {version}: ТАЙМАУТ после {elapsed_time:.2f} сек")
        return False, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        _logger.error(f"Версия {version}: ИСКЛЮЧЕНИЕ {e} за {elapsed_time:.2f} сек")
        return False, elapsed_time


def cleanup_test_artifacts():
    """
    Удаляет созданные тестовые каталоги после успешного завершения всех тестов.
    """
    dirs_to_clean = [TEST_BASE_DIR, BACKUP_DIR, ODOO_PROJECTS_DIR]

    for directory in dirs_to_clean:
        if directory.exists():
            _logger.info(f"Удаление тестовой директории: {directory}")
            cleanup_directory(directory)


def main():
    """Основная функция тестирования."""
    setup_logging()

    _logger.info("=" * 60)
    _logger.info("Запуск тестирования создания проектов Odoo")
    _logger.info("=" * 60)

    # Словарь для хранения результатов
    results = {}
    all_success = True

    try:
        for version in ODOO_VERSIONS:
            _logger.info("-" * 60)
            _logger.info(f"Обработка версии Odoo: {version}")
            _logger.info("-" * 60)

            # Шаг 1: Создаем каталог для версии
            work_dir = create_test_environment(version)

            # Шаг 2: Создаем файл .env
            port_offset = ODOO_VERSIONS.index(version) * 10
            create_env_file(work_dir, port_offset)

            # Шаг 3-6: Запускаем скрипт и получаем результаты
            success, elapsed_time = run_odpm_script(work_dir, version)

            # Сохраняем результаты
            results[version] = {
                "success": success,
                "elapsed_time": elapsed_time,
                "work_dir": work_dir,
            }

            if not success:
                all_success = False
                _logger.warning(f"Тест для версии {version} завершен с ошибкой")
            else:
                _logger.info(f"Тест для версии {version} завершен успешно")

        # Шаг 7: Вывод итоговых результатов
        _logger.info("=" * 60)
        _logger.info("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
        _logger.info("=" * 60)

        for version, result in results.items():
            status = "✓ УСПЕХ" if result["success"] else "✗ ОШИБКА"
            time_str = (
                f"{result['elapsed_time']:.2f} сек"
                if result["elapsed_time"] > 0
                else "N/A"
            )
            _logger.info(f"{version}: {status} | Время: {time_str}")

        if all_success:
            _logger.info("=" * 60)
            _logger.info("Все тесты завершены успешно!")
            _logger.info("Удаление тестовых каталогов...")
            cleanup_test_artifacts()
            _logger.info("Тестовые каталоги удалены")
            _logger.info("=" * 60)
            return 0
        else:
            _logger.warning("Некоторые тесты завершились с ошибками")
            _logger.warning("Тестовые каталоги сохранены для отладки")
            return 1

    except KeyboardInterrupt:
        _logger.info("Тестирование прервано пользователем (Control+C)")
        return 1
    except Exception as e:
        _logger.exception(f"Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
