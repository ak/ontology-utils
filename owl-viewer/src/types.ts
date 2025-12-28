export interface OntologyClass {
  id: string;
  label: string;
  description: string;
  children: string[];
  parents: string[];
}

export interface OntologyData {
  classMap: Map<string, OntologyClass>;
  roots: OntologyClass[];
}
