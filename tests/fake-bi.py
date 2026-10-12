"""Docker integration fixture; no real credentials or footage."""
import hashlib,json,secrets
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sessions=set();password='not-a-real-password'
class FakeBI(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,data,code=200):
  blob=json.dumps(data).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(blob)));self.end_headers();self.wfile.write(blob)
 def do_GET(self):self.reply({'status':'ok'})
 def do_POST(self):
  p=json.loads(self.rfile.read(int(self.headers['Content-Length'])));cmd=p.get('cmd');session=p.get('session')
  if cmd=='login' and not session:
   session=secrets.token_hex(16);sessions.add(session);self.reply({'result':'fail','session':session});return
  if session not in sessions:self.reply({'result':'fail','data':{'reason':'INVALID SESSION'}});return
  if cmd=='login':
   response=p.get('response')
   if response and response!=hashlib.md5(f'test-admin:{session}:{password}'.encode()).hexdigest():self.reply({'result':'fail','data':{'reason':'Invalid login'}});return
   self.reply({'result':'success','session':session,'data':{'admin':True,'clips':True,'clipcreate':True,'audio':True,'version':'fixture'}});return
  data=[]
  if cmd=='camlist':data=[{'optionValue':'cam1','optionDisplay':'Test camera','isOnline':True}]
  self.reply({'result':'success','data':data})
ThreadingHTTPServer(('0.0.0.0',8081),FakeBI).serve_forever()
