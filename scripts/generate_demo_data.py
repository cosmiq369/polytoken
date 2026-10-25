"""Fixed-seed fictional model-fit conversations. Paired translations are pending review."""
from pathlib import Path
import json
import random
import runpy

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261025

# English instructions are identical in both paired columns. The compatibility
# column name text_native denotes actual workload text, including Latin script.
COMPANY_CONFIGS = [
 ('samudra', 'te', 'Telugu telecom customer support', 'chat', 200000, 8.0, 'unsloth/Llama-3.2-3B-Instruct',
  'You assist the fictional Samudra Telecom app. Reply in the user\'s Telugu, romanized Telugu or Tenglish style. Ask one relevant question at a time. Keep replies brief. Never invent a charge, plan, ticket or completed action. Do not request passwords or payment credentials.'),
 ('swara', 'hi', 'Hindi health-information and clinic-access assistant', 'voice', 120000, 3.0, 'unsloth/Llama-3.2-3B-Instruct',
  'You assist the fictional Swara Care voice service in Hindi. Explain clinic access and administrative information clearly for a listener. You cannot access bookings or diagnose illness. Do not invent availability. Protect personal data. Give the relevant steps and explain important limits.'),
 ('raitu', 'te', 'Telugu agricultural advisory for farmers', 'voice', 80000, 3.0, 'unsloth/Llama-3.2-3B-Instruct',
  'You assist the fictional Raitu Mitra voice service in Telugu. Use clear rural vocabulary and medium-length spoken answers. Ask about the crop, field and observed condition. Do not prescribe a chemical or invent a diagnosis, weather forecast, subsidy or market price. Refer uncertain decisions to the local agricultural officer.'),
 ('paisa', 'hi', 'Hinglish fintech app support', 'chat', 300000, 6.0, 'Qwen/Qwen3-4B',
  'You assist the fictional Paisa Saathi fintech app in concise Hinglish. Explain app navigation and payment status. Never request an OTP, PIN or card number. Do not promise a refund, approve credit or give investment advice. Ask one necessary follow-up question and use only the information supplied.'),
]
# topic, user in code-mix / romanized / script, English, assistant variants, English
TE = [
 ('recharge', 'Na recharge pending undi, app lo status check cheyyala?', 'Naa punaruddharana inkaa kaaledu, ippudu em cheyyaali?', 'నా రీచార్జి ఇంకా కాలేదు, ఇప్పుడు ఏం చేయాలి?', 'My recharge is still pending; what should I do now?',
  'App payment history lo status chudandi; pending unte malli pay cheyyakandi.', 'Chellimpu charitralo paristhiti chudandi; inkaa kaakapothe marosari chellinchakandi.', 'చెల్లింపు చరిత్రలో పరిస్థితి చూడండి; ఇంకా కాకపోతే మరోసారి చెల్లించకండి.', 'Check the payment history status; if it is still pending, do not pay again.'),
 ('data', 'Mobile data slow ga undi, calls matram work avutunnayi.', 'Antarjaalam nemmadigaa undi, maatlaadatam maatram baagundi.', 'అంతర్జాలం నెమ్మదిగా ఉంది, మాట్లాడటం మాత్రం బాగుంది.', 'Internet is slow, but calls are working.',
  'Issue oka area lone unda? Phone restart try chesara?', 'Ee samasya oke chota undaa? Phone aapi malli on chesaaraa?', 'ఈ సమస్య ఒకే చోట ఉందా? ఫోన్ ఆపి మళ్లీ ఆన్ చేశారా?', 'Does this happen in one area only? Have you restarted the phone?'),
 ('bill', 'Bill lo extra charge vachindi, details ekkada chudali?', 'Ee nela lekkalo adanapu rusumu undi, vivaraalu ekkada chudaali?', 'ఈ నెల లెక్కలో అదనపు రుసుము ఉంది, వివరాలు ఎక్కడ చూడాలి?', 'This month has an extra charge; where can I see the details?',
  'App bill details open cheyyandi. Ye charge category kanipistondi?', 'Chellimpu vivaraalu teravandi. Adanapu rusumu peru emani undi?', 'చెల్లింపు వివరాలు తెరవండి. అదనపు రుసుము పేరు ఏమని ఉంది?', 'Open the bill details. What is the extra charge called?'),
 ('plan', 'Plan change cheyyali, current data saripovatledu.', 'Prastuta pathakam saripovatledu, vere pathakam kaavaali.', 'ప్రస్తుత పథకం సరిపోవట్లేదు, వేరే పథకం కావాలి.', 'My current plan is not enough; I need a different plan.',
  'App lo available plans compare cheyyandi; price and validity confirm chesi select cheyyandi.', 'Andubaatulo unna pathakaalu polchandi; rusumu, gaduvu nirdhaarinchaaka enchukondi.', 'అందుబాటులో ఉన్న పథకాలు పోల్చండి; రుసుము, గడువు నిర్ధారించాక ఎంచుకోండి.', 'Compare the available plans; confirm the price and validity before choosing.'),
 ('sim', 'SIM miss ayyindi, block request ela pettali?', 'Naa sim poyindi, daanini aapadaaniki emi cheyyaali?', 'నా సిమ్ పోయింది, దానిని ఆపడానికి ఏమి చేయాలి?', 'My SIM is lost; how can I block it?',
  'Official support lo SIM block process follow avvandi. Ikkada OTP share cheyyakandi.', 'Adhikaarika sahaayam dwaaraa sim nilipivese paddhati telusukondi. Rahasya sanketam ikkada pampakandi.', 'అధికారిక సహాయం ద్వారా సిమ్ నిలిపివేసే పద్ధతి తెలుసుకోండి. రహస్య సంకేతం ఇక్కడ పంపకండి.', 'Use official support to learn the SIM blocking process. Do not share a secret code here.'),
 ('roaming', 'Travel lo roaming work avutunda? Coverage check cheyyali.', 'Prayaanamlo seva untundaa? Andubaatu telusukovaali.', 'ప్రయాణంలో సేవ ఉంటుందా? అందుబాటు తెలుసుకోవాలి.', 'Will service work while travelling? I need to check availability.',
  'Destination cheppandi; official coverage and roaming charges check chesi travel plan cheyyandi.', 'Velle pradesam cheppandi; adhikaarika andubaatu, rusumulu chusi prayaanam nirnayinchandi.', 'వెళ్లే ప్రదేశం చెప్పండి; అధికారిక అందుబాటు, రుసుములు చూసి ప్రయాణం నిర్ణయించండి.', 'Tell us the destination; check official availability and charges before planning the trip.'),
 ('ticket', 'Support ticket update raledu, status ekkada untundi?', 'Naa firyaadu gurinchi samaachaaram raaledu, ekkada chudaali?', 'నా ఫిర్యాదు గురించి సమాచారం రాలేదు, ఎక్కడ చూడాలి?', 'I have no update on my complaint; where can I check?',
  'Official support history lo ticket status chudandi. Resolution time ikkada confirm cheyyalenu.', 'Adhikaarika sahaaya charitralo firyaadu paristhiti chudandi. Parishkaara samayam nenu nirdhaarinchalenu.', 'అధికారిక సహాయ చరిత్రలో ఫిర్యాదు పరిస్థితి చూడండి. పరిష్కార సమయం నేను నిర్ధారించలేను.', 'Check the complaint status in official support history. I cannot confirm a resolution time here.'),
 ('device', 'New phone lo network ravatledu, settings check cheyyala?', 'Kotta phonelo seva raavatledu, amarikalu chudaalaa?', 'కొత్త ఫోన్లో సేవ రావట్లేదు, అమరికలు చూడాలా?', 'Service is unavailable on my new phone; should I check settings?',
  'Screen lo ye message vastondi? Personal details lekunda error text cheppandi.', 'Terameeda emi kanipistondi? Vyaktigata vivaraalu lekundaa sandesam cheppandi.', 'తెరమీద ఏమి కనిపిస్తోంది? వ్యక్తిగత వివరాలు లేకుండా సందేశం చెప్పండి.', 'What message appears on the screen? Share the message without personal details.'),
]
FARM = [
 ('వరిలో ఆకులు పసుపుగా ఉన్నాయి', 'Paddy leaves are yellow', 'వరి'),
 ('పత్తిలో ఆకులు ముడుచుకుంటున్నాయి', 'Cotton leaves are curling', 'పత్తి'),
 ('మిరప పొలంలో నీరు నిలిచింది', 'Water is standing in the chilli field', 'మిరప'),
 ('మొక్కజొన్న మొలకలు తక్కువగా వచ్చాయి', 'Few maize seedlings emerged', 'మొక్కజొన్న'),
 ('వేరుశనగ ఆకులపై మచ్చలు ఉన్నాయి', 'Groundnut leaves have spots', 'వేరుశనగ'),
 ('కందిలో నేల ఎండిపోతోంది', 'The soil in the pigeon pea field is drying', 'కంది'),
 ('జొన్న కోతకు కూలీలు దొరకలేదు', 'Workers are unavailable for the sorghum harvest', 'జొన్న'),
 ('పెసర గింజలు నిల్వలో తడిశాయి', 'Stored green gram seeds became damp', 'పెసర'),
]
FIN = [
 ('UPI payment pending hai', 'My UPI payment is pending', 'Transaction history mein status dekhiye; pending ho to dobara pay mat kijiye.', 'Check the transaction status in history; if pending, do not pay again.'),
 ('Refund status update nahi hua', 'My refund status has not updated', 'Support section mein refund status check kijiye; refund date confirm nahi kar sakta.', 'Check the refund status in support; I cannot confirm a refund date.'),
 ('SIP auto-debit ka notification aaya', 'I received a SIP auto-debit notification', 'Mandate details mein debit date verify kijiye. Yeh investment recommendation nahi hai.', 'Verify the debit date in the mandate details. This is not an investment recommendation.'),
 ('Savings account statement download karna hai', 'I want to download my savings account statement', 'Statement menu mein date range choose kijiye; account number yahan share mat kijiye.', 'Choose the date range in the statement menu; do not share your account number here.'),
 ('KYC update ka message aaya', 'I received a KYC update message', 'Official app mein KYC status dekhiye; SMS link par OTP enter mat kijiye.', 'Check KYC status in the official app; do not enter an OTP through an SMS link.'),
 ('Card limit screen nahi mil raha', 'I cannot find the card limit screen', 'Card settings mein available options dekhiye. Limit approval guarantee nahi hai.', 'Check the available options in card settings. Limit approval is not guaranteed.'),
 ('NEFT transfer ka receipt chahiye', 'I need the receipt for an NEFT transfer', 'Transaction details mein receipt option dekhiye; PIN kabhi share mat kijiye.', 'Look for the receipt option in transaction details; never share your PIN.'),
 ('App login error aa raha hai', 'The app shows a login error', 'Error message bina personal details batayiye; OTP ya password nahi chahiye.', 'Tell us the error message without personal details; no OTP or password is needed.'),
]


def build():
    rng=random.Random(SEED)
    configs=[]; chats={}
    legacy=runpy.run_path(str(ROOT/'scripts/generate_demo_data_v2.py'))['build']()[1]['swara']
    swara_by={}
    for row in legacy: swara_by.setdefault(row['chat_id'],[]).append(row)
    for company,lang,role,channel,volume,target,model,prompt in COMPANY_CONFIGS:
        configs.append(dict(company=company,language=lang,role=role,channel=channel,monthly_chats=volume,
            latency_target_s=target,model_in_use=model,current_model={'unsloth/Llama-3.2-3B-Instruct':'meta-llama/Llama-3.2-3B-Instruct'}.get(model,model),system_prompt_native=prompt,
            system_prompt_en=prompt,review_status='pending',dataset_version='model-fit-v1'))
        rows=[]
        for i in range(40):
            chat_id=f'{company}-fit-{i+1:03d}'
            def add(native,en):
                rows.append(dict(chat_id=chat_id,turn=1+sum(r['chat_id']==chat_id for r in rows),
                    role='user' if sum(r['chat_id']==chat_id for r in rows)%2==0 else 'assistant',
                    text_native=native,text_en=en,lang=lang,review_status='pending'))
            if company=='swara':
                original=list(swara_by.values())[i]
                for row in original: add(row['text_native'],row['text_en'])
                continue
            if company=='samudra':
                t=TE[i%8]; mode=0 if i<24 else 1 if i<36 else 2
                # Time-of-day and device context vary naturally, never fabricated prices.
                when=rng.choice([('ee udayam','this morning'),('ninna','yesterday'),('ee saayantram','this evening')])
                native_when={'ee udayam':'ఈ ఉదయం','ninna':'నిన్న','ee saayantram':'ఈ సాయంత్రం'}[when[0]]
                add(t[1+mode]+' '+(native_when if mode==2 else when[0])+'.', t[4]+' '+when[1].capitalize()+'.')
                add(t[5+mode],t[8])
                add(['Android app use chestunna, next step cheppandi.','Android phone vaadutunnaanu, taruvaata emi cheyyaali?','ఆండ్రాయిడ్ ఫోన్ వాడుతున్నాను, తర్వాత ఏమి చేయాలి?'][mode], 'I use an Android phone; what should I do next?')
                add(['Official app support open chesi '+t[0]+' issue select cheyyandi; details confirm cheyyandi.', 'Adhikaarika sahaaya bhaagamlo ee samasya enchukoni vivaraalu nirdhaarinchandi.', 'అధికారిక సహాయ భాగంలో ఈ సమస్య ఎంచుకుని వివరాలు నిర్ధారించండి.'][mode], 'Open official support, select this issue and confirm the details.')
                if i%3==0:
                    add(['App update kuda chesanu, issue alage undi.','Maarpulu chesinaa samasya alage undi.','మార్పులు చేసినా సమస్య అలాగే ఉంది.'][mode], 'The issue remains after updating the app.' if mode==0 else 'The issue remains after making the changes.')
                    add(['Support ki already tried steps cheppandi; ticket confirmation vachaka save chesukondi.','Meeru chesina prayatnaalu sahaaya sibbandiki cheppandi; firyaadu nirdhaarana vachchaaka daachukondi.','మీరు చేసిన ప్రయత్నాలు సహాయ సిబ్బందికి చెప్పండి; ఫిర్యాదు నిర్ధారణ వచ్చాక దాచుకోండి.'][mode], 'Tell support what you have tried; save the complaint confirmation when it arrives.')
            elif company=='raitu':
                issue,en,crop=FARM[i%8]; acres=1+i//8
                crop_en=('paddy','cotton','chilli','maize','groundnut','pigeon pea','sorghum','green gram')[i%8]
                add(f'నా {acres} ఎకరాల పొలంలో {issue}. ఏం గమనించాలి?',f'{en} in my {acres}-acre field. What should I observe?')
                add(f'{crop} పరిస్థితి తెలుసుకోవడానికి ముందు సమస్య ఎప్పటి నుంచి ఉందో చెప్పండి. పొలమంతా ఉందా, ఒక మూలలో మాత్రమే ఉందా గమనించండి. నేలలో తేమ, ఇటీవలి నీటి పారుదల వివరాలు కూడా ఉపయోగపడతాయి. ఈ వివరాలు లేకుండా కారణాన్ని ఖచ్చితంగా చెప్పలేను.',f'To understand the {crop_en} condition, first say when the problem began. Observe whether it affects the whole field or one corner. Soil moisture and recent irrigation details also help. I cannot determine the cause without these details.')
                days=1+i%5
                add(f'{days} రోజుల నుంచి ఒక మూలలో ఉంది. నిన్న నీరు పెట్టాను. ఎవరిని అడగాలి?',f'It has affected one corner for {days} days. I irrigated yesterday. Whom should I ask?')
                add('స్థానిక వ్యవసాయ అధికారికి మీరు గమనించిన మార్పులు, నీరు పెట్టిన సమయం చెప్పండి. ప్రభావిత భాగాన్ని చూపించండి; మిగతా పొలంతో పోల్చమని అడగండి. పరిశీలన లేకుండా మందు లేదా మోతాదు నిర్ణయించవద్దు. అధికారి చెప్పిన తదుపరి చర్యను నిర్ధారించుకోండి.', 'Tell the local agricultural officer about the observed changes and irrigation time. Show the affected area and ask them to compare it with the rest of the field. Do not decide on a chemical or dose without inspection. Confirm the next step with the officer.')
            else:
                issue,en,answer,answer_en=FIN[i%8]; amount=500+250*(i//8)
                add(f'{issue}, app mein INR {amount} dikh raha hai.',f'{en}; the app shows INR {amount}.')
                add(answer,answer_en)
                add(f'Android app use karta hoon, {1+i%5} din se same screen hai.',f'I use the Android app; the screen has been the same for {1+i%5} days.')
                add('Help section mein issue report kijiye; screenshot mein personal details hide kijiye.', 'Report the issue in Help; hide personal details in any screenshot.')
        chats[company]=rows
    return configs,chats


def main():
    configs,chats=build()
    out=ROOT/'data/demo'; out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('bot_config',configs),*[(f'{c}_chats',r) for c,r in chats.items()]]:
        (out/f'{name}.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    print({c:dict(chats=len({r['chat_id'] for r in rows}),turns=len(rows)) for c,rows in chats.items()})

if __name__=='__main__': main()
