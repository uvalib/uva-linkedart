"""
Author: Ethan Gruber
Date modified: July 2026
Function: Load CSV files into appropriate SQLite table for the entity normalization webapp
"""

import argparse, sqlite3, sys, os, csv, uuid
import xml.etree.ElementTree as ET

DATABASE = 'entities.db'

#create SQLite tables if they don't exist
def create_tables():
    create_other = """
    CREATE TABLE IF NOT EXISTS TABLE_NAME (
        id text PRIMARY KEY,
        term text NOT NULL, 
        preferred_label text, 
        uri text
    );
    """
    
    create_places = """
    CREATE TABLE IF NOT EXISTS places (
        id text PRIMARY KEY,
        term text NOT NULL, 
        preferred_label text, 
        uri text,
        countryName text,
        adminName text,
        fcl text
    );
    """  
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            tables = ['cpf', 'genres', 'relators', 'subjects']
            
            #create table if it doesn't exist
            for table in tables:
                sql = create_other.replace('TABLE_NAME', table)
                cursor.execute(sql)   
            cursor.execute(create_places)
            conn.commit()
    
    except sqlite3.OperationalError as e:
        print(e) 
        sys.exit(1)


#insert each row into the appropriate table
def insert_into_db(table, row):

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        data = tuple(row)
        
        if table == 'places':
            cursor.execute("INSERT INTO " + table + "(id, term, preferred_label, uri, countryName, adminName, fcl) VALUES(?, ?, ?, ?, ?, ?, ?)", data)
        else:
            cursor.execute("INSERT INTO " + table + "(id, term, preferred_label, uri) VALUES(?, ?, ?, ?)", data)
            
        conn.commit()
        
        
def query_table(table):
    entities = []
    sql = 'SELECT id FROM ' + table
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(sql)            
    rows = cursor.fetchall()
    
    for row in rows:
        entities.append(row[0])
    
    return entities

def file_valid(filename):
    return os.path.isfile(filename)
        
def table_valid(table):
    if table == 'subjects' or table == 'cpf' or table == 'genres' or table == 'places' or table == 'relators':
        return True
    else:
        return False

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Filename, including directory path and .csv extension")
    parser.add_argument("-t", "--table", help="Table name to upload into: 'cpf', 'genres', 'relators', 'places', 'subjects'")
    args = parser.parse_args()
    
    #validate arguments
    if args.file and args.table:
        table = args.table
        filename = args.file
        
        if table_valid(table) == True and file_valid(filename) == True:
            
            create_tables()
            
            entities = query_table(table)
            
            #insert new rows from CSV into table if the ID does not exist
            with open(filename, mode ='r', encoding="utf-8") as file:    
                cr = csv.reader(file, delimiter=',', quotechar='"')
                header = next(cr)
                
                count = 0
                
                for row in cr:
                    id = row[0] 
                    if id not in entities:
                        insert_into_db(table, row)
                        count += 1
                        
                print("Inserted", count, "rows into", table)
            
            #parse the role XML file to extract the techniques    
            if table == 'relators':
                print("Checking relator - AAT technique concordance")
                count = 0
                tree = ET.parse('../mods-to-linkedart/roles.xml')
                root = tree.getroot()
                
                for role in root.findall('./role'):
                    if role.get('technique'):
                        id = str(uuid.uuid3(uuid.NAMESPACE_URL, role.get('technique')))
                        tuple = (id, role.text, role.get('techniqueLabel'), role.get('technique'))
                        if id not in entities:
                            insert_into_db(table, tuple)
                            count += 1
                            
                print("Inserted", count, "rows into", table)
                       
        else:
            print("Error: table or filename is invalid")
        
    else:
        if not args.file:
            print("Error: --file must be set")
        if not args.table:
            print("Error: --table must be set")
    
    #create_tables()
            
if __name__=="__main__":
    main()