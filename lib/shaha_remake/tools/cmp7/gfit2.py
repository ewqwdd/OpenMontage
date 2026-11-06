import sys, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit, build_A, fx_A as fx
fr=[int(x) for x in sys.argv[1].split(',')]
D=0
for f in fr:
    a=np.asarray(Image.open(f'full/{f+1:04d}.png').convert('RGB'),np.float32); L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    D=D+(hp>22).astype(np.float32)
D=kit.gblur(D,3.0); D[:150]=0; D[540:]=0
lay,st=build_A.big_layer(fr[0]); g=lay[2]
best=[]
for sx in np.arange(1.05,1.36,0.03):
  for sy in np.arange(0.98,1.36,0.04):
    for cx in range(480,560,8):
      for cy in range(330,400,6):
        m=fx.scale_about(g,sx,cx,cy,sy)>0.5
        m=m.astype(np.float32); n=m.sum()
        # normalized correlation with mean-removed D
        sc=(D*m).sum()/n - (D*(1-m)).sum()/(m.size-n)
        best.append((sc,sx,sy,cx,cy))
best.sort(reverse=True)
for b in best[:6]: print('%.4f sx %.2f sy %.2f c %d,%d'%b)
