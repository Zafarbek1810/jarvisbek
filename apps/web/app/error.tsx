'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <main className="loading"><h1>Sahifani ochib bo‘lmadi</h1><p>Kutilmagan xatolik yuz berdi.</p><button className="button button-primary" onClick={reset}>Qayta urinish</button></main>;}
