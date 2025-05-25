[![ru](https://img.shields.io/badge/lang-ru-green.svg)](https://github.com/aayartsev/odoo_dev_project/blob/3.0/README-RU.MD)

# Odoo Developers Project Manager

## Goal of the project
The main goal is - to create tool for developing on odoo platform, which will meet the following requirements:
- do not depend from operating system
- do not depend from process architecture if it is possible (For example you can start this project on MacOS on M1)
- еo transfer all project information, it is enough to have an `odpm.json` in project repository, and the system will be able to easily prepare a new environment in a fully automatic mode based on it.
- To have convenient tools that are often necessary for the developer, for example:
    - fast DB recovery from the archive
    - сreation of a new DB with its own settings (country, language, demo data, etc.)
    - Changing the login and password for the administrator
    - ... and more
    - mechanisms for extending the functionality, for the future

If you are new, i recommend using this project in conjunction with the training demo [`https://github.com/aayartsev/odoo_demo_project`](https://github.com/aayartsev/odoo_demo_project).

## Prepare
You need to download and install the following programs:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Linux and MacOS users
- [git](https://git-scm.com/)
- [python3](https://www.python.org/)
- [Visual Studio Code](https://code.visualstudio.com/)


## How to start work

Create a folder where your new project environment will be located. At the end of the folder name, I add the odoo version number through a hyphen. For example, `odoo_demo_project-17`. This is due to the fact that the difference between versions is significant, and I consider the same modules for different versions as different development projects. Each version of Odoo requires its own environment. Even though the code of the same project can be located in the same repository.To get the utility to start creating an environment, you need to navigate to the directory you created earlier, for example `odoo_demo_project-17`, and then initialize it using the `--init` parameter command. As a parameter for the `--init` command, we can specify a link to a git repository (or a local directory). Also, by adding the `--branch` parameter, you can specify a specific branch to which you want to switch the repository of the project being developed. If the `--branch` parameter is not specified, the default branch will be selected:


Launch `VSCode` then threw menu File - Open Folder, open our folder `odoo_demo_project-17`.

Now we cat enable Terminal threw menu Terminal - New Terminal. Then in it you can input commands that are written below. If someone, looking at a python script, wants to run it inside a virtual environment, then do not do this. In this case, it is used instead of system scripting languages and you will only complicate your life. The virtual environment for the project will be installed inside the container.

At the very first launch of the previously described command:
```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py --init https://github.com/aayartsev/odoo_demo_project.git --branch 17.0-test_odpm_json
```
If you do not wish to contact the `git` repository for any reason, you can easily create a local development environment by simply specifying a desired directory location.

```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py --init file:///your/path/to/odoo_demo_project-17/name_of_development_directory
```

The utility will try to prepare your computer:
1. The utility will ask questions about which parameters should be saved to a file `.env`
1. If you are deploying a project from scratch, the utility will ask you to specify the odoo version and make initial settings based on this information
1. The cloning process of the main odoo repository will be started. This takes a very significant time of 40 minutes or more, so be patient
1. The repository of the developed project will be cloned, or the directory of the local file system will be connected if a path to the file system was specified.
1. A `Dockerfile` will be automatically generated for the specified `python` and `debian` version.
1. After this, the automatic build of the `Docker image` will start if it has not been built before.
1. The `docker-compose.yml` file will be automatically generated
1. Configuration files will be generated for VS Code for the debugger to work correctly
1. `docker-compose up` will start automatically
1. All python dependencies will be installed in the virtual environment
1. Odoo will start with all specified addons for selected version

You can stop this running process by using the keyboard shortcut `Ctrl+C`.

After that, you can run odoo in developer mode:
```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py -d test_db -i -u
```
This command will launch odoo inside the `Docker container` and create a new database named `test_db` and install the module from the specified project there

After that, you can open the address `http://127.0.0.1:8069` in the browser and you will see the login window.

2 configuration files are required for the system to work:
- `odpm.json` -  it also can be located in the repository with the developing project, contains the necessary information on how to start this project. If the file is not found, it will be created from the default values.
- `user_settings.json` - contains the settings and preferences of a specific developer. If the file is not found, it will be created from the default values.

## Short summary

This app build environment for your project. The project itself is a directory that is specified in a parameter `developing_project` of `user_settings.json` file or as key of `--init` param.

## Parameters in .env file:
The system will try to create a `.odpm` directory in the user's home directory of your operating system. Inside it the system will place the `.env` file. If you are launching the application for the first time, it will ask a question for each item described below in this file and offer default values. If you don't know what to answer, just press `Enter`. If you place the `.env` file in the project directory, the program will consider it a priority and try to take values from the file inside the project.
- `BACKUP_DIR` - the directory where the archives are located. It is used to specify the name of the database for recovery using command-line parameters and then the system will search for an archive with the specified name in this directory, or when saving the database to the archive, it will appear in this directory, can be used for all projects
- `ODOO_SRC_DIR` - The directory where the full clone of the repository of the `odoo` platform itself should be located. I usually put it in my user profile. It is used by all projects.
- `ODOO_PROJECTS_DIR` - create a directory where clones of all used repositories will be created. You just need specify the path to this directory, then the system itself will create this directory and clone all the repositories into it and arrange them so that there are no conflicts
- `PATH_TO_SSH_KEY` - if, for some reason, you are unable to add your repository key to the ssh agent, then you can specify the path to it here. At the moment, one key will be used for all repositories
- `ODOO_PORT` - the port on which odoo will be launched by default at the address 127.0.0.1
- `POSTGRES_PORT` - the port on which the PostgreSQL DBMS will be launched by default at the address 127.0.0.1
- `DEBUGGER_PORT` - the port on which the debugger will run by default at the address 127.0.0.1
- `GEVENT_PORT` - the port on which the Websocket Gevent System will listen by default at the address 127.0.0.1

Example:
```conf
BACKUP_DIR=/home/user/odoo_backups
ODOO_SRC_DIR=/home/user/odoo
ODOO_PROJECTS_DIR=/home/user/odoo_projects
PATH_TO_SSH_KEY=/home/user/.ssh/my_ssh_key
ODOO_PORT=8069
POSTGRES_PORT=5432
DEBUGGER_PORT=5678
GEVENT_PORT=8072
```

## Parameters in user_settings.json:

- `init_modules` - `type: String`. Parameter that specifies modules separated by commas, without spaces, which will be initiated (installed) when (re)starting the system.
- `update_modules` - `type: String` A parameter that specifies modules separated by commas, without spaces, which will be updated when (re)starting the system
- `db_creation_data` - `type: Object`. The parameters that determine the creation of a new database.
    - `db_lang` - `type: String`. Specify the default system language when creating a new database, for example: `"en_US"` or `"ru_RU"`
    - `db_country_code` - `type: String` or `false`. Specify the default country code for creating a new database, for example:`"by"`
    - `create_demo` - `type: Boolean`. Indicates whether it is necessary to create demo data in the system when creating a new database.
    - `db_default_admin_login` - `type: String`. Login for the administrator account
    - `db_default_admin_password` - `type: String`. The password for the administrator account
- `update_git_repos` - `type: Boolean`. Indicates whether the dependency repositories and odoo itself will be updated when the system is restarted
- `clean_git_repos` - `type: Boolean`. Indicates whether changes to odoo itself and dependency projects will be reset on restart
- `check_system` - `type: Boolean`. Indicates whether the system check will be started at startup. Useful for beginners. Checks if `git`, `docker`, and `docker-compose` are installed.
- `developing_project` - `type: String`.A link to the project you are developing. Example: `"git@github.com:aayartsev/odoo_demo_project.git "`
- `pre_commit_map_files` - `type: String`. A list of files for the `pre-commit` system that are taken out of the project and pushed there through the docker file mapping. It is necessary to work on non-Linux systems
- `dev_mode` - `type: String`. You can specify comma-separated [parameters for developers](https://www.oovoo.com/documentation/16.0/developer/reference/cli.html?highlight=dev#cmdoption-odoo-bin-dev). See the official documentation for your version of odoo
- `db_manager_password` - `type: String`. password for the database manager
- `sql_queries` - `type: List`. Contains a list of strings, each of which is an SQL script that will be executed when using the command line parameter `--sql-execute`
- `use_oca_dependencies` - added an experimental feature that allows automatically loading all dependencies specified in the `"oca_dependencies.txt"` file. The default value is `false`
- `create_module_links` - an experimental feature that adds soft links for all modules involved in the project to the `odoo/odoo/addons` directory. This allows the language server to automatically resolve import paths. The default value is `false`.

## Parameters in odpm.json:
- `python_version` - `type: String`. The python version is indicated in text form by its number, for example `"3.10"` or `"3.7"`,
- `distro_name` - `type: String`. The name of the distribution on which the image for running Odoo will be created. Currently, only `"debian"` is supported.
- `distro_version` - `type: String`. The version of the distribution specified in the distro_name key, indicated as a text version, for example, `"11"` or `"12"`
- `odoo_version` - `type: String`. The version of the odoo system. Examples: `"16.0"`, `"15.0"`, `"11.0"`
- `dependencies` - `type: List`. A list of links to the project repositories on which your project depends
- `requirements_txt` - `type: List`. A list of python modules, each element can be formatted in the same way as a line in a file requirements.txt

### Supported Linux Distributions and Versions with Python Versions

Currently, for Odoo versions 11 to 16 inclusive, Python 3.7 on Debian 11 (Bullseye) has been tested and works stably.
Also tested and works stably for Odoo versions 16 to 17 with Python 3.10 on Debian 11 (Bullseye) and Debian 12 (Bullseye).
Experimental support for Ubuntu distributions has begun, but it is still in its early stages, and all experiments are at your own discretion.
Supported distributions and versions:

- Stable:
    - Debian 11 (Bullseye)
        - Python 3.7, 3.10
    - Debian 12 (Bullseye)
        - Python 3.10
- Experimental:
    - Ubuntu 22.04 (Jammy)
        - Python 3.10
    - Ubuntu 20.04 (Focal)
        - Python 3.8

## Command Line Interface parameters

- `--init` - initiate a project in the current directory. As a parameter, you can specify a link to the `git` repository
- `--branch` - used together with the `--init` parameter to specify the branch of the git repository to be cloned.
- `-d` - to specify the name of the database to work with. If there is no such database, it will be automatically created based on the `db_creation_data` parameter from the configuration file `user_settings.json`
- `-i` - the parameter indicates that the modules specified in the `init_modules` parameter of the `user_settings.json` configuration file should be initialized.
- `-u` - the parameter indicates that the modules specified in the `pdate_modules` parameter of the `user_settings.json` configuration file should be updated.
- `-t` - will run tests of modules specified in `init_modules` and `update_modules`, works only when using parameters `-d`, `-i`, `-u`. If the database is being created from scratch, tests of all installed modules will be run. This may take a long time.
- `--get-dbs-list` - will show list of databases
- `--db-restore` - The system will attempt to restore a database archive. Specify the archive name, which must be located in the directory specified by the `BACKUP_DIR` parameter in the `.env` file. The database name for restoration will be taken from the `-d` parameter.
- `--db-backup` - The system will attempt to create a database archive. You can specify the archive name to be created in the directory specified by the `BACKUP_DIR` parameter in the `.env` file. If no name is provided, it will be generated automatically based on the database name from the `-d` parameter plus a timestamp. The database name for archiving will be taken from the `-d` parameter.
- `--db-drop` - accept database name as parameter. Database with selected  name will be deleted. If you will use it with  params `-d`, `-i`, `-u`, and select the same name, system will with first step delete DB and with second step will create new DB with the same name, and will install selected modules.
- `--translate` - will update translation for selected language, for example `ru_RU` or `eu_US` for database from `-d` param and for modules form `update_modules` and `init_modules` from `user_settings.json` file
- `--pip-install` - will start install of all python packages from odoo `requirements.txt` and from `requirements_txt` param to environment inside `docker container`.
- `--start-precommit` - will start pre-commit for your project inside container, specified in parameter `developing_project` from file `user_settings.json`.
- `--build-image` - will build Docker image for your odoo version
- `--set-admin-pass` - when you specify the value of this parameter, the administrator account will have its password and login changed to those specified in the `db_default_admin_login` and `db_default_admin_password` parameters in the `user_settings.json` configuration file. Be sure to specify the name of the database for which you want to change the password and use the `-d database_name` parameter.
- `--sql-execute` - wen this parameter is used, the SQL scripts specified in the `sql_queries` parameter of the `user_settings.json` configuration file will be executed. Each script is a separate string that is an element of the list.You must specify the name of the database for which you want to change the password and use the parameter `-d database_name`.
- `--export-po-files` will create files for selected language, for example `ru_RU` or `eu_US`. System will create `po` and `pot` files for modules that are listed in `update_modules` parameter of `user_settings.json` file in your project environment.You must specify the name of the database for which you want to create translation files and use the parameter `-d database_name`
- `scaffold my_module_name` - The additional command `scaffold` creates a module with the specified name in the project being developed. In this case, `my_module_name`.
    - `-t` - The name of the directory where the templates for generating the module are located in the directory with the specified name. The templates are written using [jinja2](https://jinja.palletsprojects.com/en/stable/)
