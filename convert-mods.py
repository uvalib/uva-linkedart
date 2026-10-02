"""
Author: Ethan Gruber
Date: October 2026
Function: Read a MODS file or directory of MODS files and apply the XSLT transformation to embed concept URIs,
    then transform the enriched MODS into Linked Art JSON-LD and RDF/XML and Turtle
"""

import sys, os, requests, subprocess, math, urllib.parse, time, glob, argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from rdflib import Graph, plugin
from rdflib.serializer import Serializer

SAXON_PATH = "../saxon/SaxonHE12-4J/saxon-he-12.4.jar"
MODS_SCHEMA = "http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-6.xsd"

def transform_mods(output: str, dir=None, file=None):
    #if a directory is provided, then combine all MODS files into one MODS file for transformation
    if dir:
        path = dir
        combine_xml_files(dir, output)    
        
    elif file:
        path = file        
    
    print("Embedding URIs in MODS")
    
    #re-transform MODS to embed entity URIs and other minor normalization
    #cmd = f"java -jar {SAXON_PATH} -xsl:marc-to-mods/embed_uris_in_mods.xsl -s:{path} -o:{path}"
    #result = subprocess.call(cmd, shell=True, text=True)

    print("Transforming MODS to Linked Art JSON-LD")
    
    #transform to Linked Art JSON-LD and RDF/XML
    #cmd = f"java -jar {SAXON_PATH} -xsl:mods-to-linkedart/mods-to-linkedart.xsl -s:mods{output}.xml -o:json/{output}.json"
    #result = subprocess.call(cmd, shell=True, text=True)
    
    """
    print("Transforming MODS to Linked Art CIDOC-CRM RDF/XML")
    
    cmd = f"java -jar {SAXON_PATH} -xsl:mods-to-linkedart/mods-to-cidoccrm.xsl -s:mods/{modsfile} -o:rdf/objects.rdf"
    result = subprocess.call(cmd, shell=True, text=True)
    
    print("Transforming RDF/XML to TTL")
    graph = Graph()
    graph.parse("rdf/objects.rdf", format='application/rdf+xml')
    graph.serialize(destination="rdf/objects.ttl", format='text/turtle')
    """

def combine_xml_files(dir, output):
    
    print(f"Combining MODS files in {dir} and adding PID, if missing")
    xml_files = glob.glob(f"{dir}/*.xml")
    
    ET.register_namespace('',"http://www.loc.gov/mods/v3")
    ET.register_namespace('xsi',"http://www.w3.org/2001/XMLSchema-instance")
    combined = ET.Element('modsCollection', attrib={"xsi:schemaLocation": MODS_SCHEMA})
    ET.indent(combined, space="\t", level=0)
    
    for xml_file in xml_files:
        data = ET.parse(xml_file).getroot()
        
        if data.tag == 'modsCollection':            
            #append all MODS records into the root mods:modsCollection element
            for record in data.findall('.//{http://www.loc.gov/mods/v3}mods'):                
                combined.append(record)
        else:            
            #convert filename back into PID for insertion into MODS record
            path = Path(xml_file)
            pid = path.name.replace(".xml", "").replace("_", ":")
            
            recordInfo = data.find("./{http://www.loc.gov/mods/v3}recordInfo")
            contains_pid = False
            
            #evaluate whether the PID has already been inserted into the MODS record
            for recordIdentifier in recordInfo.findall("./{http://www.loc.gov/mods/v3}recordIdentifier"):
                if recordIdentifier.get("source") == "PID":
                    contains_pid = True
            
            #insert PID into recordInfo subelement
            if contains_pid == False:
                ET.SubElement(recordInfo, "recordIdentifier", source="PID").text = pid
            
            combined.append(data)
    
    xml_data = ET.tostring(combined)
    with open(f"mods/{output}.xml", "wb") as f:
        f.write(xml_data)
        
def main():
    
    #accept input arguments in order to determine the file or directory transformation process
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="MODS file to process")
    parser.add_argument("-d", "--dir", help="Process a directory of MODS files")
    parser.add_argument("-o", "--output", default="objects", help="Output filename, without extension. It is used to name the output MODS, JSON-LD and RDF")
    args = parser.parse_args()
    
    if args.file and args.dir:
        sys.exit("Only one of file or dir arguments is acceptable")
    else:
        #create necessary folders
        if not os.path.isdir("json"):
            os.makedirs("json")
        if not os.path.isdir("rdf"):
            os.makedirs("rdf")
        
        if args.file:
            if os.path.exists(args.file):
                transform_mods(output=args.output, file=args.file)
            else:
                sys.exit("File not found")
        elif args.dir:
            if os.path.exists(args.dir):
                transform_mods(output=args.output, dir=args.dir)
            else:
                sys.exit("Directory not found")
        else:
            sys.exit("File or dir not set")
    
    #enrich and transform MODS into Linked Open Datas
    #transform_mods()
    
    

if __name__=="__main__":
    main()