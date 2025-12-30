# ontology-utils

A small collection of utilities for working with ontologies and ontology-related tooling.

Repository structure

- `go-filter-bp` — Utilities for filtering and processing biological process annotations (Python).
- `reactome-pathways` — Fetch and convert pathways (Python).
- `owl-viewer` — Web-based OWL/ontology viewer built with Vite + React (TypeScript).

Projects

- `go-filter-bp`
	- Tools to filter and extract Gene Ontology biological process annotations.
	- Run:
		```bash
		uv run filter_biological_process.py
		```

- `reactome-pathways`
	- Fetch pathway hierarchies from the Reactome Content Service for a species (by NCBI Taxonomy ID) and converts them into an OWL ontology. OWL classes are created under the https://reactome.org/pathway/ namespace.
	- Run:
		```bash
		uv run pathways_to_owl.py
		```

- `owl-viewer`
	- Interactive viewer for OWL/ontology files and related visualizations.
	- Contents: Vite + React app located in `owl-viewer/`.
	- Quick start:
		- From the `owl-viewer` directory run:
			```bash
			npm install
			npm run dev
			```
