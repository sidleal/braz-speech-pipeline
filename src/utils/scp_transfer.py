import paramiko
from scp import SCPClient
import os
import shlex

from src.config import CONFIG
from src.utils.logger import logger


class FileTransfer:
    def __enter__(self):
        self.ssh = self._create_ssh_client(
            CONFIG.sshtunnel.host,
            CONFIG.sshtunnel.port,
            CONFIG.sshtunnel.username,
            CONFIG.sshtunnel.password,
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
            folders = folder_path.split("/")

            # Remove any empty folder names resulting from leading/trailing slashes
            folders = [folder for folder in folders if folder]

            # Create each folder recursively, if it does not exist
            for i in range(1, len(folders) + 1):
                partial_path = "/".join(folders[:i])

                if (
                    partial_path in CONFIG.remote.dataset_path
                    or partial_path == CONFIG.remote.dataset_path
                ):
                    continue

                escaped_partial_path = shlex.quote(partial_path)

                command = f"mkdir {escaped_partial_path} 2> /dev/null || true"  # Ignore error if the folder already exists
                self.ssh.exec_command(command)
        else:
            escaped_folder_path = shlex.quote(folder_path)
            command = f"mkdir {escaped_folder_path} 2> /dev/null || true"  # Ignore error if the folder already exists
            self.ssh.exec_command(command)

    def put(self, source: str, target: str, target_is_folder: bool = False, **kwargs):
        if target_is_folder:
            self.mkdir(target)
            filename = os.path.basename(source)
            filename = shlex.quote(filename)  # Escape special characters here
            target = os.path.join(target, filename)
        else:
            target_directory = os.path.dirname(target)
            escaped_target_directory = shlex.quote(target_directory)
            self.mkdir(escaped_target_directory)

        source = shlex.quote(source)  # Escape source file path
        target = shlex.quote(target)  # Escape target file path
        try:
            self.scp.put(source, target, **kwargs)
        except Exception as e:
            logger.error(f"Error transferring file.")
            logger.debug(e)