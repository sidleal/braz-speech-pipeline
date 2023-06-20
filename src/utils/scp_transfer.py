import paramiko
from scp import SCPClient
import os

from src.config import CONFIG


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

    def put(self, source: str, target: str, target_is_folder: bool = True, **kwargs):
        
        if target_is_folder:
            filename = os.path.basename(source)
            destination = os.path.join(target, filename)
            self.scp.put(source, destination, **kwargs)
        else:
            self.scp.put(source, target, **kwargs)

        