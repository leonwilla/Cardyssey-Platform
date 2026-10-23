#!/usr/bin/env python3
"""Conservative manual eBay diagnostic of one card; never imports guessed sale prices."""
import sys,json,re,subprocess,os,time,fcntl
from pathlib import Path
BASE=Path('/home/tv/cardyssey-ebay-collector');DIR=BASE/'admin-card-tests';DIR.mkdir(exist_ok=True)
method,card_id=sys.argv[1:3]
if not re.fullmatch(r'[A-Za-z0-9_-]{2,90}',card_id):raise SystemExit('INVALID_CARD_ID')
folder=DIR/card_id
if method=='status':
 p=folder/'state.json';print(p.read_text() if p.exists() else json.dumps({'status':'NOT_STARTED'}));sys.exit(0)
if method!='start':raise SystemExit('BAD_ACTION')
q=sys.argv[3].strip()
if not 3<=len(q)<=160 or any(x in q for x in '\r\n\x00'):raise SystemExit('BAD_QUERY')
with (DIR/'.lock').open('w') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if subprocess.run(['pgrep','-f','^python3 -u anniversary_batch.py'],capture_output=True).returncode==0:print(json.dumps({'error':'EBAY_BROWSER_BUSY'}));sys.exit(0)
 if (folder/'state.json').exists() and json.loads((folder/'state.json').read_text()).get('status')=='RUNNING':print(json.dumps({'error':'CARD_TEST_RUNNING'}));sys.exit(0)
 # validate card ID against the actual catalog, never accept a user-provided variant ID
 from subprocess import check_output
 sql="SELECT COALESCE(json_agg(t),'[]') FROM (SELECT card_id,name,local_id,set_id,variants FROM catalog_cards_mirror WHERE language_code='de' AND card_id='"+card_id+"') t"
 cards=json.loads(check_output(['docker','exec','cardyssey-db','psql','-U','cardyssey','-d','cardyssey','-Atc',sql],text=True,timeout=12))
 if len(cards)!=1:print(json.dumps({'error':'CARD_NOT_FOUND'}));sys.exit(0)
 if cards[0]['set_id'] in ('sv01','sv02'):
  cards[0]['denominator']=198 if cards[0]['set_id']=='sv01' else 193
 folder.mkdir(exist_ok=True)
 (folder/'request.json').write_text(json.dumps({'card':cards[0],'query':q},ensure_ascii=False))
 state={'status':'RUNNING','cardId':card_id,'query':q,'startedAt':time.time()};(folder/'state.json').write_text(json.dumps(state))
 log=(folder/'runner.log').open('w')
 subprocess.Popen(['python3',str(BASE/'run_single_card_test.py'),str(folder)],cwd=str(BASE),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 print(json.dumps(state))
