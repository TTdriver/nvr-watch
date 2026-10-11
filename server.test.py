import importlib.util,unittest,threading,json,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
spec=importlib.util.spec_from_file_location('watch',Path(__file__).with_name('server.py'));watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)
class AdapterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.calls=[]
  def fake(base,body):
   cls.calls.append(body)
   if body['cmd']=='login':return {'result':'success','session':'fake-bi-session','data':{'admin':False,'clips':True,'license':'private-license'}}
   return {'result':'success','data':[]}
  watch.upstream_json=fake;cls.server=watch.ThreadingHTTPServer(('127.0.0.1',0),watch.Handler);cls.server.bi='http://unused';cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def post(self,path,body,opener=None,headers=None):
  request=urllib.request.Request(self.url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**(headers or {})})
  return opener.open(request) if opener else urllib.request.urlopen(request)
 def test_unauthenticated(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.post('/api/json',{'cmd':'camlist'})
  self.assertEqual(e.exception.code,401)
 def test_login_and_filtering(self):
  opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  with self.post('/api/login',{'username':'test','password':'test'},opener) as r:
   data=json.load(r);self.assertNotIn('session',data);self.assertNotIn('license',data['data']);self.assertIn('HttpOnly',r.headers['Set-Cookie'])
  with self.post('/api/json',{'cmd':'cliplist','camera':'garage','delete':True,'session':'attacker'},opener) as r:self.assertEqual(json.load(r)['result'],'success')
  call=self.calls[-1];self.assertNotIn('delete',call);self.assertEqual(call['session'],'fake-bi-session')
  with self.assertRaises(urllib.error.HTTPError) as e:self.post('/api/json',{'cmd':'camconfig','camera':'garage','enable':False},opener)
  self.assertEqual(e.exception.code,403)
  with self.post('/api/json',{'cmd':'logout'},opener) as r:self.assertEqual(json.load(r)['result'],'success')
  with self.assertRaises(urllib.error.HTTPError):self.post('/api/json',{'cmd':'camlist'},opener)
 def test_cross_origin_blocked(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.post('/api/login',{'username':'test','password':'test'},headers={'Origin':'http://other.example'})
  self.assertEqual(e.exception.code,403)
if __name__=='__main__':unittest.main()
