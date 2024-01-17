from typing import Iterable, Union
import paramiko
from scp import SCPClient
import os
import pipes
from enum import Enum
from pathlib import Path

from src.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ContentType(Enum):
    FILES = "files"
    FOLDERS = "folders"
    ALL = "all"


class FileTransfer:
    def __enter__(self):
        self.ssh = self._create_ssh_client(
            CONFIG.sshtunnel.host,
            CONFIG.sshtunnel.port,
            CONFIG.sshtunnel.username,
            CONFIG.sshtunnel.password,
        )
        transport = self.ssh.get_transport()
        # Ensure the connection is kept alive for the duration of the transcription
        transport.set_keepalive(30)
        if transport is None or not transport.is_active():
            raise Exception("SSH connection is not active.")

        # Ensure that the channel does not time out while transfering audio segments
        self.scp = SCPClient(transport, socket_timeout=None)
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

        injected_command = "".join(out)
        # reinterpret printf output as a command

        # command = f"mkdir -p -v {folder_path}"  # Ignore error if the folder already exists
        self.ssh.exec_command(injected_command)

    def put(
        self,
        source: Union[str, Iterable[str]],
        target: str,
        target_is_folder: bool = False,
        **kwargs
    ):
        if target_is_folder:
            self.mkdir(target)
        else:
            target_directory = os.path.dirname(target)
            self.mkdir(target_directory)

        try:
            self.scp.put(source, target.encode(), **kwargs)
        except Exception as e:
            logger.error(f"Error transferring files.")
            logger.debug(e)
        else:
            logger.debug(f"Files transferred successfully.")

    def read_all_files(self, path):
        command = f"ls {path}"
        stdin, stdout, stderr = self.ssh.exec_command(command)
        print(stderr)
        return stdout.readlines()

    def read_all_files_in_folder_and_subfolders(self, path):
        command = f"find {path} -type f"
        stdin, stdout, stderr = self.ssh.exec_command(command)
        print(stderr)
        return stdout.readlines()

    def list_directory_contents(
        self,
        path: Path,
        content_type: ContentType = ContentType.ALL,
        recursive: bool = False,
    ):
        # Validate the content_type parameter
        if not isinstance(content_type, ContentType):
            raise ValueError(
                f"Invalid content_type: {content_type}. Must be an instance of ContentType enum."
            )

        # Build the command based on the user options
        if recursive:
            # Using the find command to list contents recursively
            command = f"find {path}"
            if content_type == ContentType.FILES:
                # If listing files only, limit to files
                command += " -type f"
            elif content_type == ContentType.FOLDERS:
                # If listing folders only, limit to directories
                command += " -type d"
        else:
            # Using the ls command to list contents of the specified directory only
            if content_type == ContentType.FILES:
                command = f"ls -p {path} | grep -v /"  # The -p option appends a / to directory names
            elif content_type == ContentType.FOLDERS:
                command = f"ls -d {path}/*/"
            else:  # content_type == "all"
                command = f"ls {path}"

        # Execute the command
        stdin, stdout, stderr = self.ssh.exec_command(command)

        # Collect and return the results
        result = stdout.readlines()
        if stderr.readlines():
            logger.error(f"Error listing directory contents: {stderr.readlines()}")
        return result
