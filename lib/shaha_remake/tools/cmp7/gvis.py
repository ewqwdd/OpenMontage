"""ghost visibility map of the reference dot ghost 76-82: dot density / ghost coverage, 20 px cells, smoothed."""
import sys, json, numpy as np; from PIL import Image
sys.path.insert(0,'.'); import kit, build_A, fx_A as fx
C=20
def dots(f):
    a=np.asarray(Image.open(f'full/{f+1:04d}.png').convert('RGB'),np.float32); L=a.mean(-1); hp=L-kit.gblur(L,2.0)
    return (hp>22).astype(np.float32)
def cells(m): return m.reshape(kit.H//C,C,kit.W//C,C).mean((1,3))
base=cells((dots(73)+dots(74)+dots(75))/3)
GEO=tuple(build_A.GHOST['geo'])
gm=build_A.ghost_mask()
cov=cells(gm)
out={}
for f in range(76,83):
    d=np.clip(cells(dots(f))-base,0,None)
    w=np.clip(cov,0,1)
    # normalised convolution: smooth density and coverage separately
    def sm(a): return kit.gblur(np.repeat(np.repeat(a,C,0),C,1),25.0)[C//2::C,C//2::C]
    v=sm(d*w)/np.maximum(sm(w*w),1e-3)
    v[sm(w)<0.02]=0
    out[f]=v
k=np.percentile(np.concatenate([out[f][cov>0.3] for f in (78,79,80,81)]),95)
print('k (dot px per ghost px at full vis) %.3f'%k)
js={}
for f,v in out.items():
    v=np.clip(v/k,0,1.2); js[f]=np.round(v,2).tolist()
    print(f); 
    for r in v[7:28]: print(''.join(' .:-=+*#%@'[min(9,int(x*8))] for x in r))
json.dump({'cell':C,'geo':GEO,'k':float(k),'vis':js},open('spec/ghost_vis_A.json','w'))
