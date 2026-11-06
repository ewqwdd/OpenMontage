import sys, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit, build_A, fx_A as fx
fr=[int(x) for x in sys.argv[1].split(',')]
D=0
for f in fr:
    a=np.asarray(Image.open(f'full/{f+1:04d}.png').convert('RGB'),np.float32); L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    D=D+(hp>22).astype(np.float32)
D=kit.gblur(D,3.0); D[:150]=0; D[560:]=0
lay,st=build_A.big_layer(fr[0]); g=lay[2]
res=[]
for sx in np.arange(1.0,1.3,0.02):
  for cx in range(440,580,4):
    for sy in np.arange(1.0,1.36,0.03):
      for top in range(180,200,3):
        cy=(top-214*sy)/(1-sy) if abs(1-sy)>1e-3 else 342
        m=(fx.scale_about(g,sx,cx,cy,sy)>0.5).astype(np.float32); n=m.sum()
        res.append(((D*m).sum()/n-(D*(1-m)).sum()/(m.size-n),sx,cx,sy,top,cy))
res.sort(reverse=True)
for b in res[:5]: print('%.4f sx %.2f cx %d sy %.2f top %d cy %.0f'%b)
