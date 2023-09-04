import paramiko
from scp import SCPClient
import os

from src.config import CONFIG
from src.utils.logger import logger

class FileTransfer:
    def __enter__(self):
        self.ssh = self._create_ssh_client(
            CONFIG.sshtunnel.host,
            CONFIG.sshtunnel.port,
            CONFIG.sshtunnel.username,
            CONFIG.sshtunnel.password
        )
        self.scp = SCPClient(self.ssh.get_transport())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scp.close()
        self.ssh.close()

    def _create_ssh_client(self, server, port, user, password):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, port, user, password)
        return client
    

    def mkdir(self, folder_path: str, recursive: bool = True):
        if recursive:
            # Split the folder path into individual folder names
            folders = folder_path.split('/')

            # Remove any empty folder names resulting from leading/trailing slashes
            folders = [folder for folder in folders if folder]

            # Create each folder recursively, if it does not exist
            for i in range(1, len(folders) + 1):
                partial_path = '/'.join(folders[:i])
                
                if partial_path in CONFIG.remote.dataset_path or partial_path == CONFIG.remote.dataset_path:
                    continue
                
                command = f"mkdir {partial_path} 2> /dev/null || true"  # Ignore error if the folder already exists
                self.ssh.exec_command(command)
        else:
            command = f"mkdir {folder_path} 2> /dev/null || true"  # Ignore error if the folder already exists
            self.ssh.exec_command(command)
            
    def put(self, source: str, target: str, target_is_folder: bool = False, **kwargs):      
        target = target.replace(" ", "\ ")  
        if target_is_folder:
            self.mkdir(target)
            filename = os.path.basename(source).replace(" ", "\ ") 
            target = os.path.join(target, filename)
        else:
            self.mkdir(os.path.dirname(target))
        
        print("transfering from", source, "to", target)
        self.scp.put(source, target, **kwargs)

        