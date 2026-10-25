"""Generate scene clips using the user's local ElevenLabs settings; never log credentials."""
import base64, hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import httpx
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/video/audio';OUT.mkdir(parents=True,exist_ok=True)
scenes=json.loads((ROOT/'docs/video/scenes.json').read_text())
assert len(scenes)==7
env=dotenv_values(ROOT/'.env')
missing=[k for k in ['ELEVENLABS_API_KEY','ELEVENLABS_VOICE_ID'] if not env.get(k)]
if missing:print('Missing settings: '+', '.join(missing));sys.exit(2)
model='eleven_multilingual_v2'
def log(event,**values):
 with (ROOT/'logs/sample/video_production.jsonl').open('a') as f:f.write(json.dumps(dict(event=event,timestamp=datetime.now(timezone.utc).isoformat(),**values))+'\n')
with httpx.Client(timeout=150) as client:
 for i,scene in enumerate(scenes):
  file=OUT/(scene['id']+'.mp3');meta=OUT/(scene['id']+'.json')
  digest=hashlib.sha256(scene['text'].encode()).hexdigest()
  if file.exists() and meta.exists() and json.loads(meta.read_text()).get('text_sha256')==digest:
   print(scene['id']+' reused',flush=True);continue
  payload=dict(text=scene['text'],model_id=model,voice_settings=dict(stability=.55,similarity_boost=.8,style=.18,speed=.9,use_speaker_boost=True),apply_text_normalization='auto')
  if i:payload['previous_text']=scenes[i-1]['text']
  if i<len(scenes)-1:payload['next_text']=scenes[i+1]['text']
  try:
   response=client.post('https://api.elevenlabs.io/v1/text-to-speech/'+env['ELEVENLABS_VOICE_ID']+'/with-timestamps',params={'output_format':'mp3_44100_128'},headers={'xi-api-key':env['ELEVENLABS_API_KEY']},json=payload)
  except httpx.HTTPError as e:
   log('tts_failed',scene=scene['id'],ok=False,error_class=type(e).__name__);print('Speech request failed; '+type(e).__name__);sys.exit(1)
  if response.status_code!=200:
   # Do not dump request URLs, headers or arbitrary server response data.
   log('tts_failed',scene=scene['id'],ok=False,http_status=response.status_code);print('Speech request failed; HTTP '+str(response.status_code));sys.exit(1)
  result=response.json();file.write_bytes(base64.b64decode(result['audio_base64']))
  duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(file)]))
  record=dict(scene=scene['id'],model=model,text=scene['text'],text_sha256=digest,duration=duration,alignment=result.get('normalized_alignment') or result['alignment'],audio_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
  meta.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
  log('tts_generated',scene=scene['id'],ok=True,model=model,characters=len(scene['text']),duration=duration,text_sha256=digest,audio_sha256=record['audio_sha256'])
  print(scene['id']+': '+str(round(duration,2))+' s',flush=True)
