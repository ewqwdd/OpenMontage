import sys, os, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit
def d(p,th=22):
    a=np.asarray(Image.open(p).convert('RGB'),np.float32); L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    return (hp>th)
for f in map(int,sys.argv[1:]):
    m=d(f'full/{f+1:04d}.png')[160:560,0:960].reshape(10,40,24,40).sum((1,3))
    print(f); print('\n'.join(' '.join('%3d'%v for v in r) for r in m))
