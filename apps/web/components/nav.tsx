import Link from 'next/link';
const links = ['dashboard', 'jobs', 'candidates', 'screenings', 'analytics', 'settings'];
export function Nav() { return <aside className="min-h-screen w-64 border-r border-slate-800 bg-slate-950 p-6"><div className="mb-8 text-xl font-bold">ATS SaaS</div><nav className="space-y-2">{links.map((link) => <Link className="block rounded-lg px-3 py-2 text-slate-300 hover:bg-slate-800" href={`/${link}`} key={link}>{link[0].toUpperCase()+link.slice(1)}</Link>)}</nav></aside>; }
