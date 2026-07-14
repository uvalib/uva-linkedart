"""
Author: Ethan Gruber
Date modified: July
Function: Simple Python Flask webapp to serve as a layer over SPARQL
"""

from flask import Flask, render_template, request, Response
from SPARQLWrapper import SPARQLWrapper, TURTLE, JSON
from geomet import wkt
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

def query_places_for_object(uri):
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
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
    sparql.setQuery(sparql_query.replace("URI", uri))
    sparql.setReturnFormat(JSON)    
    
    try:
        results = sparql.queryAndConvert()
    
        return results
    except Exception as e:        
        return render_template('error.html') 

def query_object(uri):
    #use SPARQLWrapper to execute the SPARQL query
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql_query = """
    PREFIX la: <https://linked.art/ns/terms/>
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label ?place ?placeLabel ?coords ?creator ?creatorLabel ?technique ?techniqueLabel ?type ?typeLabel ?manifest WHERE {
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
    sparql.setQuery(sparql_query.replace("URI", uri))
    sparql.setReturnFormat(JSON)    
    
    try:
        results = sparql.queryAndConvert()
    
        return results
    except Exception as e:        
        return render_template('error.html') 

@app.route('/')
@app.route('/home')
def index():
    return render_template('page.html', page="index", data=None)

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
        
        if "results" in results:
        
            for row in results["results"]["bindings"]:
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
    
    if uri:
        results = query_places_for_object(uri)
        
        geoJson = {"type" : "FeatureCollection"}
        features = []
        
        for row in results["results"]["bindings"]:
            if "prodPlace" in row:            
                feature = {"type": "Feature", "name": row["prodPlaceLabel"]["value"]}
                geometry = wkt.loads(row["prodPlaceCoords"]["value"])
                feature["geometry"] = geometry
                feature["properties"] = {"toponym": row["prodPlaceLabel"]["value"], "gazetteer_uri": row["prodPlace"]["value"], "type": "productionPlace"}
                
                features.append(feature)
            elif "subjectPlace" in row:
                feature = {"type": "Feature", "name": row["subjectPlaceLabel"]["value"]}
                geometry = wkt.loads(row["subjectPlaceCoords"]["value"])
                feature["geometry"] = geometry
                feature["properties"] = {"toponym": row["subjectPlaceLabel"]["value"], "gazetteer_uri": row["subjectPlace"]["value"], "type": "subjectPlace"}
                
                features.append(feature)
        
        geoJson["features"] = features
        
        return geoJson
    else:
        return {"error": "no uri parameter supplied"}

if __name__=="__main__":
    main()

