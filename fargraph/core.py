"""Evidence-bound dependency graph for Python, Lean, Markdown, and GitHub workflows.

No execution of indexed source files; no network; no modifications to the analyzed tree.
This is syntactic analysis and must not be treated as a complete call graph.
"""
from __future__ import annotations

import ast
import builtins
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Iterable
from urllib.parse import unquote, urlsplit

VERSION = "0.1.0"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build", ".fargraph", ".gitnexus"}
SUPPORTED = {".py", ".md", ".lean", ".yml", ".yaml"}
MAX_SOURCE_BYTES = 2_000_000
LINK = re.compile(r"(?<!!)\[[^\]]+\]\((<?[^)\s>]+>?)(?:\s+['\"][^)]*['\"])?\)|!\[[^\]]*\]\((<?[^)\s>]+>?)\)")
REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*<?([^\s>]+)>?", re.M)
LEAN_IMPORT = re.compile(r"^\s*import\s+([A-Za-z0-9_.\s]+?)\s*(?:--.*)?$", re.M)
GH_USES = re.compile(r"^\s*-?\s*uses\s*:\s*['\"]?([^\s'\"#]+)", re.M)


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    path: str
    line: int = 0
    label: str = ""


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str
    path: str
    line: int
    certainty: str  # resolved_path, syntactic_candidate, unresolved
    detail: str = ""


@dataclass
class Graph:
    root: Path
    tracked_only: bool = False
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    hashes: dict[str, str] = field(default_factory=dict)
    diagnostics: list[dict] = field(default_factory=list)
    source_snapshots: dict[str, tuple[int, str | None]] = field(default_factory=dict, repr=False)
    _edge_keys: set = field(default_factory=set, repr=False)
    _source_paths: frozenset[str] | None = field(default=None, repr=False)

    def add_node(self, id: str, kind: str, path: str, line: int = 0, label: str = "") -> str:
        self.nodes.setdefault(id, Node(id, kind, path, line, label))
        return id

    def add_edge(self, src: str, dst: str, kind: str, path: str, line: int,
                 certainty: str, detail: str = "") -> None:
        edge = Edge(src, dst, kind, path, line, certainty, detail)
        if edge not in self._edge_keys:
            self._edge_keys.add(edge)
            self.edges.append(edge)

    def diagnostic(self, kind: str, path: str, line: int, detail: str) -> None:
        self.diagnostics.append({"kind": kind, "path": path, "line": line, "detail": detail})

    def _source_files(self) -> list[Path]:
        if self._source_paths is None:
            return _discover_files(self.root, tracked_only=self.tracked_only)
        return sorted(self.root / path for path in self._source_paths
                      if Path(path).suffix.lower() in SUPPORTED)

    def to_dict(self) -> dict:
        return {
            "schema": "fargraph/0.1",
            "version": VERSION,
            "root": str(self.root),
            "nodes": [asdict(self.nodes[n]) for n in sorted(self.nodes)],
            "edges": [asdict(e) for e in sorted(self.edges, key=lambda e: (e.source,e.target,e.kind,e.path,e.line,e.detail))],
            "hashes": dict(sorted(self.hashes.items())),
            "diagnostics": sorted(self.diagnostics, key=lambda d: (d["path"], d["line"], d["kind"], d["detail"])),
            "nonclaims": [
                "An omitted edge does not prove independence or safety.",
                "Calls are syntactic candidates, not confirmed runtime call edges.",
                "A filesystem link or import is not scientific evidence or governance authority.",
                "Results are bounded by indexed files, supported constructs and source hashes.",
            ],
        }

    def freshness(self) -> dict:
        """Detect drift within the same inventory scope and excluded symlinks."""
        changed = []
        snapshots = self.source_snapshots if self._source_paths is not None else self.hashes
        for rel, snapshot in sorted(snapshots.items()):
            path = self.root / rel
            try:
                resolved = path.resolve()
                if (not path.is_file() or not resolved.is_relative_to(self.root)
                        or (self._source_paths is not None and resolved != path)):
                    changed.append(rel)
                    continue
                size, content = _bounded_source(path)
                digest = _source_digest(content)
                current = (size, digest) if self._source_paths is not None else digest
                if current != snapshot:
                    changed.append(rel)
            except (OSError, RuntimeError):
                changed.append(rel)
        excluded = {d['path']: d for d in self.diagnostics
                    if d['kind'] == 'external_symlink'}
        for rel, recorded in sorted(excluded.items()):
            path = self.root / rel
            try:
                if (not path.is_symlink()
                        or path.resolve().is_relative_to(self.root)
                        or hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest() != recorded['detail']):
                    changed.append(rel)
            except (OSError, RuntimeError):
                changed.append(rel)
        ignored = {d['path'] for d in self.diagnostics
                   if d['kind'] in {'skipped_large_file', 'unreadable', 'external_symlink'}}
        new = []
        for path in self._source_files():
            rel = path.relative_to(self.root).as_posix()
            if rel not in self.hashes and rel not in ignored:
                new.append(rel)
        return {'fresh': not changed and not new,
                'changed_or_removed': sorted(set(changed)),
                'new_files': new, 'unindexed_at_snapshot': sorted(ignored)}

    def stats(self) -> dict:
        by_kind: dict[str, int] = defaultdict(int)
        by_certainty: dict[str, int] = defaultdict(int)
        for edge in self.edges:
            by_kind[edge.kind] += 1
            by_certainty[edge.certainty] += 1
        return {"schema": "fargraph/0.1", "files": len(self.hashes),
                "nodes": len(self.nodes), "edges": len(self.edges),
                "edge_types": dict(sorted(by_kind.items())),
                "certainty": dict(sorted(by_certainty.items())),
                "diagnostics": len(self.diagnostics)}

    def impact(self, changed_files: Iterable[str], max_depth: int = 8) -> dict:
        """Reverse dependency walk, preserving an evidence path for every reached node."""
        changed = sorted(set(_normalize_query_path(self.root, p, exact=self._source_paths is not None)
                             for p in changed_files))
        seeds = set()
        missing = []
        for path in changed:
            nid = f"file:{path}"
            if nid not in self.nodes:
                missing.append(path)
                continue
            seeds.add(nid)
            seeds.update(n.id for n in self.nodes.values() if n.kind == "symbol" and n.path == path)
        reverse: dict[str, list[Edge]] = defaultdict(list)
        for edge in self.edges:
            if edge.certainty != "unresolved":
                reverse[edge.target].append(edge)
        queue = deque((nid, [], 0) for nid in sorted(seeds))
        visited: dict[str, list[Edge]] = {}
        cutoff = False
        while queue:
            nid, explanation, depth = queue.popleft()
            if nid in visited:
                continue
            visited[nid] = explanation
            if depth >= max_depth:
                if any(e.source not in visited for e in reverse[nid]):
                    cutoff = True
                continue
            for edge in sorted(reverse[nid], key=lambda e: (e.source,e.kind,e.path,e.line)):
                if edge.source not in visited:
                    queue.append((edge.source, [edge] + explanation, depth + 1))
        affected = []
        for path in sorted(set(self.nodes[n].path for n in visited if self.nodes[n].path and self.nodes[n].path not in changed)):
            candidate_paths = [visited[n] for n in visited if self.nodes[n].path == path and visited[n]]
            if candidate_paths:
                explanation = min(candidate_paths, key=lambda arr:(len(arr),str(arr)))
                affected.append({"path": path, "reason": [asdict(e) for e in explanation]})
        return {"schema": "fargraph/0.1", "changed": changed, "missing": missing,
                "possibly_affected": affected, "max_depth": max_depth,
                "truncated": cutoff,
                "coverage_warning": "Known paths only; unresolved and dynamic dependencies may be absent."}

    def trace(self, source: str, target: str, max_depth: int = 10) -> dict:
        if source not in self.nodes or target not in self.nodes:
            return {"found": False, "error": "One or both node IDs do not exist", "source":source,"target":target}
        outbound: dict[str, list[Edge]] = defaultdict(list)
        for e in self.edges:
            if e.certainty != "unresolved":
                outbound[e.source].append(e)
        queue=deque([(source, [])]); seen={source}
        while queue:
            nid,path=queue.popleft()
            if nid==target:
                return {"found": True, "source":source,"target":target,"edges":[asdict(e) for e in path]}
            if len(path)>=max_depth:
                continue
            for e in sorted(outbound[nid],key=lambda z:(z.target,z.kind,z.line)):
                if e.target not in seen:
                    seen.add(e.target);queue.append((e.target,path+[e]))
        return {"found":False,"source":source,"target":target,"max_depth":max_depth,
                "coverage_warning":"No path found in known graph is not evidence that no relationship exists."}


def _normalize_query_path(root: Path, path: str, exact: bool = False) -> str:
    if not path or '\x00' in path:
        raise ValueError("Empty or invalid path")
    candidate = Path(os.path.abspath(root / path)) if exact else (root / path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Path leaves repository root")
    return candidate.relative_to(root).as_posix()


def _resolve_local(g: Graph, current: str, raw: str) -> tuple[str | None, str]:
    """Only accept existing in-root files/dirs. Never resolve network locations."""
    raw = raw.strip().strip('<>')
    if not raw or raw.startswith('#') or raw.startswith('//'):
        return None, "external_or_fragment"
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None, "invalid_path"
    if parsed.scheme or parsed.netloc or raw.lower().startswith(('mailto:', 'data:')):
        return None, "external_or_fragment"
    path = unquote(parsed.path).replace('\\', '/')
    if not path:
        return None, "external_or_fragment"
    root = g.root
    target = root / path.lstrip('/') if path.startswith('/') else (root / current).parent / path
    index_names = ('README.md', 'index.md', 'action.yml', 'action.yaml')
    if g._source_paths is not None:
        target = Path(os.path.abspath(target))
        if not target.is_relative_to(root):
            return None, "outside_root"
        rel = target.relative_to(root)
        for candidate in (rel, *(rel / name for name in index_names)):
            if candidate.as_posix() in g._source_paths:
                return candidate.as_posix(), "resolved"
        return rel.as_posix(), "missing"
    try:
        candidate = target.resolve()
    except (OSError, RuntimeError):
        return None, "invalid_path"
    if not candidate.is_relative_to(root):
        return None, "outside_root"
    if candidate.is_dir():
        for name in index_names:
            if (candidate/name).is_file():
                candidate = candidate/name
                break
    if not candidate.is_file():
        return candidate.relative_to(root).as_posix(), "missing"
    return candidate.relative_to(root).as_posix(), "resolved"


def _py_module_target(g: Graph, source_path: str, module: str, level: int = 0) -> str | None:
    src = PurePosixPath(source_path)
    base = list(src.parent.parts)
    if level:
        # level=1 means current package; level=2 means parent package.
        base = base[:max(0, len(base) - (level - 1))]
    else:
        base = []
    parts = [*base, *module.split('.')] if module else base
    root = g.root
    candidates=[]
    if parts:
        candidates.append(root.joinpath(*parts[:-1],parts[-1]+'.py'))
    candidates.append(root.joinpath(*parts,'__init__.py'))
    for cand in candidates:
        if g._source_paths is not None:
            rel = cand.relative_to(root).as_posix()
            if rel in g._source_paths:
                return rel
            continue
        if cand.is_file() and cand.resolve().is_relative_to(root):
            return cand.resolve().relative_to(root).as_posix()
    return None


def _bounded_source(path: Path) -> tuple[int, bytes | None]:
    size = path.stat().st_size
    if size > MAX_SOURCE_BYTES:
        return size, None
    with path.open("rb") as stream:
        content = stream.read(MAX_SOURCE_BYTES + 1)
    return len(content), content if len(content) <= MAX_SOURCE_BYTES else None


def _source_digest(content: bytes | None) -> str | None:
    return hashlib.sha256(content).hexdigest() if content is not None else None


def _read_source(g: Graph, path: Path) -> str | None:
    rel=path.relative_to(g.root).as_posix()
    try:
        size, content = _bounded_source(path)
        digest = _source_digest(content)
        if g._source_paths is not None:
            g.source_snapshots[rel] = (size, digest)
        if content is None or digest is None:
            g.diagnostic('skipped_large_file',rel,0,f'{size} bytes')
            return None
        text=content.decode('utf-8')
        g.hashes[rel]=digest
        g.add_node(f'file:{rel}', 'file', rel, 1, rel)
        return text
    except OSError as exc:
        if g._source_paths is not None:
            raise ValueError(f'Cannot read pinned source: {rel}') from exc
        g.diagnostic('unreadable',rel,0,str(exc))
        return None
    except UnicodeError as exc:
        g.diagnostic('unreadable',rel,0,str(exc))
        return None


def _file_edge(g:Graph, src:str, raw:str, kind:str, line:int, relative_override: str|None=None) -> None:
    dest,status = _resolve_local(g, relative_override or src,raw)
    if status=='external_or_fragment':
        return
    if status=='outside_root':
        g.diagnostic('out_of_root_link',src,line,raw)
        return
    if status=='invalid_path':
        g.diagnostic('invalid_link',src,line,raw)
        return
    if dest is None:
        return
    target=f'file:{dest}'
    if status!='resolved':
        # Preserve missing targets explicitly so analysis doesn't treat them as known dependencies.
        target=f'unresolved:{src}:{line}:{raw}'
        g.add_node(target,'unresolved',src,line,raw)
        g.diagnostic('unresolved_path',src,line,raw)
    else:
        g.add_node(f'file:{dest}', 'file', dest, 1, dest)
    g.add_edge(f'file:{src}', target, kind, src, line,
               'resolved_path' if status=='resolved' else 'unresolved',raw)


def _markdown(g: Graph, rel: str, body: str) -> None:
    # Index link references, but never claim anchor or reference semantics are verified.
    for match in LINK.finditer(body):
        raw=match.group(1) or match.group(2)
        line=body.count('\n',0,match.start())+1
        _file_edge(g,rel,raw,'markdown_link',line)
    for match in REF_DEF.finditer(body):
        line=body.count('\n',0,match.start())+1
        _file_edge(g,rel,match.group(1),'markdown_reference',line)


def _lean(g: Graph, rel: str, body: str) -> None:
    for match in LEAN_IMPORT.finditer(body):
        line=body.count('\n',0,match.start())+1
        for name in match.group(1).split():
            target=name.replace('.','/')+'.lean'
            # Lean roots are project-relative, not relative to importing file.
            dest,status=_resolve_local(g,rel,'/'+target)
            if status=='resolved' and dest:
                g.add_node(f'file:{dest}','file',dest,1,dest)
                g.add_edge(f'file:{rel}', f'file:{dest}', 'lean_import',rel,line,'resolved_path',name)
            else:
                g.diagnostic('unresolved_lean_import',rel,line,name)
                unresolved=f'unresolved:{rel}:{line}:lean:{name}'
                g.add_node(unresolved,'unresolved',rel,line,name)
                g.add_edge(f'file:{rel}',unresolved,'lean_import',rel,line,'unresolved',name)


def _workflow(g:Graph,rel:str,body:str)->None:
    if not rel.startswith('.github/workflows/'):
        return
    for match in GH_USES.finditer(body):
        raw=match.group(1)
        if not raw.startswith('./') and not raw.startswith('../'):
            continue
        line=body.count('\n',0,match.start())+1
        # In a workflow, local action `uses` paths are repository-relative.
        _file_edge(g,rel,'/'+(raw[2:] if raw.startswith('./') else raw),'workflow_uses',line)


class PythonVisitor(ast.NodeVisitor):
    def __init__(self, g: Graph, rel: str, tree: ast.AST) -> None:
        self.g,self.rel,self.tree=g,rel,tree
        self.stack: list[str] = []
        self.symbols: dict[str,str] = {}
        self.import_aliases: dict[str,str] = {}
        self.pending: list[tuple[str,ast.Call]]=[]
        # Pre-register all definitions to support forward references.
        self._register(tree,[])

    def _register(self,node:ast.AST,scope:list[str]) -> None:
        for sub in ast.iter_child_nodes(node):
            if isinstance(sub,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                qual='.'.join(scope+[sub.name])
                sid=f'symbol:{self.rel}:{qual}:{sub.lineno}'
                self.g.add_node(sid,'symbol',self.rel,sub.lineno,qual)
                self.g.add_edge(f'file:{self.rel}',sid,'contains',self.rel,sub.lineno,'resolved_path',qual)
                self.symbols[qual]=sid
                self._register(sub,scope+[sub.name])
            elif isinstance(sub,(ast.Module,ast.If,ast.For,ast.While,ast.Try,ast.With,ast.Match)):
                self._register(sub,scope)

    def run(self) -> None:
        self.visit(self.tree)
        for caller,call in self.pending:
            call_name=self._call_name(call.func)
            if not call_name:
                continue
            # Safe syntactic resolution: local symbol matching only, never assume a runtime binding.
            candidates=[]
            scope=self._scope_of(caller)
            if call_name.startswith('self.') and scope:
                candidates.append(scope.rsplit('.',1)[0]+'.'+call_name[len('self.'):])
            for i in range(len(scope.split('.')) if scope else 0,-1,-1):
                prefix='.'.join(scope.split('.')[:i])
                candidates.append((prefix+'.' if prefix else '')+call_name)
            candidates.append(call_name)
            target=next((self.symbols[c] for c in candidates if c in self.symbols),None)
            if target:
                self.g.add_edge(caller,target,'python_call',self.rel,call.lineno,'syntactic_candidate',call_name)
            elif ((call_name.startswith('self.') or '.' not in call_name)
                  and call_name.split('.')[0] not in self.import_aliases
                  and call_name not in vars(builtins)):
                self.g.diagnostic('unresolved_python_call',self.rel,call.lineno,call_name)

    def _scope_of(self, caller:str)->str:
        node=self.g.nodes.get(caller)
        return node.label if node and node.kind=='symbol' else ''

    @staticmethod
    def _call_name(node:ast.AST)->str|None:
        if isinstance(node,ast.Name):return node.id
        if isinstance(node,ast.Attribute):
            left=PythonVisitor._call_name(node.value)
            if left:return left+'.'+node.attr
        return None

    def visit_Import(self,node:ast.Import)->None:
        for alias in node.names:
            self.import_aliases[alias.asname or alias.name.split('.')[0]]=alias.name
            target=_py_module_target(self.g,self.rel,alias.name)
            self._import(target,node.lineno,alias.name)

    def visit_ImportFrom(self,node:ast.ImportFrom)->None:
        module=node.module or ''
        target=_py_module_target(self.g,self.rel,module,node.level)
        self._import(target,node.lineno,'.'*node.level+module)
        for alias in node.names:
            self.import_aliases[alias.asname or alias.name]=(module+'.' if module else '')+alias.name
            # `from pkg import child` can load a child submodule; record that edge
            # separately when the corresponding local source file exists.
            if alias.name == '*':
                continue
            candidate = _py_module_target(self.g,self.rel,
                         (module+'.' if module else '')+alias.name,node.level)
            if candidate and candidate != target:
                self._import(candidate,node.lineno,'.'*node.level+(module+'.' if module else '')+alias.name)

    def _import(self,target:str|None,line:int,module:str)->None:
        if target:
            self.g.add_node(f'file:{target}','file',target,1,target)
            self.g.add_edge(f'file:{self.rel}',f'file:{target}','python_import',self.rel,line,'resolved_path',module)
        else:
            # External module imports are unknown, not necessarily errors.
            self.g.diagnostic('external_or_unresolved_python_import',self.rel,line,module)

    def _definition(self,node:ast.AST)->None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self,node:ast.ClassDef)->None:self._definition(node)
    def visit_FunctionDef(self,node:ast.FunctionDef)->None:self._definition(node)
    def visit_AsyncFunctionDef(self,node:ast.AsyncFunctionDef)->None:self._definition(node)

    def visit_Call(self,node:ast.Call)->None:
        qual='.'.join(self.stack)
        sid=self.symbols.get(qual) if qual else None
        if sid:self.pending.append((sid,node))
        self.generic_visit(node)


def _python(g:Graph,rel:str,body:str)->None:
    try:
        tree=ast.parse(body,filename=rel)
    except SyntaxError as exc:
        g.diagnostic('python_syntax_error',rel,exc.lineno or 0,exc.msg)
        return
    PythonVisitor(g,rel,tree).run()


def _discover_files(root: Path, tracked_only: bool = False) -> list[Path]:
    """Prune local caches or discover the caller's staged file inventory."""
    if tracked_only:
        done = subprocess.run(
            ['git', '-C', str(root), 'ls-files', '--cached', '-z'],
            capture_output=True, check=True, timeout=30,
        )
        found = []
        for raw in done.stdout.split(b'\0'):
            if not raw:
                continue
            path = root / os.fsdecode(raw)
            if path.suffix.lower() in SUPPORTED and (path.is_file() or path.is_symlink()):
                found.append(path)
        return sorted(found)
    found = []
    for dirname, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not
                         (Path(dirname)/d).is_symlink())
        for name in sorted(files):
            path=Path(dirname)/name
            if path.suffix.lower() in SUPPORTED:
                found.append(path)
    return sorted(found)


def build(root: str | Path, tracked_only: bool = False, *,
          source_paths: frozenset[str] | None = None) -> Graph:
    root=Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f'Not a directory: {root}')
    g=Graph(root, tracked_only=tracked_only, _source_paths=source_paths)
    for path in g._source_files():
        rel=path.relative_to(root)
        if source_paths is not None and (not path.is_file() or path.resolve() != path):
            raise ValueError(f'Pinned source is missing or not a regular file: {rel.as_posix()}')
        if path.is_symlink() and not path.resolve().is_relative_to(root):
            # Excluded links are not graph evidence, but preserve their literal
            # target identity to detect meaningful changes during freshness.
            target_digest = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
            g.diagnostic('external_symlink',rel.as_posix(),0,target_digest)
            continue
        body=_read_source(g,path)
        if body is None:continue
        rel=path.relative_to(root).as_posix()
        ext=path.suffix.lower()
        if ext=='.py':_python(g,rel,body)
        elif ext=='.md':_markdown(g,rel,body)
        elif ext=='.lean':_lean(g,rel,body)
        elif ext in {'.yml','.yaml'}:_workflow(g,rel,body)
    # Report edge destinations that refer to files which weren't indexed.
    for edge in g.edges:
        if edge.target.startswith('file:') and edge.target[5:] not in g.hashes:
            g.diagnostic('target_not_indexed',edge.path,edge.line,edge.target[5:])
    return g


def git_changed_files(root: Path, base: str, head: str = 'HEAD',
                      diff_filter: str = 'ACMRTUXB') -> list[str]:
    # NUL-terminated Git paths avoid core.quotePath's escaped display format
    # and preserve Unicode, spaces and literal newlines in filenames.
    if diff_filter not in {'ACMRTUXB', 'D'}:
        raise ValueError('Unsupported Git diff filter')
    command=['git','--no-replace-objects','-C',str(root),'diff','--no-renames','--ignore-submodules=none','--name-only','-z',
             '--diff-filter='+diff_filter,f'{base}...{head}','--']
    done=subprocess.run(command,check=True,capture_output=True,timeout=30)
    return sorted(set(os.fsdecode(p) for p in done.stdout.split(b'\0') if p))


def save(g:Graph,output:Path)->None:
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(g.to_dict(),indent=2,sort_keys=True)+'\n',encoding='utf8')
