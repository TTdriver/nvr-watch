"""Persistent recorder settings."""
import ipaddress,json,os,re,tempfile,threading
from pathlib import Path
from urllib.parse import urlsplit
from cryptography.fernet import Fernet,InvalidToken

class SettingsError(ValueError):pass

class SettingsStore:
 def __init__(self,folder,initial=None):
  self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.folder.chmod(0o700)
  self.lock=threading.RLock();self.path=self.folder/'settings.json'
  keyfile=self.folder/'encryption.key'
  if not keyfile.exists():self.write(keyfile,Fernet.generate_key())
  self.fernet=Fernet(keyfile.read_bytes())
  self.data=json.loads(self.path.read_text()) if self.path.exists() else dict(initial or {})
  self.data.setdefault('refresh_interval',30)
 def write(self,path,blob):
  descriptor,name=tempfile.mkstemp(prefix='.write-',dir=self.folder)
  try:
   os.fchmod(descriptor,0o600)
   with os.fdopen(descriptor,'wb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
   os.replace(name,path)
  finally:
   if os.path.exists(name):os.unlink(name)
 def public(self):
  with self.lock:
   url=urlsplit(self.data.get('bi',''))
   return {'configured':bool(url.hostname),'scheme':url.scheme or 'http','hostname':url.hostname or '', 'port':url.port or (443 if url.scheme=='https' else 80 if url.hostname else 81),'username':self.data.get('username',''),'password_saved':bool(self.data.get('password_encrypted')),'refresh_interval':self.data.get('refresh_interval',30)}
 def password(self):
  value=self.data.get('password_encrypted')
  try:return self.fernet.decrypt(value.encode()).decode() if value else ''
  except InvalidToken:raise SettingsError('The saved password cannot be decrypted. Restore the matching encryption key or enter the BI password again.')
 def candidate(self,body):
  scheme=body.get('scheme');host=body.get('hostname','');port=body.get('port');username=body.get('username','');password=body.get('password','');interval=body.get('refresh_interval',30)
  if not isinstance(host,str):raise SettingsError('Enter an IP address or hostname.')
  host=host.strip()
  if scheme not in {'http','https'}:raise SettingsError('Choose HTTP or HTTPS.')
  if not isinstance(host,str) or not host or len(host)>253 or not re.fullmatch(r'[A-Za-z0-9._:-]+',host):raise SettingsError('Enter an IP address or hostname without a protocol, path or port.')
  if ':' in host:
   try:ipaddress.IPv6Address(host)
   except ValueError:raise SettingsError('Enter a valid IPv6 address, or put the port in its separate field.')
   host='['+host+']'
  if type(port) is not int or not 1<=port<=65535:raise SettingsError('Web server port must be between 1 and 65535.')
  if not isinstance(username,str) or not username.strip() or len(username)>128:raise SettingsError('Enter a Blue Iris username.')
  if not isinstance(password,str) or len(password)>1024:raise SettingsError('Password is too long.')
  if type(interval) is not int or not 10<=interval<=300:raise SettingsError('Refresh interval must be between 10 and 300 seconds.')
  if not password:
   with self.lock:password=self.password()
  if not password:raise SettingsError('Enter a Blue Iris password.')
  return {'bi':f'{scheme}://{host}:{port}','username':username.strip(),'password':password,'refresh_interval':interval}
 def save(self,candidate):
  with self.lock:
   data={k:v for k,v in candidate.items() if k!='password'}
   data['password_encrypted']=self.fernet.encrypt(candidate['password'].encode()).decode()
   self.write(self.path,(json.dumps(data,indent=2)+'\n').encode());self.data=data
  return self.public()
