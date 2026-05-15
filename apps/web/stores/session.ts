import { create } from 'zustand';
type SessionState = { token?: string; role: 'admin' | 'recruiter' | 'viewer'; setToken: (token: string) => void };
export const useSession = create<SessionState>((set) => ({ role: 'recruiter', setToken: (token) => set({ token }) }));
