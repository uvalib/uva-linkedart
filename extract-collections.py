"""
Author: Ethan Gruber
Date: October 2026
Function: Iterate through MODS files and extract all distinct collection relatedItems
"""

import glob, os, uuid, csv
from pathlib import Path
import xml.etree.ElementTree as ET

def main():
    
    collections = []
    collections_metadata = []
    
    #C:\Users\ewg4x\projects\tracksys-mods\temp
    
    path = Path(r"../tracksys-mods")
    xml_files = glob.glob(os.path.join(path, "*.xml"))
    
    #for each MODS file in the folder, look for terms that are not in subject[@authority = 'lcsh']
    for xml_file in xml_files:
        metadata = {}
        id = ""
        
        ET.register_namespace('',"http://www.loc.gov/mods/v3")
        tree = ET.parse(xml_file)
        root = tree.getroot()
                
        namespaces = {'mods': 'http://www.loc.gov/mods/v3'}
        
        for collection in root.findall("mods:relatedItem[@type = 'host']", namespaces):
            displayLabel = collection.get('displayLabel')
            genre = collection.find("genre[@displayLabel = 'legacy set code']")
            
            #ignore relatedItems that only contain the original set code
            if genre is None:
                #use the title from Part of only
                if displayLabel == "Part of":
                    title = collection.find("mods:titleInfo/mods:title", namespaces)
                    
                    if title is not None:                        
                        id = str(uuid.uuid3(uuid.NAMESPACE_URL, title.text))
                        
                        metadata["id"] = id
                        metadata["title"] = title.text
                    
                
                accnum = collection.find("mods:identifier[@type = 'accession number']", namespaces)
                if accnum is not None:
                    metadata["accnum"] = accnum.text
                    
                url = collection.find("mods:location/mods:url", namespaces)
                if url is not None:
                    metadata["uri"] = url.text
                    
                physLoc = collection.find("mods:location/mods:physicalLocation", namespaces)
                if physLoc is not None:
                    metadata["physLoc"] = physLoc.text
            
            if len(id) > 0:
                if id not in collections:
                    collections_metadata.append(metadata)
                    collections.append(id)
                    print(metadata)
                

    #write collections to CSV
    if len(collections_metadata) > 0:
        with open('collections.csv', 'w', newline='', encoding="utf-8") as csvfile:
            fieldnames = ["id", "title", "accnum", "uri", "physLoc"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in collections_metadata:
                writer.writerow(row)

if __name__=="__main__":
    main()