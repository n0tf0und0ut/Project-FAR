"""Minimal MCP stdio bridge for read-only FARGraph tools.

This supports the MCP core initialization and tools endpoints. It deliberately has
no filesystem write tool, and accepts only paths under the configured root.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import build

PROTOCOL='2025-11-25'

def specs():
    return [
      {'name':'fargraph_status','description':'Check index freshness against current source hashes.',
       'inputSchema':{'type':'object','properties':{},'additionalProperties':False}},
      {'name':'fargraph_stats','description':'Report the indexed file, edge, and diagnostic coverage; advisory only.',
       'inputSchema':{'type':'object','properties':{},'additionalProperties':False}},
      {'name':'fargraph_impact','description':'Trace potential upstream impact with source and line evidence; not a completeness proof.',
       'inputSchema':{'type':'object','properties':{'files':{'type':'array','items':{'type':'string'}},'depth':{'type':'integer','minimum':1,'maximum':100}},'required':['files']}},
      {'name':'fargraph_trace','description':'Find evidence-bounded path between indexed node IDs.',
       'inputSchema':{'type':'object','properties':{'source':{'type':'string'},'target':{'type':'string'},'depth':{'type':'integer','minimum':1,'maximum':100}},'required':['source','target']}},
      {'name':'fargraph_refresh','description':'Rebuild the graph after repository file changes.',
       'inputSchema':{'type':'object','properties':{},'additionalProperties':False}},
    ]

class Server:
    def __init__(self,root:str):
        self.root=Path(root).expanduser().resolve()
        self.graph=build(self.root)

    def handle(self,msg:dict) -> dict|None:
        if not isinstance(msg,dict):return None
        if 'id' not in msg:return None  # notification
        mid=msg['id'];method=msg.get('method','')
        if method=='initialize':
            # Offer only the version we implement; never echo an unsupported version.
            return {'jsonrpc':'2.0','id':mid,'result':{'protocolVersion':PROTOCOL,
                'capabilities':{'tools':{'listChanged':False}},
                'serverInfo':{'name':'fargraph-prototype','version':'0.1.0'}}}
        if method=='ping':return {'jsonrpc':'2.0','id':mid,'result':{}}
        if method=='tools/list':return {'jsonrpc':'2.0','id':mid,'result':{'tools':specs()}}
        if method!='tools/call':
            return {'jsonrpc':'2.0','id':mid,'error':{'code':-32601,'message':'Method not found'}}
        params=msg.get('params') or {}
        name=params.get('name')
        a=params.get('arguments') or {}
        try:
            if name=='fargraph_status':result=self.graph.freshness()
            elif name=='fargraph_stats':result={**self.graph.stats(),'freshness':self.graph.freshness()}
            elif name=='fargraph_refresh':
                self.graph=build(self.root)
                result=self.graph.stats()
            elif name=='fargraph_impact':
                if not self.graph.freshness()['fresh']:
                    raise ValueError('Index is stale; call fargraph_refresh before impact analysis')
                if not isinstance(a.get('files'),list) or any(not isinstance(p,str) for p in a['files']):
                    raise ValueError('files must be a list of paths')
                depth=a.get('depth',8)
                if not isinstance(depth,int) or not 1<=depth<=100:raise ValueError('Invalid depth')
                result=self.graph.impact(a['files'],depth)
            elif name=='fargraph_trace':
                if not self.graph.freshness()['fresh']:
                    raise ValueError('Index is stale; call fargraph_refresh before tracing')
                if not isinstance(a.get('source'),str) or not isinstance(a.get('target'),str):
                    raise ValueError('source and target must be node IDs')
                depth=a.get('depth',10)
                if not isinstance(depth,int) or not 1<=depth<=100:raise ValueError('Invalid depth')
                result=self.graph.trace(a['source'],a['target'],depth)
            else:raise ValueError('Unknown tool')
            return {'jsonrpc':'2.0','id':mid,'result':{'content':[{'type':'text','text':json.dumps(result,sort_keys=True)}],'isError':False}}
        except (ValueError,OSError) as exc:
            return {'jsonrpc':'2.0','id':mid,'result':{'content':[{'type':'text','text':str(exc)}],'isError':True}}


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description='Read-only FARGraph MCP server over stdio')
    p.add_argument('--root',required=True)
    args=p.parse_args(argv)
    try:server=Server(args.root)
    except (ValueError,OSError) as exc:
        print(str(exc),file=sys.stderr)
        return 2
    for line in sys.stdin:
        try:
            msg=json.loads(line)
            reply=server.handle(msg)
        except (ValueError,TypeError) as exc:
            reply={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply,separators=(',',':'))+'\n')
            sys.stdout.flush()
    return 0

if __name__=='__main__':raise SystemExit(main())
