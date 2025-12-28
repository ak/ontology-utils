import React, { useState } from 'react';
import { Upload, Search, ChevronRight, ChevronDown, Info, Folder, FolderOpen, FileText } from 'lucide-react';

interface OntologyClass {
  id: string;
  label: string;
  description: string;
  children: string[];
  parents: string[];
}

interface OntologyData {
  classMap: Map<string, OntologyClass>;
  roots: OntologyClass[];
}

const OWLViewer: React.FC = () => {
  const [, setFile] = useState<File | null>(null);
  const [ontologyData, setOntologyData] = useState<OntologyData | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<OntologyClass | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [rootNodes, setRootNodes] = useState<OntologyClass[]>([]);

  const parseOWL = (xmlText: string): OntologyData => {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
    
    const classMap = new Map<string, OntologyClass>();
    const parentChildMap = new Map<string, string[]>();
    const childParentMap = new Map<string, string[]>();
    
    // Parse OWL classes
    const owlClasses = xmlDoc.getElementsByTagName('owl:Class');
    for (let i = 0; i < owlClasses.length; i++) {
      const cls = owlClasses[i];
      const id = cls.getAttribute('rdf:about') || cls.getAttribute('rdf:ID');
      
      if (id) {
        const label = cls.getElementsByTagName('rdfs:label')[0]?.textContent || id.split('#').pop()?.split('/').pop() || id;
        const description = cls.getElementsByTagName('rdfs:comment')[0]?.textContent || '';
        
        classMap.set(id, {
          id: id,
          label: label,
          description: description,
          children: [],
          parents: []
        });
        
        // Parse subClassOf relationships
        const subClassOf = cls.getElementsByTagName('rdfs:subClassOf');
        for (let j = 0; j < subClassOf.length; j++) {
          const parent = subClassOf[j].getAttribute('rdf:resource');
          if (parent) {
            if (!parentChildMap.has(parent)) {
              parentChildMap.set(parent, []);
            }
            parentChildMap.get(parent)!.push(id);
            
            if (!childParentMap.has(id)) {
              childParentMap.set(id, []);
            }
            childParentMap.get(id)!.push(parent);
          }
        }
      }
    }
    
    // Build children and parents arrays
    classMap.forEach((node, id) => {
      node.children = parentChildMap.get(id) || [];
      node.parents = childParentMap.get(id) || [];
    });
    
    // Find root nodes (nodes with no parents)
    const roots: OntologyClass[] = [];
    classMap.forEach((node) => {
      if (node.parents.length === 0) {
        roots.push(node);
      }
    });
    
    const sortedRoots = roots.length > 0 
      ? roots.sort((a, b) => a.label.localeCompare(b.label))
      : Array.from(classMap.values()).slice(0, 10).sort((a, b) => a.label.localeCompare(b.label));
    
    return {
      classMap,
      roots: sortedRoots
    };
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFile = e.target.files?.[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = event.target?.result;
        if (typeof result === 'string') {
          const parsed = parseOWL(result);
          setOntologyData(parsed);
          setRootNodes(parsed.roots);
          setExpandedNodes(new Set());
          setSelectedNode(null);
        }
      };
      reader.readAsText(uploadedFile);
    }
  };

  const toggleNode = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const getChildNodes = (nodeId: string): OntologyClass[] => {
    if (!ontologyData) return [];
    const node = ontologyData.classMap.get(nodeId);
    if (!node) return [];
    return node.children
      .map(childId => ontologyData.classMap.get(childId))
      .filter((child): child is OntologyClass => child !== undefined)
      .sort((a, b) => a.label.localeCompare(b.label));
  };

  const renderTreeNode = (node: OntologyClass, depth: number = 0): React.ReactNode => {
    if (!node) return null;
    
    const isExpanded = expandedNodes.has(node.id);
    const isSelected = selectedNode?.id === node.id;
    const hasChildren = node.children.length > 0;
    const matchesSearch = searchTerm && node.label.toLowerCase().includes(searchTerm.toLowerCase());
    
    return (
      <div key={node.id} className="select-none">
        <div
          className={`flex items-center py-2 px-3 rounded-lg cursor-pointer transition-colors ${
            isSelected ? 'bg-blue-100 text-blue-900' : matchesSearch ? 'bg-green-50' : 'hover:bg-slate-100'
          }`}
          style={{ paddingLeft: `${depth * 24 + 12}px` }}
          onClick={() => {
            setSelectedNode(node);
            if (hasChildren) {
              toggleNode(node.id);
            }
          }}
        >
          {hasChildren ? (
            <span className="mr-2 flex-shrink-0">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-slate-600" />
              ) : (
                <ChevronRight className="w-4 h-4 text-slate-600" />
              )}
            </span>
          ) : (
            <span className="mr-2 flex-shrink-0 w-4" />
          )}
          
          {hasChildren ? (
            isExpanded ? (
              <FolderOpen className="w-4 h-4 mr-2 text-blue-500 flex-shrink-0" />
            ) : (
              <Folder className="w-4 h-4 mr-2 text-blue-500 flex-shrink-0" />
            )
          ) : (
            <FileText className="w-4 h-4 mr-2 text-slate-400 flex-shrink-0" />
          )}
          
          <span className={`text-sm ${matchesSearch ? 'font-semibold text-green-700' : 'text-slate-700'}`}>
            {node.label}
          </span>
          
          {hasChildren && (
            <span className="ml-auto text-xs text-slate-400 flex-shrink-0">
              ({node.children.length})
            </span>
          )}
        </div>
        
        {isExpanded && hasChildren && (
          <div>
            {getChildNodes(node.id).map(child => renderTreeNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const hasMatchingChild = (nodeId: string, term: string): boolean => {
    const node = ontologyData?.classMap.get(nodeId);
    if (!node) return false;
    if (node.label.toLowerCase().includes(term.toLowerCase())) return true;
    return node.children.some(childId => hasMatchingChild(childId, term));
  };

  const filteredRootNodes = searchTerm
    ? rootNodes.filter(node => {
        const matchesNode = node.label.toLowerCase().includes(searchTerm.toLowerCase());
        return matchesNode || hasMatchingChild(node.id, searchTerm);
      })
    : rootNodes;

  const expandAll = () => {
    if (!ontologyData) return;
    const allNodeIds = new Set<string>();
    ontologyData.classMap.forEach((node, id) => {
      if (node.children.length > 0) {
        allNodeIds.add(id);
      }
    });
    setExpandedNodes(allNodeIds);
  };

  const collapseAll = () => {
    setExpandedNodes(new Set());
  };

  return (
    <div className="w-full h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-slate-200 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
              <Info className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-800">OWL Viewer</h1>
              <p className="text-sm text-slate-500">Browse ontology hierarchy</p>
            </div>
          </div>
          
          <label className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 cursor-pointer flex items-center gap-2 transition-colors">
            <Upload className="w-4 h-4" />
            Upload OWL File
            <input type="file" accept=".owl,.rdf,.xml" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Tree View */}
        <div className="flex-1 flex flex-col bg-white border-r border-slate-200">
          {/* Search and Controls */}
          <div className="p-4 border-b border-slate-200 space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search terms..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            {ontologyData && (
              <div className="flex gap-2">
                <button
                  onClick={expandAll}
                  className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors"
                >
                  Expand All
                </button>
                <button
                  onClick={collapseAll}
                  className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded transition-colors"
                >
                  Collapse All
                </button>
              </div>
            )}
          </div>

          {/* Tree */}
          <div className="flex-1 overflow-auto p-4">
            {ontologyData ? (
              filteredRootNodes.length > 0 ? (
                <div className="space-y-1">
                  {filteredRootNodes.map(node => renderTreeNode(node, 0))}
                </div>
              ) : (
                <div className="text-center text-slate-500 mt-8">
                  No results found for "{searchTerm}"
                </div>
              )
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Upload className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-slate-700 mb-2">No Ontology Loaded</h3>
                  <p className="text-slate-500">Upload an OWL/RDF file to begin browsing</p>
                </div>
              </div>
            )}
          </div>

          {/* Stats */}
          {ontologyData && (
            <div className="p-4 border-t border-slate-200 bg-slate-50">
              <div className="text-sm text-slate-600 space-y-1">
                <div className="flex justify-between">
                  <span className="font-semibold">Total Classes:</span>
                  <span>{ontologyData.classMap.size}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold">Root Nodes:</span>
                  <span>{rootNodes.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold">Expanded:</span>
                  <span>{expandedNodes.size}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Details Panel */}
        {ontologyData && (
          <div className="w-96 bg-white flex flex-col">
            <div className="p-4 border-b border-slate-200">
              <h2 className="text-lg font-semibold text-slate-800">Details</h2>
            </div>

            <div className="flex-1 overflow-auto p-4">
              {selectedNode ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Label</label>
                    <div className="text-slate-800 mt-1 font-medium">{selectedNode.label}</div>
                  </div>
                  
                  <div>
                    <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">ID</label>
                    <div className="text-slate-600 text-xs mt-1 break-all bg-slate-50 p-2 rounded">
                      {selectedNode.id}
                    </div>
                  </div>
                  
                  {selectedNode.description && (
                    <div>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</label>
                      <div className="text-slate-700 text-sm mt-1 leading-relaxed">
                        {selectedNode.description}
                      </div>
                    </div>
                  )}
                  
                  {selectedNode.parents.length > 0 && (
                    <div>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">
                        Parent Classes ({selectedNode.parents.length})
                      </label>
                      <div className="space-y-2">
                        {selectedNode.parents
                          .map(parentId => ontologyData.classMap.get(parentId))
                          .filter((parent): parent is OntologyClass => parent !== undefined)
                          .sort((a, b) => a.label.localeCompare(b.label))
                          .map(parent => (
                            <button
                              key={parent.id}
                              onClick={() => {
                                setSelectedNode(parent);
                                setExpandedNodes(new Set([...expandedNodes, parent.id]));
                              }}
                              className="w-full text-left px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm transition-colors flex items-center gap-2"
                            >
                              <ChevronRight className="w-4 h-4 flex-shrink-0" />
                              <span className="truncate">{parent.label}</span>
                            </button>
                          ))}
                      </div>
                    </div>
                  )}
                  
                  {selectedNode.children.length > 0 && (
                    <div>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">
                        Child Classes ({selectedNode.children.length})
                      </label>
                      <div className="space-y-2">
                        {selectedNode.children
                          .map(childId => ontologyData.classMap.get(childId))
                          .filter((child): child is OntologyClass => child !== undefined)
                          .sort((a, b) => a.label.localeCompare(b.label))
                          .slice(0, 10)
                          .map(child => (
                            <button
                              key={child.id}
                              onClick={() => {
                                setSelectedNode(child);
                                setExpandedNodes(new Set([...expandedNodes, selectedNode.id]));
                              }}
                              className="w-full text-left px-3 py-2 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg text-sm transition-colors flex items-center gap-2"
                            >
                              <ChevronRight className="w-4 h-4 flex-shrink-0" />
                              <span className="truncate">{child.label}</span>
                            </button>
                          ))}
                        {selectedNode.children.length > 10 && (
                          <div className="text-xs text-slate-500 text-center pt-1">
                            +{selectedNode.children.length - 10} more children
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {selectedNode.parents.length === 0 && selectedNode.children.length === 0 && (
                    <div className="text-center text-slate-500 py-8">
                      <FileText className="w-12 h-12 mx-auto mb-2 text-slate-300" />
                      <p className="text-sm">Leaf node with no relationships</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-slate-500 mt-8">
                  <Info className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                  <p className="text-sm">Click on a node to view details</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OWLViewer;