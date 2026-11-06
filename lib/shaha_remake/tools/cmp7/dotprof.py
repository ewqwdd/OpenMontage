import sys, os, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit
MD=os.environ.get('MD','out/final2')
y0,y1=int(os.environ.get('Y0',150)),int(os.environ.get('Y1',560)); CW=int(os.environ.get('CW',40))
def dots(p):
    a=np.asarray(Image.open(p).convert('RGB'),np.float32)
    L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    grey=(a[...,0]-a[...,1])<35
    d=(hp>22)&grey
    d[:y0]=0; d[y1:]=0
    return d
for f in map(int,sys.argv[1:]):
    for nm,p in (('ref ',f'full/{f+1:04d}.png'),('mine',f'{MD}/{f:04d}.png')):
        d=dots(p); c=d.reshape(d.shape[0],-1,CW).sum((0,2))
        print(f,nm,' '.join('%3d'%v for v in c))
    # vertical profile
    for nm,p in (('ref ',f'full/{f+1:04d}.png'),('mine',f'{MD}/{f:04d}.png')):
        d=dots(p)[:, 40:920]; c=d[y0:y1].reshape(-1,20,d.shape[1]).sum((1,2))
        print('   rows',nm,' '.join('%3d'%v for v in c))
