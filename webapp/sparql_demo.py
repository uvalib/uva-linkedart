"""
Author: Ethan Gruber
Date modified: July 2026
Function: Simple Python Flask webapp to serve as a layer over SPARQL
"""

import math, requests
from flask import Flask, render_template, request, Response
from geomet import wkt
from rdflib import Graph
from werkzeug.middleware.proxy_fix import ProxyFix

session = requests.Session()

SPARQL_ENDPOINT = "http://localhost:3030/uvalib/query"
LIMIT = 10

app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

def query_objects(offset):
    sparql_query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX la: <https://linked.art/ns/terms/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?object ?label ?date (group_concat(?creatorLabel; separator="; ") as ?creators) WHERE {{
      ?object rdf:type  crm:E22_Human-Made_Object ;
              rdfs:label ?label .
      OPTIONAL {{?object crm:P108i_was_produced_by/crm:P4_has_time-span/rdfs:label ?date}}
      OPTIONAL {{?object crm:P108i_was_produced_by/crm:P14_carried_out_by ?creator .
      ?creator rdfs:label ?creatorLabel}}
    }} GROUP BY ?object ?label ?date LIMIT {LIMIT} OFFSET {offset}
    """    
    
    resp = session.get(
        SPARQL_ENDPOINT,
        params={"query": sparql_query, "format": "json"},
        headers={"Accept": "application/sparql-results+json"},
    )
    return resp.json()

def query_objects_count():
    sparql_query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    SELECT (COUNT(?object) as ?count) WHERE {
      ?object rdf:type crm:E22_Human-Made_Object 
    }
    """
    
    resp = session.get(
        SPARQL_ENDPOINT,
        params={"query": sparql_query, "format": "json"},
        headers={"Accept": "application/sparql-results+json"},
    )    
    return resp.json()

def get_label(uri):
    sparql_query = f"""
    PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label WHERE {{
        <{uri}> rdfs:label ?label
    }}
    """    
    
    resp = session.get(
        SPARQL_ENDPOINT,
        params={"query": sparql_query, "format": "json"},
        headers={"Accept": "application/sparql-results+json"},
    )    
    return resp.json()["results"]["bindings"][0]["label"]["value"]

def query_places():
    sparql_query = """
    PREFIX la: <https://linked.art/ns/terms/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT (count(?object) as ?count) ?prodPlace ?prodPlaceLabel ?prodPlaceCoords ?subjectPlace ?subjectPlaceLabel ?subjectPlaceCoords WHERE {
      {?object crm:P108i_was_produced_by/crm:P7_took_place_at ?prodPlace .
        ?prodPlace rdfs:label ?prodPlaceLabel ;
                   crm:P168_place_is_defined_by ?prodPlaceCoords 
      }
      UNION {?object crm:P129_is_about ?subject .
        ?subject crm:P94i_was_created_by/crm:P15_was_influenced_by ?subjectPlace .
        ?subjectPlace rdfs:label ?subjectPlaceLabel .
        {?subjectPlace crm:P168_place_is_defined_by ?subjectPlaceCoords}
        UNION {?subjectPlace la:equivalent/crm:P168_place_is_defined_by ?subjectPlaceCoords }
      }
    } GROUP BY ?prodPlace ?prodPlaceLabel ?prodPlaceCoords ?subjectPlace ?subjectPlaceLabel ?subjectPlaceCoords ORDER BY DESC(?count)
    """
    
    resp = session.get(
        SPARQL_ENDPOINT,
        params={"query": sparql_query, "format": "json"},
        headers={"Accept": "application/sparql-results+json"},
    )    
    return resp.json()

def query_places_for_object(uri):
    sparql_query = """
    PREFIX la: <https://linked.art/ns/terms/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?prodPlace ?prodPlaceLabel ?prodPlaceCoords ?subjectPlace ?subjectPlaceLabel ?subjectPlaceCoords WHERE {
        BIND (<URI> as ?object)
        {?object crm:P108i_was_produced_by/crm:P7_took_place_at ?prodPlace .
            ?prodPlace rdfs:label ?prodPlaceLabel ;
                crm:P168_place_is_defined_by ?prodPlaceCoords 
        }
        UNION {?object crm:P129_is_about ?subject .
        ?subject crm:P94i_was_created_by/crm:P15_was_influenced_by ?subjectPlace .
          ?subjectPlace rdfs:label ?subjectPlaceLabel .
        {?subjectPlace crm:P168_place_is_defined_by ?subjectPlaceCoords}
        UNION {?subjectPlace la:equivalent/crm:P168_place_is_defined_by ?subjectPlaceCoords }
      }
    }
    """
    
    resp = session.get(
        SPARQL_ENDPOINT,
        params={"query": sparql_query.replace("URI", uri), "format": "json"},
        headers={"Accept": "application/sparql-results+json"},
    )    
    return resp.json()

#DESCRIBE query for object
def get_object(uri):
    sparql_query = f"DESCRIBE <{uri}>"
    resp = session.get(
        SPARQL_ENDPOINT,
        params={"query": sparql_query, "format": "ttl"},
        headers={"Accept": "text/turtle"},
    )    
    return resp.text
    

def query_object(uri):
    sparql_query = """
    PREFIX la: <https://linked.art/ns/terms/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?object ?label ?place ?placeLabel ?coords ?creator ?creatorLabel ?technique ?techniqueLabel ?type ?typeLabel ?manifest WHERE {
      BIND (<URI> as ?object)
      ?object rdfs:label ?label .
      OPTIONAL {?object crm:P108i_was_produced_by/crm:P7_took_place_at ?place .
      ?place rdfs:label ?placeLabel .
        OPTIONAL {?place crm:P168_place_is_defined_by ?coords }}
      OPTIONAL {
        {?object crm:P108i_was_produced_by ?prod .
          ?prod crm:P14_carried_out_by ?creator 
        OPTIONAL {?prod crm:P32_used_general_technique ?technique .
          ?technique rdfs:label ?techniqueLabel}}
        UNION {?object crm:P108i_was_produced_by/crm:P9_consists_of ?part .
          ?part crm:P14_carried_out_by ?creator
          OPTIONAL {?part crm:P32_used_general_technique ?technique .
          ?technique rdfs:label ?techniqueLabel}}
        ?creator rdfs:label ?creatorLabel
      }
      OPTIONAL {?object crm:P2_has_type ?type .
      ?type rdfs:label ?typeLabel}
      OPTIONAL {?object crm:P129i_is_subject_of/la:digitally_carried_by/la:access_point ?manifest}
    }
    """
    
    resp = session.get(
        SPARQL_ENDPOINT,
        params={"query": sparql_query.replace("URI", uri), "format": "json"},
        headers={"Accept": "application/sparql-results+json"},
    )    
    return resp.json()

@app.route('/')
@app.route('/home')
def index():
    page = request.args.get('page', 1, type=int)  # Get page number from query params (default = 1)
    offset = (page - 1) * LIMIT
    
    count_response = query_objects_count()
    count = int(count_response["results"]["bindings"][0]["count"]["value"])
    last = math.ceil(count / LIMIT)
    
    results = query_objects(offset=offset)
    
    return render_template('page.html', page="index", data=results, limit=LIMIT, count=count, page_num=page, last=last)

@app.route('/object')
def page_object():
    #uri = "https://search.lib.virginia.edu/sources/images/items/u1002440"
    uri = request.args.get('uri')
    
    if uri:
        metadata = {}
        types = {}
        places = {}
        creators = {}
        
        hasCoords = False
        
        results = query_object(uri)
        
        ttl = get_object(uri)
        metadata["ttl"] = ttl
        
        if "results" in results:
        
            for row in results["results"]["bindings"]:
                if "object" not in metadata:
                    metadata["uri"] = row["object"]["value"]
                if "label" not in metadata:
                    metadata["label"] = row["label"]["value"]        
                if "manifest" not in metadata and "manifest" in row:
                    metadata["manifest"] = row["manifest"]["value"]
                if "type" in row:
                    if row["type"]["value"] not in types:
                        types[row["type"]["value"]] = row["typeLabel"]["value"]
                if "place" in row:
                    if row["place"]["value"] not in places:
                        places[row["place"]["value"]] = {"label": row["placeLabel"]["value"]}
                        
                        if "coords" in row:
                            if len(row["coords"]["value"]) > 0:
                                places[row["place"]["value"]]["coords"] = row["coords"]["value"]
                                hasCoords = True
                        
                if "creator" in row:
                    if row["creator"]["value"] not in creators:
                        creators[row["creator"]["value"]] = {"label" : row["creatorLabel"]["value"]}
                        
                        if "technique" in row:
                            creators[row["creator"]["value"]]["technique"] = row["technique"]["value"]
                            creators[row["creator"]["value"]]["techniqueLabel"] = row["techniqueLabel"]["value"]
                    
            if len(types) > 0:
                metadata["types"] = types
            if len(places) > 0:                
                metadata["places"] = places
            if len(creators) > 0:
                metadata["creators"] = creators
            
            return render_template('page.html', page="object", data=metadata, hasCoords=hasCoords)
        
        else:
            return render_template('page.html', page="index", data=None) 
        
    else:
        return render_template('page.html', page="index", data=None) 
    
@app.route('/getGeo')
def generate_geojson():
    uri = request.args.get('uri')
    
    #choose which query to execute, one for a specific object URI, or all objects in the endpoint
    if uri:
        results = query_places_for_object(uri)   
        maxCount = None
        grade = None     
    else:
        results = query_places()
        maxCount = int(results["results"]["bindings"][0]["count"]["value"])
        grade = math.ceil(maxCount / 5)
        
    #process results    
    geoJson = {"type" : "FeatureCollection"}
    features = []
        
    for row in results["results"]["bindings"]:
        if "prodPlace" in row:            
            feature = {"type": "Feature", "name": row["prodPlaceLabel"]["value"]}
            geometry = wkt.loads(row["prodPlaceCoords"]["value"])
            feature["geometry"] = geometry
            feature["properties"] = {"toponym": row["prodPlaceLabel"]["value"], "gazetteer_uri": row["prodPlace"]["value"], "type": "productionPlace"}
            if "count" in row:
                count = int(row["count"]["value"])
                radius = derive_radius(count, grade)
                
                feature["properties"]["radius"] = radius
                 
            
            features.append(feature)
        elif "subjectPlace" in row:
            feature = {"type": "Feature", "name": row["subjectPlaceLabel"]["value"]}
            geometry = wkt.loads(row["subjectPlaceCoords"]["value"])
            feature["geometry"] = geometry
            feature["properties"] = {"toponym": row["subjectPlaceLabel"]["value"], "gazetteer_uri": row["subjectPlace"]["value"], "type": "subjectPlace"}
            if "count" in row:
                count = int(row["count"]["value"])
                radius = derive_radius(count, grade)
                
                feature["properties"]["radius"] = radius
            
            features.append(feature)
    
    geoJson["features"] = features
    
    return geoJson    

def derive_radius(count, grade):
    radius = 5
    
    if count <= grade: 
        radius = 5
    elif count > grade and count <= (grade * 2):
        radius = 10
    elif count > (grade * 2) and count <= (grade * 3):
        radius = 15
    elif count > (grade * 3) and count <= (grade * 4):
        radius = 20
    elif count > (grade * 4):
        radius = 25
    else:
        radius = 5
        
    return radius


if __name__ == '__main__':
    app.run(debug=True, threaded=True)

