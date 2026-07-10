"""
Author: Ethan Gruber
Date: June 2026
Function: Iterate through CSV with two columns (catalog_key and pid) to request MARC XML from API to convert to modsign2map
"""

import csv, re, os, requests, subprocess, math, urllib.parse, time, glob
from xml.etree import ElementTree as ET
from rdflib import Graph, plugin
from rdflib.serializer import Serializer

SAXON_PATH = "../saxon/SaxonHE12-4J/saxon-he-12.4.jar"
ROWS = 100

def transform_marcxml():
    
    print("Transforming MARC to MODS")
    
    marcfile = "marc.xml"
    modsfile = "mods.xml"

    #convert MARC XML to MODS
    cmd = f"java -jar {SAXON_PATH} -xsl:marc-to-mods/MARC21slim2MODS3-7.xsl -s:marc/{marcfile} -o:mods/{modsfile}"
    result = subprocess.call(cmd, shell=True, text=True)
    
    #re-transform MODS to embed entity URIs and other minor normalization
    cmd = f"java -jar {SAXON_PATH} -xsl:marc-to-mods/embed_uris_in_mods.xsl -s:mods/{modsfile} -o:mods/{modsfile}"
    result = subprocess.call(cmd, shell=True, text=True)

    print("Transforming MODS to Linked Art JSON-LD")
    
    #transform to Linked Art JSON-LD and RDF/XML
    cmd = f"java -jar {SAXON_PATH} -xsl:mods-to-linkedart/mods-to-linkedart.xsl -s:mods/{modsfile} -o:json/objects.json"
    result = subprocess.call(cmd, shell=True, text=True)
    
    print("Transforming MODS to Linked Art CIDOC-CRM RDF/XML")
    
    cmd = f"java -jar {SAXON_PATH} -xsl:mods-to-linkedart/mods-to-cidoccrm.xsl -s:mods/{modsfile} -o:rdf/objects.rdf"
    result = subprocess.call(cmd, shell=True, text=True)
    
    print("Transforming RDF/XML to TTL")
    graph = Graph()
    graph.parse("rdf/objects.rdf", format='application/rdf+xml')
    graph.serialize(destination="rdf/objects.ttl", format='text/turtle')

def download_marcxml(ckey_param, batch):
    url = "https://ils.lib.virginia.edu/uhtbin/getMarc?ckey=" + ckey_param + "&type=xml"
    
    filename = "{:04d}".format(batch)
    
    response = requests.get(url)
    if response.status_code == 200:
        with open("marc/" + filename + ".xml", 'wb') as file:
            file.write(response.content)
    else:
        print('Failed to download file.')
        
def cleanup():        
    #delete XML files
    for filename in os.listdir('marc'):
        if filename.endswith('.xml'):
            file_path = os.path.join('marc', filename)
            os.remove(file_path)

#combine MARC XML files into one file for transformatino
def combine_xml_files():
    
    print("Combining MARC batches into single MARC XML file")
    
    xml_files = glob.glob("marc/*.xml")
    
    combined = ET.Element('collection', attrib={"xmlns":"http://www.loc.gov/MARC21/slim"})
    ET.indent(combined, space="\t", level=0)
    
    for xml_file in xml_files:
        data = ET.parse(xml_file).getroot()
        
        if data.tag == 'collection':            
            #append all MARC records into the root marc:collection element
            for record in data.findall('.//{http://www.loc.gov/MARC21/slim}record'):
                combined.append(record)
        else:
            combined.append(data)
    
    xml_data = ET.tostring(combined)
    with open("marc/marc.xml", "wb") as f:
        f.write(xml_data)
        
def main():
    ckeys = []
    
    #id = "u5711721"
    
    #create xml folder if it doesn't exist
    if not os.path.isdir("marc"):
        os.makedirs("marc")
    if not os.path.isdir("json"):
        os.makedirs("json")
    if not os.path.isdir("mods"):
        os.makedirs("mods")
        
    cleanup()
    
    #enable testing on a single ckey
    if 'id' in locals():
        download_marcxml(id, batch=0)
    else:
        #read ckey column into list
        with open('dpla_sirsi.csv', newline='') as file:
            reader = csv.reader(file, delimiter=',', quotechar='"')
            header = next(reader)
            for row in reader:
                ckey = row[1]
                if ckey not in ckeys:
                    ckeys.append(ckey)
        
        #iterate through ckeys 100 at a time
        num = len(ckeys)
        page = 0 #start page at 0 for the beginning
        while (page * ROWS) < num:
            start = page * ROWS
            end = (page + 1) * ROWS
            
            print("Page", str(page + 1), "of", str(math.ceil(num / ROWS)))
            
            ckey_param = ','.join(ckeys[start:end])
            
            download_marcxml(ckey_param, batch=page + 1)
            
            page = page + 1
    
    #combine all MARC XML into one file
    combine_xml_files()
    
    #transform batch of MARC XML into MODS and continue workflow
    transform_marcxml()
    
    cleanup()
    
    

if __name__=="__main__":
    main()