"""
Author: Ethan Gruber
Date: September 2026
Function: Harvest MODS XML files from Tracksys connected to DPLA exports
"""

import requests, json, os

def main():
    if not os.path.exists("mods/tracksys"):
        os.makedirs("mods/tracksys")
    
    dpla_list = "https://tracksys-api-ws-dev.internal.lib.virginia.edu/api/published/dpla"
    
    try:
        response = requests.get(dpla_list)
    except:
        print("Unable to request content")
    else:        
        text = response.text
        pids = text.split(",")
        
        count = 1
        
        for pid in pids:
            url = f"https://tracksys-api-ws-dev.internal.lib.virginia.edu/api/pid/{pid}"
            
            with requests.get(url) as response:
                print(f"Reading {count} of {len(pids)}: {pid}")
                obj = json.loads(response.text)
                
                if obj["type"] == "xml_metadata":
                    xml_url = f"https://tracksys-api-ws-dev.internal.lib.virginia.edu/api/metadata/{pid}?type=mods"
                    response = requests.get(xml_url)
                    
                    filename = pid.replace(":", "_")
                    
                    with open(f"mods/tracksys/{filename}.xml", 'w', encoding="utf8") as file:
                        print(f"Writing {pid}")
                        file.write(response.text)
                        
            count += 1
    
    
if __name__=="__main__":
    main()