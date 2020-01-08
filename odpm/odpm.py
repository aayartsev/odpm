#!/usr/bin/python3
# -*- coding: utf-8 -*-

import subprocess
import os, signal
import git
import time
import sys
import json
import argparse
import logging
import zipfile
import shutil
import urllib
import io
from string import Template

script_dir = os.path.dirname(os.path.abspath(__file__))
home_dir = os.path.expanduser("~") + "/"
_logger = logging.getLogger(__name__)
project_config_file = "odpm_project.json"
project_dir = os.getcwd()


parser = argparse.ArgumentParser()
parser.add_argument('--drop-db', help='db name to drop')
parser.add_argument('--backup-db', help='db name to backup, working with opiton --arch-path')
parser.add_argument('--restore-db', help='db name to restore, working with opiton --arch-path')
parser.add_argument('--arch-path', help='path to database archive, working with options --backup-db and --restore-db')
parser.add_argument('--init', help='init project with current name default params and create default odoo project with default module')
parser.add_argument('--update', type=bool, nargs='?',const=True, default=False,help='this is option will update all git repos (odoo, depends, dev_project etc...)')
parser.add_argument('--project-path', help='this is option tell to the programm in wich project context we will work')

parser.add_argument('--dev-restart', type=bool, nargs='?', const=True, default=False, help='this option restarting odoo with your project params')
parser.add_argument('--create-module', help='this option will create dummy odoo module with frontend files')

options = parser.parse_args()

if options.project_path:
    if options.project_path[-1] =="/":
        options.project_path = options.project_path[:-1]
    project_dir = options.project_path
    
project_config_path = os.path.join(project_dir, project_config_file)
if not os.path.exists(project_config_path) and not options.init:
    print(u"Перейдите в каталог где существует %s файл или укажите каталог проекта с помощью параметра --project-path '/путь/к/каталогу/с/проектом/' "%(project_config_file))
    exit()
if os.path.exists(project_config_path):
    JSON_CONF = json.loads(open(project_config_path).read())
else:
    JSON_CONF ={}


if 'projects_dir' in JSON_CONF.keys():
    projects_dir = JSON_CONF['projects_dir']
else:
    projects_dir = os.path.join(home_dir,"projects")
if not os.path.exists(projects_dir):
    os.mkdir(projects_dir)

if 'odoo_projects_dir' in JSON_CONF.keys():
    odoo_projects_dir = JSON_CONF['odoo_projects_dir']
else:
    odoo_projects_dir = os.path.join(home_dir,"odoo_projects")
if not os.path.exists(odoo_projects_dir):
        os.mkdir(odoo_projects_dir)

if 'odoo_dir' in JSON_CONF.keys():
    odoo_dir = JSON_CONF['odoo_dir']
else:
    odoo_dir = os.path.join(home_dir,"odoo")
if not os.path.exists(odoo_dir):
        os.mkdir(odoo_dir)

sys.path.insert(1, odoo_dir)

if 'odoo_venvs_dir' in JSON_CONF.keys():
    odoo_venvs_dir = JSON_CONF['odoo_venvs_dir']
else:
    odoo_venvs_dir = os.path.join(home_dir,"odoo_venvs")
if not os.path.exists(odoo_venvs_dir):
        os.mkdir(odoo_venvs_dir)



if 'dependencies_projects_urls' not in JSON_CONF.keys():
    dependencies_projects_urls = []
else:
    dependencies_projects_urls = JSON_CONF['dependencies_projects_urls']
    
if 'dev_project_url' not in JSON_CONF.keys():
    dev_project_url = None
else:
    dev_project_url = JSON_CONF['dev_project_url']
    
if 'odoo_version_for_project' not in JSON_CONF.keys():
    odoo_version_for_project = "12.0"
else:
    odoo_version_for_project = JSON_CONF['odoo_version_for_project']

if 'project_name' not in JSON_CONF.keys():
    project_name = None
else:
    project_name = JSON_CONF['project_name']

if 'modules_to_update' not in JSON_CONF.keys():
    modules_to_update = None
else:
    modules_to_update = JSON_CONF['modules_to_update']

if 'get_pull' not in JSON_CONF.keys():
    get_pull = None
else:
    get_pull = JSON_CONF['get_pull']

if options.update:
    get_pull = True

if 'database_name' not in JSON_CONF.keys():
    database_name = None
else:
    database_name = JSON_CONF['database_name']


if 'git_servers_params' not in JSON_CONF.keys():
    git_servers_params = {}
else:
    git_servers_params = JSON_CONF['git_servers_params']





# def restore_db(db, dump_file, copy=False):
#     filestore_dest = home_dir + '/.local/share/Odoo/filestore/' + db
#     assert isinstance(db, pycompat.string_types)
#     if odoo.service.db.exp_db_exist(db):
#         _logger.info('RESTORE DB: %s already exists', db)
#         raise Exception("Database %s already exists"%(db))

#     odoo.service.db._create_empty_database(db)

#     filestore_path = None
#     with odoo.tools.osutil.tempdir() as dump_dir:
#         if zipfile.is_zipfile(dump_file):
#             # v8 format
#             with zipfile.ZipFile(dump_file, 'r') as z:
#                 # only extract known members!
#                 filestore = [m for m in z.namelist() if m.startswith('filestore/')]
#                 z.extractall(dump_dir, ['dump.sql'] + filestore)

#                 if filestore:
#                     filestore_path = os.path.join(dump_dir, 'filestore')

#             pg_cmd = 'psql'
#             pg_args = ['-q', '-f', os.path.join(dump_dir, 'dump.sql')]

#         else:
#             # <= 7.0 format (raw pg_dump output)
#             pg_cmd = 'pg_restore'
#             pg_args = ['--no-owner', dump_file]

#         args = []
#         args.append('--dbname=' + db)
#         pg_args = args + pg_args

#         if odoo.tools.exec_pg_command(pg_cmd, *pg_args):
#             raise Exception("Couldn't restore database")

#         registry = odoo.modules.registry.Registry.new(db)
#         cr = registry.cursor()
#         # env = odoo.api.Environment(cr, SUPERUSER_ID, {})
#         if filestore_path:
#             shutil.move(filestore_path, filestore_dest)

#         if odoo.tools.config['unaccent']:
#             try:
#                 with cr.savepoint():
#                     cr.execute("CREATE EXTENSION unaccent")
#             except psycopg2.Error:
#                 pass

#     _logger.info('RESTORE DB: %s', db)


# drop_data_base = JSON_CONF['drop_data_base']
if options.drop_db:
    odoo_version = odoo_version_for_project.split('.')[0]
    current_odoo_version_venv_dir = os.path.join(odoo_venvs_dir,'venv_odoo_%s'%(odoo_version))
    activate_this = os.path.join(current_odoo_version_venv_dir, 'bin', 'activate_this.py')
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this), {})
    import odoo
    from odoo.tools.misc import str2bool, xlwt, file_open
    from odoo.tools import pycompat
    from odoo import SUPERUSER_ID
    odoo.service.db.exp_drop(options.drop_db)
    exit()
    
if options.backup_db:
    if not options.arch_path:
        print(u"Для того, чтобы создать архив базы данных, необходимо указать параметр --arch-path 'путь/к/архиву.zip' ")
        exit()
    odoo_version = odoo_version_for_project.split('.')[0]
    current_odoo_version_venv_dir = os.path.join(odoo_venvs_dir,'venv_odoo_%s'%(odoo_version))
    activate_this = os.path.join(current_odoo_version_venv_dir, 'bin', 'activate_this.py')
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this), {})
    import odoo
    from odoo.tools.misc import str2bool, xlwt, file_open
    from odoo.tools import pycompat
    from odoo import SUPERUSER_ID
    dump_stream = odoo.service.db.dump_db(options.backup_db, None, 'zip')
    file_arch = open(options.arch_path, 'wb')
    for line in dump_stream.readlines():
        file_arch.write(line)
    file_arch.close()
    exit()
    



odoo_venv_dir = os.path.join(odoo_venvs_dir,'venv_odoo_'+ odoo_version_for_project.split('.')[0] + "/")
python_version= False
pip_version = False
if int(odoo_version_for_project.split('.')[0]) <= 10:
    python_version = '2'
    pip_version = ''
else:
    python_version = '3'
    pip_version = '3'

def run_command(command,handler_func=None, stdout=True):
    current_proc = subprocess.Popen(command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
 
    all_string = ""
 
    for line in iter(current_proc.stdout.readline, b''):
        if stdout:
            sys.stdout.buffer.write(line)
        str_line = line.rstrip().decode("utf-8")
        all_string = all_string + str_line
        if handler_func:
            handler_func(line,current_proc)
    return all_string



def get_right_git_url(url):
    current_server = None
    for server_name in git_servers_params.keys():
        if server_name in url:
            current_server = server_name
    
    params ={
        "user":urllib.parse.quote(git_servers_params[current_server]["user"]),
        "password":urllib.parse.quote(git_servers_params[current_server]["password"]),
        "gitserver":current_server
    }
    def generate_string_with_template_params(string_to_fill):
        return Template(string_to_fill).substitute(params)
    part_of_url =''
    for url_element in url.split("/")[3:]:
        part_of_url = part_of_url + "/" + url_element
    if current_server:
        git_url = generate_string_with_template_params('https://${user}:${password}@${gitserver}%s'%(part_of_url))
        return git_url
    else:
        return url
    
def write_new_file(filename,content):
    file= open(filename,"w")
    file.write(content)
    file.close
    
def get_list_of_modules_in_project(project_path):
    current_dirs = False
    current_files = False
    list_of_all_files = []
    for i,j,y in os.walk(project_path):
        for elemet in y:
            list_of_all_files.append(elemet)
        if not current_dirs:
            current_dirs = j
            current_files = y
    return current_dirs, current_files , list_of_all_files
    
# Функция для которая сканирует содрежимое каталога с проектом и отдает кортеж с анализом ситуации
def check_dir_content(full_dir_path):
    dir_is_module = False
    dir_is_git_repo = False
    dir_has_module = False
    recources = get_list_of_modules_in_project(full_dir_path)
    dirs_list = recources[0]
    files_list = recources[1]
    list_of_all_files_with_subdirs = recources[2]
    if files_list and '__manifest__.py' in files_list:
        dir_is_module = True
    # print(list_of_all_files_with_subdirs)
    if '__manifest__.py' in list_of_all_files_with_subdirs:
        dir_has_module = True
    if dirs_list and '.git' in dirs_list:
        dir_is_git_repo = True
    
    return dirs_list, files_list, dir_is_module, dir_is_git_repo, dir_has_module
    
def modify_from_module_to_project(this_project_name):
    this_project_dir = os.path.join(odoo_projects_dir,this_project_name)
    temp_project_dir = os.path.join('/tmp',this_project_name)
    module_dir = os.path.join(this_project_dir,this_project_name)
    run_command('mv %s /tmp/'%(this_project_dir))
    run_command('mkdir -p %s'%(module_dir))
    run_command('mv %s %s/'%(temp_project_dir,this_project_dir))

def checkout_git_repo(repo_dir,branch_name):
    repo = git.Repo(repo_dir)
    branch = repo.active_branch
    if branch.name != branch_name:
        repo.git.stash()
        repo.git.checkout(branch_name)
        
def check_odoo_venv():
    odoo_version = odoo_version_for_project.split('.')[0]
    current_odoo_version_venv_dir = os.path.join(odoo_venvs_dir,'venv_odoo_%s'%(odoo_version))
    command_create_venv = 'virtualenv --python=python%s %s'%(python_version,current_odoo_version_venv_dir)
    command_install_requirements = 'cd %s && pip%s install -r requirements.txt'%(odoo_dir,pip_version) # source %s/bin/activate && 
    # if not subprocess.check_call( [ 'virtualenv', current_odoo_version_venv_dir ] ):
    activate_this = os.path.join(current_odoo_version_venv_dir, 'bin', 'activate_this.py')
    if not os.path.exists(activate_this):
        run_command(command_create_venv)
        exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this), {})
        run_command(command_install_requirements)
        
def check_if_project_exists(project_url):
    current_projects = []
    for i,j,y in os.walk(odoo_projects_dir):
        if not current_projects:
            current_projects = j
    project_name_from_url = project_url.split("/")[-1].split(".")[0]
    project_dir = os.path.join(odoo_projects_dir,project_name_from_url)
    
    if not project_name_from_url in current_projects:
        git.Git(odoo_projects_dir).clone(get_right_git_url(project_url))
        checkout_git_repo(project_dir,odoo_version_for_project)
        project_content = check_dir_content(os.path.join(odoo_projects_dir,project_name_from_url))
        if project_content[2]:
            modify_from_module_to_project(project_name_from_url)
            project_dir = os.path.join(project_dir,project_name_from_url)
    else:
        project_content = check_dir_content(os.path.join(odoo_projects_dir,project_name_from_url))
        if project_content[2]:
            modify_from_module_to_project(project_name_from_url)
            project_dir = os.path.join(project_dir,project_name_from_url)
        if not project_content[3]:
            project_dir = os.path.join(project_dir,project_name_from_url)
        g = git.cmd.Git(project_dir)
        if get_pull:
            g.pull()
    repo = git.Repo(project_dir)
    branch = repo.active_branch
    if branch.name != odoo_version_for_project:
        repo.git.stash()
        repo.git.checkout(odoo_version_for_project)
    return project_name_from_url
    
def create_dummy_odoo_module(module_name,module_path):
    odoo_version = odoo_version_for_project.split('.')[0]
    current_odoo_version_venv_dir = '%s/venv_odoo_%s'%(odoo_venvs_dir,odoo_version)
    activate_this = os.path.join(current_odoo_version_venv_dir, 'bin', 'activate_this.py')
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this), {})
    start_odoo_for_template_creating = Template(
        """python${python_version} ${odoo_bin_path} scaffold -t ${module_template_path} ${module_name} ${module_path}""").substitute({
            "python_version":python_version,
            "odoo_bin_path":os.path.join(odoo_dir,'odoo-bin'),
            "module_template_path":os.path.join(script_dir,'templates/default'),
            "module_path":module_path,
            "module_name":module_name,
        })
    run_command(start_odoo_for_template_creating)

def main():
    # check odoo repo
    if not os.path.exists(os.path.join(odoo_dir,".git")):
        # run_command('mkdir -p %s'%(odoo_dir))
        git.Git(home_dir).clone("https://github.com/odoo/odoo.git")
        checkout_git_repo(odoo_dir,odoo_version_for_project)
    
    check_odoo_venv()

if __name__ == "__main__":
    main()
    

    
if not os.path.exists(odoo_projects_dir):
    run_command('mkdir -p %s'%(odoo_projects_dir))
dependencies_projects_names_list = []

for project_url in dependencies_projects_urls:
    project_name_from_url = check_if_project_exists(project_url)
    dependencies_projects_names_list.append(project_name_from_url)



if options.init:
    project_name = options.init
    odoo_project_dir = os.path.join(odoo_projects_dir,project_name)
    run_command('mkdir -p %s'%(odoo_project_dir))
    create_dummy_odoo_module(project_name,odoo_project_dir)
    project_dir = os.path.join(projects_dir,project_name)
    run_command('mkdir -p %s'%(project_dir))
    new_config_file = os.path.join(project_dir,project_config_file)
    new_config = {
        "dependencies_projects_urls": dependencies_projects_urls,
        "dev_project_url": dev_project_url,
        "odoo_version_for_project": odoo_version_for_project,
        "project_name": project_name,
        "modules_to_update":[project_name],
        "git_servers_params":{
        }
    }
    with io.open(new_config_file, 'w', encoding='utf8') as config_file:
        json.dump(new_config, config_file, indent=4)
    
odoo_project_dir = os.path.join(odoo_projects_dir,project_name)

if dev_project_url:
    project_dir_from_url = check_if_project_exists(dev_project_url)
    odoo_project_dir = os.path.join(odoo_projects_dir,project_dir_from_url)
    # if not project_name:
    #     project_name = project_dir_from_url

if not check_dir_content(odoo_project_dir)[4]:
    print(u"There is not odoo module in project. Try to start odpm --init your_project_name")
    exit()
# odoo_project_dir


# else:
#     run_command('mkdir -p %s%s'%(odoo_projects_dir,project_name))
#     project_dir_path = '%s%s/'%(odoo_projects_dir,project_name)
#     init_module_dir_path = '%s%s'%(project_dir_path,project_name)
    
#     # Тут нужно будет инициировать проект

#     if not check_dir_content(init_module_dir_path)[2]:
#         odoo_version = odoo_version_for_project.split('.')[0]
#         current_odoo_version_venv_dir = os.path.join(odoo_venvs_dir,'venv_odoo_%s'%(odoo_version))
#         activate_this = os.path.join(current_odoo_version_venv_dir, 'bin', 'activate_this.py')
#         exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this), {})
#         run_command('%s/odoo-bin scaffold -t default %s %s'%(odoo_dir,project_name,project_dir_path) )
    
    # 

# if not dev_project_url:
#     project_dir_from_url = project_name


if check_dir_content(odoo_dir)[3]:
    checkout_git_repo(odoo_dir,odoo_version_for_project)

if not modules_to_update:
    modules_to_update =[project_name]

string_modules_to_update = ""
for module_name  in modules_to_update:
    string_modules_to_update = string_modules_to_update + module_name + ","
string_modules_to_update = string_modules_to_update[:-1]
    
if not database_name:
    database_name = project_name + '_' + odoo_version_for_project.split('.')[0]




project_odoo_modules_dir = os.path.join(projects_dir,project_name,'odoo_modules')
# if not os.path.exists(odoo_modules_dir):
#     os.makedirs(odoo_modules_dir, exist_ok=True)

run_command('rm -rf %s'%(project_odoo_modules_dir))
run_command('ln -s %s %s'%(odoo_project_dir,project_odoo_modules_dir))

addons_string = ''
for project in dependencies_projects_names_list:
    if os.path.exists(os.path.join(odoo_projects_dir,project)):
        addons_string = addons_string + os.path.join(odoo_projects_dir,project) + ","

# if project_dir_from_url:
if os.path.exists(odoo_project_dir):
    addons_string = addons_string + odoo_project_dir + ","

odoo_addons_dir = os.path.join(odoo_dir,'addons')
odoo_odoo_addons_dir = os.path.join(odoo_dir,'odoo/addons')

if os.path.exists(odoo_addons_dir):
    addons_string = addons_string + odoo_addons_dir + ","

if os.path.exists(odoo_odoo_addons_dir):
    addons_string = addons_string + odoo_odoo_addons_dir + ","

if addons_string[-1] == ',':
    addons_string = addons_string[:-1]

write_new_file(os.path.join(projects_dir,project_name,'dev_odoo_config_file.conf'),
"""[options]
addons_path = %s
"""%(addons_string))


# write_new_file('%s%s/prod_odoo_config_file.conf'%(projects_dir,project_name),
# """[options]
# addons_path = %s
# dbfilter = ^%d$
# proxy_mode = True
# """%(addons_string))


dev_restart_odoo_sh = os.path.join(projects_dir,project_name,'dev_restart_odoo.sh')
dev_restart_odoo_sh_content = Template(
"""#!/bin/bash
pkill -9 -f ${odoo_bin_path}
cd ${current_project_dir}
source ${odoo_venv_activate}
${odoo_bin_path} -c ${current_project_dir}/dev_odoo_config_file.conf -u ${string_modules_to_update} -d ${database_name} -i ${string_modules_to_update}""").substitute({
    "current_project_dir":os.path.join(projects_dir,project_name),
    "odoo_bin_path":os.path.join(odoo_dir,'odoo-bin'),
    "odoo_venv_activate":os.path.join(odoo_venv_dir,'bin/activate'),
    "string_modules_to_update":string_modules_to_update,
    "database_name":database_name
})

write_new_file(dev_restart_odoo_sh,dev_restart_odoo_sh_content)
run_command('chmod +x %s'%(dev_restart_odoo_sh))

write_new_file(os.path.join(projects_dir,project_name,'.gitignore'),
"""*.pyc
*.zip

dev_odoo_config_file.conf
prod_odoo_config_file.conf
dev_restart_odoo.sh
prod_restart_odoo.sh
""")


project_info = check_dir_content(os.path.join(odoo_projects_dir,project_name))

if options.restore_db:
    if not options.arch_path:
        print(u"Для того, чтобы восстановить базу данных, необходимо указать параметр --arch-path 'путь/к/архиву.zip' ")
        exit()
    odoo_version = odoo_version_for_project.split('.')[0]
    current_odoo_version_venv_dir = '%s/venv_odoo_%s'%(odoo_venvs_dir,odoo_version)
    activate_this = os.path.join(current_odoo_version_venv_dir, 'bin', 'activate_this.py')
    exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this), {})
    import odoo
    from odoo.tools.misc import str2bool, xlwt, file_open
    from odoo.tools import pycompat
    from odoo import SUPERUSER_ID
    print(options.arch_path)
    restore_db(options.restore_db,options.arch_path,False)
    odoo_pid = None
    def output_handler(output_line,process):
        str_line = output_line.rstrip().decode("utf-8").strip()
        try:
            odoo_pid = str_line.split(" ")[2]
        except:
            pass
        if "Modules loaded" in str_line:
            process.kill()
            odoo_pid = int(odoo_pid)
            os.kill(odoo_pid, signal.SIGKILL)
            # exit()
        # print(str_line)
    
    start_odoo_for_restore_db = 'python3 %s/odoo-bin -c %s%s/dev_odoo_config_file.conf -u %s -d %s -i %s --http-port %s'%(odoo_dir,projects_dir,project_name,string_modules_to_update,options.restore_db,string_modules_to_update,"8049")
    run_command(start_odoo_for_restore_db,output_handler, True)
    exit()
    
if options.dev_restart:
    process=subprocess.Popen(dev_restart_odoo_sh,shell=True,stdout=subprocess.PIPE)
    result=process.communicate()




if options.create_module:
    module_name = options.create_module
    create_dummy_odoo_module(moule_name,project_odoo_modules_dir)