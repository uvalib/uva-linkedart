"""
Author: Ethan Gruber
Date modified: July
Function: Simple Python Flask webapp to serve as a layer over SPARQL
"""

from flask import Flask, render_template, request, Response
from SPARQLWrapper import SPARQLWrapper, TURTLE, JSON
#from werkzeug.middleware.proxy_fix import ProxyFix

SPARQL_ENDPOINT = "http://localhost:3030/uvalib/query"

app = Flask(__name__)

def get_label(uri):
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql_query = f"""
    PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label WHERE {{
        <{uri}> rdfs:label ?label
    }}
    """    
    
    sparql.setReturnFormat(JSON)
    sparql.setQuery(sparql_query)
    
    try:
        results = sparql.queryAndConvert()

        return results["results"]["bindings"][0]["label"]["value"]
    except Exception as e:
        print(e)

def query_object(uri):
    #use SPARQLWrapper to execute the SPARQL query
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql_query = """
    PREFIX la: <https://linked.art/ns/terms/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label ?place ?placeLabel ?coords ?creator ?creatorLabel ?type ?typeLabel ?manifest WHERE {
      BIND (<URI> as ?object)
      ?object rdfs:label ?label .
      OPTIONAL {?object crm:P108i_was_produced_by/crm:P7_took_place_at ?place .
      ?place rdfs:label ?placeLabel .
        OPTIONAL {?place crm:P168_place_is_defined_by ?coords }}
      OPTIONAL {
        {?object crm:P108i_was_produced_by/crm:P14_carried_out_by ?creator}
        UNION {?object crm:P108i_was_produced_by/crm:P9_consists_of/crm:P14_carried_out_by ?creator}
        ?creator rdfs:label ?creatorLabel
      }
      OPTIONAL {?object crm:P2_has_type ?type .
      ?type rdfs:label ?typeLabel}
      OPTIONAL {?object crm:P129i_is_subject_of/la:digitally_carried_by/la:access_point ?manifest}
    }
    """
    sparql.setQuery(sparql_query.replace("URI", uri))
    sparql.setReturnFormat(JSON)    
    
    try:
        results = sparql.queryAndConvert()
    
        return results
    except Exception as e:
        print(e)

@app.route('/')
@app.route('/home')
def index():
    return render_template('page.html', page="index", data=None)

@app.route('/object')
def page_object():
    uri = request.args.get('uri')  # Get page number from query params (default = 1)
    
    if uri:
    #uri = "https://search.lib.virginia.edu/sources/images/items/u1002440"
    
        metadata = {}
        types = {}
        places = {}
        creators = {}
        
        results = query_object(uri)
        
        for row in results["results"]["bindings"]:
            if "label" not in metadata:
                metadata["label"] = row["label"]["value"]        
            if "manifest" not in metadata and "manifest" in row:
                metadata["manifest"] = row["manifest"]["value"]
            if "type" in row:
                if row["type"]["value"] not in types:
                    types[row["type"]["value"]] = row["typeLabel"]["value"]
            if "place" in row:
                if row["place"]["value"] not in types:
                    places[row["place"]["value"]] = {"label": row["placeLabel"]["value"], "coords": row["coords"]["value"]}
            if "creator" in row:
                if row["creator"]["value"] not in types:
                    creators[row["creator"]["value"]] = row["creatorLabel"]["value"]
                
    
        metadata["types"] = types
        metadata["places"] = places
        metadata["creators"] = creators
        
        return render_template('page.html', page="object", data=metadata)
        
    else:
       return render_template('page.html', page="index", data=None) 

if __name__=="__main__":
    main()

