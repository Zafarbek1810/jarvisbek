import React from 'react';
import {describe,it,expect,vi,beforeEach} from 'vitest';
import {render,fireEvent,screen,waitFor} from '@testing-library/react';
vi.mock('react-native',async()=>{
 const React=await import('react');
 return {
  View:({children}:{children:React.ReactNode})=><div>{children}</div>,
  Text:({children,accessibilityRole}:{children:React.ReactNode;accessibilityRole?:string})=><span role={accessibilityRole}>{children}</span>,
  TextInput:({placeholder,value,onChangeText,secureTextEntry}:{placeholder:string;value:string;onChangeText:(value:string)=>void;secureTextEntry?:boolean})=><input aria-label={placeholder} placeholder={placeholder} value={value} onChange={e=>onChangeText(e.target.value)} type={secureTextEntry?'password':'text'}/>,
  Pressable:({children,onPress,disabled}:{children:React.ReactNode;onPress:()=>void;disabled?:boolean})=><button disabled={disabled} onClick={onPress}>{children}</button>,
  ScrollView:({children}:{children:React.ReactNode})=><div>{children}</div>,
  StyleSheet:{create:(styles:unknown)=>styles},Alert:{alert:vi.fn()},ActivityIndicator:()=> <span>Yuklanmoqda</span>
 };
});
vi.mock('react-native-safe-area-context',()=>({SafeAreaView:({children}:{children:React.ReactNode})=><div>{children}</div>}));
vi.mock('expo-audio',()=>({useAudioRecorder:()=>({}),RecordingPresets:{HIGH_QUALITY:{}},AudioModule:{},setAudioModeAsync:vi.fn()}));
vi.mock('../api',()=>({API:'http://192.168.1.25:8010/api/v1',restore:vi.fn(),storeSession:vi.fn(),call:vi.fn(),raw:vi.fn(),logout:vi.fn()}));
import {call,restore,storeSession} from '../api';
import Home from '../app/index';
beforeEach(()=>{vi.clearAllMocks();vi.mocked(restore).mockResolvedValue(false);vi.mocked(storeSession).mockResolvedValue(undefined);});
describe('Mobil muhim ekranlar',()=>{
 it('kirishdan so‘ng vazifa yaratib, saqlangan vazifani ko‘rsatadi',async()=>{
  const tasks:{id:string;title:string;description:string}[]=[];
  vi.mocked(call).mockImplementation(async(path,init)=>{
   if(path.startsWith('/auth/login'))return {access_token:'test',refresh_token:'test-refresh'};
   if(path==='/dashboard')return {counts:{tasks:0,memories:0,projects:0,knowledge:0}};
   if(path==='/tasks'&&init?.method==='POST'){tasks.push({id:'one',...JSON.parse(String(init.body))});return tasks[0];}
   if(path==='/tasks')return {items:[...tasks]};
   throw new Error('Kutilmagan so‘rov');
  });
  render(<Home/>);
  await screen.findByText('Yana xush kelibsiz');
  fireEvent.change(screen.getByPlaceholderText('Elektron pochta'),{target:{value:'ali@example.uz'}});
  fireEvent.change(screen.getByPlaceholderText('Parol (kamida 10 belgi)'),{target:{value:'strong-test-password'}});
  fireEvent.click(screen.getByRole('button',{name:'Kirish'}));
  await screen.findByText('Bugun nimaga erishamiz?');
  expect(storeSession).toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Vazifalar'}));
  await screen.findByText('Yangi yozuv');
  fireEvent.change(screen.getByPlaceholderText('Nomi'),{target:{value:'O‘zbekcha loyihani tekshirish'}});
  fireEvent.click(screen.getByRole('button',{name:'Saqlash'}));
  await screen.findByText('O‘zbekcha loyihani tekshirish');
 });
 it('kirish xatosini o‘zbekcha ko‘rsatadi',async()=>{
  vi.mocked(call).mockRejectedValue(new Error('Pochta yoki parol noto‘g‘ri.'));
  render(<Home/>);await screen.findByText('Yana xush kelibsiz');
  fireEvent.click(screen.getByRole('button',{name:'Kirish'}));
  await waitFor(()=>expect(screen.getByRole('alert').textContent).toBe('Pochta yoki parol noto‘g‘ri.'));
 });
});
