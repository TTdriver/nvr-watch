import json,tempfile,unittest
from pathlib import Path
from settings import SettingsStore,SettingsError
class SettingsTests(unittest.TestCase):
 def test_encrypted_persistence_and_redaction(self):
  with tempfile.TemporaryDirectory() as folder:
   store=SettingsStore(folder);code=(Path(folder)/'admin-access-code').read_text().strip()
   self.assertTrue(store.check_code(code));self.assertFalse(store.check_code('wrong'))
   candidate=store.candidate({'scheme':'http','hostname':'recorder.local','port':81,'username':'viewer','password':'private-test-password','refresh_interval':20})
   store.save(candidate)
   self.assertNotIn('private-test-password',(Path(folder)/'settings.json').read_text())
   self.assertNotIn('password',store.public());self.assertTrue(store.public()['password_saved'])
   recreated=SettingsStore(folder);self.assertEqual(recreated.password(),'private-test-password');self.assertEqual(recreated.public()['hostname'],'recorder.local')
   self.assertTrue(recreated.check_code(code));self.assertFalse(recreated.new_admin_code)
   self.assertEqual((Path(folder)/'settings.json').stat().st_mode&0o777,0o600)
 def test_validation_and_keep_password(self):
  with tempfile.TemporaryDirectory() as folder:
   store=SettingsStore(folder);body={'scheme':'https','hostname':'recorder.local','port':443,'username':'viewer','password':'existing','refresh_interval':30}
   store.save(store.candidate(body));body['password']='';self.assertEqual(store.candidate(body)['password'],'existing')
   for key,value in [('hostname','host/path'),('hostname','host:81'),('hostname',123),('scheme','file'),('port',0),('refresh_interval',1),('username','')]:
    bad=dict(body);bad[key]=value
    with self.assertRaises(SettingsError):store.candidate(bad)
if __name__=='__main__':unittest.main()
