"""Black-box Docker Compose verification used by CI."""
import argparse,hashlib,http.cookiejar,json,subprocess,tempfile,urllib.request
from pathlib import Path
COMPOSE=['docker','compose','-f','compose.build.yaml','-f','compose.test.yaml']
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--url',required=True);parser.add_argument('--verify-persistence',action='store_true');args=parser.parse_args()
 client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def request(path,body=None):
  req=urllib.request.Request(args.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
  with client.open(req,timeout=15) as response:return json.load(response)
 def read_data(name):return subprocess.check_output(COMPOSE+['exec','-T','nvr-watch','python','-c',f'from pathlib import Path; print(Path("/data/{name}").read_text(),end="")'],text=True).strip()
 assert request('/healthz')['status']=='ok'
 code=read_data('admin-access-code');request('/api/admin/login',{'code':code})
 expected=Path(tempfile.gettempdir())/'nvr-watch-container-check.json'
 if args.verify_persistence:
  prior=json.loads(expected.read_text());data=request('/api/settings')['data']
  assert data['hostname']=='bi-reference' and data['refresh_interval']==15 and data['password_saved']
  assert hashlib.sha256(code.encode()).hexdigest()==prior['code_hash']
  request('/api/login-saved',{});assert len(request('/api/json',{'cmd':'camlist'})['data'])==1
  expected.unlink();print('PASS: settings, encrypted password and administrator access survive container recreation.')
 else:
  values={'scheme':'http','hostname':'bi-reference','port':8081,'username':'test-viewer','password':'not-a-real-password','refresh_interval':15}
  assert request('/api/settings/test',values)['data']['connected']
  public=request('/api/settings',values)['data'];assert public['password_saved'] and 'password' not in public
  assert 'not-a-real-password' not in read_data('settings.json')
  request('/api/login-saved',{});assert len(request('/api/json',{'cmd':'camlist'})['data'])==1
  expected.write_text(json.dumps({'code_hash':hashlib.sha256(code.encode()).hexdigest()}));print('PASS: Docker health, settings UI API, connection test, account access and credential encryption.')
if __name__=='__main__':main()
