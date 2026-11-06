import sys, os, numpy as np; from PIL import Image
MD=os.environ.get('MD','out/final2'); y0,y1=map(int,sys.argv[1].split(','))
for f in map(int,sys.argv[2:]):
    for nm,p in (('ref ',f'full/{f+1:04d}.png'),('mine',f'{MD}/{f:04d}.png')):
        L=np.asarray(Image.open(p).convert('L'),np.float32)[y0:y1]
        rl=[];cov=[]
        for th in (100,150,200):
            m=L>th; cov.append(m.mean()*100)
            d=np.diff(m.astype(int),axis=1); n=(d==1).sum()
            rl.append(m.sum()/max(n,1))
        print(f,nm,'cover%% >100/150/200: %.1f %.1f %.1f  mean run %.1f %.1f %.1f'%(*cov,*rl))
