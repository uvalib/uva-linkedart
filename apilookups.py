"""
Author: Ethan Gruber
Date: June 2026
Function: Functions for looking terms up in various LOD vocabulary systems, such as LOC, Getty, Geonames
"""

import requests, urllib, json, yaml
import xml.etree.ElementTree as ET
from joblib._multiprocessing_helpers import name

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

def get_marc_country(marcCountry):
    uri = "http://id.loc.gov/vocabulary/countries/" + marcCountry
    with urllib.request.urlopen(uri + ".skos.json") as url:
        data = json.loads(url.read().decode())
        
        #iterate through objects in the JSON-LD to look for the concept URI which contains the skos:prefLabel
        for object in data:
            if object["@id"] == uri:
                for label in object["http://www.w3.org/2004/02/skos/core#prefLabel"]:
                    if label["@language"] == "en":
                        prefLabel = label["@value"]
                        return {"prefLabel": prefLabel, "uri": uri}  
          
        
def lookup_loc(term, scheme, rdftype, subdivision):
    schemes = {"lcnaf": "scheme:http://id.loc.gov/authorities/names", 
               "lcsh": "scheme:http://id.loc.gov/authorities/subjects", 
               "lcgft": "scheme:http://id.loc.gov/authorities/genreForms",
               "relators": "scheme:http://id.loc.gov/vocabulary/relators", 
               "lcsh_lcnaf": "scheme:http://id.loc.gov/authorities/names OR scheme:http://id.loc.gov/authorities/subjects"}
    
    if subdivision is not None:    
        url = "http://id.loc.gov/search/?q=" + urllib.parse.quote('"' + term + '"') + "&q=" + schemes[scheme] + "&q=" + rdftype + "&q=" + urllib.parse.quote(subdivision) + "&format=atom-xml"
    else:
        url = "http://id.loc.gov/search/?q=" + urllib.parse.quote('"' + term + '"') + "&q=" + schemes[scheme] + "&q=" + rdftype + "&format=atom-xml"
    
    print("Looking up", term)
    
    headers = {"User-Agent": "EntityNormalization/UVALibrary"}
    
    response = requests.get(url, headers=headers)
    root = ET.fromstring(response.content)
    
    namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
    
    entry = root.find('.//atom:entry', namespaces)
    
    tuple = ()
    
    if entry is not None:    
        title = entry.find('atom:title', namespaces).text  
        link = entry.find('atom:link', namespaces).get('href')
            
        tuple = (term, title, link)                
    else:
        tuple = (term, '', '')
        
    return tuple

def lookup_getty(term):
    print("Querying", term)
    
    url = "https://services.getty.edu/vocab/reconcile/"
    
    headers = {"User-Agent": "EntityNormalization/UVALibrary"}
    
    response = requests.get(url + "?queries=" + '{"q0": {"query":"' + term + '", "type": "/aat", "limit": 10}}', headers=headers)
    
    data = response.json()
    
    if len(data["q0"]["result"]) > 0:
        obj = data["q0"]["result"][0]
        
        tuple = (term, obj["name"], "http://vocab.getty.edu/" + obj["id"])
    else:
        tuple = (term, '', '')
        
    return tuple
    
def lookup_geonames(query, featureClass):
    geonames_key = config["geonames_key"]
    
    print("Querying", query)
    
    if featureClass is None:
        url = "http://api.geonames.org/searchJSON?formatted=true&q=" + urllib.parse.quote(query) + "&maxRows=10&lang=en&username=" + geonames_key
    else:
        param = "name" if featureClass == "A" else "q"
        url = "http://api.geonames.org/searchJSON?formatted=true&" + param + "=" + urllib.parse.quote(query) + "&featureClass=" + featureClass + "&maxRows=10&lang=en&username=" + geonames_key
    
    headers = {"User-Agent": "EntityNormalization/UVALibrary"}
    
    response = requests.get(url, headers=headers)
    
    
    data = response.json()
    
    if 'totalResultsCount' in data:    
        if data['totalResultsCount'] > 0:
            obj = data['geonames'][0]
            
            uri = "https://sws.geonames.org/" + str(obj['geonameId']) + "/"
            
            if "countryName" in obj:
                countryName = obj["countryName"]
            else:
                countryName = ''
                
            if "adminName1" in obj:
                adminName = obj["adminName1"]
            else:
                adminName = ''
            
            tuple = (query, obj['name'], uri, countryName, adminName, obj['fcl'])
        
            return tuple
    
def test_geographic():
    xml = """
    <mods xmlns="http://www.loc.gov/mods/v3">
        <subject>
            <hierarchicalGeographic>
                <country>United States</country>
                <state>West Virginia</state>
                <city>Springfield</city>
            </hierarchicalGeographic>
        </subject>
    </mods>
    """
    
    namespaces = {'mods': 'http://www.loc.gov/mods/v3'}
    
    root = ET.fromstring(xml)
    
    for geo in root.findall('.//mods:subject/mods:hierarchicalGeographic', namespaces):
        hier = {"places": []}
        for child in geo:
            hier["places"].append({"type": child.tag.split('}')[-1], "value": child.text})
            
        #only evaluate the lowest-level concept
        last = hier["places"][-1]
        
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
        
        
        if term:            
            print(term)
        if featureClass:
            print(featureClass)
    
        tuple = lookup_geonames(query=term, featureClass=featureClass)
        
        return tuple
    
    
def main():
    print("Testing apilookups")
    
    """
    term = "west virginia"    
    tuple = lookup_geonames(query=term, featureClass="A")    
    print(tuple)
    """
    
    tuple = test_geographic()
    print(tuple)
    
    
if __name__=="__main__":
    main()