"""Original M2 audio sketches; Python standard library only."""
import hashlib, json, math, random, struct, wave, sys
from pathlib import Path
RATE = 48000
CUES = {
 'sfx_footstep_stone':(.32,False), 'sfx_footstep_wood':(.32,False),
 'sfx_amb_forge':(8,True), 'sfx_combat_hit':(.35,False),
 'sfx_combat_parry':(.48,False), 'sfx_weapon_sword':(.45,False),
 'sfx_combat_telegraph':(.55,False), 'sfx_discrepancy_pulse':(1.2,False),
 'music_main':(12,True), 'music_kael':(12,True), 'music_noah':(12,True),
 'music_abyss_catacombs':(12,True), 'sfx_weather_rain':(8,True)}
MOTIFS = {'music_main':(62,65,64,69),'music_kael':(50,53,52,57),
          'music_noah':(69,72,71,76),'music_abyss_catacombs':(38,41,40,45)}
def render(name, duration):
    rng=random.Random(name); n=round(duration*RATE); out=[]; low=0.0
    for i in range(n):
        t=i/RATE; noise=rng.uniform(-1,1); low=.94*low+.06*noise
        if name in MOTIFS:
            beat=int(t/.75); u=t% .75; note=MOTIFS[name][beat%4]; f=440*2**((note-69)/12)
            a=min(1,u/.045)*math.exp(-3*u/.75)*min(1,(.75-u)/.07)
            x=.38*a*(math.sin(2*math.pi*f*u)+.22*math.sin(4*math.pi*f*u))
            x+=.10*math.sin(2*math.pi*55*t)*math.sin(math.pi*t/duration)**2
        elif name=='sfx_amb_forge':
            u=t%2; x=.16*low+.34*math.exp(-7*u)*(math.sin(2*math.pi*431*u)+.45*math.sin(2*math.pi*919*u))
        elif name=='sfx_weather_rain': x=.35*low+.08*noise
        elif 'footstep' in name:
            f=92 if 'stone' in name else 145; x=math.exp(-13*t)*(.52*low+.25*math.sin(2*math.pi*f*t)+.17*noise)
        elif 'parry' in name: x=.48*math.exp(-8*t)*(math.sin(2*math.pi*1120*t)+.3*math.sin(2*math.pi*1733*t))
        elif 'hit' in name: x=math.exp(-12*t)*(.48*math.sin(2*math.pi*(85*t-30*t*t))+.4*low)
        elif 'sword' in name: x=.45*noise*math.sin(math.pi*t/duration)**2+.15*low
        elif 'telegraph' in name: x=.34*math.sin(2*math.pi*(170*t+230*t*t))*math.sin(math.pi*t/duration)
        else: x=.38*math.sin(2*math.pi*(65*t+11*math.sin(4*t))) * math.sin(math.pi*t/duration)**2+.12*low
        edge=min(1,i/480,(n-1-i)/480); out.append(round(24000*x*edge))
    return out

def generate(dest):
    dest.mkdir(parents=True,exist_ok=True); rows=[]
    for name,(duration,loop) in CUES.items():
        samples=render(name,duration); p=dest/(name+'.wav')
        with wave.open(str(p),'wb') as w:
            w.setparams((1,2,RATE,len(samples),'NONE','not compressed')); w.writeframes(struct.pack('<'+'h'*len(samples),*samples))
        rows.append(dict(id=name,file=p.name,seconds=duration,loop=loop,frames=len(samples),sample_rate=RATE,peak=max(map(abs,samples)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status='generated_prototype',rights='project original; all rights reserved'))
    (dest/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows
if __name__=='__main__': generate(Path(sys.argv[1]))
