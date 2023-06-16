import paramiko
from scp import SCPClient

from src.config import CONFIG

def _createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

ssh = _createSSHClient(CONFIG.sshtunnel.host, CONFIG.sshtunnel.port, CONFIG.sshtunnel.username, password= CONFIG.sshtunnel.password)
scp = SCPClient(ssh.get_transport())