"""Black-box Docker Compose verification used by CI."""
import argparse,http.cookiejar,json,subprocess,tempfile,urllib.request
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
 credentials={'username':'test-admin','password':'not-a-real-password'}
 expected=Path(tempfile.gettempdir())/'nvr-watch-container-check.json'
 if args.verify_persistence:
  prior=json.loads(expected.read_text());request('/api/login',credentials);data=request('/api/settings')['data']
  assert data['hostname']=='bi-reference' and data['refresh_interval']==15 and data['password_saved']
  assert data['hostname']==prior['hostname']
  request('/api/login-saved',{});assert len(request('/api/json',{'cmd':'camlist'})['data'])==1
  expected.unlink();print('PASS: settings, encrypted password and Blue Iris administrator sign-in survive container recreation.')
 else:
  values={'scheme':'http','hostname':'bi-reference','port':8081,'username':'test-admin','password':'not-a-real-password','refresh_interval':15}
  assert request('/api/settings/test',values)['data']['connected']
  assert request('/api/settings',values)['data']['admin']
  public=request('/api/settings')['data'];assert public['password_saved'] and 'password' not in public
  assert 'not-a-real-password' not in read_data('settings.json')
  request('/api/login-saved',{});assert len(request('/api/json',{'cmd':'camlist'})['data'])==1
  expected.write_text(json.dumps({'hostname':public['hostname']}));print('PASS: Docker health, settings UI API, connection test, account access and credential encryption.')
if __name__=='__main__':main()
