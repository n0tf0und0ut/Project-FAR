"""CLI entry point for FARGraph. All output is JSON, suitable for tool adapters."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import build, git_changed_files, save, VERSION


def create_parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog='fargraph',description='Evidence-bound repository dependency intelligence')
    p.add_argument('--root',default='.',help='Repository directory to inspect')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('stats',help='Summarize indexed source and coverage')
    index=sub.add_parser('index',help='Write a reproducible graph as JSON')
    index.add_argument('--output',required=True,help='Destination outside repository recommended')
    impact=sub.add_parser('impact',help='Find potentially affected files from changed paths')
    impact.add_argument('files',nargs='*')
    impact.add_argument('--git-base',help='Include Git changes from BASE...HEAD')
    impact.add_argument('--head',default='HEAD')
    impact.add_argument('--depth',type=int,default=8)
    trace=sub.add_parser('trace',help='Find graph path between known node IDs')
    trace.add_argument('source');trace.add_argument('target')
    trace.add_argument('--depth',type=int,default=10)
    return p


def main(argv:list[str]|None=None) -> int:
    args=create_parser().parse_args(argv)
    try:
        root=Path(args.root).expanduser().resolve()
        g=build(root)
        if args.command=='stats':result=g.stats()
        elif args.command=='index':
            output=Path(args.output).expanduser().resolve()
            if output.is_relative_to(root):
                raise ValueError('For reproducibility, write the graph outside the indexed repository')
            save(g,output)
            result={'saved':str(output),**g.stats()}
        elif args.command=='impact':
            if not args.files and not args.git_base:
                raise ValueError('Provide changed files or --git-base')
            changed=args.files[:]
            if args.git_base:
                changed+=git_changed_files(root,args.git_base,args.head)
            if args.depth<1:raise ValueError('--depth must be >= 1')
            result=g.impact(changed,args.depth)
        elif args.command=='trace':
            if args.depth<1:raise ValueError('--depth must be >= 1')
            result=g.trace(args.source,args.target,args.depth)
        else:raise AssertionError(args.command)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0
    except (ValueError,OSError,RuntimeError) as exc:
        print(json.dumps({'error':str(exc),'version':VERSION}),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
