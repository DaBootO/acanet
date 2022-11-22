# base imports
import os
import sqlite3
import sys

# auxiliary imports
import requests
import json
import subprocess
from fuzzywuzzy import fuzz
import itertools

# colorama terminal coloring
from colorama import init, Fore, Back, Style
init()

def red_print(text):
    print(Fore.RED + '[!] ' + str(text) + Style.RESET_ALL)

def yellow_print(text):
    print(Fore.YELLOW + '[?] ' + str(text) + Style.RESET_ALL)

def thread_print(text, thread='+'):
    print(f"[{thread}] {str(text)}")

def green_thread_print(text, thread='+'):
    print(Fore.GREEN +  f"[{thread}] {str(text)}" + Style.RESET_ALL)

class SQLiteHandler:
    def __init__(self):
        self.tables = {
            'literature':
                [
                    ['lit_id', 'INTEGER', 'PRIMARY KEY'],
                    ['DOI', 'TEXT'],
                    ['author', 'TEXT'],
                    ['title', 'TEXT'],
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
        connection = sqlite3.connect(os.path.join('db', 'lit.sqlite'))
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

class RubyAnystyle:
    def __init__(self):
        pass
    
    def call_anystyle(self, parse_string):
        output = subprocess.check_output(f"""echo '{parse_string}' | anystyle parse /dev/stdin""", shell=True)
        return json.loads(output)[0]

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
        self.ruby_anystyle = RubyAnystyle()
        self.doi_stack = iter([])
    
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
        """calling the Crossref RESTful API. works/doi endpoint. Ready for multithreading

        Args:
            DOI (str): DOI of the needed lit object
            thread (int, optional): thread number. just interesting after multithreadign implementatation. Defaults to None.

        Returns:
            json: json obj for further parsing
        """
        if thread == None: thread = "+"
        URL = self.generate_url_works_doi(DOI)
        print(f"[{thread}] GET: works/{DOI}")
        response = requests.get(URL, headers=self.user_agent_header)
        return json.loads(response.text)
    
    def call_works_query_api(self, query, thread='+'):
        """calling the Crossref RESTful Api. works/query endpoint. Ready for multithreading.

        Args:
            query (dict): dict of query arguments
            thread (int, optional): thread number. just interesting after multithreading implementation. Defaults to None.

        Raises:
            SystemExit: if arguments not correct exit script

        Returns:
            json: json obj for further parsing
        """
        for k in query.keys():
            if k not in self.allowed_args:
                red_print(f"key: {k} not allowed!")
                red_print(f"allowed args:")
                for a in self.allowed_args:
                    red_print(f"{a}")
                raise SystemExit('NotAllowed keys in query! Exiting...')
        
        URL, QUERY = self.generate_url_works_query(query)
        print(f"[{thread}] GET: works?{QUERY}")
        response = requests.get(URL, headers=self.user_agent_header)
        return json.loads(response.text)
    
    def parse_json_works_doi(self, json_obj, thread='+'):
        doi = json_obj['message']['DOI']
        author = json_obj['message']['author']
        reference = json_obj['message']['reference']
        # thread_print(doi)
        # thread_print(author)
        for r in reference:
            if 'ISSN' in r.keys():
                yellow_print(f"FOUND ISSN: {r['ISSN']}")
            if 'DOI' not in r.keys():
                red_print('DOI not found! Trying with anystyle...')
                output = self.ruby_anystyle.call_anystyle(r['unstructured'])
                output_author = output['author'][0]
                output_title = output['title']
                if output_author == {} or output_title == []:
                    red_print('NOT able to go further because there is no sufficient data...')
                    break
                query = {
                    'query.author': output_author['given'] + " " + output_author['family'],
                    'query.title': output_title[0]
                }
                works_query_output = self.call_works_query_api(query)
                self.parse_json_works_query(works_query_output, fuzzy_string=output_title[0])
            else:
                green_thread_print(f"found DOI: {r['DOI']}")
    
    def parse_json_works_query(self, json_obj, fuzzy_string=None, thread='+'):
        lit_list = json_obj['message']['items']
        if lit_list == []:
            red_print("parsed list empty! returning...")
            return
        if fuzzy_string != None:
            comparison = [[fuzz.partial_ratio(fuzzy_string, lit['title'][0]), lit['title'][0]] for lit in lit_list]
            sorted_comparison = sorted(comparison, key=lambda x: x[0])[::-1]
            if sorted_comparison[0][0] < 95:
                red_print("Could not find a suitable option. Skipping...")
                
        # for lit in lit_list:
        #     title = lit['title'][0]
            # red_print(lit['DOI'])
            # red_print(lit['title'])
            # red_print(lit['author'][0])
    
if __name__ == '__main__':
    print('TEST here')
    CAPI = CrossrefAPI(user_agent_mail="testmail@mail.com")
    SQLTest = SQLiteHandler()
    # query = {'query.title': 'testing this shit', 'query.author': 'Dario Contrino'}
    # x = CAPI.call_works_query_api(query)
    # print(x)
    test = CAPI.call_works_doi_api("10.1007/s11340-011-9584-y")
    CAPI.parse_json_works_doi(test)
    # for i in range(10):
    #     if 'reference' in test['message'].keys():
    #         print(f"[+] {test['message']['reference'][0]['unstructured']}")
    #         doi = test['message']['reference'][0]['DOI']
    #         test = CAPI.call_works_doi_api(doi)
    #     else:
    #         print("[+] FINISHED BC NO DOIs LEFT!")
    