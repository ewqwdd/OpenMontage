import sys, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit, build_A, fx_A as fx
def dm(f):
    a=np.asarray(Image.open(f'full/{f+1:04d}.png').convert('RGB'),np.float32); L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    return (hp>22).astype(np.float32)
base=(dm(73)+dm(74)+dm(75))/3
D=sum(np.clip(dm(f)-base,0,1) for f in (78,79,80,81))
D=kit.gblur(D,2.5); D[:160]=0; D[540:]=0; D[:,200:760]=0
lay,st=build_A.big_layer(79); g=lay[2]
def ero(m,r):
    o=m.copy()
    for dy in range(-r,r+1):
        for dx in range(-r,r+1):
            if dx*dx+dy*dy<=r*r: o&=np.roll(m,(dy,dx),(0,1))
    return o
res=[]
for sx in (1.18,1.2,1.22):
 for cx in (528,532,536):
  for sy in np.arange(1.03,1.30,0.03):
   for top in range(184,200,3):
    cy=(top-214*sy)/(1-sy)
    m0=fx.scale_about(g,sx,cx,cy,sy)>0.5
    for e in (0,3,5,7,9):
        m=(ero(m0,e) if e else m0).astype(np.float32); m[:,200:760]=0; n=m.sum()
        res.append(((D*m).sum()/n-(D*(1-m))[160:540].sum()/((1-m)[160:540].sum()),sx,cx,sy,top,cy,e))
res.sort(reverse=True)
for b in res[:8]: print('%.4f sx %.2f cx %d sy %.2f top %d cy %.0f ero %d'%b)
