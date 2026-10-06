"""
Author: Ethan Gruber
Date: October 2026
Function: Read authority fields from list of MARC records to reconcile to URIs
"""

import sys, csv, re, os, urllib, uuid, time, yaml, argparse
import xml.etree.ElementTree as ET
from itertools import count

#local functions
from apilookups import get_marc_country, lookup_loc, lookup_getty, lookup_geonames

PROCESS = ['names', 'subjects', 'genres', 'relators', 'places', 'materials', 'techniques']

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

#complex dicts for looking up in LOD entity systems
cpf = {}
genres = {}
materials = {}
places = {}
relators = {}
subjects = {}
techniques = {}
marcCountries = {}

#simpler lists or dicts for writing to text/CSV for further evaluation; no external lookups
provenance = []

#evaluate the MODS file to determin whether it is a combined modsCollection or a standalone record
def parse_mods(file=None, dir=None):
   
    tree = ET.parse(file)
    root = tree.getroot()
    
    namespaces = {'mods': 'http://www.loc.gov/mods/v3'}
    
    if root.tag == "{http://www.loc.gov/mods/v3}mods":
        extract_entities(root)
    else:
        for record in root.findall('.//mods:mods', namespaces):
            extract_entities(record)
    
#extract entities from mods:mods    
def extract_entities(record):
    #global name_concordance
    global cpf
    global subjects
    global genres
    global places
    global relators
    global materials
    global techniques
    global marcCountries
    
    global provenance
    
    namespaces = {'mods': 'http://www.loc.gov/mods/v3'}
    
    #only process entity-record relationship for names
    if 'names' in PROCESS:        
        #concatenate nameParts with a single whitespace. Be sure the XSLT stylesheet for embedding URIs in MODS matches the lookup key 
        for name in record.findall('mods:name[@type]', namespaces):
            nameParts = []
            for namePart in name.findall('mods:namePart', namespaces):
                nameParts.append(namePart.text)
            
            term = " ".join(nameParts)            
            
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, term))
            if id not in cpf:                
                tuple = lookup_loc(term=term, scheme='lcnaf', rdftype='rdftype:Name', subdivision=None)        
                cpf[id] = tuple            
                time.sleep(1)
                
        #not typical, but names might be in relatedItem[@type = 'original']
        for name in record.findall("mods:relatedItem[@type = 'original']/mods:name[@type]", namespaces):
            nameParts = []
            for namePart in name.findall('mods:namePart', namespaces):
                nameParts.append(namePart.text)
                
            term = " ".join(nameParts)
                
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, term))
            if id not in cpf:                
                tuple = lookup_loc(term=term, scheme='lcnaf', rdftype='rdftype:Name', subdivision=None)        
                cpf[id] = tuple            
                time.sleep(1)
        
    if 'subjects' in PROCESS:
        for subject in record.findall('mods:subject', namespaces):
            if subject.get('authority') == 'lcsh':                
                position = 1
                
                first_component = subject[0].tag.split('}')[-1]
                for part in subject:
                    code = part.tag.split('}')[-1]                    
                    
                    #if the subject is a name, then concatenate nameParts with a single whitespace. Be sure the XSLT stylesheet for embedding URIs in MODS matches the lookup key
                    if code == 'name':                        
                        nameParts = []
                        for namePart in part.findall('mods:namePart', namespaces):
                            nameParts.append(namePart.text)
                        
                        term = " ".join(nameParts)
                    else:
                        term = part.text
                        
                    tuple = ()
                    
                    #generate UUID as a key, based on the code and string
                    id = str(uuid.uuid3(uuid.NAMESPACE_URL, code + ":" + term))
                    
                    if id not in subjects:                        
                        #ignore c, e: generally misused or unused
                        if position == 1:
                            tuple = lookup_loc(term=term, scheme='lcsh_lcnaf', rdftype='rdftype:Topic OR rdftype:Name OR rdftype:Geographic', subdivision="-memberOf:http://id.loc.gov/authorities/subjects/collection_GeographicSubdivisions")
                        elif position == 2 and code == 'topic' and first_component == 'geographic':
                            tuple = lookup_loc(term=term, scheme='lcsh', rdftype='rdftype:Topic', subdivision=None)
                        elif code == 'genre':
                            tuple = lookup_loc(term=term, scheme='lcsh', rdftype='rdftype:GenreForm', subdivision=None)
                        elif position > 1 and code == 'topic':
                            tuple = lookup_loc(term=term, scheme='lcsh', rdftype='rdftype:Topic', subdivision="memberOf:http://id.loc.gov/authorities/subjects/collection_Subdivisions")
                        elif code == 'temporal':
                            tuple = lookup_loc(term=term, scheme='lcsh', rdftype='rdftype:Topic', subdivision="memberOf:http://id.loc.gov/authorities/subjects/collection_Subdivisions")
                        elif code == 'geographic':
                            tuple = lookup_loc(term=term, scheme='lcnaf', rdftype='rdftype:Geographic', subdivision="-memberOf:http://id.loc.gov/authorities/subjects/collection_GeographicSubdivisions")
                
                        subjects[id] = tuple  
                        position += 1
                        #wait 1 second before issuing another HTTP request
                        time.sleep(1) 
                        
                    del term
                        
            else:
                for part in subject:
                    term = part.text
                    
                    id = str(uuid.uuid3(uuid.NAMESPACE_URL, "topic:" + term))
                    if id not in subjects:                    
                        #look up any subject that isn't @authority = 'lcsh' in LC first. If no response, then query Wikidata
                        tuple = lookup_loc(term=term, scheme='lcsh_lcnaf', rdftype='rdftype:Topic OR rdftype:Name OR rdftype:Geographic', subdivision="-memberOf:http://id.loc.gov/authorities/subjects/collection_GeographicSubdivisions")
                        
                        #if there is a label extracted from LC, then add the term to the subject dict
                        if len(tuple[1]) > 0:
                            subjects[id] = tuple
                            time.sleep(1)
                        else:
                            #Query Wikidata
                            print(f"No match for {term} in Library of Congress")
                            print(tuple)
                            
                    del term
    
    if 'relators' in PROCESS:
        for relator in record.findall('.//mods:roleTerm', namespaces):
            term = relator.text
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, term))
            
            if id not in relators:
                tuple = lookup_loc(term=term, scheme='relators', rdftype='rdftype:Role', subdivision=None)
                
                relators[id] = tuple
                time.sleep(1)
            del term
                            
    if 'genres' in PROCESS:
        for genre in record.findall('mods:genre', namespaces):
            if genre.get('authority'):
                authority = genre.get('authority')
                term = genre.text
                
                tuple = ()
                    
                #generate UUID as a key, based on the code and string
                id = str(uuid.uuid3(uuid.NAMESPACE_URL, authority + ":" + term))
                
                if id not in genres:
                    if authority == 'aat':
                        tuple = lookup_getty(term=term)
                        genres[id] = tuple
                        time.sleep(1)     
                    elif authority == 'fast':
                        print("Fast", term)
                    elif authority == 'lctgm':
                        tuple = lookup_loc(term=term, scheme='lctgm', rdftype='rdftype:Authority', subdivision=None)
                        genres[id] = tuple
                        time.sleep(1)
                    elif authority == 'lcfgt':
                        tuple = lookup_loc(term=term, scheme='lcgtf', rdftype='rdftype:GenreForm', subdivision=None)
                        genres[id] = tuple
                        time.sleep(1)
                del term
                         
    if 'places' in PROCESS:
        
        if record.find("mods:relatedItem[@type = 'original']", namespaces) is not None:
            originInfo = record.find("mods:relatedItem[@type = 'original']", namespaces)
        else:
            originInfo = record.find("mods:originInfo", namespaces)
        
        #look up the marc country code in LOC in order to use the preferred label as a search term for Geonames
        for place in originInfo.findall('mods:place/mods:placeTerm', namespaces):                
            if place.get('type') == 'code' and place.get('authority') == 'marccountry':
                marcCountry = place.text
                #only look up the MARC country code once
                if marcCountry not in marcCountries:
                    marcCountries[marcCountry] = get_marc_country(marcCountry)                    
            elif place.get('type') == 'text':
                term = place.text
            
        if "marcCountry" in locals() and "term" in locals():    
            #ignore unknown place
            if marcCountry != 'xx':
                query = term + ', ' + marcCountries[marcCountry]["prefLabel"]
                id = str(uuid.uuid3(uuid.NAMESPACE_URL, marcCountry + ":" + term))
                
                if id not in places:                        
                    tuple = lookup_geonames(query, featureClass=None) 
                    places[id] = tuple
                    time.sleep(1)
        elif "term" in locals():
            query = term
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, term))
                
            if id not in places:                        
                tuple = lookup_geonames(query, featureClass=None) 
                places[id] = tuple
                time.sleep(1)
        
        #next, look for geographic subjects
        for geo in record.findall('mods:subject/mods:hierarchicalGeographic', namespaces):
            hier = {"places": []}
            for child in geo:
                hier["places"].append({"type": child.tag.split('}')[-1], "value": child.text})
                
            #only evaluate the lowest-level concept
            last = hier["places"][-1]
            
            if len(hier["places"]) > 0:
                if len(hier["places"]) >= 2:        
                    if last["type"] == "city":
                        if hier["places"][-2]["type"] == "state" or hier["places"][-2]["type"] == "province" or hier["places"][-2]["type"] == "country":
                            term = last["value"] + ", " + hier["places"][-2]["value"]
                            featureClass = "P"
                        else: 
                            term = last["value"]
                            featureClass = "P"
                    elif last["type"] == "state" or last["type"] == "province" or last["type"] == "territory":
                        if hier["places"][-2]["type"] == "country":
                            term = last["value"] + ", " + hier["places"][-2]["value"]
                            featureClass = "A"
                        else:
                            term = last["value"]
                            featureClass = "A"
                    elif last["type"] == "county":
                        if hier["places"][-2] == "state" or hier["places"][-2] == "country":
                            term = last["value"] + ", " + hier["places"][-2]["value"]
                            featureClass = "A"
                        else:
                            term = last["value"]
                            featureClass = "A"
                    elif last["type"] == "citySection":
                        if hier["places"][-2] == "city" or hier["places"][-2] == "county" or hier["places"][-2] == "state" or hier["places"][-2] == "province":
                            term = last["value"] + ", " + hier["places"][-2]["value"]
                            featureClass = "P"
                        else:
                            term = last["value"]
                            featureClass = "P"
                    else:
                        term = last["value"]
                        featureClass = None
                elif len(hier["places"]) == 1:
                    if hier["places"][0]["type"] == "country":
                        term = hier["places"][0]["value"]
                        featureClass = "A"
                    else:
                        term = hier["places"][0]["value"]
                        featureClass = None
                        
                id = str(uuid.uuid3(uuid.NAMESPACE_URL, term)) 
                if id not in places:
                    tuple = lookup_geonames(query=term, featureClass=featureClass)
                    places[id] = tuple
                    time.sleep(1)
                del term
                    
        #look for simple subject/geographic
        for geo in record.findall('mods:subject/mods:geographic', namespaces):
            term = geo.text
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, term)) 
            if id not in places:
                tuple = lookup_geonames(query=term, featureClass=None)
                places[id] = tuple
                time.sleep(1)
            del term
                
    if 'materials' in PROCESS:
        if record.find("mods:relatedItem[@type = 'original']", namespaces) is not None:
            physDesc = record.find("mods:relatedItem[@type = 'original']/mods:physicalDescription", namespaces)
        else:
            physDesc = record.find("mods:physicalDescription", namespaces)
            
        for material in physDesc.findall("mods:form[@type = 'material']", namespaces):
            term = material.text   
            
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, term))
            if id not in materials:
                tuple = lookup_getty(term=term)
                materials[id] = tuple
                time.sleep(1) 
            del term
                
    if 'techniques' in PROCESS:
        if record.find("mods:relatedItem[@type = 'original']", namespaces) is not None:
            physDesc = record.find("mods:relatedItem[@type = 'original']/mods:physicalDescription", namespaces)
        else:
            physDesc = record.find("mods:physicalDescription", namespaces)
            
        for technique in physDesc.findall("mods:form[@type = 'technique']", namespaces):
            term = technique.text   
            
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, term))
            if id not in techniques:
                tuple = lookup_getty(term=term)
                techniques[id] = tuple
                time.sleep(1)                 
            del term
                            

def write_csv():
    global subjects
    global genres
    global relators
    global places
    global cpf
    global materials
    global techniques      
    global provenance
    
    #write a csv file for each concept type defined in the PROCESS constant
    if 'names' in PROCESS:
        #write names and LCNAF URIs to CSV
        with open('names.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Literal Value", "Preferred Label", "URI"))
            
            for key, tuple in cpf.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
            
    if 'relators' in PROCESS:
        with open('relators.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Literal Value", "Preferred Label", "URI"))
        
            for key, tuple in relators.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
    
    if 'materials' in PROCESS:
        with open('materials.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Literal Value", "Preferred Label", "URI"))
        
            for key, tuple in materials.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
    
    if 'techniques' in PROCESS:
        with open('techniques.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Literal Value", "Preferred Label", "URI"))
        
            for key, tuple in techniques.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
    
    if 'subjects' in PROCESS:
        with open('subjects.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Literal Value", "Preferred Label", "URI"))
        
            for key, tuple in subjects.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
                
    if 'genres' in PROCESS:
        with open('genres.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Literal Value", "Preferred Label", "URI"))
        
            for key, tuple in genres.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
                   
    if 'places' in PROCESS:
        with open('places.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Literal Value", "Preferred Label", "URI", "Country Name", "Admin Name", "Feature Class"))
        
            for key, tuple in places.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2], tuple[3], tuple[4], tuple[5]))
    
    print("Process completed. Writing CSV files.")

def main():
    #accept input arguments in order to determine the file or directory transformation process
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="MODS file to process")
    parser.add_argument("-d", "--dir", help="Process a directory of MODS files")
    args = parser.parse_args()
    
    if args.file and args.dir:
        sys.exit("Only one of file or dir arguments is acceptable")
    else:        
        if args.file:
            if os.path.exists(args.file):
                parse_mods(file=args.file)
            else:
                sys.exit("File not found")
        elif args.dir:
            if os.path.exists(args.dir):
                parse_mods(dir=args.dir)
            else:
                sys.exit("Directory not found")
        else:
            sys.exit("File or dir not set")
    
    
    write_csv()
    
    
if __name__=="__main__":
    main()
