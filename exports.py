"""Account-scoped segment exports. Cleanup only touches records created here."""
import re,secrets,threading,time

class ExportError(Exception):
 def __init__(self,message,code=400):super().__init__(message);self.code=code

class ExportManager:
 def __init__(self,base,call):self.base=base;self.call=call;self.jobs={};self.lock=threading.RLock()
 def create(self,owner,bi,body):
  path=body.get('path');start=body.get('startms');duration=body.get('msec')
  if not isinstance(path,str) or not re.fullmatch(r'@[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]+)?',path):raise ExportError('Choose a recording to export.')
  if type(start) is not int or type(duration) is not int or start<0 or duration<=0:raise ExportError('Choose a valid start and end time.')
  with self.lock:
   if sum(j['owner']==owner and j['status'] not in {'done','error','cancelled'} for j in self.jobs.values())>=2:raise ExportError('Wait for your current exports to finish.',429)
  permission=self.call(self.base,{'cmd':'login','session':bi})
  if permission.get('result')!='success':raise ExportError('Sign in again to export footage.',401)
  if not permission.get('data',{}).get('clipcreate'):raise ExportError('Your BI account needs permission to export clips.',403)
  stats=self.call(self.base,{'cmd':'clipstats','session':bi,'path':path})
  if stats.get('result')!='success':raise ExportError('BI could not access this recording.',403)
  length=stats.get('data',{}).get('msec',0)
  if not isinstance(length,(int,float)) or start+duration>length:raise ExportError('The selected range must fit inside the recording.')
  result=self.call(self.base,{'cmd':'export','session':bi,'path':path,'startms':start,'msec':duration,'format':1,'profile':0,'reencode':False,'audio':True,'substream':2})
  if result.get('result')!='success':raise ExportError(result.get('data',{}).get('reason','BI could not start the export.'),502)
  data=result.get('data',{});record=data.get('path')
  if not isinstance(record,str) or not re.fullmatch(r'@[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]+)?',record):raise ExportError('BI returned an unexpected export identifier.',502)
  identifier=secrets.token_urlsafe(18);filename=re.sub(r'[^A-Za-z0-9_.-]','_',str(body.get('filename','nvr-watch-segment.mp4')))[:120]
  if not filename.lower().endswith('.mp4'):filename+='.mp4'
  job={'owner':owner,'bi':bi,'source':path,'record':record,'queue_record':record,'camera':stats.get('data',{}).get('camera','index'),'date':stats.get('data',{}).get('date',0),'resolved':False,'created':time.monotonic(),'status':'queued','filename':filename,'polled':0,'uri':None,'progress':0}
  self.update(job,data)
  with self.lock:self.jobs[identifier]=job
  try:self.resolve(job)
  except (OSError,ValueError):pass
  return self.public(identifier,job)
 def update(self,job,data):
  job['status']=str(data.get('status','queued')).lower();job['progress']=max(0,min(100,float(data.get('progress') or 0)));job['error']=str(data.get('error') or '')
  uri=data.get('uri')
  if uri:
   if not isinstance(uri,str) or '\\' in uri or uri.startswith('/') or any(p in {'.','..'} for p in uri.split('/')) or not uri.lower().endswith('.mp4'):raise ExportError('BI returned an unexpected download path.',502)
   job['uri']=uri
 def resolve(self,job):
  # BI 6 returns an internal queue number, while later requests require the
  # timestamp-based database locator. Match only this newly generated filename.
  if job.get('resolved') or not job.get('uri'):return
  date=int(job.get('date') or 0)
  result=self.call(self.base,{'cmd':'cliplist','session':job['bi'],'camera':job.get('camera','index'),'view':'clipboard','startdate':max(0,date-86400),'enddate':date+172800 if date else int(time.time()+86400)})
  rows=result.get('data',[])
  if not isinstance(rows,list):return
  row=next((r for r in rows if r.get('file')==job['uri'] and str(r.get('path','')).lower().endswith('.mp4')),None)
  if row and re.fullmatch(r'@[A-Za-z0-9_-]+\.mp4',row['path'],re.I) and row['path'].split('.')[0]!=job['source'].split('.')[0]:job['record']=row['path'];job['resolved']=True
 def get(self,identifier,owner):
  with self.lock:job=self.jobs.get(identifier)
  if not job or job['owner']!=owner:raise ExportError('Export not found. Prepare the segment again.',404)
  return job
 def status(self,identifier,owner,bi):
  job=self.get(identifier,owner)
  if job['status'] not in {'done','error'} and time.monotonic()-job['polled']>=1:
   job['bi']=bi;self.resolve(job)
   payload={'cmd':'export','session':bi}
   if job.get('resolved'):payload['path']=job['record']
   result=self.call(self.base,payload)
   if result.get('result')!='success' and job.get('resolved'):
    stats=self.call(self.base,{'cmd':'clipstats','session':bi,'path':job['record']})
    details=stats.get('data',{})
    if stats.get('result')=='success' and details.get('file')==job['uri'] and not int(details.get('flags',512))&512:
     job['status']='done';job['progress']=100;job['polled']=time.monotonic()
     return self.public(identifier,job)
   if result.get('result')!='success':raise ExportError('BI could not check the export.',502)
   rows=result.get('data',[])
   if isinstance(rows,dict):rows=[rows]
   data=next((item for item in rows if item.get('path','').split('.')[0] in {job['record'].split('.')[0],job.get('queue_record',job['record']).split('.')[0]}),None)
   if data is None:raise ExportError('BI no longer reports this download. Please try again.',502)
   self.update(job,data);job['polled']=time.monotonic();job['bi']=bi
  return self.public(identifier,job)
 def public(self,identifier,job):
  return {'id':identifier,'status':job['status'],'progress':job['progress'],'error':job.get('error',''),'download':f'/api/exports/{identifier}/download' if job['status']=='done' and job['uri'] else None}
 def cleanup(self,identifier):
  with self.lock:job=self.jobs.get(identifier)
  if not job:return
  # Never delete a source record, even if a provider returns an alias or bad response.
  if job.get('cancelled_at'):job['resolved']=False
  self.resolve(job)
  if job.get('cancelled_at') and not job.get('resolved'):
   if time.monotonic()-job['cancelled_at']>3600:
    with self.lock:self.jobs.pop(identifier,None)
   return
  safe=job.get('resolved') and job.get('uri') and job['record'].split('.')[0]!=job['source'].split('.')[0]
  if safe:
   stats=self.call(self.base,{'cmd':'clipstats','session':job['bi'],'path':job['record']})
   details=stats.get('data',{})
   if stats.get('result')!='success':
    if job.get('cancelled_at') and time.monotonic()-job['cancelled_at']>60:
     with self.lock:self.jobs.pop(identifier,None)
    return
   if details.get('file')!=job['uri']:return
   if int(details.get('flags',512))&512:
    result=self.call(self.base,{'cmd':'export','session':job['bi'],'path':job['record'],'delete':True})
   else:
    # Completed BI 6 exports become normal Clipboard MP4 records. Only this
    # verified generated product is deleted; source footage is never eligible.
    result=self.call(self.base,{'cmd':'delclip','session':job['bi'],'path':job['record'],'flags':0})
   if result.get('result')!='success':return
   if int(details.get('flags',512))&512:
    # BI can finish an active conversion after accepting queued deletion.
    # Retain its identity and retry cleanup so cancellation leaves no copy.
    job['cancelled_at']=job.get('cancelled_at',time.monotonic());job['status']='cancelled';return
  with self.lock:self.jobs.pop(identifier,None)
 def cancel(self,identifier,owner,bi):
  job=self.get(identifier,owner);job['bi']=bi
  self.resolve(job)
  if not job.get('resolved'):raise ExportError('BI has not registered the export yet. Try Cancel again shortly.',409)
  self.cleanup(identifier)
  if identifier in self.jobs and not job.get('cancelled_at'):raise ExportError('BI could not cancel this export. Try again shortly.',502)
  return {'status':'cancelled'}
 def cleanup_expired(self):
  with self.lock:expired=[i for i,j in self.jobs.items() if j.get('cancelled_at') or time.monotonic()-j['created']>3600]
  for i in expired:
   try:
    self.cleanup(i)
   except (OSError,ValueError,TypeError,ExportError):pass
