"""Organic Code at its finest.. er worst -nb
Copyright (c) <year> <copyright holders>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions: 
The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

~~~~~~~~~

In other words... do what you like with this mass of hackery,
although please if you decide to capitalize on it, send me some
beer and a free copy of your product (inside a brand new Audi RS8
with chrome rims, black leather, and a gps navigation system).

See more hackery or contact me:
http://nikolajbaer.us

PyWeek 6 is dead. Long Live Pyweek 6!

"""
import sys
import time
import random
import os 
import math
import pygame
import data 
WIDTH,HEIGHT=640,480
TICK = pygame.USEREVENT + 1 
   
# Increase the game_depth for true deep sea fun! 
game_width,game_depth=2000,5000

NO_SOUND=False
music=[]
game_over=None
game_over_screens={}
show_debug,show_help,show_controls=False,False,False
light_offset_vec=(48,-2)
MAX_HEALTH=100
sub_health=MAX_HEALTH
gametick=0
tilt=0
MAX_TILT=35
MAX_SPEED=4
descent=0.0
speed=0.0
x=WIDTH/2
depth=HEIGHT/2
light_is_on=False
thrust_on=False
last_depth_range=0
velocity=0.0

first_damage=False
first_low_signal=False

# particle lists
bubbles=[]
trench_collide_particles=[]
current_particles=[[(random.randint(0,WIDTH),random.randint(0,HEIGHT)),(0,0),random.randint(1,4)] for i in range(30)]
current_v=(random.randint(-30,30),random.randint(-30,30))

# Game Logic
sub_radius=60
trench_offset=HEIGHT/2 # where to start the trench from top of game "world"
trench_line=[0 for i in range(trench_offset)] # prime initial sea
samples=[]
lowest_sample=0
gathering=False
show_gather=False
gather_offset_vec=(65,25)
gather_radius=12
sample_load=0
MAX_LOAD=1000
boatzone=pygame.Rect(400,200,60,60)
overall_samples=0
MAX_BATTERY=6000
battery_power=MAX_BATTERY
msg_q=[]
msg_start=0
msg_end=0

# keep track of "sample" runs to compile a samples/time ratio
# as a score
SAMPLE_RUN_START=1000
score=0
tmp_score=0
sample_run=0
sample_run_end=0
last_distance=None

def vlen(v): return math.sqrt(v[0]**2+v[1]**2)
def unitize(v,s=1.0):
    l=vlen(v)
    return (v[0]/l*s,v[1]/l*s)
def vrotate(v,a):
    ar=math.radians(a)
    st = math.sin(ar)
    ct = math.cos(ar)
    return ( v[0]*ct + v[1]*st, v[1]*ct - v[0]*st)

def gen_samples(game_depth):
    for i in range(game_depth):
        if trench_line[i] and random.random() < 0.05: 
            dr=float(i)/game_depth
            samples.append((trench_line[i]+random.randint(-3,5),i,\
                    random.randint(int(dr*10),10+int(dr*dr*80))))

def queue_msg(txt,t):
    msg_q.append((txt,t))    

def gen_fuzz(surf):
    for i in range(surf.get_width()*surf.get_height()):
        r=random.randint(0,255)
        # i think this "fades out" the edges.. like a tv screen
        alphax=int((1.0-(abs(i%WIDTH-WIDTH/2)/float(WIDTH/2))**2)*60)
        alphay=int((1.0-(abs(i/WIDTH-HEIGHT/2)/float(HEIGHT/2))**2)*60)
        alpha=alphax < alphay and alphax or alphay
        surf.set_at((i%WIDTH,i/WIDTH),(r,r,r,alpha))

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
    global sub_health,first_damage
    if not first_damage:
        queue_msg("Watch out, those trench walls can scrape up your hull!",60)
        first_damage=True
    if sub_health - velocity < MAX_HEALTH*0.2 and sub_health > MAX_HEALTH*0.2:
        queue_msg("Warning, your hull is critically damaged",50)
        queue_msg("Return to the research vessel to repair!",50)
    sub_health -= velocity 
    if sub_health <= 0:
        end_game("health")
    for i in range(random.randint(1,int(velocity)+2)):
        trench_collide_particles.append([x+sub_radius,depth,random.randint(10,20)])

def end_game(reason):
    global game_over
    game_over=reason
    #load_music_loop("endgame.mp3")

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

def debug(txt):
    global debug_txt
    debug_txt=txt

def tick():
    global depth,descent,x,gametick,light_is_on,speed
    global velocity,current_v,gathering,sample_load,overall_samples
    global battery_power,sub_health
    global score,tmp_score,last_distance,sample_run
    descent=math.tan(math.radians(float(tilt))) * -8.0
    cuv=unitize(current_v,0.5)
    depth += descent +cuv[1]
    x += speed + cuv[0]
    collide()
    velocity=math.sqrt((descent+cuv[1])**2+(speed+cuv[0])**2)
    light_is_on = depth > 2000


    if sub_health < MAX_HEALTH*0.2 or battery_power < MAX_BATTERY*0.2 or sample_load > MAX_LOAD*0.9: load_music_loop("return.mp3")
    elif depth > 3000: load_music_loop("deep.mp3")
    else: load_music_loop("surface.mp3")

    # Add bubbles
    if thrust_on or \
       (descent > 0 and gametick%(velocity < 0.1 and 20 or int(10/velocity*2+7))==0 ):
        if thrust_on and random.random()>0.4 or random.random()>0.5:
            bubbles.append([x,depth,random.random()*20+30])

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
    battery_power -= 0.5

    if battery_power + 2 > MAX_BATTERY*0.2 and battery_power - 2 < MAX_BATTERY*0.2:
        queue_msg("Warning you are critically low on batteries",50)
        queue_msg("Return to the research vessel to recharge",50)

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

    if boatzone.collidepoint(x,depth): 
        if sample_load > 5:
            sample_load-=5
            overall_samples+=5
        else:
            overall_samples+=sample_load
            sample_load=0
        if battery_power < MAX_BATTERY: battery_power += 10
        if sub_health < MAX_HEALTH: sub_health += 10
        if tmp_score > score:
            queue_msg("Congratulations, your new high score is: %0.4f"%tmp_score,50)
            score=tmp_score 
            tmp_score=0
        elif tmp_score:
            queue_msg("You got a %0.4f on that last run"%tmp_score,50)
            queue_msg("You've done better, keep trying!",50)
            tmp_score=0

    elif battery_power <= 0:
        end_game("battery") 

    dist=vlen((x,depth))
    if last_distance < SAMPLE_RUN_START and dist > SAMPLE_RUN_START:
        sample_run=gametick
    elif last_distance > SAMPLE_RUN_START and dist < SAMPLE_RUN_START:
        sample_run_end=gametick
        s=sample_load/float(sample_run_end-sample_run)
        tmp_score=s
    last_distance=dist

    if len(msg_q) and gametick: 
        global msg_start,msg_end
        if msg_start and msg_end < gametick:
            m=msg_q.pop(0)
            msg_start=0

    gametick+=1

def gather_sample(s):
    global sample_load
    if sample_load >= MAX_LOAD: return
    if sample_load < MAX_LOAD and sample_load+s[2] > MAX_LOAD:
        queue_msg("Good Job, your sub is full!",50)
        queue_msg("Head back to the research vessel to offload",50)
    if sample_load+s[2] > MAX_LOAD:
        sample_load = MAX_LOAD 
    else: sample_load+=s[2]
    samples.remove(s)

def gen_trench(surf):
    width,height=surf.get_width(),surf.get_height()
    surf.fill((0,0,0,0))
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
        pygame.draw.line(surf,(0,0,0,255),(width,i),(width-d,i),1)
        trench_line.append(width-d)
        last_d=d

def render_gauge(surf,pos,radius,min,max,v,units,gcolor):
    pygame.draw.circle(surf,gcolor,pos,radius,1)
    for i in range(10):
        ptr = vrotate((radius/8,0),i*31.5-45)
        pygame.draw.line(surf,gcolor,(pos[0]+ptr[0]*5,pos[1]+ptr[1]*5),
                         (pos[0]+ptr[0]*7,pos[1]+ptr[1]*7))
    pr_ratio = float(v-min)/max 
    ptr = vrotate((radius*0.9,0),(pr_ratio*-270)-135)
    pygame.draw.line(surf,gcolor,pos,(pos[0]+ptr[0],pos[1]+ptr[1]),3)
    pcolor=(255,255,255)
    tsurf = f1.render("%.2f%s"%(v,units),1,pcolor)
    surf.blit(tsurf,(pos[0]-radius+(radius*2-tsurf.get_width())/2,pos[1]+radius))

def draw_depthometer(surf):
    start=round(depth < 400 and 0 or depth-400)
    for i in range(start-start%25,start+500,25):
        if i<0: continue
        y=round(30+(i-start)/2.0)
        if not i%100:
            if not i%200:
                tdsurf = f1.render("%i ft"%(i/4),1,(255,255,255,200))
                tl,tt=WIDTH-tdsurf.get_width()-30,y-tdsurf.get_height()/2
                surf.blit(tdsurf,(tl,tt))
                pygame.draw.line(surf,(255,255,255,200),(WIDTH-24,y),(WIDTH-20,y),1)
            else:
                pygame.draw.line(surf,(255,255,255,200),(WIDTH-60,y),(WIDTH-20,y),1)
        else:
            pygame.draw.line(surf,(255,255,255,128),(WIDTH-50,y),(WIDTH-20,y),1)
    dy=round(30+(depth-start)/2.0)
    pygame.draw.line(surf,(128,255,128),(WIDTH-30,dy),(WIDTH-10,dy),1)

    start=round(x<400 and 0 or x-500)
    for i in range(start-start%20,start+500,20):
        if not i%200:
            tdsurf = pygame.transform.rotate(f1.render("%i ft"%(i/4),1,(255,255,255,200)),90)
            surf.blit(tdsurf,(i-start+70-tdsurf.get_width()/2,HEIGHT-35))
        else:
            pygame.draw.line(surf,(255,255,255,128),(70+i-start,HEIGHT-35),(70+i-start,HEIGHT-20),1)
    
def render():
    global tilt,first_low_signal
    top=depth-HEIGHT/2
    left=x-WIDTH/2
    # Draw Water Gradient
    fxsurf.fill((0,0,0))
    fxsurf.blit(water_surf,(0,0),(left,top,WIDTH,HEIGHT))

    sig_noise=(vlen((x,depth))/float(vlen((game_width,game_depth))))**2
    sig_strength=1.0-sig_noise

    if not first_low_signal and sig_strength < 0.3:
        queue_msg("Your signal is getting low, your sub might get finicky!",60)
        first_low_signal=True
    # Draw "current particles"
    for cp in current_particles:
        pygame.draw.circle(fxsurf,(100,100,255,cp[2]*4+180),cp[0],cp[2]/2.0)

    # Draw Light Column 
    if light_is_on:
        lov=vrotate(light_offset_vec,tilt)
        lb=(WIDTH/2.0+lov[0],HEIGHT/2.0+lov[1])
        tr=math.radians(tilt)
        lbt=(math.cos(-tr),math.sin(-tr))
        for i in range(len(lightballs)):
            fxsurf.blit(lightballs[i],
                        (lb[0]+(0.5-random.random())*2,
                         lb[1]+(0.5-random.random())*2))
            lb=((lb[0]+0.3*lbt[0]*lightballs[i].get_width()),
                (lb[1]+0.3*lbt[1]*lightballs[i].get_height()))
    # Draw bubbles
    for b in bubbles:
        pygame.draw.circle(fxsurf,(255,255,255,b[2]/100.0*100+150),
                    (b[0]-left,
                    b[1]-top),
                    b[1]<10 and 1 or b[1]/game_depth+3,1)
        b[2] -= 1
        b[0]=b[0] + 3-random.random()*6
        b[1]=b[1] - (random.random()*2+2)
        if b[2] <= 0:
            bubbles.remove(b)  

    # Draw trench
    fxsurf.blit(trench_surf,(0,0),(left,top-trench_offset,WIDTH,HEIGHT))

    # Draw (visible) Samples
    for s in get_samples():
        pygame.draw.circle(fxsurf,(int(128*s[2]/100.0)+127,0,0,128),
                                   (s[0]-left,s[1]-top),3+int(s[2]/100.0*6))


    # Draw collide particles
    for cp in trench_collide_particles:
        pygame.draw.circle(fxsurf,(200,200,200,cp[2]*4),(cp[0]-left,cp[1]-top),cp[2]/3)
        cp[2]-=1
        cp[0]+=random.randint(-3,2)
        cp[1]+=random.randint(-2,2)
        if not cp[2]:
            trench_collide_particles.remove(cp)

    # Draw Sub
    si=int(tilt)+MAX_TILT
    if si<=0:si=0
    cursubimg = show_gather and subimgs2[si] or subimgs[si]

    #debug collide
    #pygame.draw.line(fxsurf,(255,0,0),(x-left,depth-top),(trench_line[int(depth)]-left,HEIGHT/2),1)

    # Blit FX surf
    fxsurf.blit(cursubimg,(WIDTH/2.0-cursubimg.get_width()/2.0,
                           HEIGHT/2.0-cursubimg.get_height()/2.0))

     #debug gather vec
    #if show_gather:
    #    gv=vrotate(gather_offset_vec,tilt)
    #    pygame.draw.circle(fxsurf,(255,0,0),(WIDTH/2+gv[0],HEIGHT/2+gv[1]),12)

    # Add Signal "distortion" fuzz if appropriate
    if sig_strength < 0.8:
        for i in range(random.randint(0,round(sig_noise**2*10))):
            rh=random.randint(0,int(sig_noise**2*10))
            fxsurf.blit(fuzz_surf,(0,random.randint(0,HEIGHT)),
                    (0,random.randint(0,HEIGHT-rh),WIDTH,rh))
  
    # do blackout
    depth_range=depth-depth%(game_depth/32)
    if depth > game_depth*0.15:
        if depth_range != last_depth_range:
            global last_depth_range
            last_depth_range=depth_range
            blackout_surf.fill((0,0,0,255))
            mid=WIDTH/2,HEIGHT/2
            c=depth_range/float(game_depth)
            for i in range(255,-1,-1):
                pygame.draw.circle(blackout_surf,(0,0,0,i*c),mid,int(i/255.0*HEIGHT))
        fxsurf.blit(blackout_surf,(0,0)) 

    # Draw HUD
    draw_depthometer(fxsurf) 
    render_gauge(fxsurf,(WIDTH-40,340),30,0,4,velocity," ft/s",(180,180,20,200))

    screen.blit(fxsurf,(0,0)) 
 
   
    if sub_health > MAX_HEALTH*0.5: health_color=(32,255,32)
    elif sub_health > MAX_HEALTH*0.25: health_color=(255,255,32)
    else: health_color=(255,32,32)
    pygame.draw.rect(screen,(200,200,200),(10,10,20,100),1)
    pygame.draw.rect(screen,health_color,(10,10+(100-sub_health/MAX_HEALTH*100),20,sub_health/MAX_HEALTH*100))


    # Debug
    if show_debug:
        pygame.draw.rect(screen,(180,180,20),(0,0,mini_trench_surf.get_width(),mini_trench_surf.get_height()))
        screen.blit(mini_trench_surf,(0,0)) 
        pygame.draw.circle(screen,(255,0,0),(float(x)/game_width*mini_trench_surf.get_width(),
                       float(depth)/game_depth*mini_trench_surf.get_height()),2)

        tsurf = f1.render(debug_txt,1,(180,180,20))
        screen.blit(tsurf,(0,HEIGHT-tsurf.get_height()-2)) 
    # End Debug

    tsurf = f1.render("Score: %.4f"%(score),1,(180,180,20))
    screen.blit(tsurf,(10,HEIGHT-200)) 

    tsurf = f1.render("%i samples gathered"%(overall_samples),1,(180,180,20))
    screen.blit(tsurf,(10,115)) 
    sgbot=tsurf.get_height()+120
    pygame.draw.rect(screen,(180,180,20),(10,sgbot,20,100),1)

    if sample_load:
        slh=float(sample_load)/MAX_LOAD*96
        pygame.draw.rect(screen,(180,180,20),
                (12,tsurf.get_height()+120+96-slh,16,slh))
    tsurf = f1.render("%i samples in sub"%(sample_load),1,(180,180,20))
    screen.blit(tsurf,(10,sgbot+110)) 

 
    pygame.draw.rect(screen,(180,180,20),(200,10,200,10),1)
    pygame.draw.rect(screen,(180,180,20),(200,12,float(battery_power)/MAX_BATTERY*200,6))
    pygame.draw.polygon(screen,(180,180,20),
        ((412,8),(416,8),(416,10),(418,10),(418,20),(410,20),(410,10),(412,10)))

    tsurf = f1.render("Signal Strength: %.1f%%"%(sig_strength*100),1,(0,255,0))
    screen.blit(tsurf,(305,45-tsurf.get_height())) 
    for i in range(10):
        color= i <= sig_strength*10 and (0,255,0) or (100,100,100)
        pygame.draw.line(screen,color,(200+i*10,45),(200+i*10,45-i*2))


    # do shit to make ht msgs show up
    if len(msg_q):  
        global msg_start,msg_end
        if not msg_start:
            msg_start=gametick
            msg_end=gametick+msg_q[0][1]
        tsurf=f2.render(msg_q[0][0],1,(100,255,100,200))
        screen.blit(tsurf,(WIDTH/2-tsurf.get_width()/2,HEIGHT/2+180-tsurf.get_height()/2)) 

    if show_help:
        screen.blit(help_surf,((WIDTH-help_surf.get_width())/2,(HEIGHT-help_surf.get_height())/2)) 
    if show_controls:
        screen.blit(controls_surf,((WIDTH-controls_surf.get_width())/2,(HEIGHT-controls_surf.get_height())/2)) 
    
    if game_over:
        screen.blit(game_over_screens[game_over],(0,0))

def checkKeys():
    global tilt,speed,light_is_on,thrust_on,show_gather,gathering,show_debug
    global show_help,show_controls
    sig_noise=(vlen((x,depth))/float(vlen((game_width,game_depth))))**2
    sig_strength=1.0-sig_noise

    keys = pygame.key.get_pressed()
    if keys[pygame.K_q]:
        sys.exit()      

    if game_over: return

    if keys[pygame.K_DOWN]:
        if tilt > 0-MAX_TILT: tilt -= 0.4+(sig_noise*2*(0.5-random.random()))
    if keys[pygame.K_UP]:
        if tilt < MAX_TILT: tilt+=0.4+(sig_noise*2*2*(0.5-random.random()))
    if keys[pygame.K_LEFT]:
        if speed > 0-MAX_SPEED:
            speed -= 0.2+(sig_noise*2*(0.5-random.random()))
    if keys[pygame.K_RIGHT]:
        if speed < MAX_SPEED:
            speed += 0.2+(sig_noise*2*(0.5-random.random()))

    show_debug=keys[pygame.K_d]
    show_help=keys[pygame.K_h]
    show_controls=keys[pygame.K_c]

    if not keys[pygame.K_SPACE]:
        if show_gather and sample_load<MAX_LOAD: gathering=True
        show_gather=False
    else: show_gather=True
            
    thrust_on=keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]

#Surfaces
screen=None
fxsurf=None
boatimg=None
water_surf=None
sunbeams=None
trench_surf=None
mini_trench_surf=None
blackout_surf=None
subimg=None
subenvimg=None
lightimg=None
fuzz_surf=None
help_surf=None
controls_surf=None
#font
f1=None
# container of generated surfaces
lightballs=[]
subimgs=[]
subimgs2=[]

cur_musicfile=None

def load_music_loop(filename):
    if NO_SOUND: return
    global cur_musicfile
    if cur_musicfile and cur_musicfile != filename:
        pygame.mixer.music.fadeout(100)
    elif cur_musicfile == filename: return
    pygame.mixer.music.load(data.filepath(filename))
    pygame.mixer.music.play(-1)
    cur_musicfile=filename
 
def main():
    global screen,fxsurf,boatimg,water_surf
    global sunbeams,trench_surf,mini_trench_surf
    global blackout_surf,subimg,lightimg,fuzz_surf
    global f1,f2,music
    global msg_txt,help_surf,controls_surf

    pygame.init()
    size = WIDTH,HEIGHT 
    screen = pygame.display.set_mode(size)
    fxsurf = pygame.Surface(size,pygame.SRCALPHA,32)
    f1 = pygame.font.SysFont("Arial",16)
    f2 = pygame.font.SysFont("Arial",24)

    introimg=pygame.image.load(data.filepath("intro.png")).convert_alpha()
    screen.blit(introimg,(0,0))
    pygame.display.update()

    pygame.time.set_timer(TICK,50)
    
    boatimg=pygame.image.load(data.filepath("boat.png")).convert_alpha()
    water_surf = pygame.Surface((game_width,game_depth))
    inc=game_depth/250
    for i in range(250):
        water_surf.fill((0,0,255-i),(0,inc*i,game_width,inc))
    
    sunbeams=pygame.image.load(data.filepath("sunbeams.png")).convert_alpha()
    water_surf.blit(sunbeams,(0,0))
    water_surf.blit(boatimg,(300,-5))
    trench_surf = pygame.Surface((game_width,game_depth),pygame.SRCALPHA,32)
    gen_trench(trench_surf)
   
    help_surf=pygame.image.load(data.filepath("help.png")).convert_alpha()
    controls_surf=pygame.image.load(data.filepath("controls.png")).convert_alpha()

    gen_samples(game_depth)
    mini_trench_surf=pygame.transform.scale(trench_surf,(200.0/game_depth*game_width,200))
    
    blackout_surf = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA,32)
    fuzz_surf = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA,32)
    gen_fuzz(fuzz_surf)
 
    game_over_screens["health"]=game_over_screens["battery"]=pygame.image.load(data.filepath("gameover.png")).convert_alpha()
 
    load_music_loop('surface.mp3')
 
    debug_txt="initializing.."
    subimg = pygame.image.load(data.filepath("robosub.png")).convert_alpha()
    subimg2 = pygame.image.load(data.filepath("robosub2.png")).convert_alpha()

    queue_msg("Welcome to Robosub",100)
    queue_msg("A PyWeek 6 Game by Nikolaj Baer",50)
    queue_msg("The goal is to gather scientific samples with your robotic submarine.",50)
    queue_msg("Samples are glowing red on the trench wall..",50)
    queue_msg("The trench wall is to your right, you can't miss it..",50)
    queue_msg("The samples are richest deep down, but your signal will be weak",50)
    queue_msg("And your sub will be hard to control down there..",50)
    queue_msg("Score reflects how many samples you collect on a 'run'",50)
    queue_msg("Where only the highest is kept",50)
    queue_msg("Have fun and enjoy the deep sea!",50)
    queue_msg("hold down the 'c' key to see controls",50)
    #queue_msg("and the 'h' key to see help at any time",80)
    queue_msg("press 'q' to quit at any time",80)


    for r in range(MAX_TILT*2+1):
        ri=pygame.transform.rotate(subimg,r-MAX_TILT)
        ri2=pygame.transform.rotate(subimg2,r-MAX_TILT)
        subimgs.append(ri)
        subimgs2.append(ri2)
    
    # we use a gradient image to make a nice light halo
    lightimg = pygame.image.load(data.filepath("bluegrad.png")).convert_alpha()
    for i in range(3,20):
        lightballs.append(pygame.transform.scale(lightimg,(lightimg.get_width()*i/10.0,lightimg.get_height()*i/10.0)))
    
    # and loop
    while 1:
       event = pygame.event.wait()
       if event.type == pygame.QUIT: 
          sys.exit()
       elif event.type == TICK:
          checkKeys() 
          screen.fill((0,0,0))
          tick()
          render()
          pygame.display.flip()
   
if __name__=="__main__":
    main() 
