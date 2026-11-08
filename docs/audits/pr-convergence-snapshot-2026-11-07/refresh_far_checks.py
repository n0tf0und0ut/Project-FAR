"""Apply a fully enumerated second authenticated connector pass to the snapshot sources.
This does not fabricate a result from a pending or unknown context.
"""
from pathlib import Path
p=Path(__file__).resolve().parent / 'build_far_manifest.py'
s=p.read_text()
updates={
625:('pending','success','success',128560572614,128563256456,128559957936),
597:('pending','success','failure',128555020265,128563321361,128548508503),
490:('missing','success','missing',None,128563324798,None),
617:('failure','failure','success',128556427771,128563280294,128549019584),
621:('pending','success','failure',128559878533,128563266793,128548869690),
623:('success','success','failure',128557127557,128563260409,128548759605),
601:('pending','success','failure',128558679093,128563310086,128548456055),
599:('success','success','failure',128556979491,128563317762,128548438298),
606:('success','success','failure',128557424121,128563306138,128548427839),
600:('success','success','failure',128555071352,128563313939,128548413639),
607:('success','success','failure',128554066166,128563301906,128548327145),
611:('success','success','failure',128553922359,128563294819,128548313604),
608:('pending','success','failure',128554207897,128563298284,128548296617),
614:('pending','success','failure',128556774232,128563290898,128548278000),
619:('success','success','failure',128554651001,128563273608,128548197499),
615:('pending','success','failure',128557578261,128563287695,128548179633),
618:('success','success','failure',128553881648,128563276731,128548168815),
616:('success','success','failure',128554625096,128563284124,128548155914),
620:('success','success','failure',128550365561,128563270302,128548056921),
622:('success','success','failure',128548999577,128563263699,128548035456),
}
start=s.index("ROWS = '''")
end=s.index("'''.strip()",start)+len("'''.strip()")
rows=s[start:end].splitlines()
newrows=[]
for line in rows:
    x=line.split()
    if x and x[0].isdigit():
        m,rep,rev,*_=updates[int(x[0])]
        x[-3:]=[m,rep,rev]
        line=' '.join(x)
    newrows.append(line)
s=s[:start]+'\n'.join(newrows)+s[end:]
start=s.index('CHECK_IDS = {')
end=s.index('\nCHECK_NAMES =',start)
block='CHECK_IDS = {\n'+''.join(f'    {n}:[{a},{b},{c}],\n' for n,(*states,a,b,c) in updates.items())+'}\n'
s=s[:start]+block+s[end:]
s=s.replace('approximately 22:38–23:25','approximately 22:38–23:40')
p.write_text(s)
print('updated rows / check IDs for',len(updates),'PRs')
