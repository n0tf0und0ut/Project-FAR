#!/usr/bin/env python3
"""File-source-path coverage of pinned Graphify JSON; existence only, not semantic."""
import collections,hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parent; root=D.parent/'far';graph=D.parent/'graph.json'
p=json.loads((D/'mandatory_gate_protocol.json').read_text())
assert hashlib.sha256(graph.read_bytes()).hexdigest()==p['graph_sha256']
g=json.loads(graph.read_text());covered={n.get('source_file') for n in g['nodes'] if n.get('source_file')}
groups=collections.defaultdict(set)
for x in root.rglob('*'):
 if x.is_file():groups[x.suffix.lower() or '(none)'].add(str(x.relative_to(root)))
selected=['.py','.lean','.md','.js','.sh','.yml','.yaml','.json']
count={ext:{'source_files':len(groups[ext]),'covered_as_graph_node_source_paths':len(groups[ext]&covered),
             'sample_unrepresented_paths':sorted(groups[ext]-covered)[:5]} for ext in selected}
report={'schema':'far-graphify-file-source-coverage/v0.1','status':'Research: source path coverage (not graph semantic recall)',
        'source_commit':p['source_sha'],'graph_sha256':p['graph_sha256'],
        'file_set':'All extracted source archive files under pinned commit',
        'graph_nodes':len(g['nodes']),'graph_edges':len(g['edges']),
        'unique_graph_source_paths':len(covered),
        'by_extension':count,
        'limitation':'A file represented by one node may still have incorrect or incomplete edges; zero source paths means Graphify provides no direct source node for the file in this graph.'}
(D/'mandatory_gate_coverage.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:{x:v for x,v in q.items() if x!='sample_unrepresented_paths'} for k,q in count.items()},indent=2))
