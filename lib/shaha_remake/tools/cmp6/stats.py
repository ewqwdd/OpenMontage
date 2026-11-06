import sys, numpy as np; from PIL import Image
def ero(m,r):
    o=m.copy()
    for dy in range(-r,r+1):
        for dx in range(-r,r+1): o&=np.roll(m,(dy,dx),(0,1))
    return o
def box(a,r):
    o=np.zeros_like(a)
    for dy in range(-r,r+1):
        for dx in range(-r,r+1): o+=np.roll(a,(dy,dx),(0,1))
    return o/(2*r+1)**2
def load(p): return np.asarray(Image.open(p).convert('RGB'),np.float32)
for f in map(int,sys.argv[1:]):
    out=[]
    for name,p in (('ref',f'full/{f+1:04d}.png'),('mine',f'out/build_A/{f:04d}.png')):
        a=load(p); R,G,B=a[...,0],a[...,1],a[...,2]
        red=(R>G+45)&(R>80); wht=(a.min(-1)>150)
        m=red if red.sum()>wht.sum() else wht

        core=ero(m,3)
        hp=a.mean(-1)-box(a.mean(-1),2)
        out.append(f"{name}: n={m.sum():6d} col={a[core].mean(0).round(0)} p90={np.percentile(a[core].mean(-1),90):.0f} hf_std={hp[core].std():.1f}")
    print(f, ' | '.join(out))
