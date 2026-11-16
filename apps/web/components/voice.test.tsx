import React from 'react';
import {beforeEach, expect, it, vi} from 'vitest';
import {act, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {Voice} from './voice';
import {api, request} from '../lib/api';
vi.mock('../lib/api',()=>({api:vi.fn(),request:vi.fn(),parseStream:async function*(){yield {type:'delta',content:'Salom!'};yield {type:'done',conversation_id:'voice-conversation'};}}));
const trackStop=vi.fn();const getUserMedia=vi.fn();const play=vi.fn();const pause=vi.fn();
class Recorder{
 static isTypeSupported=()=>true;
 state='inactive';mimeType='audio/webm;codecs=opus';
 onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;
 static last:Recorder;
 constructor(){Recorder.last=this;}
 start(){this.state='recording';}
 stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['recorded audio'])});this.onstop?.();}
}
function mount(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Voice/></QueryClientProvider>);}
beforeEach(()=>{
 vi.clearAllMocks();getUserMedia.mockResolvedValue({getTracks:()=>[{stop:trackStop}]});
 Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia}});
 vi.stubGlobal('MediaRecorder',Recorder);
 vi.stubGlobal('Audio',class{play=play;pause=pause;});play.mockResolvedValue(undefined);
 URL.createObjectURL=vi.fn(()=>'blob:voice-reply');URL.revokeObjectURL=vi.fn();
 vi.mocked(api).mockImplementation(async(path)=>path==='/voice/status'?{stt_configured:true,tts_configured:true,message:'Tayyor'}:{text:'Salom JARVIS'});
 vi.mocked(request).mockImplementation(async(path)=>path==='/chat/stream'?{body:{getReader:()=>({})}} as Response:{blob:async()=>new Blob(['RIFF'])} as Response);
});
it('records only after a click, transcribes, streams a reply and enables replay',async()=>{
 const view=mount();const start=await screen.findByRole('button',{name:'Ovoz yozishni boshlash'});
 await waitFor(()=>expect((start as HTMLButtonElement).disabled).toBe(false));expect(getUserMedia).not.toHaveBeenCalled();
 fireEvent.click(start);fireEvent.click(await screen.findByRole('button',{name:'Yozishni tugatish'}));
 await screen.findByText('Salom JARVIS');await screen.findByText('Salom!');
 const replay=await screen.findByRole('button',{name:'Qayta eshitish'});await waitFor(()=>expect(play).toHaveBeenCalledTimes(1));
 expect(trackStop).toHaveBeenCalled();
 expect(vi.mocked(api).mock.calls.find(([p])=>p==='/voice/transcribe')?.[1]?.body).toBeInstanceOf(FormData);
 fireEvent.click(replay);await waitFor(()=>expect(play).toHaveBeenCalledTimes(2));
 view.unmount();expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:voice-reply');
});
it('shows microphone permission errors and never uploads audio',async()=>{
 getUserMedia.mockRejectedValue(new DOMException('denied','NotAllowedError'));mount();
 const start=await screen.findByRole('button',{name:'Ovoz yozishni boshlash'});await waitFor(()=>expect((start as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(start);expect(await screen.findByRole('alert')).toHaveProperty('textContent','Mikrofonga ruxsat berilmadi. Brauzer ruxsatlarini tekshiring.');
 expect(vi.mocked(api).mock.calls.some(([p])=>p==='/voice/transcribe')).toBe(false);
});
it('stops recording on navigation without submitting the unfinished recording',async()=>{
 const view=mount();const start=await screen.findByRole('button',{name:'Ovoz yozishni boshlash'});await waitFor(()=>expect((start as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(start);await screen.findByRole('button',{name:'Yozishni tugatish'});
 act(()=>view.unmount());expect(Recorder.last.state).toBe('inactive');expect(trackStop).toHaveBeenCalled();
 expect(vi.mocked(api).mock.calls.some(([p])=>p==='/voice/transcribe')).toBe(false);
});

it('requires approval of the recognized text in local mode before sending it',async()=>{
 vi.mocked(api).mockImplementation(async(path)=>path==='/voice/status'?
  {stt_configured:true,tts_configured:false,local_only:true,message:'Tayyor'}:{text:'Chrome och'});
 mount();
 const start=await screen.findByRole('button',{name:'Ovoz yozishni boshlash'});
 await waitFor(()=>expect((start as HTMLButtonElement).disabled).toBe(false));
 fireEvent.click(start);fireEvent.click(await screen.findByRole('button',{name:'Yozishni tugatish'}));
 const review=await screen.findByRole('textbox',{name:'Jarvis eshitgan matn'});
 expect(vi.mocked(request)).not.toHaveBeenCalled();
 fireEvent.change(review,{target:{value:'Google Chrome och'}});
 fireEvent.click(screen.getByRole('button',{name:'Tasdiqlash va yuborish'}));
 await waitFor(()=>expect(vi.mocked(request)).toHaveBeenCalledWith('/chat/stream',expect.objectContaining({
  body:JSON.stringify({content:'Google Chrome och',voice_turn:true})
 })));
});
