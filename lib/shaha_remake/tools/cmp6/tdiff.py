import sys,numpy as np; from PIL import Image
d=sys.argv[1]; box=tuple(map(int,sys.argv[2].split(',')))
L=lambda p: np.asarray(Image.open(p).convert('L'),np.float32)[box[1]:box[3],box[0]:box[2]]
res=[]
for f in range(*map(int,sys.argv[3].split(':'))):
    r=np.abs(L(f'full/{f+1:04d}.png')-L(f'full/{f:04d}.png')); m=np.abs(L(f'{d}/{f:04d}.png')-L(f'{d}/{f-1:04d}.png'))
    res.append((f,r.mean(),(r>40).mean()*100,m.mean(),(m>40).mean()*100))
for x in res: print('%d ref %.1f %.2f%% | mine %.1f %.2f%%'%x)
a=np.array(res)[:,1:]; print('MEAN ref %.1f %.2f%% | mine %.1f %.2f%%'%tuple(a.mean(0)))
