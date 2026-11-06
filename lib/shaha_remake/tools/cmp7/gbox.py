import sys, os, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit
MD=os.environ.get('MD','out/final2')
def an(p):
    a=np.asarray(Image.open(p).convert('RGB'),np.float32)
    L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    d=(hp>22)&((a[...,0]-a[...,1])<35); d[:120]=0; d[600:]=0
    red=(a[...,0]>a[...,1]+45)&(a[...,0]>80)
    ys,xs=np.nonzero(d); ry,rx=np.nonzero(red)
    q=lambda v:(np.percentile(v,0.5),np.percentile(v,99.5))
    return q(xs),q(ys),q(rx),q(ry)
for f in map(int,sys.argv[1:]):
    for nm,p in (('ref ',f'full/{f+1:04d}.png'),('mine',f'{MD}/{f:04d}.png')):
        dx,dy,rx,ry=an(p)
        print(f,nm,'dots x %.0f-%.0f y %.0f-%.0f | red x %.0f-%.0f y %.0f-%.0f'%(*dx,*dy,*rx,*ry))
