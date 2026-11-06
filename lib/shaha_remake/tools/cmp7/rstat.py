import sys, os, numpy as np; from PIL import Image
MD=os.environ.get('MD','out/final2')
exec(open('cmp7/wstat.py').read().split("bx=tuple")[0].split("MD=")[0])
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
for f in map(int,sys.argv[1:]):
    for nm,p in (('ref ',f'full/{f+1:04d}.png'),('mine',f'{MD}/{f:04d}.png')):
        a=np.asarray(Image.open(p).convert('RGB'),np.float32); L=a[...,0]
        m=(a[...,0]>a[...,1]+45)&(a[...,0]>80); core=ero(m,4)
        hp1=L-box(L,1); hp4=box(L,1)-box(L,5)
        dv=np.abs(np.diff(L,axis=0))[core[1:]&core[:-1]].mean(); dh=np.abs(np.diff(L,axis=1))[core[:,1:]&core[:,:-1]].mean()
        print(f,nm,'col',a[core].mean(0).round(0).astype(int).tolist(),'R hp1 %.1f hp4 %.1f dv %.1f dh %.1f'%(hp1[core].std(),hp4[core].std(),dv,dh))
