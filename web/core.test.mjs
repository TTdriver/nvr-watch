import assert from 'node:assert/strict';
import {dayBounds,dayKey,normalizeClip,overlaps,clipAt,safePath,cameraData,mediaURL} from './core.js';
process.env.TZ='America/Chicago';
assert.equal(dayBounds('2026-03-08').end-dayBounds('2026-03-08').start,23*3600);
assert.equal(dayBounds('2026-11-01').end-dayBounds('2026-11-01').start,25*3600);
const b=dayBounds('2026-10-10'),c=normalizeClip({date:b.start-600,msec:3600000,path:'@123.bvr',camera:'garage'});
assert(overlaps(c,b));assert.equal(clipAt([c],b.start+30),c);assert.equal(clipAt([c],c.end),null);
assert(!overlaps(normalizeClip({date:b.start-3600,msec:3600000}),b));
assert.equal(cameraData([{optionValue:'index',group:['garage']},{optionValue:'garage',optionDisplay:'Garage',isOnline:true}]).length,1);
assert.equal(safePath('@123 clip.bvr'),'\u0040123%20clip.bvr'.replace('@','%40'));
const u=new URL(mediaURL('http://localhost:8081/','file/clips/@123.bvr','test-session',{time:42,speed:100}));assert.equal(u.searchParams.get('time'),'42');assert.equal(u.searchParams.get('session'),'test-session');
assert.equal(dayKey(new Date(2026,0,2)),'2026-01-02');
console.log('Passed date/DST, overlapping clips, camera filtering and authenticated URL checks.');

const event=normalizeClip({date:b.start+100,path:"@event.jpg",clip:"@clip.bvr",offset:15000,msec:10000});assert.equal(event.path,"@clip.bvr");assert.equal(event.mediaOffset,15);assert.equal(event.id,"@event.jpg");assert.throws(()=>safePath("../secret"));

assert.equal(cameraData([{optionValue:"+index",optionDisplay:"All cameras cycle"},{optionValue:"garage",optionDisplay:"Garage"}]).length,1);
