"""
Author: Ethan Gruber
Date: October 2026
Function: Iterate through MODS files and extract non-LCSH subject topics and write to a list.
    Subsequent edit: remove subject topics that resemble Getty AAT categorical facets
"""

import glob, os
from pathlib import Path
import xml.etree.ElementTree as ET

def main():
    
    un_headings = []
    
    #C:\Users\ewg4x\projects\tracksys-mods\temp
    
    path = Path(r"/usr/local/projects/tracksys-mods")
    xml_files = glob.glob(os.path.join(path, "*.xml"))
    
    #for each MODS file in the folder, look for terms that are not in subject[@authority = 'lcsh']
    for xml_file in xml_files:
        print("Reading", xml_file)
        updated = False
        
        ET.register_namespace('',"http://www.loc.gov/mods/v3")
        tree = ET.parse(xml_file)
        root = tree.getroot()
                
        namespaces = {'mods': 'http://www.loc.gov/mods/v3'}
        
        collection = root.find("mods:relatedItem[@displayLabel = 'Part of']", namespaces)
        if collection is not None:
            collectionTitle = collection.find("mods:titleInfo/mods:title", namespaces).text
        else:
            collectionTitle = ""
        
        for subject in root.findall('mods:subject', namespaces):
            if subject.get('authority') is None:
                position = 1
                for part in subject:
                    term = part.text
                    
                    #Jackson Davis records use a category qualifier in topic[2]
                    if "Jackson Davis" in collectionTitle and position == 2:
                        print("Removing:", term)
                        subject.remove(part)      
                        updated = True
                    elif " by " in term or " in " in term:
                        print("Removing:", term)
                        subject.remove(part)      
                        updated = True
                    elif term.strip() == "":
                        subject.remove(part)      
                        updated = True
                    
                    position += 1
                    
                        #un_headings.append(term)
    
        if updated == True:
            tree.write(xml_file, encoding="utf-8")
                

    #write terms to text file
    """
    if len(un_headings) > 0:
        with open('unauthorized_headings.txt', 'w', newline='', encoding="utf-8") as file:
            for line in un_headings:
                file.write('%s\n' %line)
        file.close()
    """

if __name__=="__main__":
    main()