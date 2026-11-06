import sys, os, numpy as np; from PIL import Image
sys.path.insert(0,'cmp6')
MD=os.environ.get('MD','out/final2')
def ero(m,r):
    o=m.copy()
    for dy in range(-r,r+1):
        for dx in range(-r,r+1): o&=np.roll(m,(dy,dx),(0,1))
    return o
def dil(m,r):
    o=m.copy()
    for dy in range(-r,r+1):
        for dx in range(-r,r+1): o|=np.roll(m,(dy,dx),(0,1))
    return o
def box(a,r):
    o=np.zeros_like(a)
    for dy in range(-r,r+1):
        for dx in range(-r,r+1): o+=np.roll(a,(dy,dx),(0,1))
    return o/(2*r+1)**2
def load(p): return np.asarray(Image.open(p).convert('RGB'),np.float32)
bx=tuple(map(int,sys.argv[1].split(',')))
for f in map(int,sys.argv[2:]):
    for name,p in (('ref ',f'full/{f+1:04d}.png'),('mine',f'{MD}/{f:04d}.png')):
        a=load(p)[bx[1]:bx[3],bx[0]:bx[2]]; L=a.mean(-1)
        m=a.min(-1)>140; core=ero(m,3)
        hp1=L-box(L,1); hp4=box(L,1)-box(L,5)
        dv=np.abs(np.diff(L,axis=0))[core[1:]&core[:-1]].mean(); dh=np.abs(np.diff(L,axis=1))[core[:,1:]&core[:,:-1]].mean()
        # halo rings outside mask
        rings=[]; prev=m
        for r in (2,4,7,11,16,24):
            d=dil(m,r); ring=d&~prev; prev=d
            rings.append(a[ring].mean(0).round(0).astype(int).tolist())
        # inside profile: core distance 3 vs deep
        deep=ero(m,7)
        print(f"{f} {name} col={a[core].mean(0).round(0).astype(int).tolist()} deep={a[deep].mean(0).round(0).astype(int).tolist()} hp1={hp1[core].std():.1f} hp4={hp4[core].std():.1f} dv={dv:.1f} dh={dh:.1f}")
        print("        halo rings 0-2,2-4,4-7,7-11,11-16,16-24:",rings)
