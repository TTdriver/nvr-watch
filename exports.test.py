import unittest
from exports import ExportManager,ExportError
class ExportTests(unittest.TestCase):
 def setUp(self):
  self.calls=[]
  def call(base,p):
   self.calls.append(p)
   if p['cmd']=='login':return {'result':'success','data':{'clipcreate':True}}
   if p['cmd']=='clipstats':return {'result':'success','data':{'msec':3600000,'file':'generated.mp4','flags':512}}
   if p['cmd']=='cliplist':return {'result':'success','data':[{'path':'@export.mp4','file':'generated.mp4'}]}
   if p.get('delete'):return {'result':'success'}
   if 'startms' in p:return {'result':'success','data':{'path':'@export.mp4','status':'queued','uri':'generated.mp4'}}
   return {'result':'success','data':{'path':'@export.mp4','status':'done','uri':'generated.mp4'}}
  self.manager=ExportManager('http://unused',call)
 def test_create_and_owner(self):
  job=self.manager.create('owner','bi-secret',{'path':'@source.bvr','startms':0,'msec':3600000})
  request=next(c for c in self.calls if 'startms' in c);self.assertEqual(request['msec'],3600000);self.assertFalse(request['reencode']);self.assertEqual(request['substream'],2)
  self.assertNotIn('record',job);self.assertNotIn('bi',job)
  with self.assertRaises(ExportError):self.manager.get(job['id'],'other-owner')
  status=self.manager.status(job['id'],'owner','bi-secret');self.assertEqual(status['status'],'done');self.manager.cleanup(job['id']);self.assertEqual(self.calls[-1]['path'],'@export.mp4');self.assertTrue(self.calls[-1]['delete'])
 def test_cancel_pending(self):
  job=self.manager.create('owner','bi',{'path':'@source.bvr','startms':0,'msec':1000})
  with self.assertRaises(ExportError):self.manager.cancel(job['id'],'other','bi')
  self.assertEqual(self.manager.cancel(job['id'],'owner','bi')['status'],'cancelled')
  self.assertEqual(self.calls[-1]['path'],'@export.mp4');self.assertTrue(self.calls[-1]['delete'])
 def test_bi6_completed_record_and_cleanup(self):
  calls=[]
  def call(base,p):
   calls.append(p)
   if p['cmd']=='login':return {'result':'success','data':{'clipcreate':True}}
   if p['cmd']=='clipstats':return {'result':'success','data':{'camera':'camera','date':1700000000,'msec':3600000,'file':'generated.mp4' if p['path']=='@timestamp.mp4' else 'source.bvr','flags':1024}}
   if p['cmd']=='cliplist':return {'result':'success','data':[{'path':'@timestamp.mp4','file':'generated.mp4'}]}
   if 'startms' in p:return {'result':'success','data':{'path':'@42','uri':'generated.mp4','status':'queued'}}
   if p['cmd']=='delclip':return {'result':'success'}
   return {'result':'fail','data':{'status':'Clip not BVR'}}
  manager=ExportManager('http://unused',call)
  job=manager.create('owner','bi',{'path':'@source.bvr','startms':0,'msec':1000})
  self.assertEqual(manager.status(job['id'],'owner','bi')['status'],'done')
  manager.cleanup(job['id']);self.assertEqual(calls[-1]['cmd'],'delclip');self.assertEqual(calls[-1]['path'],'@timestamp.mp4')
 def test_cleanup_rejects_filename_mismatch(self):
  job=self.manager.create('owner','bi',{'path':'@source.bvr','startms':0,'msec':1000})
  self.manager.jobs[job['id']]['uri']='different.mp4'
  self.manager.cleanup(job['id'])
  self.assertFalse(any(c.get('delete') or c['cmd']=='delclip' for c in self.calls))
 def test_bounds(self):
  for start,length in [(-1,1000),(0,0),(3599000,2000)]:
   with self.assertRaises(ExportError):self.manager.create('owner','bi',{'path':'@source.bvr','startms':start,'msec':length})
  self.assertFalse(any(c.get('cmd')=='export' for c in self.calls))
 def test_never_delete_source_alias(self):
  self.manager.jobs['job']={'owner':'owner','bi':'bi','source':'@source.bvr','record':'@source.mp4','status':'done','uri':'source.mp4'}
  self.manager.cleanup('job');self.assertFalse(any(c.get('delete') for c in self.calls))
if __name__=='__main__':unittest.main()
