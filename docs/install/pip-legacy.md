# Установка через pip и запуск из исходников

Для разработчиков самого odpm или для систем, где нет готовых пакетов `.deb` / `.rpm`.

## pip / editable

Нужен **Python 3.10+**. На Linux с [PEP 668](https://peps.python.org/pep-0668/) используйте venv или [pipx](https://pipx.pypa.io/), не `pip install` в систему.

```bash
pip install /path/to/odoo_dev_project
# для разработки odpm:
pip install -e /path/to/odoo_dev_project
odpm --version
```

Команда `odpm` берёт шаблоны из установленного пакета `dev_project`.

## Запуск без установки пакета

Скопируйте `odpm.py` и каталог `dev_project/` или клонируйте репозиторий целиком:

```bash
python3 /path/to/odoo_dev_project/odpm.py --version
```

Оба способа поддерживаются.
