import {cp,mkdir} from 'node:fs/promises';
const base = new URL('../../apps/web/.next/',import.meta.url);
await mkdir(new URL('standalone/apps/web/.next/',base),{recursive:true});
await cp(new URL('static/',base),new URL('standalone/apps/web/.next/static/',base),{recursive:true});
