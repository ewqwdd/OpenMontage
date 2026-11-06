import sys, os; from PIL import Image, ImageDraw
# usage: MD=out/final2 pair.py out x0,y0,x1,y1 scale f1 f2 ...   (ref top row, mine bottom row)
MD=os.environ.get('MD','out/build_A')
out=sys.argv[1]; box=tuple(map(int,sys.argv[2].split(','))); sc=float(sys.argv[3]); fs=[int(x) for x in sys.argv[4:]]
w,h=int((box[2]-box[0])*sc),int((box[3]-box[1])*sc)
W=Image.new('RGB',(w*len(fs),h*2+2),(80,0,0)); d=ImageDraw.Draw(W)
rs=Image.NEAREST if sc>1 else Image.LANCZOS
for k,f in enumerate(fs):
    r=Image.open(f'full/{f+1:04d}.png').convert('RGB').crop(box).resize((w,h),rs)
    m=Image.open(f'{MD}/{f:04d}.png').convert('RGB').crop(box).resize((w,h),rs)
    W.paste(r,(k*w,0)); W.paste(m,(k*w,h+2)); d.text((k*w+4,4),f'REF {f}',fill=(255,255,0)); d.text((k*w+4,h+6),f'MINE {f}',fill=(0,255,255))
W.save(out); print(W.size)
