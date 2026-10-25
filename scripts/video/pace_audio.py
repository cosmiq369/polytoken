"""Small pitch-preserving pace adjustment, with matching caption timestamps."""
import json, subprocess, hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2];scenes=json.loads((root/'docs/video/scenes.json').read_text())
for s in scenes:
 p=root/'docs/video/audio'/f"{s['id']}.mp3";m=p.with_suffix('.json');d=json.loads(m.read_text())
 if not d.get('pacing_factor'):
  tmp=p.with_suffix('.paced.mp3');subprocess.run(['ffmpeg','-v','error','-y','-i',str(p),'-af','atempo=0.94','-codec:a','libmp3lame','-b:a','128k',str(tmp)],check=True);tmp.replace(p)
  d['raw_duration']=d['duration'];d['pacing_factor']=.94
  for k in ['character_start_times_seconds','character_end_times_seconds']:d['alignment'][k]=[v/.94 for v in d['alignment'][k]]
  d['duration']=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)]));d['audio_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();m.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 s['audio_duration']=d['duration'];s['duration']=d['duration']+(4.5 if s['id']=='s02' else 3.2);s['audio_offset']=.65
(root/'docs/video/scenes.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2)+'\n')
print('Planned final length:',round(2+sum(s['duration'] for s in scenes)-7*.25,2),'seconds')
