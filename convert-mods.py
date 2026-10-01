"""
Author: Ethan Gruber
Date: October 2026
Function: Read a MODS file or directory of MODS files and apply the XSLT transformation to embed concept URIs,
    then transform the enriched MODS into Linked Art JSON-LD and RDF/XML and Turtle
"""

import sys, os, requests, subprocess, math, urllib.parse, time, glob, argparse
from pathlib import Path
from rdflib import Graph, plugin
from rdflib.serializer import Serializer

SAXON_PATH = "../saxon/SaxonHE12-4J/saxon-he-12.4.jar"

def transform_mods(dir=None, file=None):
    
    print("Embedding URIs in MODS")
    
    if dir:
        path = dir
        print(f"Combining MODS files in {dir} and adding PID, if missing")
        
    elif file:
        path = file        
    
    #re-transform MODS to embed entity URIs and other minor normalization
    #cmd = f"java -jar {SAXON_PATH} -xsl:marc-to-mods/embed_uris_in_mods.xsl -s:{path} -o:{path}"
    #result = subprocess.call(cmd, shell=True, text=True)

    print("Transforming MODS to Linked Art JSON-LD")
    
    #transform to Linked Art JSON-LD and RDF/XML
    #cmd = f"java -jar {SAXON_PATH} -xsl:mods-to-linkedart/mods-to-linkedart.xsl -s:{path} -o:json/objects.json"
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


        
def main():
    
    #accept input arguments in order to determine the file or directory transformation process
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="MODS file to process")
    parser.add_argument("-d", "--dir", help="Process a directory of MODS files")
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
                transform_mods(file=args.file)
            else:
                sys.exit("File not found")
        elif args.dir:
            if os.path.exists(args.dir):
                transform_mods(dir=args.dir)
            else:
                sys.exit("Directory not found")
        else:
            sys.exit("File or dir not set")
    
    #enrich and transform MODS into Linked Open Datas
    #transform_mods()
    
    

if __name__=="__main__":
    main()