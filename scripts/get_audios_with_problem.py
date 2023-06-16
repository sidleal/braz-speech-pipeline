import pymysql
import pandas as pd
from pathlib import Path
from config import CONFIG

def mysql_connect():
    """Connect to a MySQL server using the SSH tunnel connection
    
    :return connection: Global MySQL database connection
    """

    connection = pymysql.connect(
        host=CONFIG.mysql.host,
        user=CONFIG.mysql.username,
        passwd=CONFIG.mysql.password,
        db=CONFIG.mysql.database,
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

def get_segments_by_audio_id(db_conn, audio_id):
    query = f"""
    SELECT *
    FROM Dataset
    WHERE audio_id = {audio_id}
    """
    return run_query(db_conn, query)

def get_all_audios(db_conn):
    query = f"""
    SELECT *
    FROM Audio
    WHERE corpus_id = 2
    """
    return run_query(db_conn, query)

def analise_audios():
    db_conn = mysql_connect()
    
    audios = get_all_audios(db_conn)
    audio_with_problems = []
    
    if not audios.empty:
        for idx, audio in audios.iterrows():
            dataset = audio["name"].split("_")[1]
            audio_path = Path("data/nurc_sp") / dataset / audio["name"] / "audios"
            
            segments_on_folder = Path(audio_path).glob("*.wav")
            num_segments_on_folder = sum(1 for _ in segments_on_folder)
            
            segments_on_db = get_segments_by_audio_id(db_conn, audio["id"])
            
            if num_segments_on_folder != segments_on_db.shape[0]:
                print(f"Audio {audio['name']} need to be fixed! We have ")

if __name__ == "__main__":
    analise_audios()