'use client';
import {useEffect, useRef, useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Mic, Square, Volume2} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import {Button} from './ui/button';
import {api, request, parseStream} from '../lib/api';

type Turn = {text:string; reply:string; audio?:string};
type Status = {stt_configured:boolean; tts_configured:boolean; tts_voices?:string[]; local_only?:boolean; stt_model?:string; stt_device?:string; stt_models?:{id:string;label:string}[]; tts_engine?:string; local_voices?:{id:string;label:string}[]; message:string};
export function Voice(){
 const [phase,setPhase]=useState<'idle'|'starting'|'recording'|'transcribing'|'review'|'thinking'|'speaking'>('idle');
 const [selectedModel,setSelectedModel]=useState('');
 const [draft,setDraft]=useState('');
 const [localVoice,setLocalVoice]=useState('');
 const [selectedVoice,setSelectedVoice]=useState('uz-UZ-SardorNeural');
 const [error,setError]=useState(''); const [history,setHistory]=useState<Turn[]>([]);
 const recorder=useRef<MediaRecorder|null>(null); const tracks=useRef<MediaStream|null>(null);
 const timer=useRef<ReturnType<typeof setTimeout>|null>(null); const mounted=useRef(true);
 const audio=useRef<HTMLAudioElement|null>(null); const urls=useRef<string[]>([]);
 const conversation=useRef<string|undefined>(undefined); const controller=useRef<AbortController|null>(null);
 const {data,error:statusError,refetch}=useQuery({queryKey:['voice'],queryFn:()=>api<Status>('/voice/status'),refetchInterval:15000});
 useEffect(()=>{mounted.current=true;const audioUrls=urls.current;return ()=>{mounted.current=false;if(timer.current)clearTimeout(timer.current);if(recorder.current){recorder.current.onstop=null;if(recorder.current.state!=='inactive')recorder.current.stop();}tracks.current?.getTracks().forEach(t=>t.stop());controller.current?.abort();audio.current?.pause();audioUrls.forEach(url=>URL.revokeObjectURL(url));};},[]);
 const play=async(url:string)=>{audio.current?.pause();const player=new Audio(url);audio.current=player;player.onended=()=>{if(mounted.current)setPhase('idle');};player.onerror=()=>{if(mounted.current){setError('Ovoz ijro qilinmadi. Qayta eshitish tugmasini bosing.');setPhase('idle');}};setPhase('speaking');try{await player.play();}catch{setPhase('idle');setError('Brauzer avtomatik ovozni to‘sdi. Javob yonidagi “Qayta eshitish” tugmasini bosing.');}};
 const sendTranscript=async(text:string)=>{
  setDraft('');setError('');setPhase('thinking');
  controller.current=new AbortController();const signal=controller.current.signal;
  const turn:Turn={text,reply:''};setHistory(prev=>[turn,...prev]);
  try{
   const response=await request('/chat/stream',{method:'POST',body:JSON.stringify({content:text,voice_turn:true,conversation_id:conversation.current}),signal});
   const reader=response.body?.getReader();if(!reader)throw new Error('Javob oqimi ochilmadi. Qayta urinib ko‘ring.');
   for await(const event of parseStream(reader)){
    if(!mounted.current)return;
    if(event.type==='delta'){turn.reply+=event.content||'';setHistory(prev=>[{...turn},...prev.slice(1)]);}
    if(event.type==='done')conversation.current=event.conversation_id;
    if(event.type==='error')throw new Error(event.message);
   }
   if(data?.tts_configured&&turn.reply){
    setPhase('speaking');const speech=await request('/voice/speak',{method:'POST',body:JSON.stringify({text:turn.reply.replace(/[*#`]/g,'').slice(0,3000),voice:data.tts_voices?.length?selectedVoice:undefined,local_voice:localVoice||data.local_voices?.[0]?.id}),signal});
    if(!mounted.current)return;
    const blob=await speech.blob();if(!mounted.current)return;const url=URL.createObjectURL(blob);urls.current.push(url);turn.audio=url;
    setHistory(prev=>[{...turn},...prev.slice(1)]);await play(url);
   }else setPhase('idle');
  }catch(e){if(mounted.current){setError((e as Error).message);setPhase('idle');}}
 };
 const transcribe=async(file:Blob)=>{
  if(!mounted.current)return;
  setError('');audio.current?.pause();setPhase('transcribing');
  controller.current=new AbortController();const signal=controller.current.signal;
  try{
   const form=new FormData();form.append('file',file);
   if(selectedModel)form.append('model',selectedModel);
   const result=await api<{text:string}>('/voice/transcribe',{method:'POST',body:form,signal});
   if(!mounted.current)return;
   if(data?.local_only){setDraft(result.text);setPhase('review');}
   else await sendTranscript(result.text);
  }catch(e){if(mounted.current){setError((e as Error).message);setPhase('idle');}}
 };
 const stop=()=>{if(timer.current)clearTimeout(timer.current);if(recorder.current?.state==='recording')recorder.current.stop();};
 const start=async()=>{
  setError('');audio.current?.pause();setPhase('starting');
  try{
   if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)throw new Error('Bu brauzerda ovoz yozish mavjud emas. HTTPS yoki localhost orqali oching.');
   const stream=await navigator.mediaDevices.getUserMedia({audio:{noiseSuppression:true,echoCancellation:true,autoGainControl:true}});
   if(!mounted.current){stream.getTracks().forEach(t=>t.stop());return;}
   tracks.current=stream;
   const mime=['audio/webm;codecs=opus','audio/mp4','audio/webm','audio/ogg;codecs=opus'].find(type=>MediaRecorder.isTypeSupported(type));
   const media=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);recorder.current=media;
   const chunks:BlobPart[]=[];media.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
   media.onstop=()=>{if(timer.current)clearTimeout(timer.current);stream.getTracks().forEach(t=>t.stop());void transcribe(new Blob(chunks,{type:media.mimeType||mime||'audio/webm'}));};
   media.onerror=()=>{media.onstop=null;stream.getTracks().forEach(t=>t.stop());if(timer.current)clearTimeout(timer.current);setPhase('idle');setError('Ovoz yozilmadi. Mikrofonni tekshirib qayta urinib ko‘ring.');};
   media.start();setPhase('recording');timer.current=setTimeout(stop,60000);
  }catch(e){tracks.current?.getTracks().forEach(t=>t.stop());setPhase('idle');setError(e instanceof DOMException&&e.name==='NotAllowedError'?'Mikrofonga ruxsat berilmadi. Brauzer ruxsatlarini tekshiring.':e instanceof DOMException?'Mikrofon topilmadi yoki band. Qurilmani tekshiring.':(e as Error).message);}
 };
 const busy=phase==='review'||phase==='starting'||phase==='transcribing'||phase==='thinking';
 const labels={starting:'Mikrofon ruxsati kutilmoqda…',idle:'Gapirishga tayyormisiz?',recording:'Tinglanmoqda…',transcribing:'Ovoz matnga aylantirilmoqda…',review:'Tanilgan matnni tekshiring.',thinking:'JARVIS javob yozmoqda…',speaking:'Javob ovozda o‘qilmoqda…'};
 return <><div className="page-heading"><div><span className="eyebrow">SO‘ZLARINGIZGA QULOQ TUTAMIZ</span><h1>Ovozli yordamchi<span className="greeting-dot">.</span></h1><p>Yozishni boshlang, gapiring va tugatish tugmasini bosing.</p></div></div><section className="panel voice-panel"><div className={'orb '+(phase==='recording'?'recording':'')}><Mic size={55}/></div><h2 aria-live="polite">{labels[phase]}</h2><p>{data?.message||'Holat tekshirilmoqda…'}</p>
  {data?.local_only&&<details>
   <summary>Mahalliy ovoz sozlamalari</summary>
   <p>Mahalliy STT va Ollama · {data.stt_device==='cpu'?'CPU':'Metal / CPU avtomatik'} · {data.local_voices?.[0]?.label||(data.tts_engine==='espeak'?'eSpeak NG (o‘zbekcha)':data.tts_engine==='edge'?'Microsoft Edge (onlayn)':'Ovoz o‘chirilgan')}</p>
   <label>STT modeli{' '}<select value={selectedModel||data.stt_model} onChange={event=>setSelectedModel(event.target.value)} disabled={phase!=='idle'}>
    {data.stt_models?.map(model=><option key={model.id} value={model.id}>{model.label}</option>)}
   </select></label>
   {Boolean(data.local_voices?.length)&&<label>Javob ovozi{' '}<select value={localVoice||data.local_voices?.[0]?.id} onChange={event=>setLocalVoice(event.target.value)} disabled={phase!=='idle'}>
    {data.local_voices?.map(voice=><option key={voice.id} value={voice.id}>{voice.label}</option>)}
   </select></label>}
   <label>Audio fayl{' '}<input type="file" accept="audio/wav,audio/webm,audio/mp4,audio/ogg,.m4a" disabled={phase!=='idle'||!data.stt_configured} onChange={event=>{
    const file=event.target.files?.[0];event.target.value='';
    if(file)void transcribe(file);
   }}/></label>
  </details>}
  {phase==='review'&&<div>
   <label>Jarvis eshitgan matn<textarea value={draft} onChange={event=>setDraft(event.target.value)} maxLength={12000}/></label>
   <Button disabled={!draft.trim()} onClick={()=>void sendTranscript(draft.trim())}>Tasdiqlash va yuborish</Button>
   <Button variant="outline" onClick={()=>{setDraft('');setPhase('idle');}}>Bekor qilish</Button>
  </div>}{Boolean(data?.tts_voices?.length)&&<p><label>Javob ovozi{' '}
   <select value={selectedVoice} onChange={event=>setSelectedVoice(event.target.value)} disabled={phase!=='idle'}>
    {data?.tts_voices?.map(name=><option key={name} value={name}>{name==='uz-UZ-SardorNeural'?'Sardor':'Madina'}</option>)}
   </select>
  </label></p>}<Button disabled={busy||(!data?.stt_configured&&phase!=='recording')} onClick={()=>phase==='recording'?stop():void start()}>{phase==='recording'?<Square size={17}/>:<Mic size={17}/>} {phase==='recording'?'Yozishni tugatish':'Ovoz yozishni boshlash'}</Button>{phase==='speaking'&&<Button variant="outline" onClick={()=>{audio.current?.pause();setPhase('idle');}}>Ovozni to‘xtatish</Button>}{!data?.stt_configured&&<Button variant="outline" onClick={()=>void refetch()}>Ulanishni qayta tekshirish</Button>}<p className="muted">Ovoz faqat tugma bosilgandan keyin yoziladi. Eng ko‘pi 60 soniya.</p>{(error||statusError)&&<p className="error" role="alert">{error||(statusError as Error).message}</p>}</section>{history.map((item,index)=><section className="panel transcript" key={index}><h3>Siz aytdingiz</h3><p>{item.text}</p><h3>JARVIS javobi</h3><ReactMarkdown>{item.reply}</ReactMarkdown>{item.audio&&<Button variant="outline" disabled={busy||phase==='recording'} onClick={()=>void play(item.audio!)}><Volume2 size={16}/> Qayta eshitish</Button>}</section>)}</>;
}
