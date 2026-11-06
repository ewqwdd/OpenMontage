import sys, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit, build_A, fx_A as fx
def dm(f):
    a=np.asarray(Image.open(f'full/{f+1:04d}.png').convert('RGB'),np.float32); L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    return (hp>22).astype(np.float32)
base=(dm(73)+dm(74)+dm(75))/3
D=sum(np.clip(dm(f)-base,0,1) for f in (78,79,80,81))
D=kit.gblur(D,2.0); D[:160]=0; D[500:]=0; D[:,200:760]=0     # only the two ends (left Т О, right З А)
lay,st=build_A.big_layer(79); g=lay[2]
res=[]
for sx in np.arange(1.14,1.26,0.02):
  for cx in range(516,552,4):
    for sy in np.arange(1.0,1.36,0.03):
      for top in range(182,200,2):
        cy=(top-214*sy)/(1-sy) if abs(1-sy)>1e-3 else 342
        m=(fx.scale_about(g,sx,cx,cy,sy)>0.5).astype(np.float32); m[:,200:760]=0; n=m.sum()
        res.append(((D*m).sum()/n-(D*(1-m))[160:500].sum()/((1-m)[160:500].sum()),sx,cx,sy,top,cy))
res.sort(reverse=True)
for b in res[:6]: print('%.4f sx %.2f cx %d sy %.2f top %d cy %.0f'%b)
