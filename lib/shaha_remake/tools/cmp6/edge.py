import sys,numpy as np; from PIL import Image
def prof(p,box):
    a=np.asarray(Image.open(p).convert('L'),np.float32)[box[1]:box[3],box[0]:box[2]]
    lo,hi=np.percentile(a,8),np.percentile(a,97)
    ws=[];unders=[]
    for row in a:
        n=(row-lo)/(hi-lo)
        for x in range(8,len(n)-8):
            if n[x-1]<0.5<=n[x]:   # rising edge
                seg=n[x-8:x+8]
                i20=np.argmax(seg>0.2); i80=np.argmax(seg>0.8)
                if seg[i80]>0.8 and seg[:i20].size>0: ws.append(i80-i20); unders.append(seg[:6].min())
    return np.mean(ws),np.median(ws),np.mean(unders),lo,hi
box=tuple(map(int,sys.argv[2].split(',')))
for f in map(int,sys.argv[3].split(',')):
    r=prof(f'full/{f+1:04d}.png',box); m=prof(f'{sys.argv[1]}/{f:04d}.png',box)
    print(f,'ref w=%.2f med=%d under=%.2f lo=%.0f hi=%.0f'%r,'| mine w=%.2f med=%d under=%.2f lo=%.0f hi=%.0f'%m)
