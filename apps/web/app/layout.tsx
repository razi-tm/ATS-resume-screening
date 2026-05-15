import './globals.css';
import { Nav } from '@/components/nav';
export default function RootLayout({ children }: { children: React.ReactNode }) { return <html lang="en" className="dark"><body><div className="flex"><Nav /><main className="flex-1 p-8">{children}</main></div></body></html>; }
