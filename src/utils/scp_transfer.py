import paramiko
from scp import SCPClient
import os
import pipes

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

    def mkdir(self, folder_path: str, recursive: bool = False):

        command = f"printf '%q ' mkdir -p {pipes.quote(folder_path)}"  # Ignore error if the folder already exists
        stdin, stdout, stderr = self.ssh.exec_command(command)

        # exec_command() returns file-like objects representing the input (stdin),
        # output (stdout) and error (stderr) channels from the SSH session.
        # You may need to call read() or readlines() on these objects to retrieve the actual command output.
        out = stdout.readlines()
        err = stderr.readlines()

        logger.error(err)

        injected_command = "".join(out)
        # reinterpret printf output as a command

        # command = f"mkdir -p -v {folder_path}"  # Ignore error if the folder already exists
        self.ssh.exec_command(injected_command)

    def put(self, source: str, target: str, target_is_folder: bool = False, **kwargs):
        if target_is_folder:
            self.mkdir(target)
            filename = os.path.basename(source)
            target = os.path.join(target, filename)
        else:
            target_directory = os.path.dirname(target)
            self.mkdir(target_directory)

        try:
            self.scp.put(source, target.encode(), **kwargs)
        except Exception as e:
            logger.error(f"Error transferring file.")
            logger.debug(e)