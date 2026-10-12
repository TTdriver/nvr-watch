#!/usr/bin/env python3
"""Install NVR Watch for the current Linux user, without sudo."""
import argparse,importlib.util,json,shutil,subprocess,sys,venv
from pathlib import Path
from server import parse_options

def unit_quote(value):
 return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'

def install(app,config,units,bi=None,port=None,start=True,python_executable=None):
 source=Path(__file__).resolve().parent
 settings=json.loads((config/'config.json').read_text()) if (config/'config.json').exists() else {'bi':'','host':'0.0.0.0','port':8090}
 if bi is not None:settings['bi']=bi
 if port is not None:settings['port']=port
 # Validate before writing or changing any service.
 options=parse_options(['--bi',settings['bi'],'--host',settings['host'],'--port',str(settings['port'])])
 settings={'bi':options.bi,'host':options.host,'port':options.port}
 for folder in (app,config,units):folder.mkdir(parents=True,exist_ok=True)
 if source.resolve()!=app.resolve():
  for name in ['server.py','exports.py','settings.py','requirements.txt','install.py','README.md','AI-SETUP.md','config.example.json']:
   shutil.copy2(source/name,app/name)
  shutil.copytree(source/'web',app/'web',dirs_exist_ok=True)
 configfile=config/'config.json';configfile.write_text(json.dumps(settings,indent=2)+'\n');configfile.chmod(0o600)
 service='''[Unit]
Description=NVR Watch web interface
After=network.target

[Service]
Type=simple
ExecStart={python} {server} --config {config}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
'''.format(python=unit_quote(python_executable or sys.executable),server=unit_quote(app/'server.py'),config=unit_quote(configfile))
 (units/'nvr-watch.service').write_text(service)
 if start:
  subprocess.run(['systemctl','--user','daemon-reload'],check=True)
  subprocess.run(['systemctl','--user','enable','nvr-watch.service'],check=True)
  subprocess.run(['systemctl','--user','restart','nvr-watch.service'],check=True)
 return settings

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--bi',help='BI web server URL; existing value is preserved on updates')
 parser.add_argument('--port',type=int,help='NVR Watch port (default 8090)')
 parser.add_argument('--no-start',action='store_true',help='Install files and service without enabling or starting it')
 args=parser.parse_args()
 if sys.platform!='linux':parser.error('The service installer is for Linux. On Windows or macOS, run server.py directly.')
 root=Path.home();app=root/'.local/share/nvr-watch';config=root/'.config/nvr-watch';units=root/'.config/systemd/user'
 try:
  if importlib.util.find_spec('ensurepip') is None:parser.exit(1,'The Linux installer needs Python venv support. On Debian/Ubuntu, install python3-venv first. Docker needs no host Python installation.\n')
  app.mkdir(parents=True,exist_ok=True)
  environment=app/'.venv';venv.EnvBuilder(with_pip=True).create(environment)
  executable=environment/'bin/python'
  subprocess.run([str(executable),'-m','pip','install','-r',str(Path(__file__).resolve().parent/'requirements.txt')],check=True)
  settings=install(app,config,units,args.bi,args.port,not args.no_start,executable)
 except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:parser.exit(1,'Install failed: '+str(e)+'\n')
 print('Application:',app);print('Configuration:',config/'config.json');print('Service:',units/'nvr-watch.service')
 print('Open http://<this-computer-address>:'+str(settings['port'])+'/ and sign in with your BI account.')
if __name__=='__main__':main()
