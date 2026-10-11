#!/usr/bin/env python3
"""NVR Watch: independent static client and authenticated Blue Iris API adapter."""
import argparse, hashlib, http.cookies, json, mimetypes, os, re, secrets, ssl, threading, time
import urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from exports import ExportManager,ExportError
from settings import SettingsStore,SettingsError

WEB=Path(__file__).resolve().parent/'web'
SESSIONS={}; LOCK=threading.RLock(); ATTEMPTS={}
ADMIN_SESSIONS={};ADMIN_COOKIE='nvrwatch_admin'
READ_COMMANDS={'camlist','cliplist','alertlist','status','login'}
FIELDS={'camlist':set(),'cliplist':{'camera','startdate','enddate','view','search','tiles'},'alertlist':{'camera','startdate','enddate','view','search','tiles'},'status':set(),'login':set()}
MEDIA_KEYS={'mode','speed','time','pos','w','h','q','stream','t','nc','addmotion','addoverlay','extend','isolate','opaque'}
COOKIE='nvrwatch_session'

def upstream_json(base, payload):
 req=urllib.request.Request(base+'/json',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)

def public_login(data):
 return {k:v for k,v in (data or {}).items() if k in {'admin','clips','audio','clipcreate','version','system name','tzone'}}

def recorder_login(base,user,password):
 challenge=upstream_json(base,{'cmd':'login'});session=challenge.get('session')
 if not session:raise SettingsError('The server did not return a Blue Iris sign-in challenge. Check its address and web-server port.')
 result=upstream_json(base,{'cmd':'login','session':session,'response':hashlib.md5(f'{user}:{session}:{password}'.encode()).hexdigest()})
 if result.get('result')!='success':raise SettingsError('Blue Iris rejected the username or password.')
 return result.get('session') or session,result

def connection_error(error):
 reason=getattr(error,'reason',error)
 if isinstance(reason,ssl.SSLError):return 'HTTPS certificate verification failed. Use a trusted certificate or install its issuing CA on the portal host.'
 if isinstance(error,urllib.error.HTTPError):return 'The server returned HTTP '+str(error.code)+'. Check the address, port and Blue Iris web-server configuration.'
 return 'Cannot reach Blue Iris. Check its address, protocol and port, then the firewall and routing between the portal and recorder.'

class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,*args):pass  # Media URLs and credentials are never logged.
 def headers_common(self):
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('X-Frame-Options','SAMEORIGIN')
 def send_json(self,code,data,cookie=None):
  blob=json.dumps(data).encode();self.send_response(code);self.headers_common();self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(blob)))
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(blob)
 def auth(self):
  try:c=http.cookies.SimpleCookie();c.load(self.headers.get('Cookie',''));token=c[COOKIE].value
  except (KeyError,http.cookies.CookieError):return None,None
  with LOCK:
   record=SESSIONS.get(token)
   if not record or time.monotonic()-record['last']>43200:
    SESSIONS.pop(token,None);return None,None
   record['last']=time.monotonic();return token,record['bi']
 def unauthorized(self):self.send_json(401,{'result':'fail','data':{'reason':'Sign-in required.'}})
 def admin(self):
  try:
   cookies=http.cookies.SimpleCookie();cookies.load(self.headers.get('Cookie',''));token=cookies[ADMIN_COOKIE].value
   with LOCK:
    if ADMIN_SESSIONS.get(token,0)>time.monotonic():return True
    ADMIN_SESSIONS.pop(token,None)
  except (KeyError,http.cookies.CookieError):pass
  _,bi=self.auth()
  if bi:
   try:return bool(upstream_json(self.server.bi,{'cmd':'login','session':bi}).get('data',{}).get('admin'))
   except (OSError,ValueError):pass
  return False
 def require_admin(self):
  if self.admin():return True
  self.send_json(403,{'result':'fail','data':{'reason':'Administrator access is required.'}});return False
 def open_session(self,bi,result):
  token=secrets.token_urlsafe(32);now=time.monotonic()
  with LOCK:
   for old in [k for k,v in SESSIONS.items() if now-v['last']>43200]:SESSIONS.pop(old,None)
   old,_=self.auth()
   if old:SESSIONS.pop(old,None)
   SESSIONS[token]={'bi':bi,'last':now}
  self.send_json(200,{'result':'success','data':public_login(result.get('data'))},f'{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/')
 def do_POST(self):
  origin=self.headers.get('Origin')
  if origin and urllib.parse.urlsplit(origin).netloc!=self.headers.get('Host'):
   self.send_json(403,{'result':'fail','data':{'reason':'Origin not allowed.'}});return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=32768:raise ValueError()
   body=json.loads(self.rfile.read(size))
   if not isinstance(body,dict):raise ValueError()
  except (ValueError,UnicodeError):self.send_json(400,{'result':'fail','data':{'reason':'Invalid request.'}});return
  path=urllib.parse.urlsplit(self.path).path
  if path=='/api/admin/login':
   ip='admin:'+self.client_address[0];now=time.monotonic()
   with LOCK:
    recent=[t for t in ATTEMPTS.get(ip,[]) if now-t<60];ATTEMPTS[ip]=recent
    if len(recent)>=8:self.send_json(429,{'result':'fail','data':{'reason':'Too many attempts. Wait a minute.'}});return
    recent.append(now)
   if not self.server.settings.check_code(body.get('code')):
    self.send_json(403,{'result':'fail','data':{'reason':'Administrator access code was not accepted.'}});return
   token=secrets.token_urlsafe(32)
   with LOCK:ADMIN_SESSIONS[token]=now+43200;ATTEMPTS.pop(ip,None)
   self.send_json(200,{'result':'success','data':{}},f'{ADMIN_COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/');return
  if path=='/api/admin/logout':
   cookies=http.cookies.SimpleCookie();cookies.load(self.headers.get('Cookie',''))
   if ADMIN_COOKIE in cookies:
    with LOCK:ADMIN_SESSIONS.pop(cookies[ADMIN_COOKIE].value,None)
   self.send_json(200,{'result':'success','data':{}},f'{ADMIN_COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0');return
  if path in {'/api/settings/test','/api/settings','/api/login-saved'}:
   if not self.require_admin():return
   try:
    if path=='/api/login-saved':
     store=self.server.settings
     bi,result=recorder_login(self.server.bi,store.data.get('username',''),store.password());self.open_session(bi,result);return
    candidate=self.server.settings.candidate(body)
    bi,result=recorder_login(candidate['bi'],candidate['username'],candidate['password'])
    cameras=upstream_json(candidate['bi'],{'cmd':'camlist','session':bi})
    if cameras.get('result')!='success':raise SettingsError('Signed in, but camera access failed. Check the BI account permissions.')
    count=len([c for c in cameras.get('data',[]) if c.get('optionValue') and not c.get('group') and c.get('optionValue')!='index' and not str(c.get('optionValue')).startswith(('+','@'))])
    if path=='/api/settings':
     before=self.server.bi;data=self.server.settings.save(candidate)
     self.server.bi=candidate['bi'];self.server.refresh_interval=candidate['refresh_interval']
     if before!=self.server.bi:
      with LOCK:SESSIONS.clear()
      self.server.exports=ExportManager(self.server.bi,upstream_json)
     self.send_json(200,{'result':'success','data':data})
    else:self.send_json(200,{'result':'success','data':{'connected':True,'cameras':count,'version':result.get('data',{}).get('version'),'clipcreate':bool(result.get('data',{}).get('clipcreate'))}})
   except SettingsError as e:self.send_json(400,{'result':'fail','data':{'reason':str(e)}})
   except (OSError,ValueError,TypeError) as e:self.send_json(502,{'result':'fail','data':{'reason':connection_error(e)}})
   finally:body.clear()
   return
  if path=='/api/login':
   user=body.get('username');password=body.get('password')
   if not isinstance(user,str) or not isinstance(password,str) or not user or len(user)>128 or len(password)>1024:
    self.send_json(400,{'result':'fail','data':{'reason':'Enter your BI username and password.'}});return
   now=time.monotonic();ip=self.client_address[0]
   with LOCK:
    recent=[t for t in ATTEMPTS.get(ip,[]) if now-t<60];ATTEMPTS[ip]=recent
    if len(recent)>=8:self.send_json(429,{'result':'fail','data':{'reason':'Too many attempts. Wait a minute.'}});return
    recent.append(now)
   try:
    challenge=upstream_json(self.server.bi,{'cmd':'login'});bi=challenge.get('session')
    if not bi:raise ValueError('No authentication challenge')
    response=hashlib.md5(f'{user}:{bi}:{password}'.encode()).hexdigest()
    result=upstream_json(self.server.bi,{'cmd':'login','session':bi,'response':response})
    password=None;body.clear()
    if result.get('result')!='success':self.send_json(401,{'result':'fail','data':{'reason':'BI did not accept those credentials.'}});return
    with LOCK:
     ATTEMPTS.pop(ip,None)
    self.open_session(result.get('session') or bi,result)
   except (OSError,ValueError):self.send_json(502,{'result':'fail','data':{'reason':'The BI recorder is unavailable. Check that BI is running.'}})
   return
  cancellation=re.fullmatch(r'/api/exports/([A-Za-z0-9_-]+)/cancel',path)
  if cancellation:
   owner,bi=self.auth()
   if not bi:self.unauthorized();return
   try:self.send_json(200,{'result':'success','data':self.server.exports.cancel(cancellation.group(1),owner,bi)})
   except ExportError as e:self.send_json(e.code,{'result':'fail','data':{'reason':str(e)}})
   except (OSError,ValueError,TypeError):self.send_json(502,{'result':'fail','data':{'reason':'BI could not cancel this export.'}})
   return
  if path=='/api/exports':
   owner,bi=self.auth()
   if not bi:self.unauthorized();return
   try:self.send_json(200,{'result':'success','data':self.server.exports.create(owner,bi,body)})
   except ExportError as e:self.send_json(e.code,{'result':'fail','data':{'reason':str(e)}})
   except (OSError,ValueError,TypeError):self.send_json(502,{'result':'fail','data':{'reason':'BI could not prepare this export.'}})
   return
  if path!='/api/json':self.send_json(404,{'result':'fail'});return
  token,bi=self.auth()
  if not bi:self.unauthorized();return
  cmd=body.get('cmd')
  if cmd=='logout':
   with LOCK:SESSIONS.pop(token,None)
   try:upstream_json(self.server.bi,{'cmd':'logout','session':bi})
   except (OSError,ValueError):pass
   self.send_json(200,{'result':'success','data':{}},f'{COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0');return
  if cmd not in READ_COMMANDS:self.send_json(403,{'result':'fail','data':{'reason':'This interface only supports viewing footage.'}});return
  payload={k:v for k,v in body.items() if k in FIELDS[cmd]};payload.update(cmd=cmd,session=bi)
  try:
   result=upstream_json(self.server.bi,payload)
   if str(result.get('data',{}).get('reason','') if isinstance(result.get('data'),dict) else '').upper()=='INVALID SESSION':
    with LOCK:SESSIONS.pop(token,None)
    self.unauthorized();return
   if cmd=='login' and result.get('result')=='success':
    if result.get('session'):
     with LOCK:
      if token in SESSIONS:SESSIONS[token]['bi']=result['session']
    result['data']=public_login(result.get('data'))
   result.pop('session',None);self.send_json(200,result)
  except (OSError,ValueError):self.send_json(502,{'result':'fail','data':{'reason':'The BI recorder is unavailable. Try again shortly.'}})
 def do_GET(self):
  url=urllib.parse.urlsplit(self.path);path=urllib.parse.unquote(url.path)
  if path=='/healthz':self.send_json(200,{'status':'ok'});return
  if path=='/api/client-config':
   store=getattr(self.server,'settings',None)
   self.send_json(200,{'result':'success','data':{'configured':bool(store and store.public()['configured']),'refresh_interval':getattr(self.server,'refresh_interval',30)}});return
  if path=='/api/settings':
   if not self.require_admin():return
   self.send_json(200,{'result':'success','data':self.server.settings.public()});return
  export=re.fullmatch(r'/api/exports/([A-Za-z0-9_-]+)/(status|download)',path)
  if export:
   owner,bi=self.auth()
   if not bi:self.unauthorized();return
   identifier,action=export.groups()
   try:
    data=self.server.exports.status(identifier,owner,bi)
    if action=='status':self.send_json(200,{'result':'success','data':data});return
    job=self.server.exports.get(identifier,owner)
    if job['status']!='done' or not job['uri']:raise ExportError('The segment is not ready yet.',409)
    encoded='/'.join(urllib.parse.quote(part,safe='') for part in job['uri'].split('/'))
    request=urllib.request.Request(self.server.bi+'/clips/'+encoded+'?'+urllib.parse.urlencode({'session':bi,'dl':1}))
    with urllib.request.urlopen(request,timeout=30) as r:
     content=r.headers.get('Content-Type','')
     if content.lower().startswith(('text/','application/json')):raise ExportError('BI did not return an MP4 file.',502)
     self.send_response(200);self.headers_common();self.send_header('Content-Type','video/mp4');self.send_header('Content-Disposition','attachment; filename="'+job['filename']+'"');self.send_header('Cache-Control','no-store')
     length=r.headers.get('Content-Length')
     if length:self.send_header('Content-Length',length)
     else:self.send_header('Connection','close');self.close_connection=True
     self.end_headers()
     while True:
      chunk=r.read1(65536)
      if not chunk:break
      self.wfile.write(chunk)
     self.wfile.flush()
    try:self.server.exports.cleanup(identifier)
    except (OSError,ValueError):pass
   except ExportError as e:self.send_json(e.code,{'result':'fail','data':{'reason':str(e)}})
   except (BrokenPipeError,ConnectionResetError):self.close_connection=True
   except (OSError,ValueError,TypeError):self.close_connection=True
   return
  if path.startswith('/api/media/'):
   _,bi=self.auth()
   if not bi:self.unauthorized();return
   resource=path[len('/api/media/'):]
   if '\\' in resource or any(p in {'.','..'} for p in resource.split('/')) or not re.fullmatch(r'(?:image/[^/]+|thumbs/[^/]+|mjpg/[^/]+/video\.mjpg|file/clips/.+)',resource):
    self.send_json(400,{'result':'fail','data':{'reason':'Invalid media request.'}});return
   params={k:v for k,v in urllib.parse.parse_qsl(url.query) if k in MEDIA_KEYS};params['session']=bi
   encoded='/'.join(urllib.parse.quote(part,safe='') for part in resource.split('/'))
   request=urllib.request.Request(self.server.bi+'/'+encoded+'?'+urllib.parse.urlencode(params))
   streaming=False
   try:
    with urllib.request.urlopen(request,timeout=20) as r:
     content=r.headers.get('Content-Type','application/octet-stream')
     if not content.lower().startswith(('image/','multipart/','video/','audio/','application/octet-stream')):self.unauthorized();return
     if content.lower().startswith('image/'):
      image=r.read(16*1024*1024+1)
      if len(image)>16*1024*1024:self.send_json(502,{'result':'fail','data':{'reason':'Image exceeds the supported frame size.'}});return
      self.send_response(r.status);self.headers_common();self.send_header('Content-Type',content);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(image)));self.end_headers();streaming=True;self.wfile.write(image);return
     self.send_response(r.status);self.headers_common();self.send_header('Content-Type',content);self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();self.close_connection=True;streaming=True
     while True:
      chunk=r.read1(65536)
      if not chunk:break
      self.wfile.write(chunk);self.wfile.flush()
   except urllib.error.HTTPError as e:self.send_json(e.code,{'result':'fail','data':{'reason':'BI could not serve that footage.'}})
   except (BrokenPipeError,ConnectionResetError):pass
   except OSError:
    # After streaming headers are sent, end the connection rather than emit a second response.
    if streaming:self.close_connection=True
    else:self.send_json(502,{'result':'fail','data':{'reason':'The recorder could not load this footage.'}})
   return
  if path.startswith('/api/'):
   self.send_json(404,{'result':'fail'});return
  relative='index.html' if path=='/' else path.lstrip('/')
  if relative not in {'index.html','index.htm','login.html','login.js','styles.css','app.js','core.js','sample.svg','settings.html','settings.js'}:
   self.send_json(404,{'result':'fail'});return
  if relative=='index.htm':relative='index.html'
  file=WEB/relative
  if not file.exists():self.send_json(404,{'result':'fail'});return
  data=file.read_bytes();self.send_response(200);self.headers_common();self.send_header('Content-Type',(mimetypes.guess_type(str(file))[0] or 'application/octet-stream')+'; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-cache');self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'self'; form-action 'self'");self.end_headers();self.wfile.write(data)

def parse_options(argv=None):
 parser=argparse.ArgumentParser(description='NVR Watch web service')
 parser.add_argument('--config',type=Path,help='JSON file containing bi, host and port settings')
 parser.add_argument('--data-dir',type=Path,default=Path(os.environ.get('NVR_WATCH_DATA_DIR',Path.home()/'.config/nvr-watch')),help='Persistent settings and credential-key directory')
 parser.add_argument('--host');parser.add_argument('--port',type=int);parser.add_argument('--bi',help='Blue Iris web API URL, including its port')
 args=parser.parse_args(argv);config={}
 if args.config:
  try:config=json.loads(args.config.read_text())
  except (OSError,ValueError):parser.error('Could not read the configuration JSON file.')
  if not isinstance(config,dict):parser.error('Configuration must be a JSON object.')
 for key,default in [('host','0.0.0.0'),('port',8090),('bi','')]:
  if getattr(args,key) is None:setattr(args,key,config.get(key,default))
 if type(args.port) is not int or not 1<=args.port<=65535:parser.error('Port must be a number from 1 to 65535.')
 if not isinstance(args.host,str) or not args.host:parser.error('Host must be a listening address.')
 if not isinstance(args.bi,str):parser.error('BI must be an HTTP or HTTPS URL.')
 if not args.bi:return args
 url=urllib.parse.urlsplit(args.bi)
 if url.scheme not in {'http','https'} or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {'','/'}:parser.error('BI must be an HTTP or HTTPS server URL, without credentials or a path.')
 try:url.port
 except ValueError:parser.error('BI URL has an invalid port.')
 return args

def main():
 args=parse_options()
 store=SettingsStore(args.data_dir,{'bi':args.bi.rstrip('/')})
 server=ThreadingHTTPServer((args.host,args.port),Handler);server.daemon_threads=True;server.settings=store;server.bi=store.data.get('bi') or args.bi.rstrip('/');server.refresh_interval=store.data['refresh_interval'];server.exports=ExportManager(server.bi,upstream_json)
 if store.new_admin_code:print('Initial administrator access code: '+(store.folder/'admin-access-code').read_text().strip(),flush=True)
 def housekeeping():
  while True:
   time.sleep(5);server.exports.cleanup_expired()
 threading.Thread(target=housekeeping,daemon=True).start()
 print(f'NVR Watch listening on port {args.port}',flush=True);server.serve_forever()
if __name__=='__main__':main()
