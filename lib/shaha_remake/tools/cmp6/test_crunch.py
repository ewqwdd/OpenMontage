import sys; sys.path.insert(0,'.')
import numpy as np; from PIL import Image
import kit, build_A, crunch
from pathlib import Path
f0,f1=map(int,sys.argv[1].split(':')); q=int(sys.argv[2]); p=float(sys.argv[3]); amax=int(sys.argv[4])
src=Path('out/clean'); src.mkdir(parents=True,exist_ok=True)
for i in range(f0,f1):
    im=build_A.frame(i)
    if p>0: im=crunch.block_jitter(im, i*13+1, p=p, amax=amax)
    Image.fromarray(kit.to_u8(im)).save(src/f'{i:04d}.png')
crunch.codec_pass(src,'out/build_A',f0,f1,q=q)
