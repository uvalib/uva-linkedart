"""
Author: Ethan Gruber
Date modified: June 2026
Function: Simple FastAPI web app to reconcile entity strings to URIs with SQLite lookups. 
    Also includes EDTF date normalization to ISO8601
"""

import sqlite3, json, os, uuid, uvicorn

from edtf import parse_edtf, text_to_edtf, struct_time_to_date
from typing import Union
from fastapi import APIRouter, FastAPI, Response

DATABASE = 'entities.db'

app = FastAPI()
router = APIRouter()

@app.get("/")
def read_root():
    return {"API": "Pass 'id' or 'term' request parameter to /query/{table} path for JSON response"}

@app.get("/encode")
def encode_string(string: Union[str, None] = None):
    id = str(uuid.uuid3(uuid.NAMESPACE_URL, string))
    
    return {"id": id, 
            "string": string}

@app.get("/query/{table}")
def query_table(table: str, id: Union[str, None] = None, term: Union[str, None] = None):
    if id or term:
        output = []
        conn = sqlite3.connect(DATABASE)        
        cur = conn.cursor()
        
        if id:
            cur.execute('SELECT id,preferred_label,uri FROM ' + table + ' WHERE id =?', (id,))
        elif term:
            cur.execute('SELECT id,preferred_label,uri FROM ' + table + ' WHERE term =?', (term,))
    
        row = cur.fetchone()
        if row:
            object = {"label": row[1]}
            if row[2]:
                object["uri"] = row[2]
            output.append(object)
        conn.close()
        
        return output
    else:
        return {"error": "'id' or 'term' parameter undefined"}  

@app.get("/parse")
def parse_date(date: Union[str, None] = None):
    try:
        date
    except NameError:
        return {"error": "date parameter undefined"}
    else:
        
        if len(date) > 0:
            try:
                e = parse_edtf(date)                
            except:
                #if the date is not EDTF, then try parsing EDTF from the textual string
                try:
                    string = text_to_edtf(date)
                except: 
                    return {"error": "date param is not parseable as EDTF"}
                else:
                    try:
                        e = parse_edtf(string)
                    except:
                        return {"error": "date param is not parseable as EDTF"}
                    else:
                        fromDate = struct_time_to_date(e.lower_strict())
                        toDate = struct_time_to_date(e.upper_strict())
                        
                        object = {"fromDate": fromDate, "toDate": toDate}
                    
                        return object
            else:
                fromDate = struct_time_to_date(e.lower_strict())
                toDate = struct_time_to_date(e.upper_strict())
                
                object = {"fromDate": fromDate, "toDate": toDate}
            
                return object
        else: 
            return {"error": "date parameter is zero length"}

if __name__ == "__main__":
    uvicorn.run(app, port=8001)