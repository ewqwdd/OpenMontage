import sys; sys.path.insert(0,'.')
import numpy as np; from PIL import Image
import kit, build_A as b, fx_A as fx
import importlib
sys.argv=sys.argv
exec(open('cmp6/edge.py').read().split('box=tuple')[0])
f=int(sys.argv[1]); kind=sys.argv[2]
st=b._state(b.BIG,f); f0,f1,text,bbox,col,k_,wt=st
for soft in tuple(map(float,sys.argv[3].split(','))):
  for sharp in tuple(map(float,sys.argv[4].split(','))):
    for bold in ((1,1.5),):
        lay=fx.text_layer(text,bbox,col,f*7919,weight=wt,kind=kind,tracking=b.TRACK,bold=bold[0],bold_gain=bold[1],
            streak=(0.06,0.03),grain_h=0.05 if kind=='red' else 0.02,grain_f=0.07 if kind=='red' else 0.006,soft=soft,steps=True,sharp=sharp,
            **({'halo':((28,20,50),10,0.9),'red_ring':True} if kind=='red' else {}))
        img=kit.over_img(b.bg(f).copy(),*lay[:2])
        Image.fromarray(kit.to_u8(img)).save('/tmp/_sw.png') if False else Image.fromarray(kit.to_u8(img)).save('cmp6/_sw.png')
        w,med,u,lo,hi=prof('cmp6/_sw.png',(345,230,615,470))
        print(kind,f,'soft',soft,'sharp',sharp,'bold',bold,'w=%.2f under=%.2f lo=%.0f hi=%.0f'%(w,u,lo,hi))
