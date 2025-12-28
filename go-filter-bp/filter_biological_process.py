from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import os

# Define namespaces
OBO = Namespace("http://purl.obolibrary.org/obo/")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")

# Biological process root term
BP_ROOT = URIRef("http://purl.obolibrary.org/obo/GO_0008150")

# Download GO basic OWL file if not exists
downloaded_file = "go-basic.owl"
if os.path.exists(downloaded_file):
    print(f"Found existing {downloaded_file}, skipping download...")
else:
    print("Downloading Gene Ontology go-basic.owl...")
    url = "http://purl.obolibrary.org/obo/go/go-basic.owl"
    response = requests.get(url)
    print(f"Downloaded {len(response.content)} bytes")

    with open(downloaded_file, "wb") as f:
        f.write(response.content)
    print(f"✓ Saved downloaded file to {downloaded_file}")

# Parse with rdflib
print("\nParsing RDF graph...")
g = Graph()
g.parse(downloaded_file, format="xml")
print(f"Loaded {len(g)} triples")


def get_direct_subclasses(graph, parent_class):
    """
    Get direct subclasses of a given class
    """
    subclasses = []

    # Find direct subclasses using rdfs:subClassOf
    for s, p, o in graph.triples((None, RDFS.subClassOf, parent_class)):
        if isinstance(s, URIRef) and str(s).startswith(
            "http://purl.obolibrary.org/obo/GO_"
        ):
            subclasses.append(s)

    # Also check for subclasses through blank nodes (restrictions)
    for s, p, o in graph.triples((None, RDFS.subClassOf, None)):
        if not isinstance(s, URIRef) or not str(s).startswith(
            "http://purl.obolibrary.org/obo/GO_"
        ):
            continue

        # Check if the object is a blank node with restrictions
        if not isinstance(o, URIRef):
            # Look for restrictions that point to our parent class
            for _, _, restriction_target in graph.triples((o, None, parent_class)):
                subclasses.append(s)

    return subclasses


def parallel_dfs_traverse(graph, root_class, max_workers=None):
    """
    Parallel DFS traversal of the ontology hierarchy
    """
    if max_workers is None:
        max_workers = os.cpu_count()

    all_terms = set()
    all_terms.add(root_class)
    visited_lock = Lock()
    processed_count = 0

    def dfs_worker(node):
        """DFS worker function to explore a subtree"""
        nonlocal processed_count
        local_terms = set()
        local_terms.add(node)

        # Get direct children
        children = get_direct_subclasses(graph, node)

        with visited_lock:
            processed_count += 1
            if processed_count % 50 == 0:
                print(
                    f"\rProcessed {processed_count} nodes, found {len(all_terms)} BP terms...",
                    end="",
                    flush=True,
                )

        if not children:
            return local_terms

        # For each child, check if already visited
        unvisited_children = []
        with visited_lock:
            for child in children:
                if child not in all_terms:
                    all_terms.add(child)
                    unvisited_children.append(child)

        # Recursively process unvisited children
        for child in unvisited_children:
            child_terms = dfs_worker(child)
            local_terms.update(child_terms)

        return local_terms

    # Start parallel DFS from root
    print(f"Starting parallel DFS traversal with {max_workers} workers...")

    # Get initial children to distribute work
    initial_children = get_direct_subclasses(graph, root_class)
    with visited_lock:
        for child in initial_children:
            all_terms.add(child)

    if initial_children:
        # Process children in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(dfs_worker, child) for child in initial_children]

            for future in as_completed(futures):
                subtree_terms = future.result()
                with visited_lock:
                    all_terms.update(subtree_terms)

    return all_terms


print("\nFinding all biological process terms in hierarchy...")
bp_terms = parallel_dfs_traverse(g, BP_ROOT)
print(f"\r✓ Found {len(bp_terms)} biological process terms" + " " * 30)


# Parallel extraction of term details
def extract_term_details(term_uri):
    """Extract details for a single term"""
    go_id = str(term_uri).split("/")[-1].replace("_", ":")

    # Get label
    label = None
    for _, _, o in g.triples((term_uri, RDFS.label, None)):
        label = str(o)
        break

    # Get definition if available
    definition = None
    for _, _, o in g.triples(
        (term_uri, URIRef("http://purl.obolibrary.org/obo/IAO_0000115"), None)
    ):
        definition = str(o)
        break

    # Find parent that is closest to biological_process root
    # We traverse up the hierarchy to find the direct child of BP_ROOT
    go_bp_parent = None

    if term_uri != BP_ROOT:
        # Use BFS to find path to root
        visited = set()
        queue = [(term_uri, None)]  # (node, direct_child_of_root)

        while queue:
            current, bp_child = queue.pop(0)

            if current in visited:
                continue
            visited.add(current)

            # Get parents
            parents = []
            for s, p, o in g.triples((current, RDFS.subClassOf, None)):
                if isinstance(o, URIRef) and str(o).startswith(
                    "http://purl.obolibrary.org/obo/GO_"
                ):
                    parents.append(o)

            for parent in parents:
                if parent == BP_ROOT:
                    # Found connection to root
                    # The direct child of BP_ROOT is 'current' (not bp_child)
                    go_bp_parent = str(current).split("/")[-1].replace("_", ":")
                    break
                else:
                    # Continue searching, pass along the first non-root ancestor we found
                    # If bp_child is None, this current node might be the direct child
                    next_bp_child = bp_child if bp_child else current
                    queue.append((parent, next_bp_child))

            if go_bp_parent:
                break

    return {
        "go_id": go_id,
        "label": label or "No label",
        "definition": definition,
        "uri": str(term_uri),
        "go_bp_parent": go_bp_parent,
    }


print("\nExtracting term details in parallel...")
results = []
total_terms = len(bp_terms)
processed_count = 0
lock = Lock()

# Use ThreadPoolExecutor for parallel processing
with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
    # Submit all tasks
    future_to_term = {
        executor.submit(extract_term_details, term): term for term in bp_terms
    }

    # Process completed tasks
    for future in as_completed(future_to_term):
        result = future.result()
        results.append(result)

        with lock:
            processed_count += 1
            if processed_count % 500 == 0 or processed_count == total_terms:
                print(
                    f"\rProcessed {processed_count}/{total_terms} terms...",
                    end="",
                    flush=True,
                )

print(f"\r✓ Processed all {total_terms} terms" + " " * 30)

# Sort by GO ID
results.sort(key=lambda x: x["go_id"])

# Display first 20 terms
print("\nFirst 20 biological process terms:")
print("-" * 80)
for i, term in enumerate(results[:20], 1):
    print(f"{i}. {term['go_id']}: {term['label']}")

# Save to file
output_file = "biological_process_terms.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("GO_ID\tGO_BP_ID\tLabel\tDefinition\tURI\n")
    for term in results:
        definition = (
            term["definition"].replace("\n", " ").replace("\t", " ")
            if term["definition"]
            else ""
        )
        go_bp_parent = term["go_bp_parent"] if term["go_bp_parent"] else ""
        f.write(
            f"{term['go_id']}\t{go_bp_parent}\t{term['label']}\t{definition}\t{term['uri']}\n"
        )

print(f"\n✓ Saved {len(results)} biological process terms to {output_file}")


# Parallel RDF graph creation
def copy_triples_for_term(term_uri):
    """Copy all triples related to a term"""
    triples = []

    # Copy all triples where the term is the subject
    for s, p, o in g.triples((term_uri, None, None)):
        triples.append((s, p, o))

    # Copy all triples where the term is the object (relationships)
    for s, p, o in g.triples((None, None, term_uri)):
        if s in bp_terms:  # Only if both subject and object are BP terms
            triples.append((s, p, o))

    return triples


print("\nCreating OWL/XML subset in parallel...")
bp_graph = Graph()

# Bind OWL namespace explicitly
bp_graph.bind("owl", OWL)
bp_graph.bind("obo", OBO)
bp_graph.bind("rdfs", RDFS)
bp_graph.bind("rdf", RDF)

# Copy other namespaces from source
for prefix, namespace in g.namespaces():
    if prefix not in ["owl", "obo", "rdfs", "rdf"]:
        bp_graph.bind(prefix, namespace)

# Parallel triple collection
all_triples = []
total_bp_terms = len(bp_terms)
processed_count = 0

print(f"Collecting triples for {total_bp_terms} terms...")
with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
    future_to_term = {
        executor.submit(copy_triples_for_term, term): term for term in bp_terms
    }

    for future in as_completed(future_to_term):
        triples = future.result()
        all_triples.extend(triples)

        with lock:
            processed_count += 1
            if processed_count % 500 == 0 or processed_count == total_bp_terms:
                print(
                    f"\rProcessed {processed_count}/{total_bp_terms} terms...",
                    end="",
                    flush=True,
                )

print(f"\r✓ Collected triples for all {total_bp_terms} terms" + " " * 30)

# Add all triples to graph (deduplication happens automatically)
print("\nAdding triples to graph...")
for triple in all_triples:
    bp_graph.add(triple)

# Save as OWL/XML
owl_output = "biological_process_go.owl"
print(f"Serializing to {owl_output}...")
bp_graph.serialize(destination=owl_output, format="pretty-xml")
print(f"✓ Saved OWL/XML subset to {owl_output} ({len(bp_graph)} triples)")

print("\n" + "=" * 80)
print(f"SUMMARY: Extracted {len(results)} biological process terms")
print(f"- Source file: {downloaded_file}")
print(f"- Text file: {output_file}")
print(f"- OWL/XML file: {owl_output}")
print(f"- Used {os.cpu_count()} parallel workers")
print("=" * 80)
