"""OCR the contact sheet and full-resolution review frames without printing secrets."""
import json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];paths=[ROOT/'docs/video/contact_sheet.png',*sorted((ROOT/'docs/video/review_frames').glob('*.png'))]
patterns=[r'nvapi\s*-',r'NVIDIA_API_KEY',r'ELEVENLABS_API_KEY',r'ELEVENLABS_VOICE_ID',r'ZETARIS_PASSWORD',r'COMPANY_DB_PASSWORD',r'HF_TOKEN',r'Authorization\s*:\s*Bearer']
results=[]
for p in paths:
 result=subprocess.run(['tesseract',str(p),'stdout','--psm','11'],capture_output=True,text=True,check=True)
 hits=[pattern for pattern in patterns if re.search(pattern,result.stdout,re.I)]
 results.append(dict(path=str(p.relative_to(ROOT)),matched_patterns=hits))
report=dict(event='video_frame_ocr_secret_scan',timestamp=datetime.now(timezone.utc).isoformat(),ok=not any(r['matched_patterns'] for r in results),scope='Contact sheet plus full-resolution final video frames every ten seconds',images=len(results),results=results)
with (ROOT/'logs/sample/video_deck_validation.jsonl').open('a') as f:f.write(json.dumps(report)+'\n')
print(json.dumps(dict(ok=report['ok'],images=len(results))))
raise SystemExit(not report['ok'])
