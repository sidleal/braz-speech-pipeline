import pandas as pd
import pymysql
import logging
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import os

from src.config import CONFIG

def open_ssh_tunnel(verbose=False):
    """Open an SSH tunnel and connect using a username and password.
    
    :param verbose: Set to True to show logging
    :return tunnel: Global SSH tunnel connection
    """
    
    if verbose:
        sshtunnel.DEFAULT_LOGLEVEL = logging.DEBUG

    tunnel = SSHTunnelForwarder(
        (CONFIG.sshtunnel.host, CONFIG.sshtunnel.port),
        ssh_username = CONFIG.sshtunnel.username,
        ssh_password = CONFIG.sshtunnel.password,
        remote_bind_address = ('127.0.0.1', 3306)
    )
    
    tunnel.start()

    return tunnel

def mysql_connect(ssh_tunnel):
    """Connect to a MySQL server using the SSH tunnel connection
    
    :return connection: Global MySQL database connection
    """

    connection = pymysql.connect(
        host=CONFIG.mysql.host,
        user=CONFIG.mysql.username,
        passwd=CONFIG.mysql.password,
        db=CONFIG.mysql.database,
        port=ssh_tunnel.local_bind_port
    )

    return connection

def run_query(connection, sql):
    """Runs a given SQL query via the global database connection.
    
    :param sql: MySQL query
    :return: Pandas DataFrame containing results for SELECT queries, 
             last inserted ID for INSERT queries, None for other queries
    """
    if sql.strip().lower().startswith('select'):
        return pd.read_sql_query(sql, connection)
    else:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            connection.commit()
            if sql.strip().lower().startswith('insert'):
                return cursor.lastrowid
            
def mysql_disconnect(connection):
    """Closes the MySQL database connection.
    """
    
    connection.close()

def close_ssh_tunnel(tunnel):
    """Closes the SSH tunnel connection.
    """
    
    tunnel.close

def add_audio(db_conn, audio_name, corpus_id) -> int:
    query = f"""
INSERT INTO Audio
    (
        name, corpus_id
    )
VALUES
    (
        '{audio_name}', {corpus_id}
    )
"""
    audio_id = run_query(db_conn, query)
    return audio_id #type: ignore

def add_audio_segment(db_conn, segment_path, text_asr, audio_id, segment_num, frames, duration, start_time, end_time, speaker_id):
    query = f"""
INSERT INTO Dataset 
    (
        file_path, file_with_user, data_gold, task, 
        text_asr, audio_id, segment_num,
        audio_lenght, duration, start_time, end_time, speaker_id
    )
VALUES 
    (
        '{segment_path}', 0, 0, 1, 
        '{text_asr}', {audio_id}, {segment_num},
        {frames}, {duration}, {start_time}, {end_time}, {speaker_id}
    )
"""
    return run_query(db_conn, query)     

def update_audio_duration(db_conn, audio_id, audio_duration):
    query = f"""
    UPDATE Audio
    SET duration = {audio_duration}
    WHERE id = {audio_id}
    """
    return run_query(db_conn, query)
    
def get_audios_by_name(db_conn, audio_name):
    query = f"""
    SELECT *
    FROM Audio
    WHERE name LIKE '{audio_name}%'
    """
    return run_query(db_conn, query)