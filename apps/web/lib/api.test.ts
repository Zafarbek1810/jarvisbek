import { describe, it, expect } from 'vitest';
import { parseStream } from './api';
describe('oqimli javob',()=>{
 it('bo‘lingan UTF-8 va satrlarni saqlaydi',async()=>{
  const encoded=new TextEncoder().encode('{"type":"delta","content":"O‘zbekcha"}\n{"type":"done"}\n');
  const stream=new ReadableStream<Uint8Array>({start(c){c.enqueue(encoded.slice(0,29));c.enqueue(encoded.slice(29,31));c.enqueue(encoded.slice(31));c.close();}});
  const result=[];for await(const item of parseStream(stream.getReader()))result.push(item);
  expect(result).toEqual([{type:'delta',content:'O‘zbekcha'},{type:'done'}]);
 });
});

import {beforeEach,vi} from 'vitest';
import {request,restoreSession,useSession} from './api';
beforeEach(()=>{useSession.getState().clear();vi.unstubAllGlobals();});
it('bir vaqtdagi sessiya tiklash so‘rovlarini birlashtiradi',async()=>{
 const fetch=vi.fn(async()=>new Response(JSON.stringify({access_token:'new-token',user:{id:'one',name:'Ali',email:'ali@example.uz'}}),{status:200}));
 vi.stubGlobal('fetch',fetch);
 expect(await Promise.all([restoreSession(),restoreSession()])).toEqual([true,true]);
 expect(fetch).toHaveBeenCalledTimes(1);expect(useSession.getState().token).toBe('new-token');
});
it('muddati tugagan tokenni yangilab, so‘rovni qaytaradi',async()=>{
 useSession.getState().setSession('expired',{id:'one',name:'Ali',email:'ali@example.uz'});
 const fetch=vi.fn().mockResolvedValueOnce(new Response('{}',{status:401})).mockResolvedValueOnce(new Response(JSON.stringify({access_token:'fresh',user:{id:'one',name:'Ali',email:'ali@example.uz'}}),{status:200})).mockResolvedValueOnce(new Response('{"items":[]}',{status:200}));
 vi.stubGlobal('fetch',fetch);expect((await request('/tasks')).status).toBe(200);
 expect(new Headers(fetch.mock.calls[2][1].headers).get('Authorization')).toBe('Bearer fresh');
});
it('tarmoq xatosini o‘zbekcha ko‘rsatadi',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('network')));await expect(request('/tasks')).rejects.toThrow('Serverga ulanib bo‘lmadi.');});
it('buzilgan oqimni foydalanuvchiga tushunarli xatoga aylantiradi',async()=>{
 const stream=new ReadableStream<Uint8Array>({start(c){c.enqueue(new TextEncoder().encode('broken\n'));c.close();}});
 await expect((async()=>{for await(const event of parseStream(stream.getReader()))void event;})()).rejects.toThrow('Javob oqimi uzildi yoki buzildi.');
});
