import requests
import sqlite3
import os

class SQLiteHandler:
    def __init__(self):
        self.tables = {
            'literature':
                [
                    ['lit_id', 'INTEGER', 'PRIMARY KEY'],
                    ['lit_doi', 'TEXT'],
                    ['lit_authors', 'TEXT'],
                    ['lit_references', 'TEXT']
                ],
            'network':
                [
                    ['net_id', 'INTEGER', 'PRIMARY KEY'],
                    ['net_lit_id_from', 'INTEGER'],
                    ['net_lit_ids_to', 'INTEGER']
                ]
        }
        self.sqldb, self.sqldb_cursor = self.check_db()
    
    def check_db(self):
        """checking if the DB exists and if its contents are as expected (look at self.tables)

        Returns:
            Connection: connection to sqlite DB
        """
        connection = sqlite3.connect(os.path.join('db', 'lit.db'))
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        db_tables = [tbl[0] for tbl in cursor.fetchall()]
        for tbl in self.tables.keys():
            if tbl not in db_tables:
                print(f"[+] table {tbl} does not exist in DB. Creating...")
                cols = self.tables[tbl]
                col_query = ""
                for col in cols:
                    col_query += f"{' '.join(col)}"
                    if col != cols[-1]:
                        col_query += ','
                
                sql_query = f"CREATE TABLE IF NOT EXISTS {tbl} ({col_query})"
                cursor.execute(sql_query)
                connection.commit()
        return connection, cursor

class CrossrefAPI:
    """
    We will use the CrossrefAPI to get data about references etc. from Crossref
    """
    def __init__(self):
        self.api_url = "https://api.crossref.org/works/"
        self.api_header_accept = "accept: application/json"
    
    """
    generating the needed api_url and encoding everything to url
    """
    def generate_URL(self, DOI):
        return self.api_url + requests.utils.quote(DOI, safe='')
    
    def test(self, DOI):
        print(self.generate_URL(DOI))

if __name__ == '__main__':
    print('TEST')
    CAPI = CrossrefAPI()
    CAPI.test("10.1007/s11340-011-9584-y")
    SQLTest = SQLiteHandler()