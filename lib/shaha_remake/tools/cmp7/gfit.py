import sys, numpy as np
sys.path.insert(0,'.'); import kit, build_A, fx_A as fx
for i in (76,79,82):
    lay,st=build_A.big_layer(i); g=lay[2]>0.5
    ys,xs=np.nonzero(g); print(i,'glyph x %d-%d y %d-%d'%(xs.min(),xs.max(),ys.min(),ys.max()), 'centre',build_A._centre(st[3]))
