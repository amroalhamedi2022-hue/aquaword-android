#!/usr/bin/env python3
"""Produce AquaWord-owned PNG icons in five Android densities; no Microsoft marks."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]/'branding/icons'
DENSITIES={'mipmap-mdpi':48,'mipmap-hdpi':72,'mipmap-xhdpi':96,'mipmap-xxhdpi':144,'mipmap-xxxhdpi':192}

def make(size):
    n=max(512,size*4)
    im=Image.new('RGBA',(n,n))
    px=im.load()
    for y in range(n):
        for x in range(n):
            t=(x+y)/(2*n)
            px[x,y]=(int(9+17*t),int(67+124*t),int(122+84*t),255)
    bubble=Image.new('RGBA',(n,n),(0,0,0,0))
    d=ImageDraw.Draw(bubble)
    for cx,cy,r,a in [(.78,.2,.23,42),(.19,.76,.31,35),(.62,.87,.17,75),(.1,.08,.18,46)]:
        X,Y,R=int(cx*n),int(cy*n),int(r*n)
        d.ellipse((X-R,Y-R,X+R,Y+R),fill=(175,255,255,a))
    im=Image.alpha_composite(im,bubble.filter(ImageFilter.GaussianBlur(n/30)))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((int(.26*n),int(.16*n),int(.73*n),int(.82*n)),radius=int(.065*n),fill=(247,254,255,242))
    d.polygon([(int(.60*n),int(.16*n)),(int(.73*n),int(.31*n)),(int(.60*n),int(.31*n))],fill=(191,226,234,255))
    d.arc((int(.335*n),int(.37*n),int(.70*n),int(.70*n)),start=45,end=310,fill=(0,153,177,255),width=int(.06*n))
    d.line([(int(.37*n),int(.73*n)),(int(.62*n),int(.73*n))],fill=(69,174,194,255),width=int(.023*n))
    return im.resize((size,size),Image.Resampling.LANCZOS).convert('RGBA')

def generate():
    for name,size in DENSITIES.items():
        path=ROOT/name/'aquaword_launcher.png'
        path.parent.mkdir(parents=True,exist_ok=True)
        make(size).save(path)
        print(path)

if __name__=='__main__':
    generate()
