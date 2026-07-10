"""
Author: Ethan Gruber
Date: June 2026
Function: Read authority fields from list of MARC records to reconcile to URIs
"""

import csv, re, os, requests, subprocess, math, urllib, json, uuid, time, yaml
import xml.etree.ElementTree as ET
from itertools import count

#local functions
from apilookups import get_marc_country, lookup_loc, lookup_getty, lookup_geonames

PROCESS = ['genres']
SAXON_PATH = "../saxon/SaxonHE12-4J/saxon-he-12.4.jar"
ROWS = 100

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

ckeys = []
names = []
subjects = {}
genres = {}
places = {}
relators = {}
marcCountries = {}
name_concordance = []

def process_marcxml(ckey):
    global names
    global name_concordance
    global subjects
    global genres
    global places
    global relators
    global marcCountries
    
    #first get MARC XML from API
    url = "https://ils.lib.virginia.edu/uhtbin/getMarc?ckey=" + ckey + "&type=xml"    
    response = requests.get(url)
    if response.status_code == 200:
        with open('marc.xml', 'wb') as file:
            file.write(response.content)
    else:
        print('Failed to download file.')
    
    #transform into MODS with official LOC stylesheet for enhanced normalization
    cmd = 'java -jar ' + SAXON_PATH + ' -xsl:marc-to-mods/MARC21slim2MODS3-7.xsl -s:marc.xml -o:mods.xml'
    result = subprocess.call(cmd, shell=True, text=True)
   
    tree = ET.parse('mods.xml')
    root = tree.getroot()
    
    namespaces = {'mods': 'http://www.loc.gov/mods/v3'}
    
    #only process entity-record relationship for names
    for record in root.findall('.//mods:mods', namespaces):
        if 'names' in PROCESS:
            bib_names = []
            id = record.find('mods:recordInfo/mods:recordIdentifier[@source = "SIRSI"]', namespaces).text
        
            #personal names
            for name in record.findall('mods:name[@type]', namespaces):
                parts = []
                for part in name.findall('mods:namePart', namespaces):
                    parts.append(part.text)
                    
                #add name_string into a list to associate ckey with 1 or more names found in the MARC record
                name_string = ' '.join(parts)            
                bib_names.append(name_string)
                
                #add unique name string into names[] list for performing LCNAF lookup
                if name_string not in names:
                    names.append(name_string)           
            
            #add ckey and names into name_condordance
            name_concordance.append((id, '|'.join(bib_names)))
            
        if 'subjects' in PROCESS:
            for subject in record.findall('mods:subject', namespaces):
                if subject.get('authority') == 'lcsh':
                    parts = []
                    position = 1
                    
                    first_component = subject[0].tag.split('}')[-1]
                    for part in subject:
                        parts.append(part.text)
                        
                        term = part.text
                        code = part.tag.split('}')[-1]
                        tuple = ()
                        
                        #generate UUID as a key, based on the code and string
                        id = str(uuid.uuid3(uuid.NAMESPACE_URL, code + ":" + term))
                        
                        if id not in subjects:                        
                            #ignore c, e: generally misused or unused
                            if position == 1:
                                tuple = lookup_loc(term=term, scheme='lcsh_lcnaf', rdftype='rdftype:Topic OR rdftype:Geographic', subdivision="-memberOf:http://id.loc.gov/authorities/subjects/collection_GeographicSubdivisions")
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
        
        if 'relators' in PROCESS:
            for relator in record.findall('.//mods:roleTerm', namespaces):
                term = relator.text
                id = str(uuid.uuid3(uuid.NAMESPACE_URL, term))
                
                
                
                if id not in relators:
                    tuple = lookup_loc(term=term, scheme='relators', rdftype='rdftype:Role', subdivision=None)
                    
                    relators[id] = tuple
                    time.sleep(1)
                                
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
                        elif authority == 'lcfgt':
                            tuple = lookup_loc(term=term, scheme='lcgtf', rdftype='rdftype:GenreForm', subdivision=None)
                            genres[id] = tuple
                            time.sleep(1)
                             
        if 'places' in PROCESS:
            #look up the marc country code in LOC in order to use the preferred label as a search term for Geonames
            for record in root.findall('.//mods:mods', namespaces):
                for place in record.findall('mods:originInfo/mods:place/mods:placeTerm', namespaces):                
                    if place.get('type') == 'code' and place.get('authority') == 'marccountry':
                        marcCountry = place.text
                        #only look up the MARC country code once
                        if marcCountry not in marcCountries:
                            marcCountries[marcCountry] = get_marc_country(marcCountry)                    
                    elif place.get('type') == 'text':
                        term = place.text
                    
                if marcCountry and term:    
                    #ignore unknown place
                    if marcCountry != 'xx':
                        query = term + ', ' + marcCountries[marcCountry]["prefLabel"]
                        id = str(uuid.uuid3(uuid.NAMESPACE_URL, marcCountry + ":" + term))
                        
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
                        
            #look for simple subject/geographic
            for geo in record.findall('mods:subject/mods:geographic', namespaces):
                term = geo.text
                id = str(uuid.uuid3(uuid.NAMESPACE_URL, term)) 
                if id not in places:
                    tuple = lookup_geonames(query=term, featureClass=None)
                    places[id] = tuple
                    time.sleep(1)

def cleanup():        
    #delete XML files
    if os.path.exists('mods.xml'):
        os.remove('mods.xml')
    if os.path.exists('marc.xml'):
        os.remove('marc.xml')

def main():
    global names
    global subjects
    global genres
    global relators
    global places
    
    cleanup()
    
    #read ckey column into list
    with open('dpla_sirsi.csv', newline='') as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        header = next(reader)
        for row in reader:
            ckey = row[1]
            if ckey not in ckeys:
                ckeys.append(ckey)
                
    
    #iterate through ckeys 1000 at a time
    num = len(ckeys)
    page = 0
    while (page * ROWS) < num:
        start = page * ROWS
        end = (page + 1) * ROWS
        
        print("Page", str(page + 1), "of", str(math.ceil(num / ROWS)))
        
        ckey_param = ','.join(ckeys[start:end])
        
        process_marcxml(ckey_param)
        
        page = page + 1
    
    #lookup names if activated
    if 'names' in PROCESS:
        
        names.sort()
        cpf = {}
        for name in names:
            id = str(uuid.uuid3(uuid.NAMESPACE_URL, name))
            tuple = lookup_loc(term=name, scheme='lcnaf', rdftype='rdftype:Name', subdivision=None)
        
            cpf[id] = tuple
            
            time.sleep(1)
            
        #write name concordance to CSV
        with open('bibs-names.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ckey", "Names"))
            writer.writerows(name_concordance)
        
        #write names and LCNAF URIs to CSV
        with open('names-entities.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Sirsi Value", "Preferred Label", "URI"))
            
            for key, tuple in cpf.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
            
    if 'relators' in PROCESS:
        with open('relators.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Sirsi Value", "Preferred Label", "URI"))
        
            for key, tuple in relators.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
    
    if 'subjects' in PROCESS:
        with open('subjects.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Sirsi Value", "Preferred Label", "URI"))
        
            for key, tuple in subjects.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
    if 'genres' in PROCESS:
        with open('genres.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Sirsi Value", "Preferred Label", "URI"))
        
            for key, tuple in genres.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2]))
                   
    if 'places' in PROCESS:
        with open('places.csv', 'w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("ID", "Sirsi Value", "Preferred Label", "URI", "Country Name", "Admin Name", "Feature Class"))
        
            for key, tuple in places.items():
                if tuple is not None:        
                    writer.writerow((key, tuple[0], tuple[1], tuple[2], tuple[3], tuple[4], tuple[5]))
    
    print("Process completed. Writing CSV files and removing XML.")
    cleanup()
    
if __name__=="__main__":
    main()
