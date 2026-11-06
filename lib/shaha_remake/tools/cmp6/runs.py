import sys,numpy as np; from PIL import Image
def runs(row,th):
    b=row>th; out=[]; x=0
    while x<len(b):
        if b[x]:
            s=x
            while x<len(b) and b[x]: x+=1
            out.append((s,x-s))
        x+=1
    return out
def edgew(row):
    # mean 10-90% rise width over edges
    ws=[]
    lo,hi=row.min(),row.max()
    for x in range(2,len(row)-12):
        a,b=row[x],row[x+1]
    return 0
f=int(sys.argv[1]); dirn=sys.argv[2] if len(sys.argv)>2 else 'out/build_A'
for y in map(int,sys.argv[3].split(',')):
  for nm,p in (('ref',f'full/{f+1:04d}.png'),('mine',f'{dirn}/{f:04d}.png')):
    a=np.asarray(Image.open(p).convert('L'),np.float32)[y-3:y+4].mean(0)
    rr=runs(a,0.5*(a.max()+40))
    print(nm,y,[(s,w) for s,w in rr if w>2])
