import sys, os, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit
MD=os.environ.get('MD','out/final2'); x0,x1=map(int,sys.argv[1].split(','))
def d(p):
    a=np.asarray(Image.open(p).convert('RGB'),np.float32); L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    return ((hp>22)&((a[...,0]-a[...,1])<35))[:,x0:x1]
for f in map(int,sys.argv[2:]):
    for nm,p in (('ref ',f'full/{f+1:04d}.png'),('mine',f'{MD}/{f:04d}.png')):
        c=d(p)[150:570].reshape(-1,10,x1-x0).sum((1,2)); print(f,nm,''.join('%4d'%v for v in c))
