import sys
import argparse
import csv
import re

import requests
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL


NCBI_HOMO_SAPIENS = "9606"
ROOT_NAMESPACE = "https://reactome.org/pathway/"


def fetch_reactome_pathways(species_id):
    """
    Fetch pathway hierarchy from Reactome API for given species
    """
    url = f"https://reactome.org/ContentService/data/eventsHierarchy/{species_id}"
    print(f"Fetching pathways from {url}...")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)


def create_owl_graph():
    """Create and initialize the RDF graph with namespaces"""
    g = Graph()

    # Define namespace
    REACTOME = Namespace(ROOT_NAMESPACE)

    # Bind namespaces for prettier output
    g.bind("owl", OWL)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("reactome", REACTOME)

    return g, REACTOME


def add_pathway_to_graph(
    g,
    reactome_ns,
    pathway,
    parent_id=None,
    top_level_id=None,
    pathway_list=None,
):
    """
    Recursively add pathway and its children to RDF graph
    Only includes entries with type 'Pathway' or 'TopLevelPathway'

    Args:
        g: RDF Graph
        reactome_ns: Reactome namespace
        pathway: Pathway data from Reactome API
        parent_id: Parent pathway ID (for subClassOf relationship)
        top_level_id: Top-level parent pathway ID
        pathway_list: List to collect pathway info for CSV export
    """
    pathway_type = pathway.get("type", "Pathway")

    # Only process if type is 'Pathway' or 'TopLevelPathway'
    if pathway_type not in ["Pathway", "TopLevelPathway"]:
        # Still recurse through children in case they are Pathways
        if "children" in pathway and pathway["children"]:
            for child in pathway["children"]:
                add_pathway_to_graph(
                    g, reactome_ns, child, parent_id, top_level_id, pathway_list
                )
        return

    pathway_id = pathway.get("stId", pathway.get("dbId"))
    # Use 'name' field for label
    label_text = pathway.get("name")

    # Skip if no name field
    if not label_text:
        if "children" in pathway and pathway["children"]:
            for child in pathway["children"]:
                add_pathway_to_graph(
                    g, reactome_ns, child, parent_id, top_level_id, pathway_list
                )
        return

    # Add to pathway list for CSV export
    current_top_level = pathway_id if parent_id is None else top_level_id
    if pathway_list is not None:
        pathway_list.append(
            {
                "id": pathway_id,
                "parent_id": current_top_level,
                "name": label_text,
            }
        )

    # Create pathway URI
    pathway_uri = reactome_ns[str(pathway_id)]

    # Add as OWL Class
    g.add((pathway_uri, RDF.type, OWL.Class))

    # Add Reactome ID as annotation property
    reactome_id_prop = reactome_ns.id
    g.add((reactome_id_prop, RDF.type, OWL.AnnotationProperty))
    g.add((pathway_uri, reactome_id_prop, Literal(str(pathway_id))))

    # Add label (from name field)
    g.add((pathway_uri, RDFS.label, Literal(label_text)))

    # Add subClassOf relationship to parent
    if parent_id:
        parent_uri = reactome_ns[str(parent_id)]
        g.add((pathway_uri, RDFS.subClassOf, parent_uri))

    # Recursively process children
    if "children" in pathway and pathway["children"]:
        for child in pathway["children"]:
            add_pathway_to_graph(
                g,
                reactome_ns,
                child,
                pathway_id,
                current_top_level,
                pathway_list,
            )


def count_pathways(pathways):
    """Count total number of pathways including nested children"""
    count = len(pathways)
    for pathway in pathways:
        if "children" in pathway and pathway["children"]:
            count += count_pathways(pathway["children"])
    return count


def convert_reactome_to_owl(species_id):
    """
    Main conversion function

    Args:
        species_id: NCBI Taxonomy ID

    Returns:
        RDF Graph with OWL ontology
    """
    # Fetch pathways from Reactome
    pathways = fetch_reactome_pathways(species_id)

    print(f"Found {len(pathways)} top-level pathways")
    total_count = count_pathways(pathways)
    print(f"Total pathways (including nested): {total_count}")

    # Create RDF graph
    g, reactome_ns = create_owl_graph()
    pathway_list = []

    # Add all pathways to graph
    print("Converting to OWL format...")
    for pathway in pathways:
        add_pathway_to_graph(g, reactome_ns, pathway, pathway_list=pathway_list)

    print(f"Conversion complete! Added {len(g)} triples to the graph.")
    return g, pathway_list


def main():
    parser = argparse.ArgumentParser(description="Convert Reactome pathways to OWL")
    parser.add_argument(
        "--species-id",
        dest="species_id",
        default=NCBI_HOMO_SAPIENS,
        help="NCBI Taxonomy ID for species (default: 9606)",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default="reactome_pathways.owl",
        help="Output OWL file path (default: reactome_pathways.owl)",
    )
    args = parser.parse_args()

    graph, pathway_list = convert_reactome_to_owl(species_id=args.species_id)

    # Write to file in RDF/XML format
    output_file = args.output
    graph.serialize(destination=output_file, format="pretty-xml")

    print(f"\nOWL file saved to: {output_file}")

    # Write pathway summary to CSV file
    csv_output_file = re.sub(
        r"\.owl$", "_summary.csv", output_file, flags=re.IGNORECASE
    )
    with open(csv_output_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["id", "parent_id", "name"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for pathway in pathway_list:
            writer.writerow(pathway)

    # Also print some sample triples
    print("\n--- Sample triples (first 20) ---")
    for i, (s, p, o) in enumerate(graph):
        if i >= 20:
            break
        print(f"{s} {p} {o}")

    print(f"\n... (Total: {len(graph)} triples)")


if __name__ == "__main__":
    main()
