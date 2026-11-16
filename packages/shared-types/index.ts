export type User = { id: string; name: string; email: string };
export type StreamEvent = { type: 'start' | 'delta' | 'tool' | 'done' | 'error'; content?: string; message?: string; conversation_id?: string };
export type Task = { id: string; title: string; description: string; completed: boolean; priority: 'past' | 'o‘rta' | 'yuqori'; due_date: string; category: string; project_id: string | null };
