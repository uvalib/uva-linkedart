"""
Author: Ethan Gruber
Date: July 2026
Function: Generate RDF for concepts connected to Linked Art/CIDOC-CRM objects
"""

import sqlite3, argparse, time, csv, os
from edtf import parse_edtf, struct_time_to_date
from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, XSD, SKOS, RDFS, DCTERMS

DATABASE = 'webapp/entities.db'

entities = {}

place_types = []
place_type_uris = []

#this is for loading concordances from CSV
#wd_metadata = {}

def extract_table(table):
    
    sql = """SELECT DISTINCT uri, preferred_label
    FROM TABLE
    """
    connect = sqlite3.connect(DATABASE)
    cursor = connect.cursor()
    
    #fetch bibs
    cursor.execute(sql.replace("TABLE", table))
    rows = cursor.fetchall()
    
    process_rows(table, rows)
    
    #create concepts for place types linked to Geonames feature codes
    if table == 'places':
        print("Generating metadata for geographic feature types")
        generate_feature_types(place_types)
    
    generate_rdf(table, entities)

#process all the rows in the SQLite table into a data dictionary with properties to be mapped into RDF in a subsequent function
def process_rows(table, rows):
    global entities
    
    i = 0
    
    for concept in rows:
        if len(concept[0]) > 0:
            uri = concept[0]
            prefLabel = concept[1]
            
            print(f"Processing {i + 1} of {len(rows)}, {uri}: {prefLabel}")
            
            #only create unique RDF for a concept; the same URI may be used for small variations of strings
            if uri not in entities:
                process_concept(table, uri, prefLabel)
                
                i += 1
    
    #perform lookup of male and female AAT URIs
    if table == 'cpf':
        male = "http://vocab.getty.edu/aat/300189559"
        metadata = query_getty(uri=male)
        metadata["prefLabel"] = metadata["getty:prefLabel"]
        metadata["classified_as"] = metadata["broader"][0]
        metadata["matches"] = ["http://www.wikidata.org/entity/Q6581097"]
        entities[male] = metadata
        
        female = "http://vocab.getty.edu/aat/300189557"
        getty_data = query_getty(uri=female)    
        metadata["prefLabel"] = metadata["getty:prefLabel"]
        metadata["classified_as"] = metadata["broader"][0]
        metadata["matches"] = ["http://www.wikidata.org/entity/Q6581072"]
        entities[female] = metadata
    
    #reprocess prefLabels for places after all place hierarchies have been labeled. Turn place names into AACR2 compatible strings    
    if table == 'places':
        for uri, metadata in entities.items():
            name = metadata["geo:name"]
            
            #countries
            if "A.PCL" in metadata["geo:fcode"]:
                metadata["prefLabel"] = name
            elif metadata["geo:fcode"] == "A.ADM1":
                metadata["prefLabel"] = name
            else:
                #some places, like large regions, oceans, etc. will not have a parent country
                if "geo:parentCountry" in metadata:
                    #evaluate U.S. or Canada to extract the state
                    if  metadata["geo:parentCountry"] == "https://sws.geonames.org/6252001/" or metadata["geo:parentCountry"] == "https://sws.geonames.org/6251999/":
                        if "geo:ADM1" in metadata:
                            parentURI = metadata["geo:ADM1"]
                            parentMetadata = entities[parentURI]
                            abbr = abbreviate_adm1(name=parentMetadata["geo:name"])
                            
                            metadata["prefLabel"] = f"{name} ({abbr})"   
                        else:
                            parentMetadata = entities[metadata["geo:parentCountry"]]
                            countryName = parentMetadata["geo:name"]
                            
                            metadata["prefLabel"] = f"{name} ({countryName})"                 
                    else:
                        parentMetadata = entities[metadata["geo:parentCountry"]]
                        countryName = parentMetadata["geo:name"]
                        
                        metadata["prefLabel"] = f"{name} ({countryName})"
                else:
                    metadata["prefLabel"] = name
    
#this will perform web service query actions on the URI, dependent upon the table
def process_concept(table, uri, prefLabel):
    global entities
    global place_type_uris
    
    metadata = {}
    
    if 'wikidata.org' in uri:
        namespace = 'wikidata'
    elif 'geonames.org' in uri:
        namespace = 'geonames'  
    elif 'id.loc.gov/authorities/names/' in uri:
        namespace = 'lcnaf'
    elif 'id.loc.gov/authorities/subjects/' in uri or "id.loc.gov/authorities/childrensSubjects/" in uri:
        namespace = 'lcsh'
    elif 'id.loc.gov/authorities/genreForms/' in uri:
        namespace = 'lcgft'
    elif 'id.loc.gov/vocabulary/relators/' in uri:
        namespace = 'relators'
    elif 'vocab.getty.edu/aat/' in uri:
        namespace = 'aat'
     
    if namespace == 'geonames':
        geonames_data = query_geonames(uri)
        metadata.update(geonames_data)
        metadata["prefLabel"] = geonames_data["geo:name"]
        
        #read place_types dictionary to insert place type
        for row in place_types:
            fcode = row["Wikipedia Code"]
            
            if metadata["geo:fcode"] == fcode:
                place_type_uri = row["AAT ID"] if len(row["AAT ID"]) > 0 else "https://www.geonames.org/ontology#" + row["Wikipedia Code"]
                metadata["classified_as"] = place_type_uri
                if place_type_uri not in place_type_uris:
                    place_type_uris.append(place_type_uri)
                        
    elif namespace == 'lcnaf':
        lc_data = query_lc(uri)
        metadata["prefLabel"] = lc_data["lc:prefLabel"]
        metadata.update(lc_data)
    elif namespace == 'relators':
        lc_data = query_lc(uri)
        metadata["prefLabel"] = lc_data["lc:prefLabel"]
        #AAT URI for 'role'
        metadata["classified_as"] = "http://vocab.getty.edu/aat/300435108"
        metadata.update(lc_data)
    elif namespace == 'lcsh' or namespace == 'lcgft':
        lc_data = query_lc(uri)
        metadata["prefLabel"] = lc_data["lc:prefLabel"]
        #add "subject headings" type
        metadata["classified_as"] = "http://vocab.getty.edu/aat/300265269"
        metadata.update(lc_data)
    elif namespace == 'aat':
        getty_data = query_getty(uri)    
        
        #sometimes there is no prefLabel in the Getty thesauri based on modeling errors
        if "getty:prefLabel" in getty_data:
            metadata["prefLabel"] = getty_data["getty:prefLabel"]
        else:
            metadata["prefLabel"] = prefLabel
            
        #add P2_has_type
        if table == 'genres':
            #add "type of work" into genres
            metadata["classified_as"] = "http://vocab.getty.edu/aat/300435443"
        elif table == 'subjects':
            #add "subject headings" type
            metadata["classified_as"] = "http://vocab.getty.edu/aat/300265269"
            
        metadata.update(getty_data)
    elif namespace == 'wikidata':
        metadata["prefLabel"] = prefLabel
        
    #always do a Wikidata reverse lookup for supplemental metadata
    wd_metadata = query_wikidata(uri)
    metadata.update(wd_metadata)
        
    entities[uri] = metadata
    time.sleep(1)
    
    #if there is a broader concept URI in the concept, then iterate through parents if they are not in entities already
    if "broader" in metadata:
        #broader is an array to accommodate multiple skos:broader for subject terms
        for broader in metadata["broader"]:
            if broader not in entities:
                print("Querying broader concept of", uri, ":", broader)
                process_concept(table, broader, prefLabel=None)    
                
    #if "matches" in metadata:
    #    for matching_uri in metadata["matches"]:
    #        if "vocab.getty.edu/aat" in matching_uri:
    #            process_concept(table, matching_uri, prefLabel=None)
    
#-----------------------------------------------------
#conditional to abbreviate U.S. or Austrian state or Canadian province
#-----------------------------------------------------
def abbreviate_adm1(name):
    match name:
        case "Alabama":
            abbr = "Ala."
        case "Alaska":
            abbr = "Alaska"
        case "Arizona":
            abbr = "Ariz."
        case "Arkansas":
            abbr = "Ark."
        case "California":
            abbr = "Calif."
        case "Colorado":
            abbr = "Colo."
        case "Connecticut":
            abbr = "Conn."
        case "Delaware":
            abbr = "Del."
        case "Washington, D.C.":
            abbr = "D.C."
        case "Florida":
            abbr = "Fla."
        case "Georgia":
            abbr = "Ga."
        case "Hawaii":
            abbr = "Hawaii"
        case "Idaho":
            abbr = "Idaho"
        case "Illinois":
            abbr = "Ill."
        case "Indiana":
            abbr = "Ind."
        case "Iowa":
            abbr = "Iowa"
        case "Kansas":
            abbr = "Kans."
        case "Kentucky":
            abbr = "Ky."
        case "Louisiana":
            abbr = "La."
        case "Maine":
            abbr = "Maine"
        case "Maryland":
            abbr = "Md."
        case "Massachusetts":
            abbr = "Mass."
        case "Michigan":
            abbr = "Mich."
        case "Minnesota":
            abbr = "Minn."
        case "Mississippi":
            abbr = "Miss."
        case "Missouri":
            abbr = "Mo."
        case "Montana":
            abbr = "Mont."
        case "Nebraska":
            abbr = "Nebr."
        case "Nevada":
            abbr = "Nev."
        case "New Hampshire":
            abbr = "N.H."
        case "New Jersey":
            abbr = "N.J."
        case "New Mexico":
            abbr = "N.M."
        case "New York":
            abbr = "N.Y."
        case "North Carolina":
            abbr = "N.C."
        case "North Dakota":
            abbr = "N.D."
        case "Ohio":
            abbr = "Ohio"
        case "Oklahoma":
            abbr = "Okla."
        case "Oregon":
            abbr = "Oreg."
        case "Pennsylvania":
            abbr = "Pa."
        case "Rhode Island":
            abbr = "R.I."
        case "South Carolina":
            abbr = "S.C."
        case "South Dakota":
            abbr = "S.D"
        case "Tennessee":
            abbr = "Tenn."
        case "Texas":
            abbr = "Tex."
        case "Utah":
            abbr = "Utah"
        case "Vermont":
            abbr = "Vt."
        case "Virginia":
            abbr = "Va."
        case "Washington":
            abbr = "Wash."
        case "West Virginia":
            abbr = "W.Va."
        case "Wisconsin":
            abbr = "Wis."
        case "Wyoming":
            abbr = "Wyo."
        case "American Samoa":
            abbr = "A.S."
        case "Guam":
            abbr = "Guam"
        case "Northern Mariana Islands":
            abbr = "M.P."
        case "Puerto Rico":
            abbr = "P.R."
        case "U.S. Virgin Islands":
            abbr = "V.I."
        case "Alberta":
            abbr = "Alta."
        case "British Columbia":
            abbr = "B.C."
        case "Manitoba":
            abbr = "Man."
        case "New Brunswick":
            abbr = "N.B."
        case "Newfoundland and Labrador":
            abbr = "Nfld."
        case "Northwest Territories":
            abbr = "N.W.T."
        case "Nova Scotia":
            abbr = "N.S."
        case "Nunavut":
            abbr = "NU"
        case "Ontario":
            abbr = "Ont."
        case "Prince Edward Island":
            abbr = "P.E.I."
        case "Quebec":
            abbr = "Que."
        case "Saskatchewan":
            abbr = "Sask."
        case "Yukon":
            abbr = "Y.T."
        case "Australian Capital Territory":
            abbr = "A.C.T."
        case "Jervis Bay Territory":
            abbr = "J.B.T."
        case "New South Wales":
            abbr = "N.S.W."
        case "Northern Territory":
            abbr = "N.T."
        case "Queensland":
            abbr = "Qld."
        case "South Australia":
            abbr = "S.A."
        case "Tasmania":
            abbr = "Tas."
        case "Victoria":
            abbr = "Vic."
        case "Western Australia":
            abbr = "W.A."
        case _:
            abbr = "ERROR"
        
    return abbr        

#-----------------------------------------------------
#add geographic feature types into entities dictionary
#-----------------------------------------------------
def generate_feature_types(place_types):    
    for row in place_types:
        metadata = {}
        matches = []
        
        uri = row["AAT ID"] if len(row["AAT ID"]) > 0 else "https://www.geonames.org/ontology#" + row["Wikipedia Code"]
        
        #only create entity metadata if the place type URI has appeared in the list of places
        if uri in place_type_uris:        
            if len(row["AAT ID"]) > 0:
                metadata["prefLabel"] = row["AAT label"].strip()
                matches.append("https://www.geonames.org/ontology#" + row["Wikipedia Code"])
            else:
                metadata["prefLabel"] = row["Geonames Label"].strip()
                
            if len(row["description"]) > 0:
                metadata["description"] = row["description"].strip()
            
            metadata["type"] = "crm:E55_Type" 
            
            #AAT: place types
            metadata["classified_as"] = "http://vocab.getty.edu/aat/300435109"
            
            #matching terms
            if len(row["Wikidata URI"]) > 0:
                matches.append(row["Wikidata URI"])
                
            if len(matches) > 0:
                metadata["matches"] = matches
            
            if uri not in entities:
                entities[uri] = metadata
    

def query_getty(uri):
    print("Querying", uri, "in Getty vocabularies")
    
    metadata = {}
    broaderConcepts = []
    
    g = Graph()
    getty = Namespace("http://vocab.getty.edu/ontology#")
    xl = Namespace("http://www.w3.org/2008/05/skos-xl#")
    
    url = uri + ".rdf"
    g.parse(url)
    entity = URIRef(uri)
    
    metadata["type"] = "crm:E55_Type" 
    
    for s, p, o in g.triples((entity, SKOS.prefLabel, None)):
        #include US locale for English to distinguish between potential us-gb variations
        if o.language == 'en' or o.language == 'en-us':
            metadata["getty:prefLabel"] = str(o)
    
    for s, p, o in g.triples((entity, SKOS.broader, None)):
        broader = str(o)
        broaderConcepts.append(broader)
        
    if len(broaderConcepts) > 0:
        metadata["broader"] = broaderConcepts
    
    #disable descriptions to save space for now    
    #desc = query_getty_sparql(uri)
    #if desc is not None:
    #    metadata["description"] = desc
    
    return metadata

def query_getty_sparql(uri):
    sparql_query = """
    SELECT * WHERE {
    SERVICE <https://vocab.getty.edu/sparql> {
      <URI> skos:note ?note .
      ?note a gvp:ScopeNote ;
              dcterms:language <https://vocab.getty.edu/aat/300388277> ;
              rdf:value ?desc                                       
    }}
    """
    
    g = Graph()
    gvp = Namespace('http://vocab.getty.edu/ontology#')
    
    g.bind("rdf", RDF)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.bind("gvp", gvp)
    
    results = g.query(sparql_query.replace("URI", uri))
    
    for row in results:
        if row.desc:
            print(row.desc)
            return row.desc

def query_lc(uri):
    print("Querying", uri, "in LC")
    
    metadata = {}
    broaderConcepts = []
    
    g = Graph()
    mads = Namespace('http://www.loc.gov/mads/rdf/v1#')
    
    url = uri + ".rdf"
    g.parse(url)
    entity = URIRef(uri)

    if ((entity, RDF.type, mads.PersonalName ) in g) == True:
        metadata["type"] = "crm:E21_Person"
    elif ((entity, RDF.type, mads.Geographic ) in g) == True:
        metadata["type"] = "crm:E53_Place"
    elif ((entity, RDF.type, mads.HierarchicalGeographic ) in g) == True:
        metadata["type"] = "crm:E53_Place" 
    elif ((entity, RDF.type, mads.Topic ) in g) == True:
        metadata["type"] = "crm:E55_Type" 
    elif ((entity, RDF.type, mads.Title ) in g) == True:
        metadata["type"] = "crm:E55_Type" 
    elif ((entity, RDF.type, mads.ComplexSubject ) in g) == True:
        metadata["type"] = "crm:E55_Type" 
    elif ((entity, RDF.type, mads.GenreForm ) in g) == True:
        metadata["type"] = "crm:E55_Type" 
        metadata["classified_as"] = "http://vocab.getty.edu/aat/300435443"
    elif ((entity, RDF.type, mads.CorporateName ) in g) == True:
        metadata["type"] = "crm:E74_Group"
    elif ((entity, RDF.type, mads.FamilyName ) in g) == True:
        metadata["type"] = "crm:E74_Group"
    else:
        metadata["type"] = "crm:E55_Type"
    
    metadata["lc:prefLabel"] = str(g.value(entity, mads.authoritativeLabel))
    
    #include broader concepts
    for s, p, o in g.triples((None, mads.hasBroaderAuthority, None)):
        broader = str(o)
        #ensure the broader concept is a URI to avoid blank nodes for madsrdf:ComplexSubject
        if "http://id.loc.gov/" in broader:
            broaderConcepts.append(broader)
        
    if len(broaderConcepts) > 0:
        metadata["broader"] = broaderConcepts
        
    return metadata 

#load and parse RDF/XML from Geonames
def query_geonames(uri):
    print("Querying", uri, "in Geonames")
    
    metadata = {}
    
    g = Graph()
    gn = Namespace('http://www.geonames.org/ontology#')
    geo = Namespace('http://www.w3.org/2003/01/geo/wgs84_pos#')
    
    g.bind("rdf", RDF)
    g.bind('gn', gn)
    g.bind('geo', geo)
    
    url = uri + "about.rdf"
    entity = g.parse(url)
    
    #evaluate triples
    for s, p, o in entity:
        if p == gn.name:
            metadata["geo:name"] = str(o)
        if p == geo.lat:
            metadata["geo:lat"] = str(o)
        if p == geo.long:
            metadata["geo:long"] = str(o)
        if p == gn.parentCountry:
            metadata["geo:parentCountry"] = str(o)
        if p == gn.parentADM1:
            metadata["geo:ADM1"] = str(o)
        if p == gn.parentADM2:
            metadata["geo:ADM2"] = str(o)
        if p == gn.parentADM3:
            metadata["geo:ADM3"] = str(o)
        if p == gn.parentADM4:
            metadata["geo:ADM4"] = str(o)
        if p == gn.featureClass:
            metadata["geo:fcl"] = str(o).split("#")[-1]    
        if p == gn.featureCode:
            metadata["geo:fcode"] = featureClass = str(o).split("#")[-1] 
    
    #determine the immediate parent
    if "geo:ADM4" in metadata:
        metadata["broader"] = [metadata["geo:ADM4"]]
    elif "geo:ADM3" in metadata:
        metadata["broader"] = [metadata["geo:ADM3"]]
    elif "geo:ADM2" in metadata:
        metadata["broader"] = [metadata["geo:ADM2"]]
    elif "geo:ADM1" in metadata:
        metadata["broader"] = [metadata["geo:ADM1"]]
    elif "geo:parentCountry" in metadata:
        metadata["broader"] = [metadata["geo:parentCountry"]]
    
    #all RDF type    
    metadata["type"] = "crm:E53_Place"
        
    #no else statement, parentCountry is top concept    
    
    return metadata

#Query Wikidata SPARQL endpoint to extract matching URIs in other schemes and supplemental metadata  
def query_wikidata(uri):
    #evaluate the namespace of the URI to determine which SPARQL query to submit to Wikidata
    if 'wikidata.org' in uri:
        id = uri
        namespace = 'wikidata'
    elif 'geonames.org' in uri:
        id = uri.split("/")[-2]
        namespace = 'geonames'  
    else:
        id = uri.split("/")[-1]
        if 'id.loc.gov/authorities/names/' in uri:
            namespace = 'lcnaf'
        elif 'id.loc.gov/authorities/subjects/' in uri or "id.loc.gov/authorities/childrensSubjects/" in uri:
            namespace = 'lcsh'
        elif 'id.loc.gov/authorities/genreForms/' in uri:
            namespace = 'lcgft'
        elif 'id.loc.gov/vocabulary/relators/' in uri:
            id = f"relators/{id}"
            namespace = 'relators'
        elif 'vocab.getty.edu/aat/' in uri:
            namespace = 'aat'
        
    print("Querying", id, "in Wikidata")   
    
    metadata = {}
    matches = []
    
    if namespace == 'aat':        
        sparql_query = """
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT * WHERE {
        SERVICE <https://qlever.dev/api/wikidata> {
          ?entity wdt:P1014 "ID".
          OPTIONAL {?entity wdt:P4953 ?lcgft}
          OPTIONAL {?entity wdt:P5160 ?lctgm}
          OPTIONAL {?entity wdt:P4801 ?relators}
        }}
        """
    elif namespace == 'lcgft':        
        sparql_query = """
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT * WHERE {
        SERVICE <https://qlever.dev/api/wikidata> {
          ?entity wdt:P4953 "ID".
          OPTIONAL {?entity wdt:P1014 ?aat}
          OPTIONAL {?entity wdt:P5160 ?lctgm}
          OPTIONAL {?entity wdt:P244 ?lcsh}
        }}
        """
    elif namespace == 'relators':        
        sparql_query = """
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT * WHERE {
        SERVICE <https://qlever.dev/api/wikidata> {
          ?entity wdt:P4801 "ID".
          OPTIONAL {?entity wdt:P1014 ?aat}
          OPTIONAL {?entity wdt:P5160 ?lctgm}
          OPTIONAL {?entity wdt:P244 ?lcsh}
        }}
        """
    elif namespace == 'lcnaf' or namespace == 'lcsh':
        sparql_query = """
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT * WHERE {
        SERVICE <https://qlever.dev/api/wikidata> {
          ?entity wdt:P244 "ID".
          OPTIONAL {?entity wdt:P214 ?viaf}
          OPTIONAL {?entity wdt:P245 ?ulan}
          OPTIONAL {?entity wdt:P10832 ?wcat}
          OPTIONAL {?entity wdt:P648 ?openlibrary}
          OPTIONAL {?entity wdt:P3430 ?snac}
          OPTIONAL {?entity wdt:P1566 ?geonames}
          OPTIONAL {?entity wdt:P1667 ?tgn}
          OPTIONAL {?entity wdt:P2163 ?fast}
          OPTIONAL {?entity wdt:P1014 ?aat}
          OPTIONAL {?entity wdt:P21 ?sexorgender}
          OPTIONAL {?entity wdt:P569 ?birth}
          OPTIONAL {?entity wdt:P570 ?death}
          OPTIONAL {?entity wdt:P571 ?inception}
          OPTIONAL {?entity wdt:P625 ?coords}
        }}
        """ 
    elif namespace == 'geonames':
        sparql_query = """
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT * WHERE {
        SERVICE <https://qlever.dev/api/wikidata> {
          ?entity wdt:P1566 "ID".
            OPTIONAL {?entity wdt:P1667 ?tgn}
            OPTIONAL {?entity wdt:P244 ?lcnaf}
            OPTIONAL {?entity wdt:P2163 ?fast}
            OPTIONAL {?entity wdt:P10832 ?wcat}
            OPTIONAL {?entity wdt:P648 ?openlibrary}
        }}
        """  
    elif namespace == 'wikidata':
        sparql_query = """
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT * WHERE {
        SERVICE <https://qlever.dev/api/wikidata> {
          BIND (<ID> as ?entity)
          OPTIONAL {?entity wdt:P214 ?viaf}
          OPTIONAL {?entity wdt:P245 ?ulan}
          OPTIONAL {?entity wdt:P10832 ?wcat}
          OPTIONAL {?entity wdt:P648 ?openlibrary}
          OPTIONAL {?entity wdt:P3430 ?snac}
          OPTIONAL {?entity wdt:P1566 ?geonames}
          OPTIONAL {?entity wdt:P1667 ?tgn}
          OPTIONAL {?entity wdt:P2163 ?fast}
          OPTIONAL {?entity wdt:P21 ?sexorgender}
          OPTIONAL {?entity wdt:P569 ?birth}
          OPTIONAL {?entity wdt:P570 ?death}
          OPTIONAL {?entity wdt:P571 ?inception}
        }}
        """ 
     
    try:
        g = Graph()
        wdt = Namespace('http://www.wikidata.org/prop/direct/')
        g.bind('wdt', wdt)
        results = g.query(sparql_query.replace("ID", id))
    except urllib.error.HTTPError as e:
        print(e.reason)
    else:
        if namespace == "aat":
            for row in results:
                if str(row.entity) not in matches:                    
                    matches.append(str(row.entity))
                if row.lcgft:
                    exactMatch = "http://id.loc.gov/authorities/genreForms/" + row.lcgft
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.lctgm:
                    exactMatch = "http://id.loc.gov/vocabulary/graphicMaterials/" + row.lctgm
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.relators:
                    exactMatch = "http://id.loc.gov/vocabulary/" + row.relators
                    if exactMatch not in matches:
                        matches.append(exactMatch)
        if namespace == "lcgft":
            for row in results:
                if str(row.entity) not in matches:                    
                    matches.append(str(row.entity))
                if row.aat:
                    exactMatch = "http://vocab.getty.edu/aat/" + row.aat
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.lctgm:
                    exactMatch = "http://id.loc.gov/vocabulary/graphicMaterials/" + row.lctgm
                    if exactMatch not in matches:
                        matches.append(exactMatch)
        if namespace == "relators":
            for row in results:
                if str(row.entity) not in matches:                    
                    matches.append(str(row.entity))
                if row.aat:
                    exactMatch = "http://vocab.getty.edu/aat/" + row.aat
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.lctgm:
                    exactMatch = "http://id.loc.gov/vocabulary/graphicMaterials/" + row.lctgm
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.lcsh:
                    exactMatch = "http://id.loc.gov/authorities/subjects/" + row.lcsh
                    if exactMatch not in matches:
                        matches.append(exactMatch)
        elif namespace == 'lcnaf' or namespace == 'lcsh' or namespace == 'wikidata':
            for row in results:                
                if str(row.entity) not in matches:
                    #do not insert the same URI into the matching array for a Wikidata entity
                    if 'namespace' != 'wikidata':
                        matches.append(str(row.entity))
                if row.viaf:
                    exactMatch = "http://viaf.org/viaf/" + row.viaf
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.ulan:
                    exactMatch = "http://vocab.getty.edu/ulan/" + row.ulan
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.wcat:
                    exactMatch = "https://id.oclc.org/worldcat/entity/" + row.wcat
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.openlibrary:
                    exactMatch = "https://openlibrary.org/works/" + row.openlibrary
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.snac:
                    exactMatch = "https://snaccooperative.org/ark:/99166/" + row.snac
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.tgn:
                    exactMatch = "http://vocab.getty.edu/tgn/" + row.tgn
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.geonames:
                    exactMatch = "https://sws.geonames.org/" + row.geonames + "/"
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.fast:
                    exactMatch = "http://id.worldcat.org/fast/" + row.fast
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.aat:
                    exactMatch = "http://vocab.getty.edu/aat/" + row.aat
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                
                #coordinates for subjects, distinct from places from LCNAF
                if namespace == 'lcsh':                    
                    if row.coords:
                        metadata["wd:coords"] = str(row.coords)
                
                if namespace == 'wikidata':        
                    if str(row.type) == "http://www.wikidata.org/entity/Q5":
                        metadata["type"] = "crm:E21_Person"
                    else:
                        metadata["type"] = "crm:E74_Group"
                                                
                #other metadata
                if row.birth:
                    if "wd:birth" not in metadata:
                        metadata["wd:birth"] = str(row.birth) 
                if row.death:
                    if "wd:death" not in metadata:
                        metadata["wd:death"] = str(row.death) 
                if row.inception:
                    if "wd:inception" not in metadata:
                        metadata["wd:inception"] = str(row.inception) 
                if row.sexorgender:
                    if "wd:sexorgender" not in metadata:
                        metadata["wd:sexorgender"] = str(row.sexorgender)   
                        
        elif namespace == 'geonames':
            for row in results:
                if str(row.entity) not in matches:
                    matches.append(str(row.entity))
                if row.tgn:
                    exactMatch = "http://vocab.getty.edu/tgn/" + row.tgn
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.lcnaf:
                    exactMatch = "http://id.loc.gov/authorities/names/" + row.lcnaf
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.fast:
                    exactMatch = "http://id.worldcat.org/fast/" + row.fast
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.wcat:
                    exactMatch = "https://id.oclc.org/worldcat/entity/" + row.wcat
                    if exactMatch not in matches:
                        matches.append(exactMatch)
                if row.openlibrary:
                    exactMatch = "https://openlibrary.org/works/" + row.openlibrary
                    if exactMatch not in matches:
                        matches.append(exactMatch)
    

    metadata["matches"] = matches             
    return metadata

def generate_rdf(table, entities):
    print("Generating RDF graph")
    
    g = Graph()
    crm = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
    la = Namespace('https://linked.art/ns/terms/')
    opengis = Namespace('http://www.opengis.net/ont/geosparql#')
    
    g.bind('crm', crm)
    g.bind('la', la)
    g.bind("skos", SKOS)
    g.bind("xsd", XSD)
    g.bind("rdf", RDF)
    g.bind("geo", opengis)
    
    for uri, metadata in entities.items():
        #print(metadata)
        
        subject = URIRef(uri)
        if "type" in metadata:
            rdf_class = metadata["type"]
        else:
            rdf_class= "crm:E55_Type"
            
        type = URIRef(rdf_class.replace("crm:", "http://www.cidoc-crm.org/cidoc-crm/"))
        
        g.add((subject, RDF.type, type))
        g.add((subject, RDFS.label, Literal(metadata["prefLabel"], lang="en")))
        
        #general classification for AAT when creating genreform RDF
        if "classified_as" in metadata:
            #object/work type 
            g.add((subject, crm.P2_has_type, URIRef(metadata["classified_as"])))
            
        #CIDOC CRM label
        name = BNode()
        
        g.add((subject, crm.P1_is_identified_by, name))
        g.add((name, RDF.type, crm.E33_E41_Linguistic_Appellation))
        g.add((name, crm.P2_has_type, URIRef("http://vocab.getty.edu/aat/300404670")))
        g.add((name, crm.P190_has_symbolic_content, Literal(metadata["prefLabel"])))
        
        if "wd:coords" in metadata:
            g.add((subject, crm.P168_place_is_defined_by, Literal(metadata["wd:coords"], datatype=opengis.wktLiteral)))
        
        #-------------------------
        #PERSONS AND ORGANIZATIONS
        #-------------------------
        
        if "wd:birth" in metadata:
            date = metadata["wd:birth"].split("T")[0]
            if date[-5:] == '01-01':
                fromDate = date + "T00:00:00Z"
                toDate = date[:-6] + "-12-31T23:59:59Z"
            else:
                fromDate = date + "T00:00:00Z"
                toDate = date + "T23:59:59Z"  
                               
            birth_node = BNode()
            birth_timespan = BNode()
            
            g.add((subject, crm.P98i_was_born, birth_node))
            g.add((birth_node, RDF.type, crm.E67_Birth))
            g.add((birth_node, URIRef("http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span"), birth_timespan))
            g.add((birth_timespan, RDF.type, URIRef("http://www.cidoc-crm.org/cidoc-crm/E52_Time-Span")))
            g.add((birth_timespan, crm.P82a_begin_of_the_begin, Literal(fromDate, datatype=XSD.dateTime)))
            g.add((birth_timespan, crm.P82b_end_of_the_end, Literal(toDate, datatype=XSD.dateTime)))
             
        if "wd:death" in metadata:       
            date = metadata["wd:death"].split("T")[0]
            if date[-5:] == '01-01':
                fromDate = date + "T00:00:00Z"
                toDate = date[:-6] + "-12-31T23:59:59Z"
            else:
                fromDate = date + "T00:00:00Z"
                toDate = date + "T23:59:59Z"  
                
            if range is not None:                    
                death_node = BNode()
                death_timespan = BNode()
                
                g.add((subject, crm.P100i_died_in, death_node))
                g.add((death_node, RDF.type, crm.E69_Death))
                g.add((death_node, URIRef("http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span"), death_timespan))
                g.add((death_timespan, RDF.type, URIRef("http://www.cidoc-crm.org/cidoc-crm/E52_Time-Span")))
                g.add((death_timespan, crm.P82a_begin_of_the_begin, Literal(fromDate, datatype=XSD.dateTime)))
                g.add((death_timespan, crm.P82b_end_of_the_end, Literal(toDate, datatype=XSD.dateTime)))
            
        
        if "wd:inception" in metadata:
            date = metadata["wd:inception"].split("T")[0]
            if date[-5:] == '01-01':
                fromDate = date + "T00:00:00Z"
                toDate = date[:-6] + "-12-31T23:59:59Z"
            else:
                fromDate = date + "T00:00:00Z"
                toDate = date + "T23:59:59Z"  
                
            if range is not None:                    
                inception_node = BNode()
                inception_timespan = BNode()
                
                g.add((subject, crm.P95i_was_formed_by, inception_node))
                g.add((inception_node, RDF.type, crm.E66_Formation))
                g.add((inception_node, URIRef("http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span"), inception_timespan))
                g.add((inception_timespan, RDF.type, URIRef("http://www.cidoc-crm.org/cidoc-crm/E52_Time-Span")))
                g.add((inception_timespan, crm.P82a_begin_of_the_begin, Literal(fromDate, datatype=XSD.dateTime)))
                g.add((inception_timespan, crm.P82b_end_of_the_end, Literal(toDate, datatype=XSD.dateTime)))
            
        if "wd:sexorgender" in metadata:
            #same as classified_as
            #replace Wikidata with AAT
            if metadata["wd:sexorgender"] == "http://www.wikidata.org/entity/Q6581097":
                sexorgender = "http://vocab.getty.edu/aat/300189559"
            elif metadata["wd:sexorgender"] == "http://www.wikidata.org/entity/Q6581072":
                sexorgender = "http://vocab.getty.edu/aat/300189557"
            g.add((subject, crm.P2_has_type, URIRef(sexorgender)))
        
        #---------------------------
        #PLACES
        #---------------------------
        
        if "geo:lat" in metadata and "geo:long" in metadata:
            if metadata["geo:fcl"] == "P":
            #Only map the lat and long for populated places
                lat = metadata["geo:lat"]
                long = metadata["geo:long"]
                
                g.add((subject, crm.P168_place_is_defined_by, Literal(f"POINT({long} {lat})", datatype=opengis.wktLiteral)))
        
        #---------------------------
        #MATCHING AND BROADER URIS
        #---------------------------
        
        if "matches" in metadata:
            for equivalent in metadata["matches"]:
                object = URIRef(equivalent)
                g.add((subject, la.equivalent, object))
        
        if "broader" in metadata:
            for broader in metadata["broader"]:
                object = URIRef(broader)
                
                #geographic entities use a different property than general types
                if "geonames" in uri:
                    g.add((subject, crm.P89_falls_within, object))
                else:
                    g.add((subject, SKOS.broader, object))
    
    filename = f"rdf/{table}.ttl"
    g.serialize(format="turtle", destination=filename)
    #print(g.serialize(format="turtle"))
        

def load_entities_csv(table):
    global wd_metadata
    
    filename = table + "-wikidata.csv"
    
    if os.path.exists(filename):
        with open(filename, 'r', newline='', encoding="utf-8") as file:
            print(f"Extracting data from {filename}")
            reader = csv.DictReader(file)
            for row in reader:
                metadata = {}
                
                uri = row["URI"]
                
                if len(row["Matches"]) > 0:
                    metadata["matches"] = row["Matches"].split("|")
                if len(row["Birth"]) > 0:
                    metadata["wd:birth"] = row["Birth"]
                if len(row["Death"]) > 0:
                    metadata["wd:death"] = row["Death"]
                if len(row["Inception"]) > 0:
                    metadata["wd:inception"] = row["Inception"]
                if len(row["SexOrGender"]) > 0:
                    metadata["wd:sexorgender"] = row["SexOrGender"]
                if len(row["Type"]) > 0:
                    metadata["type"] = row["Type"]
                
                wd_metadata[uri] = metadata

def main():
    global place_types
    
    if not os.path.isdir("rdf"):
        os.makedirs("rdf")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--table", help="Table name to extract entities from: 'cpf', 'genres', 'relators', 'places', 'subjects'")
    args = parser.parse_args()
    
    #validate arguments
    if args.table:
        table = args.table
        
        #load place types from CSV when processing the places table
        if table == 'places':
            with open('geonames_feature_codes.csv', 'r') as file:
                reader = csv.DictReader(file)
                place_types = list(reader)
        
        extract_table(table)
    else:
        print("Table must be set")
        


if __name__=="__main__":
    main()