"""Trim synchronized recordings, assemble crossfades and burn aligned captions."""
import difflib,hashlib,json,math,re,subprocess,textwrap
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/video';TMP=Path('/tmp/polytoken-video-build');TMP.mkdir(exist_ok=True)
scenes=json.loads((OUT/'scenes.json').read_text());FADE=.25;FPS=25
font='/System/Library/Fonts/Supplemental/Arial.ttf';bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def run(args):
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def audit(event,**kw):
 with (ROOT/'logs/sample/video_production.jsonl').open('a') as f:f.write(json.dumps(dict(event=event,timestamp=datetime.now(timezone.utc).isoformat(),**kw))+'\n')
# Use a binary sync slate to locate the exact first recorded scene frame, excluding all setup.
for s in scenes:
 raw=OUT/'screen'/f"{s['id']}-raw.webm";target=OUT/'screen'/f"{s['id']}.mp4"
 if not raw.exists() and target.exists():continue
 info=probe(raw);rate=info['streams'][0]['avg_frame_rate'];a,b=map(int,rate.split('/'));fps=a/b
 pixels=subprocess.check_output(['ffmpeg','-v','error','-i',str(raw),'-vf','crop=8:8:10:10,scale=1:1','-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','-'])
 rgb=list(zip(pixels[::3],pixels[1::3],pixels[2::3]));mag=[i for i,(r,g,b) in enumerate(rgb) if r>200 and g<60 and b>200];cyan=[i for i,(r,g,b) in enumerate(rgb) if r<60 and g>200 and b>200]
 assert mag and cyan, 'Missing sync slate '+s['id'];start=(max(mag)+1)/fps;end=min(i for i in cyan if i>max(mag))/fps
 assert abs((end-start)-s['duration'])<.45,(s['id'],start,end,s['duration'])
 run(['-ss',start,'-i',raw,'-t',s['duration'],'-vf','fps=25,format=yuv420p','-c:v','libx264','-preset','fast','-crf','20','-an',target]);audit('scene_trimmed',scene=s['id'],start=start,end=end,duration=s['duration'],ok=True)
 print('Trimmed',s['id'],flush=True)
# Source audio is unchanged speech: scene-boundary trims and silence margins only.
clips={c['scene']:c for c in json.loads((OUT/'scene_boundaries.json').read_text())['clips']}
segments=[];durations=[];cursor=0;captions=[]
for s in scenes:
 audio=OUT/'assets/voice'/f"{s['scene']}.wav";dest=TMP/f"{s['id']}.mp4";duration=s['duration'];offset=s['audio_offset']
 run(['-i',OUT/'screen'/f"{s['id']}.mp4",'-i',audio,'-filter_complex',f'[1:a]adelay={round(offset*1000)}:all=1,apad,atrim=duration={duration},aresample=48000[a]','-map','0:v','-map','[a]','-t',duration,'-c:v','copy','-c:a','aac','-b:a','192k',dest])
 segments.append(dest);durations.append(duration);s['timeline_start']=cursor
 c=clips[s['scene']];heard=c['words'];canonical=c['caption_text'].split()
 clean=lambda w: re.sub(r'[^a-z0-9]', '',w.lower())
 aligned=[None]*len(canonical)
 matcher=difflib.SequenceMatcher(None,[clean(w['word']) for w in heard],[clean(w) for w in canonical],autojunk=False)
 for op,i,j,k,l in matcher.get_opcodes():
  if k==l:continue
  if op=='equal':
   for source,target in zip(range(i,j),range(k,l)):aligned[target]=(heard[source]['start'],heard[source]['end'])
  else:
   start=heard[i]['start'] if i<len(heard) else heard[-1]['end']
   end=heard[j-1]['end'] if j>i else start+.12
   width=max(.04,end-start)/(l-k)
   for target in range(k,l):aligned[target]=(start+(target-k)*width,start+(target-k+1)*width)
 words=[(w,max(0,t[0]-c['file_start_s']),min(s['audio_duration'],t[1]-c['file_start_s'])) for w,t in zip(canonical,aligned)]
 group=[]
 def emit(g):
  if g:captions.append(dict(start=cursor+offset+g[0][1],end=cursor+offset+g[-1][2]+.12,text=' '.join(w[0] for w in g)))
 for word in words:
  if group and (len(' '.join(w[0] for w in group))+len(word[0])>86 or word[2]-group[0][1]>4.5):emit(group);group=[]
  group.append(word)
  if word[0].endswith(('.', '?', '!')):emit(group);group=[]
 emit(group);cursor+=duration-FADE
# Round duration to the actual frame grid used by the rendered scene files.
actual=[float(probe(p)['format']['duration']) for p in segments];total=sum(actual)-FADE*(len(segments)-1)
# Caption times use the editorial timeline; accumulated quantisation is under one frame per scene.
def stamp(t):
 ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02}:{m:02}:{s:02},{ms:03}'
for i,c in enumerate(captions[:-1]):c['end']=min(c['end'],captions[i+1]['start']-.02)
srt='\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n"+'\n'.join(textwrap.wrap(c['text'],width=48)) for i,c in enumerate(captions))+'\n'
(OUT/'PolyToken_demo.srt').write_text(srt)
# Render a caption band using Pillow so no platform subtitle filter is required.
capdir=TMP/'captions';capdir.mkdir(exist_ok=True);blank=Image.new('RGB',(1920,130),'#111318');blank.save(capdir/'blank.png');track=[];last=0
for i,c in enumerate(captions):
 start=round(c['start']*FPS)/FPS;end=round(c['end']*FPS)/FPS
 if start>last:track.append(('blank.png',start-last))
 im=blank.copy();draw=ImageDraw.Draw(im);lines=textwrap.wrap(c['text'],width=48);f=ImageFont.truetype(font,36)
 for j,line in enumerate(lines):
  w=draw.textbbox((0,0),line,font=f)[2];draw.text(((1920-w)/2,18+j*43),line,font=f,fill='#ffffff')
 name=f'{i:03}.png';im.save(capdir/name);track.append((name,max(.04,end-start)));last=end
if total>last:track.append(('blank.png',total-last))
concat='ffconcat version 1.0\n'+''.join(f"file '{name}'\nduration {dur:.6f}\n" for name,dur in track)+"file 'blank.png'\n"
(capdir/'captions.ffconcat').write_text(concat)
run(['-f','concat','-safe','0','-i',capdir/'captions.ffconcat','-vf','fps=25','-t',total,'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',TMP/'caption-band.mp4'])
args=[]
for segment in segments:args+=['-i',segment]
filters=[]
for i in range(len(segments)):filters += [f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps=25[v{i}]',f'[{i}:a]asetpts=PTS-STARTPTS[a{i}]']
v='v0';a='a0';length=actual[0]
for i in range(1,len(segments)):
 vn=f'xv{i}';an=f'xa{i}';filters += [f'[{v}][v{i}]xfade=transition=fade:duration={FADE}:offset={length-FADE}[{vn}]',f'[{a}][a{i}]acrossfade=d={FADE}[{an}]'];v=vn;a=an;length+=actual[i]-FADE
# Single intermediate keeps the render memory bounded and allows measured loudness normalization.
run([*args,'-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map',f'[{v}]','-map',f'[{a}]','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',TMP/'joined.mp4'])
print('Crossfades assembled',flush=True)
measure=subprocess.run(['ffmpeg','-hide_banner','-i',str(TMP/'joined.mp4'),'-af','highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
levels=json.loads(re.findall(r'\{[^{}]+\}',measure.stderr)[-1]);norm=f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={levels['input_i']}:measured_TP={levels['input_tp']}:measured_LRA={levels['input_lra']}:measured_thresh={levels['input_thresh']}:offset={levels['target_offset']}:linear=true"
run(['-i',TMP/'joined.mp4','-i',TMP/'caption-band.mp4','-filter_complex_threads','1','-filter_complex',f'[0:v][1:v]overlay=0:950:shortest=1[v];[0:a]highpass=f=80,{norm},aresample=48000[a]','-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',OUT/'PolyToken_demo.mp4'])
final=probe(OUT/'PolyToken_demo.mp4');length=float(final['format']['duration']);assert 165<=length<=210
# Contact sheet every ten seconds; full-size frames are retained for OCR checks.
frames=OUT/'review_frames';frames.mkdir(exist_ok=True);images=[]
for t in range(0,math.ceil(length),10):
 dest=frames/f'{t:03}.png';run(['-ss',t,'-i',OUT/'PolyToken_demo.mp4','-frames:v','1',dest]);images.append((t,dest))
cols=3;cw=640;ch=390;sheet=Image.new('RGB',(cols*cw,math.ceil(len(images)/cols)*ch),'#202329');draw=ImageDraw.Draw(sheet)
for i,(t,dest) in enumerate(images):
 im=Image.open(dest).resize((640,360));x=(i%cols)*cw;y=(i//cols)*ch;sheet.paste(im,(x,y+30));draw.text((x+12,y+5),f'{t//60:02}:{t%60:02}',font=ImageFont.truetype(font,21),fill='white')
sheet.save(OUT/'contact_sheet.png')
# Six dedicated full-size review frames: architecture, Raitu costs/quality, both ratios,
# checked Q&A and a recompute recipe, in addition to the 10-second contact sheet.
for scene_id,offset,name in [('s03',17,'architecture'),('s04',23,'raitu-cost-quality'),('s05',9,'native-6x'),('s05',15,'tenglish-1.12x'),('s06',12,'checked-answer'),('s07',2,'recompute')]:
 t=next(s['timeline_start'] for s in scenes if s['id']==scene_id)+offset
 run(['-ss',t,'-i',OUT/'PolyToken_demo.mp4','-frames:v','1',frames/f'key-{name}.png'])
(OUT/'scenes.json').write_text(json.dumps(scenes,indent=2,ensure_ascii=False)+'\n')
manifest=dict(duration=length,scene_durations={s['id']:s['duration'] for s in scenes},audio_durations={s['id']:s['audio_duration'] for s in scenes},title_duration=0,crossfade=.25,width=1920,height=1080,video_codec=final['streams'][0]['codec_name'],audio_codec=next(s['codec_name'] for s in final['streams'] if s['codec_type']=='audio'),caption_count=len(captions),live_app_fraction_min=1-(8.4+scenes[-1]['duration'])/length,sha256=hashlib.sha256((OUT/'PolyToken_demo.mp4').read_bytes()).hexdigest(),loudness_input=levels)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');audit('video_assembled',ok=True,**manifest);print(json.dumps(manifest,indent=2))
