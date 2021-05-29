"""
What follows is a failed port to pyglet. It is only marginally functional.
"""
import sys
import time
import random
import os 
import math

import pyglet
from pyglet.window import key
from pyglet.graphics import *
from pyglet.gl import * 
from pyglet.sprite import Sprite

import Image
import ImageDraw

import primitives
import data 

PYGLET_VSYNC=0
pyglet.resource.path=['data']
pyglet.resource.reindex()

WIDTH,HEIGHT=640,480
MIDX,MIDY=WIDTH/2,HEIGHT/2
w = None
keys = None
game_width,game_depth=2000,5000

show_debug=False
light_offset_vec=(48,-2)
sub_health=1000
gametick=0
tilt=0
MAX_TILT=30
MAX_SPEED=3
descent=0.0
speed=0.0
x=MIDX
depth=MIDY
light_is_on=False
thrust_on=False
last_depth_range=0
velocity=0.0
debug_text=""
font=None

sprites={}
images={}

# particle lists
bubbles=[]
trench_collide_particles=[]
current_particles=None
lightballs=[]
current_v=None

# Game Logic
sub_radius=60
trench_offset=HEIGHT/2 # where to start the trench from top of game "world"
samples=[]
lowest_sample=0
gathering=False
show_gather=False
gather_offset_vec=(65,25)
gather_radius=12
sample_load=0
MAX_LOAD=1000
boatzone=(400,200,60,60)
overall_samples=0
MAX_BATTERY=10000
battery_power=MAX_BATTERY
trench_line=[]

HUD_DEPTH=1.0
HUD_COLOR_LIGHT=(255,255,255,255)
HUD_COLOR_DARK=(200,200,200,255)

################################
# 2D Vec helpers 
################################

def pt_in_rect(p,r):
    return p[0] >= r[0] and p[0] < r[0]+r[2] and p[1] >= r[1] and p[1] < r[1]+r[3]

def vlen(v): return math.sqrt(v[0]**2+v[1]**2)

def unitize(v,s=1.0):
    l=vlen(v)
    return (v[0]/l*s,v[1]/l*s)

def vrotate(v,a):
    ar=math.radians(a)
    st = math.sin(ar)
    ct = math.cos(ar)
    return ( v[0]*ct + v[1]*st, v[1]*ct - v[0]*st)

################################
# Generate Procedural Stuff
################################
def gen_samples(game_depth):
    for i in range(game_depth):
        if trench_line[i] and random.random() < 0.05: 
            dr=float(i)/game_depth
            samples.append((trench_line[i]+random.randint(-3,5),i,\
                    random.randint(int(dr*10),10+int(dr*dr*80))))

def gen_trench(trenchimg):
    global trench_line
    imgdraw = ImageDraw.Draw(trenchimg)
    trench_line=[0 for i in range(trench_offset)] # prime initial sea
    width,height=game_width,game_depth
    last_d,v=0,0
    for i in range(height):
        if last_d < width*0.25:
            if i < 100:
                v+=(0.6-random.random())
            elif i > game_depth-100:
                v+=(0.2-random.random())
            else:
                v+=(0.51-random.random())
        else:
            v+=0.5-random.random()
            if v<-1.7: v=-1.7
            elif v > 1.7: v=1.7
        d=last_d+v
        if d < width*0.25 and i > 100: v*=-1
        if d > width*0.5 and i < game_depth-100: v*=-1
        #if d > width*0.5: d=width*0.5
        #elif d < width*0.25: d=width*0.25
        #draw_line(surf,(0,0,0,255),(width,i),(width-d,i),1)
        #imgdraw.line((width, i,width-d,i),fill=(0,0,0,255))
        trench_line.append(width-d)
        last_d=d
    del imgdraw 

################################
# Game Logic 
################################

def get_samples():
    i=lowest_sample
    top,bottom=depth-HEIGHT/2,depth+HEIGHT/2
    while samples[i][1] > top and i >0: i-=1
    start,end=i,i
    while len(samples[end])==3 and samples[end][1] < bottom and i < len(samples):
        end+=1
        if end == len(samples): break
    return samples[start:end]

def register_damage(velocity):
    global sub_health
    sub_health -= velocity 
    for i in range(random.randint(1,int(velocity)+2)):
        trench_collide_particles.append([x+sub_radius,depth,random.randint(10,20)])

def collide():
    global x,depth,speed
    if depth<HEIGHT/2: depth=HEIGHT/2
    if depth>game_depth: depth=game_depth
    if x<WIDTH/2: x=WIDTH/2
    if x+sub_radius > trench_line[int(depth)]:
        x=trench_line[int(depth)]-sub_radius
        if speed: 
            register_damage(abs(velocity))
        speed=0


def tick():
    global depth,descent,x,gametick,light_is_on,speed
    global velocity,current_v,gathering,sample_load,overall_samples
    global battery_power
    descent=math.tan(math.radians(float(tilt))) * -8.0
    cuv=unitize(current_v,0.5)
    depth += descent +cuv[1]
    x += speed + cuv[0]
    collide()
    velocity=math.sqrt((descent+cuv[1])**2+(speed+cuv[0])**2)
    light_is_on = depth > 2000

    # Add bubbles
    if thrust_on or \
       (descent > 0 and gametick%(velocity < 0.1 and 20 or int(10/velocity*2+7))==0 ):
        if thrust_on and random.random()>0.4 or random.random()>0.5:
            bubbles.append([Sprite(images["bubble"],x,depth),random.random()*20+30])

    # have current waver
    current_v=unitize((current_v[0]+random.randint(-5,5),
                       current_v[1]+random.randint(-5,5)),100.0)
    # Move current bubbles
    for cp in current_particles:
        cp[0]=(cp[0][0]+cp[1][0],cp[0][1]+cp[1][1]) 
        if cp[0][0] < 0: cp[0]=(WIDTH,cp[0][1])
        elif cp[0][0] > WIDTH: cp[0]=(0,cp[0][1])
        if cp[0][1] < 0: cp[0]=(cp[0][0],HEIGHT)
        elif cp[0][1] > HEIGHT: cp[0] = (cp[0][0],0)
        cuv=unitize(current_v,5.0)
        cp[1]=unitize((cuv[0]+cp[1][0]+random.randint(-3,3),
                       cuv[1]+cp[1][1]+random.randint(-3,3)),2.0)

    if thrust_on:
        battery_power-=2
    if light_is_on:
        battery_power-=0.5

    if gathering:
        gv=vrotate(gather_offset_vec,tilt) 
        sg=0 
        for s in get_samples():
            c=gv[0]+x,gv[1]+depth     
            if vlen((c[0]-s[0],c[1]-s[1])) < gather_radius:
                gather_sample(s)
                sg+=1
        gathering=False
    # Update Debug Text
    debug("Depth: %.1f Tilt: %.1f Light: %s Trenchline: %i X: %i Velocity: %f"%\
            (depth,tilt,light_is_on and "On" or "Off",trench_line[int(depth)],x,velocity))

    if pt_in_rect((x,depth),boatzone): 
        if sample_load > 5:
            sample_load-=5
            overall_samples+=5
        else:
            overall_samples+=sample_load
            sample_load=0
        if battery_power < MAX_BATTERY: battery_power += 10 

    gametick+=1

def gather_sample(s):
    global sample_load
    if sample_load > MAX_LOAD: return
    if sample_load+s[2] > MAX_LOAD:
        sample_load = MAX_LOAD 
    else: sample_load+=s[2]
    samples.remove(s)

################################
# Render Logic 
################################

def debug(txt):
    global debug_txt
    debug_txt=txt

def render_gauge(pos,radius,min,max,v,units):
    draw_circle(HUD_DEPTH,HUD_COLOR_LIGHT,pos,radius,1)
    for i in range(10):
        ptr = vrotate((radius/8,0),i*31.5-45)
        draw_line(HUD_DEPTH,HUD_COLOR_LIGHT,(pos[0]+ptr[0]*5,pos[1]+ptr[1]*5),
                         (pos[0]+ptr[0]*7,pos[1]+ptr[1]*7))
    pr_ratio = float(v-min)/max 
    ptr = vrotate((radius*0.9,0),(pr_ratio*-270)-135)
    draw_line(HUD_DEPTH,HUD_COLOR_LIGHT,pos,(pos[0]+ptr[0],pos[1]+ptr[1]),3)
    pcolor=HUD_COLOR_LIGHT
   
    #surf.blit(tsurf,(pos[0]-radius+(radius*2-tsurf.get_width())/2,pos[1]+radius))

def draw_depthometer(pos):
    start=round(depth < 400 and 0 or depth-400)
    for i in range(start-start%25,start+500,25):
        if i<0: continue
        y=round((i-start)/2.0)
        if not i%100:
            if not i%200:
                #label=pyglet.text.Label("%i ft"%(i/4),
                #    font_name="Arial",font_size=11,x=pos[0],y=pos[1])
                #label.valign="center"
                #label.draw()
                draw_line(HUD_DEPTH,HUD_COLOR_LIGHT,
                          (pos[0],pos[1]-y),(pos[0]+40,pos[1]-y),1)
            else:
                draw_line(HUD_DEPTH,HUD_COLOR_DARK,
                          (pos[0]+10,pos[1]-y),(pos[0]+40,pos[1]-y),1)
        else:
            draw_line(HUD_DEPTH,HUD_COLOR_DARK,
                          (pos[0]+20,pos[1]-y),(pos[0]+40,pos[1]-y),1)
    dy=round((depth-start)/2.0)
    draw_line(HUD_DEPTH,HUD_COLOR_DARK,
                (pos[0]+40,pos[1]-dy),(pos[0]+50,pos[1]-dy),1)

def render():
    global tilt
    top=HEIGHT
    left=0.0
    sig_noise=(vlen((x,depth))/float(vlen((game_width,game_depth))))**2
    sig_strength=1.0-sig_noise

    glClear(GL_COLOR_BUFFER_BIT)
    glLoadIdentity()
    curdepth=0.0

    # calc signal noise
    # Draw Water Gradient
    draw_water((0,0,int(255*(1.0-(depth-WIDTH/2)/game_depth)),255),(0,0,int(255*(1.0-(depth+WIDTH/2)/game_depth)),255))

    # Draw "current particles"
    for cp in current_particles:
        draw_circle(curdepth,(100,100,255,cp[2]*4+180),cp[0],cp[2]/2.0)
    curdepth+=0.01

    # Draw stuff in world coords 
    glPushMatrix()
    glTranslatef(MIDX-x,depth-MIDY,0)
    sprites["sunbeams"].draw()
    sprites["boat"].draw()

    draw_line(HUD_DEPTH,(255,255,255,255),(0,0),(100,100))
    curdepth+=0.01

    # Draw collide particles
    for cp in trench_collide_particles:
        draw_circle(curdepth,(200,200,200,cp[2]*4),(cp[0]-left,cp[1]-top),cp[2]/3)
        cp[2]-=1
        cp[0]+=random.randint(-3,2)
        cp[1]+=random.randint(-2,2)
        if not cp[2]:
            trench_collide_particles.remove(cp)

    # Draw bubbles
    for b in bubbles:
        b[0].draw()
        b[0].set_position(b[0].x+3-random.random()*6,b[0].y+random.random()*2+2)
        b[0].opacity=b[1]*4
        b[1] -= 1
        if b[1] <= 0: bubbles.remove(b)  
    curdepth+=0.01

    # Draw trench
    #fxsurf.blit(trench_surf,(0,0),(left,top-trench_offset,WIDTH,HEIGHT))
    curdepth+=0.01

    # Draw (visible) Samples
    for s in get_samples():
        draw_circle(curdepth,(int(128*s[2]/100.0)+127,0,0,128),
                                   (s[0]-left,s[1]-top),3+int(s[2]/100.0*6))
    glPopMatrix()
    
    # Draw stuff in "sub coords" 
    # Draw Light Column 
    if light_is_on:
        glPushMatrix()
        glTranslatef(MIDX,MIDY,0)
        glRotatef(tilt,0,0,1)
        for lb in lightballs:
            lb.draw()
        glPopMatrix()
    curdepth+=0.01

    # Draw Sub
    if not show_gather:
        spr=sprites["robosub"]
        spr.rotation=-tilt
        sprites["robosub"].draw()
    else:
        spr=sprites["robosub2"]
        spr.rotation=-tilt
        sprites["robosub2"].draw()
    #debug collide

    # Add Signal "distortion" fuzz if appropriate
    if sig_strength < 0.8:
        for i in range(random.randint(0,round(sig_noise**2*10))):
            rh=random.randint(0,int(sig_noise**2*10))
            #fxsurf.blit(fuzz_surf,(0,random.randint(0,HEIGHT)),
            #        (0,random.randint(0,HEIGHT-rh),WIDTH,rh))
  
    # do blackout
    depth_range=depth-depth%(game_depth/32)
    bo=sprites["blackout"]
    bo.scale=(1.0-depth/game_depth)*2.0+1.0
    bo.opacity=int((depth/game_depth)*255)
    bo.draw()

    # Draw HUD
    draw_depthometer((WIDTH-100,0.0)) 
    render_gauge((WIDTH-40,340),30,0,4,velocity," ft/s")

    #screen.blit(fxsurf,(0,0)) 
    draw_rect(HUD_DEPTH,HUD_COLOR_LIGHT,(10,10,20,100),1)
    draw_rect(HUD_DEPTH,HUD_COLOR_LIGHT,(10,10+(100-sub_health/10),20,sub_health/10))

    # Debug
    if show_debug:
        label=pyglet.text.Label(debug_text,font_name="Arial",font_size=11,x=0,y=0)
        label.valign="center"
        label.draw()

    if sample_load:
        slh=float(sample_load)/MAX_LOAD*96
        draw_rect(HUD_DEPTH,HUD_COLOR_LIGHT,(12,120+96-slh,16,slh))
    draw_rect(HUD_DEPTH,HUD_COLOR_LIGHT,(200,10,200,10),1)
    draw_rect(HUD_DEPTH,HUD_COLOR_LIGHT,(200,12,float(battery_power)/MAX_BATTERY*200,6))

    for i in range(10):
        color= i <= sig_strength*10 and HUD_COLOR_LIGHT or HUD_COLOR_DARK 
        draw_line(HUD_DEPTH,color,(200+i*10,45),(200+i*10,45-i*2))

################################
# Pygame Adapters 
################################

def draw_line(depth,color,p1,p2,width=1):
    p=primitives.Line(p1,p2,z=depth,color=color,stroke=width)
    p.render()

def draw_rect(depth,color,rect,width=0):
    p=primitives.Polygon([(rect[0],rect[1]),
                          (rect[0]+rect[2],rect[1]),
                          (rect[0]+rect[2],rect[1]+rect[3]),
                          (rect[0],rect[1]+rect[3])],
                          z=depth,color=color,stroke=width)
    p.render()

def draw_circle(depth,color,p,radius,width=1):
    c=primitives.Circle(x=p[0],y=p[1],z=depth,width=radius*2,color=color,stroke=width)
    c.render()

def draw_water(bottom_color,top_color):
    glBegin(GL_QUADS)
    glColor4f(*bottom_color)
    glVertex3f(0.0,0.0,0.0) 
    glVertex3f(WIDTH,0.0,0.0) 
    glColor4f(*top_color)
    glVertex3f(WIDTH,HEIGHT,0.0) 
    glVertex3f(0.0,HEIGHT,0.0) 
    glEnd()

def draw_tex_face(tex,texrect,rect,depth=0):
    glBindTexture(GL_TEXTURE_2D,tex.id)
    glBegin(GL_QUADS)
    glTexCoord2f(texrect[0],texrect[1] )
    glVertex3f(rect[0], rect[1], depth)
    glTexCoord2f(texrect[0]+texrect[2], texrect[1])
    glVertex3f( rect[0]+rect[2],rect[1], depth)
    glTexCoord2f(texrect[0]+texrect[2],texrect[1]+texrect[3]) 
    glVertex3f( rect[0]+rect[2], rect[1]+rect[3],  depth)
    glTexCoord2f(texrect[0],texrect[1]+texrect[3])
    glVertex3f(rect[0], rect[1]+rect[3],depth)
    glEnd()	

################################
# Event Handlers 
################################

def update(dt):
    checkKeys()
    tick()

def on_draw():
    render() 
 
def checkKeys():
    global tilt,speed,light_is_on,thrust_on,show_gather,gathering,show_debug
    if keys[key.Q]:
        sys.exit()      
    if keys[key.DOWN]:
        if tilt > 0-MAX_TILT: tilt -= 0.4
    if keys[key.UP]:
        if tilt < MAX_TILT: tilt+=0.4 
    if keys[key.LEFT]:
        if speed > 0-MAX_SPEED: speed -= 0.2
    if keys[key.RIGHT]:
        if speed < MAX_SPEED: speed += 0.2
    show_debug=keys[key.D]
    if not keys[key.SPACE]:
        if show_gather and sample_load<MAX_LOAD: gathering=True
        show_gather=False
    else: show_gather=True
    thrust_on=keys[key.LEFT] or keys[key.RIGHT]

################################
# Resource Loaders/Init 
################################

def load_resources():
    res=["water","boat","sunbeams","blackout",
         "fuzz","robosub","robosub2","bluegrad","bubble"]
    midanchor=["robosub","robosub2","bubble","bluegrad","blackout"]
    for r in res:
        images[r]=pyglet.resource.image("%s.png"%r)
        if r in midanchor:
            images[r].anchor_x = images[r].width/2
            images[r].anchor_y = images[r].height/2
        sprites[r]=Sprite(images[r],0,0)

    sprites["boat"].set_position(0,HEIGHT-sprites["boat"].height+5)
    sprites["sunbeams"].set_position(0,HEIGHT-sprites["sunbeams"].height)
    sprites["robosub"].set_position(MIDX,MIDY)
    sprites["robosub2"].set_position(MIDX,MIDY)
    sprites["blackout"].set_position(MIDX,MIDY)

    bgw=images["bluegrad"].width
    r=bgw
    for i in range(10):
        s=Sprite(images["bluegrad"],r,0)
        s.scale=i/10.0+1.0
        lightballs.append(s)
        r+=bgw*s.scale


def main():
    global keys,w,current_v,current_particles,font
    w=pyglet.window.Window(width=WIDTH,height=HEIGHT)
    keys=key.KeyStateHandler()
    w.push_handlers(keys)
    w.push_handlers(on_draw)
    font = pyglet.font.load('Arial', 11)
    #glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Init some randomized data
    current_particles= [[(random.randint(0,WIDTH),random.randint(0,HEIGHT)),(0,0),random.randint(1,4)] for i in range(30)]
    current_v=(random.randint(-30,30),random.randint(-30,30))
    load_resources()

    glClear(GL_COLOR_BUFFER_BIT)
    glLoadIdentity()
    print "generating terrain"
    trenchimg=Image.new('RGB',(game_width,game_depth),(0,0,0))
    gen_trench(trenchimg)

    print "generating samples"
    gen_samples(game_depth)
    print "running app"
    pyglet.clock.schedule(update)
    pyglet.app.run()

if __name__=="__main__":
    main()
