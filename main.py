# base imports
import os
import sqlite3
import sys

# auxiliary imports
import requests
import json

# colorama terminal coloring
from colorama import init, Fore, Back, Style
init()

def red_print(text):
    print(Fore.RED + text + Style.RESET_ALL)

class SQLiteHandler:
    def __init__(self):
        self.tables = {
            'literature':
                [
                    ['lit_id', 'INTEGER', 'PRIMARY KEY'],
                    ['DOI', 'TEXT'],
                    ['author', 'TEXT'],
                    ['lit_references', 'TEXT']
                ],
            'network':
                [
                    ['net_id', 'INTEGER', 'PRIMARY KEY'],
                    ['DOI', 'TEXT'],
                    ['net_lit_id_from', 'INTEGER'],
                    ['net_lit_ids_to', 'INTEGER']
                ]
        }
        self.sqldb, self.sqldb_cursor = self.check_db()
    
    def check_db(self):
        """checking if the DB exists and if its contents are as expected (look at self.tables)

        Returns:
            Connection, Cursor: connection and cursor to sqlite DB
        """
        connection = sqlite3.connect(os.path.join('db', 'lit.db'))
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        db_tables = [tbl[0] for tbl in cursor.fetchall()]
        for tbl in self.tables.keys():
            if tbl not in db_tables:
                red_print(f"[+] table {tbl} does not exist in DB. Creating...")
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
    def __init__(self, user_agent_mail):
        self.api_url = "https://api.crossref.org/works/"
        self.user_agent_header = self.generate_user_agent(user_agent_mail)
        self.allowed_args = [
            "query.author",
            "query.title"
        ]
    
    def encode_url(self, text):
        """url-encoding string

        Args:
            text (str): string to be encoded

        Returns:
            str: url-encoded text
        """
        return requests.utils.quote(text, safe='+')
    
    def generate_user_agent(self, user_agent_mail):
        """generating user-agent per 'etiquette' of Crossref API

        Args:
            user_agent_mail (str): mail address where Crossref can send an email to if the script is doing sth dumb

        Returns:
            dict: user-agent as dict ready for requests
        """
        TEMPLATE = {
            'User-Agent': f'Acanet/0.1 (https://github.com/DaBootO/acanet; mailto:{user_agent_mail})',
            'Accept': 'application/json'
        }
        return TEMPLATE
    
    def generate_url_works_doi(self, DOI):
        """generates url-encoded URL for the works/DOI endpoint of the CrossrefAPI

        Args:
            DOI (str): DOI of the wanted lit obj

        Returns:
            str: url-encoded url ready for requests
        """
        return self.api_url + self.encode_url(DOI)
    
    def generate_url_works_query(self, query):
        query_str = ""
        for k in query.keys():
            query_str += f"{k}={self.encode_url(query[k].replace(' ', '+'))}&"
        
        return self.api_url[:-1] + '?' + query_str[:-1], query_str[:-1]
    
    def call_works_doi_api(self, DOI, thread=None):
        """calling the Crossref RESTful API. Ready for multithreading

        Args:
            DOI (str): DOI of the needed lit object
            thread (int, optional): thread number. just interesting afte multithreadign implementatation. Defaults to None.

        Returns:
            json: json obj for further parsing
        """
        if thread == None: thread = "+"
        URL = self.generate_url_works_doi(DOI)
        print(f"[{thread}] GET: works/{DOI}")
        response = requests.get(URL, headers=self.user_agent_header)
        return json.loads(response.text)
    
    def call_works_query_api(self, query, thread=None):       
        for k in query.keys():
            if k not in self.allowed_args:
                red_print(f"[+] key: {k} not allowed!")
                red_print(f"[+] allowed args:")
                for a in self.allowed_args:
                    red_print(f"[+] {a}")
                raise SystemExit('NotAllowed keys in query! Exiting...')
        
        if thread == None: thread = "+"
        URL, QUERY = self.generate_url_works_query(query)
        print(f"[{thread}] GET: works?{QUERY}")
        response = requests.get(URL, headers=self.user_agent_header)
        return json.loads(response.text)

if __name__ == '__main__':
    print('TEST here')
    CAPI = CrossrefAPI(user_agent_mail="testmail@mail.com")
    SQLTest = SQLiteHandler()
    query = {'query.title': 'testing this shit', 'query.author': 'Dario Contrino'}
    x = CAPI.call_works_query_api(query)
    print(x)
    # test = CAPI.call_works_doi_api("10.1007/s11340-011-9584-y")
    # for i in range(10):
    #     if 'reference' in test['message'].keys():
    #         print(f"[+] {test['message']['reference'][0]['unstructured']}")
    #         doi = test['message']['reference'][0]['DOI']
    #         test = CAPI.call_works_doi_api(doi)
    #     else:
    #         print("[+] FINISHED BC NO DOIs LEFT!")
    