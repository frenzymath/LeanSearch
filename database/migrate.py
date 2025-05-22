from psycopg import Connection

def migrate(conn: Connection):
    with conn.cursor() as cursor:
        cursor.execute("ALTER TABLE module ADD COLUMN project_name TEXT")
        cursor.execute("UPDATE module SET project_name = 'mathlib'")
