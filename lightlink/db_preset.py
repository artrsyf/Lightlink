import psycopg2
import environ

env = environ.Env()
environ.Env().read_env()

def executSqlScript(sql_file_path):
    print(f"*SERVER RESPONSE: Chosen sql script path: {sql_file_path}")
    try:
        conn = psycopg2.connect(
            dbname=env("POSTGRES_DB"),
            user=env("POSTGRES_USER"),
            password=env("POSTGRES_PASSWORD"),
            host=env("POSTGRES_CONTAINER_SERVICE")
        )

        cur = conn.cursor()

        with open(sql_file_path, 'r') as file:
            sql_script = file.read()

        cur.execute(sql_script)
        conn.commit()

        cur.close()
        conn.close()
    except Exception as ex:
        print(f"*SERVER RESPONSE: Failed to execute dafault domain preset in database - {ex}")
    else:
        print(f"*SERVER RESPONSE: Succesfully checked database preset")

executSqlScript(env("SQL_PRESET_FILE_PATH"))