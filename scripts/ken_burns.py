import sys, subprocess, math, numpy as np
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
W, H, FPS, DUR = 1080, 1920, 30, 8
N = FPS*DUR
im = Image.open(src).convert("RGB")
# cover-fit to 9:16 at 2x for subpixel quality
SW, SH = W*2, H*2
s = max(SW/im.width, SH/im.height)
im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
l, t = (im.width-SW)//2, (im.height-SH)//2
im = im.crop((l, t, l+SW, t+SH))
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def blob(cx, cy, r):
    return np.exp(-(((xx-cx)/r)**2 + ((yy-cy)/r)**2))
ff = subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
    "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264","-preset","slow","-crf","16",
    "-pix_fmt","yuv420p","-movflags","+faststart",out], stdin=subprocess.PIPE)
for i in range(N):
    p = i/(N-1)
    e = 0.5-0.5*math.cos(math.pi*p)          # ease in-out
    z = 1.0 + 0.08*e                          # 1.00 -> 1.08 slow zoom
    cw, ch = SW/z, SH/z
    cx, cy = SW/2, SH/2 - 40*e                # tiny upward drift toward headline
    x0, y0 = cx-cw/2, cy-ch/2
    sx = cw/W
    f = im.transform((W,H), Image.AFFINE, (sx,0,x0, 0,sx,y0), Image.BICUBIC)
    a = np.asarray(f, dtype=np.float32)/255
    # calm warm light leaks drifting along edges
    ph = 2*math.pi*p
    L  = 0.55*blob(-60 + 160*p, 250 + 120*math.sin(ph*0.5), 520)[...,None]*np.array([1.0,0.72,0.35])
    L += 0.40*blob(W+80 - 140*p, H-380 - 160*p, 600)[...,None]*np.array([1.0,0.55,0.30])
    L += 0.18*blob(W*0.8, -100 + 60*math.sin(ph), 450)[...,None]*np.array([1.0,0.9,0.6])
    fade = min(1, i/(FPS*1.0), (N-1-i)/(FPS*1.0))   # leaks breathe in/out
    L *= (0.55 + 0.45*fade)*(0.85 + 0.15*math.sin(ph*1.3))
    a = 1-(1-a)*(1-np.clip(L,0,1))            # screen blend
    ff.stdin.write((np.clip(a,0,1)*255+0.5).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
