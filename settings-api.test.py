import http.cookiejar,importlib.util,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from settings import SettingsStore
from exports import ExportManager
spec=importlib.util.spec_from_file_location('watch_settings_test',Path(__file__).with_name('server.py'));watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)
class SettingsAPITests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.settings=SettingsStore(self.temp.name)
  self.calls=[]
  def upstream(base,p):
   self.calls.append((base,p))
   if p['cmd']=='login' and not p.get('session'):return {'result':'fail','session':'challenge'}
   if p['cmd']=='login':return {'result':'success','data':{'admin':False,'clipcreate':True}}
   if p['cmd']=='camlist':return {'result':'success','data':[{'optionValue':'cam1','optionDisplay':'Camera'}]}
   return {'result':'success','data':{}}
  watch.upstream_json=upstream;self.server=watch.ThreadingHTTPServer(('127.0.0.1',0),watch.Handler);self.server.bi='http://old.example:81';self.server.settings=self.settings;self.server.exports=ExportManager(self.server.bi,upstream);self.server.refresh_interval=30
  threading.Thread(target=self.server.serve_forever,daemon=True).start();self.url='http://127.0.0.1:'+str(self.server.server_port)
  self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def tearDown(self):self.server.shutdown();self.server.server_close();self.temp.cleanup()
 def request(self,path,body=None):
  request=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
  with self.client.open(request) as r:return json.load(r)
 def unlock(self):self.request('/api/admin/login',{'code':(Path(self.temp.name)/'admin-access-code').read_text().strip()})
 def body(self):return {'scheme':'http','hostname':'recorder.example','port':81,'username':'viewer','password':'private-example-password','refresh_interval':15}
 def test_admin_required_and_redaction(self):
  for path in ['/api/settings','/api/settings/test']:
   with self.assertRaises(urllib.error.HTTPError) as error:self.request(path,self.body() if path.endswith('test') else None)
   self.assertEqual(error.exception.code,403)
  self.unlock();result=self.request('/api/settings/test',self.body())
  self.assertEqual(result['data']['cameras'],1);self.assertNotIn('session',result['data']);self.assertNotIn('password',json.dumps(result))
  result=self.request('/api/settings',self.body());self.assertTrue(result['data']['password_saved']);self.assertNotIn('private-example-password',json.dumps(result));self.assertEqual(self.server.bi,'http://recorder.example:81')
  self.assertEqual(SettingsStore(self.temp.name).password(),'private-example-password')
  with self.client.open(self.url+'/api/client-config') as r:self.assertEqual(json.load(r)['data']['refresh_interval'],15)
 def test_regular_bi_user_is_not_admin(self):
  self.request('/api/login',{'username':'viewer','password':'viewer'})
  with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/settings')
  self.assertEqual(error.exception.code,403)
 def test_unavailable_error_does_not_save(self):
  self.unlock()
  def fail(*args):raise urllib.error.URLError('unreachable')
  watch.upstream_json=fail
  with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/settings',self.body())
  result=json.load(error.exception);self.assertIn('Cannot reach Blue Iris',result['data']['reason']);self.assertFalse(self.settings.path.exists())
if __name__=='__main__':unittest.main()
