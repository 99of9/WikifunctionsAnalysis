#Python code to illustrate parsing of XML files
# importing the required modules
import re
import json
import html
import csv
import ast
import hashlib
import xml.etree.ElementTree as ET
import networkx as nx
import matplotlib.pyplot as plt

def string_to_colour(s):
	# Hash the string using md5 for consistency
	h = hashlib.md5(s.encode("utf-8")).hexdigest()
	# Use first 6 hex digits as an RGB colour
	return f"#{h[:6]}"

def create_adjacency_list(edges, directed=False):
    """
    Creates an adjacency list from a list of edge pairs.

    Args:
        edges: A list of tuples, where each tuple (u, v) represents an edge
               between vertex u and vertex v.
        directed: A boolean indicating whether the graph is directed (True)
                  or undirected (False). Defaults to False (undirected).

    Returns:
        A dictionary representing the adjacency list.
    """
    adjacency_list = {}

    # Initialize all vertices found in the edges
    for u, v in edges:
        if u not in adjacency_list:
            adjacency_list[u] = []
        if v not in adjacency_list:
            adjacency_list[v] = []

    # Add edges to the adjacency list
    for u, v in edges:
        adjacency_list[u].append(v)
        if not directed:  # For undirected graphs, add the reverse edge
            adjacency_list[v].append(u)
    
    return adjacency_list


def parseXML(xmlfile):

    # create element tree object
    tree = ET.parse(xmlfile)

    # get root element
    root = tree.getroot()
    print(f"Root element tag: {root.tag}")

    # create empty list for items
    items = []

    # Define the namespace
    ns = {"mw": "http://www.mediawiki.org/xml/export-0.11/"}

    #titles I care about:
    pattern = re.compile(r"^Z\d+$")  # matches titles like Z123, Z4567

    #for child in root.findall("mw:siteinfo", ns):
    #    print("Found child:", child.tag)

    def strip_ns(tag):
	    return tag.split("}")[-1] if "}" in tag else tag

    for item in root:
        #print("Tag without ns:", strip_ns(item.tag))

        if strip_ns(item.tag) == "page":
            title = item.find("mw:title", ns).text
            if not pattern.match(title):
                continue
		    
            # Get the revision text
            text_node = item.find("mw:revision/mw:text", ns)
            if text_node is None or text_node.text is None:
                continue
            
            # Unescape &quot; etc. and parse JSON
            json_str = html.unescape(text_node.text)
            try:
                obj = json.loads(json_str)
            except json.JSONDecodeError:
                continue  # skip malformed

            try:
                otype = obj.get("Z2K2").get("Z1K1")
            except:
                continue

            page_id = item.find("mw:id", ns).text

            if otype == "Z14":
                try:
                    composition = obj.get("Z2K2").get("Z14K2")
                    parent = obj.get("Z2K2").get("Z14K1")
                except:
                    composition = "failed"
                    parent = "failed"
                    print("failed")
                    continue
            else:
                parent = None
                composition = None

            if otype == "Z8":
                try:
                    rtype = obj.get("Z2K2").get("Z8K2")
                except:
                    rtype = "failed"
                    continue
            else:
                rtype = None

            #print(title+' '+str(otype)+' '+str(composition))

		    #Check type
            if otype == "Z8" or (otype == "Z14" and composition is not None):
                details = {
				    "id": page_id,
				    "title": title,
				    "otype": otype,
                    "parent": parent,
                    "composition": composition,
                    "rtype": rtype
			    }
                items.append(details)
    
    # return items list
    return items

def collect_Z7K1(obj):
	results = []
	if isinstance(obj, dict):
		for k, v in obj.items():
			if k == "Z7K1":
				results.append(v)
			results.extend(collect_Z7K1(v))
	elif isinstance(obj, list):
		for item in obj:
			results.extend(collect_Z7K1(item))
	return results

def edges_from_items(items):
    list_of_edges = []
    for item in items:
        if item['composition'] is not None:
            pair = (item['parent'], item['title'])  # Creates a tuple as a pair
            list_of_edges.append(pair)
            all_z7k1 = collect_Z7K1(item['composition'])
            all_z7k1 = [v for v in all_z7k1 if isinstance(v, str)]
            # Deduplicate while keeping order
            seen = set()
            unique_z7k1 = [x for x in all_z7k1 if not (x in seen or seen.add(x))]

            for z in unique_z7k1:
                print('pair: '+item['title']+' '+z)
                pair = (item['title'], z)
                list_of_edges.append(pair)

            
    return list_of_edges

def plot_graph(adj_list, items):
    otype_by_title = {item["title"]: item["otype"] for item in items}
    rtype_by_title = {item["title"]: item["rtype"] for item in items}
    #print(otype_by_title['Z18100'])
    #return

    for vertex, neighbors in adj_list.items():
        print(f"{vertex}: {neighbors}")
    G = nx.DiGraph(adj_list)
    node_labels = nx.get_node_attributes(G, 'label')
    color_map = []
    for node in G.nodes():
        key = str(node).strip()  # normalise type and spacing
        otype = otype_by_title.get(key, None)
        rtype = rtype_by_title.get(key, None)
        if otype == 'Z14':
            color_map.append('lightblue')  # Z14 implementations will be lightblue
        elif otype == 'Z8':
            color_map.append(string_to_colour(str(rtype))) # Z8 functions will be a hashed colour according to their output type
        else:
            color_map.append('red') # Other nodes will be green


    pos =nx.spring_layout(G, seed = 50, iterations=50000, threshold=0.000000001, method='energy')
    plt.figure(figsize=(100,100)) 
    nx.draw(G, pos, ax = None, with_labels = True,font_size = 6, node_size = 450, node_color = color_map)
    # Save the drawn graph to a file
    plt.savefig("ZID_graph.png")

def savetoCSV(items, filename):

    # specifying the fields for csv file
    fields = ['title', 'id', 'otype', 'parent', 'composition', 'rtype']

    # writing to csv file
    with open(filename, 'w', newline="", encoding="utf-8") as csvfile:

        # creating a csv dict writer object
        writer = csv.DictWriter(csvfile, fieldnames = fields)

        # writing headers (field names)
        writer.writeheader()

        # writing data rows
        writer.writerows(items)
    
def main():
    # parse xml file
    items = parseXML('dumps/wikifunctionswiki-latest-pages-meta-current.xml/wikifunctionswiki-latest-pages-meta-current.xml')

    #prepare a graph
    edges_directed = edges_from_items(items)
    adj_list_directed = create_adjacency_list(edges_directed, directed=True)
    plot_graph(adj_list_directed, items)

    # store news items in a csv file
    savetoCSV(items, 'items.csv')
    
    
if __name__ == "__main__":

    # calling main function
    main()