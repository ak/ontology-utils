
# ontology-utils

A small collection of utilities and demos for working with ontologies and ontology-related tooling.

Repository structure

- `go-filter-bp` — Utilities for filtering and processing biological process annotations (Python).
- `owl-viewer` — Small web-based OWL/ontology viewer built with Vite + React (TypeScript).

Projects

- `go-filter-bp`
	- Purpose: Tools to filter and extract Gene Ontology biological process annotations.
	- Contents: `filter_biological_process.py` and a `pyproject.toml` for Python packaging.
	- Quick start:
		- From the `go-filter-bp` directory run:
			```bash
			uv run filter_biological_process.py
			```

- `owl-viewer`
	- Purpose: Interactive viewer for OWL/ontology files and related visualizations.
	- Contents: Vite + React app located in `owl-viewer/`.
	- Quick start:
		- From the `owl-viewer` directory run:
			```bash
			npm install
			npm run dev
			```
