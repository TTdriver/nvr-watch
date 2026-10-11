import json,tempfile,unittest
from pathlib import Path
from install import install
from server import parse_options
class InstallationTests(unittest.TestCase):
 def test_clean_install_and_preserved_connection(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);app=root/'application with spaces';config=root/'config';units=root/'services'
   install(app,config,units,'http://192.0.2.10:81',8099,start=False)
   self.assertTrue((app/'web/app.js').exists());self.assertTrue((app/'exports.py').exists())
   self.assertIn('"'+str(app/'server.py')+'"',(units/'nvr-watch.service').read_text())
   install(app,config,units,start=False)
   self.assertEqual(json.loads((config/'config.json').read_text())['bi'],'http://192.0.2.10:81')
   self.assertEqual((config/'config.json').stat().st_mode&0o777,0o600)
 def test_config_and_cli_override(self):
  with tempfile.TemporaryDirectory() as folder:
   config=Path(folder)/'config.json';config.write_text(json.dumps({'bi':'http://192.0.2.10:81','port':8099}))
   args=parse_options(['--config',str(config),'--port','8090'])
   self.assertEqual(args.bi,'http://192.0.2.10:81');self.assertEqual(args.port,8090)
if __name__=='__main__':unittest.main()
