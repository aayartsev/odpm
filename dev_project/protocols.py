from typing import Protocol
import inspect

class SystemCheckerProtocol(Protocol):

    def check_git(self):
        NotImplementedError(
                f"""Define {inspect.stack()[0][3]}  in {self.__class__.__name__}""")
    def get_groups(self):
        NotImplementedError(
                f"""Define {inspect.stack()[0][3]}  in {self.__class__.__name__}""")
    def check_docker(self):
        NotImplementedError(
                f"""Define {inspect.stack()[0][3]}  in {self.__class__.__name__}""")
    def check_running_containers(self):
        NotImplementedError(
                f"""Define {inspect.stack()[0][3]}  in {self.__class__.__name__}""")
    def check_docker_compose(self):
        NotImplementedError(
                f"""Define {inspect.stack()[0][3]}  in {self.__class__.__name__}""")
    def check_file_system(self):
        NotImplementedError(
                f"""Define {inspect.stack()[0][3]}  in {self.__class__.__name__}""")
    def check_free_space_for_odoo_developing(self):
        NotImplementedError(
                f"""Define {inspect.stack()[0][3]} in {self.__class__.__name__}""")


class CreateProjectEnvironmentProtocol(Protocol):


    def map_folders(self):
        NotImplementedError(
                f"""Define map_folders in {self.__class__.__name__}""")
    
    def generate_dockerfile(self):
        NotImplementedError(
                f"""Define generate_dockerfile in {self.__class__.__name__}""")
    
    def generate_config_file(self):
        NotImplementedError(
                f"""Define generate_config_file in {self.__class__.__name__}""")
    
    def generate_docker_compose_file(self):
        NotImplementedError(
                f"""Define generate_docker_compose_file in {self.__class__.__name__}""")
    
    def checkout_dependencies(self):
        NotImplementedError(
                f"""Define checkout_dependencies in {self.__class__.__name__}""")
    
    def update_links(self):
        NotImplementedError(
                f"""Define update_links in {self.__class__.__name__}""")
    
    def update_vscode_debugger_launcher(self):
        NotImplementedError(
                f"""Define update_vscode_debugger_launcher in {self.__class__.__name__}""")
    
    def clone_odoo(self):
        NotImplementedError(
                f"""Define clone_odoo in {self.__class__.__name__}""")
    
    def download_odoo_repository(self):
        NotImplementedError(
                f"""Define download_odoo_repository in {self.__class__.__name__}""")
    
    def build_image(self):
        NotImplementedError(
                f"""Define build_image in {self.__class__.__name__}""")
    
