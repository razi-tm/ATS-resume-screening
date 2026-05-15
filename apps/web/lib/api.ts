export type CandidateResult = { candidate_name: string; final_score: number; semantic_score: number; keyword_score: number; matched_skills: string[]; missing_skills: string[] };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export async function health(): Promise<{ status: string }> { const res = await fetch(`${API_URL}/api/v1/health`, { cache: 'no-store' }); if (!res.ok) throw new Error('API unavailable'); return res.json(); }
