import { create } from 'zustand';
import type { User, StreamEvent } from '@jarvis/shared-types';
export const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010/api/v1';
type Session = { token: string | null; user: User | null; setSession: (token: string, user: User) => void; clear: () => void };
export const useSession = create<Session>((set) => ({ token: null, user: null, setSession: (token, user) => set({token, user}), clear: () => set({token: null, user: null}) }));
let refreshPromise: Promise<boolean> | null = null;
export async function restoreSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const response = await fetch(API + '/auth/refresh', { method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json'}, body: '{}' });
      if (!response.ok) return false;
      const data = await response.json(); useSession.getState().setSession(data.access_token, data.user); return true;
    } catch { return false; }
    finally { refreshPromise = null; }
  })();
  return refreshPromise;
}
export async function request(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const token = useSession.getState().token;
  if (token) headers.set('Authorization', 'Bearer ' + token);
  let response: Response;
  try { response = await fetch(API + path, {...init, headers, credentials: 'include'}); }
  catch { throw new Error('Serverga ulanib bo‘lmadi. Backend ishga tushganini tekshiring.'); }
  if (response.status === 401 && retry && !path.startsWith('/auth/')) {
    if (await restoreSession()) return request(path, init, false);
    useSession.getState().clear();
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error?.message || 'So‘rovni bajarib bo‘lmadi.');
  }
  return response;
}
export async function api<T = Record<string, unknown>>(path: string, init: RequestInit = {}): Promise<T> { const response=await request(path,init); try{return await response.json();}catch{throw new Error('Serverdan noto‘g‘ri javob olindi. Qayta urinib ko‘ring.');} }
function streamEvent(line:string):StreamEvent{try{return JSON.parse(line);}catch{throw new Error('Javob oqimi uzildi yoki buzildi. Qayta urinib ko‘ring.');}}
export async function* parseStream(reader: ReadableStreamDefaultReader<Uint8Array>): AsyncGenerator<StreamEvent> {
  const decoder = new TextDecoder(); let buffer = '';
  while (true) {
    const {done, value} = await reader.read();
    buffer += decoder.decode(value, {stream: !done});
    const lines = buffer.split('\n'); buffer = lines.pop() || '';
    for (const line of lines) if (line.trim()) yield streamEvent(line);
    if (done) { if (buffer.trim()) yield streamEvent(buffer); break; }
  }
}
