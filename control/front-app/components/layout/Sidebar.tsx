// components/layout/Sidebar.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Server, 
  Network, 
  Shield, 
  CreditCard, 
  Settings,
  Cloud,
  Key
} from 'lucide-react';

const menuItems = [
  { name: 'Compute', icon: Server, href: '/compute' },
  { name: 'Network', icon: Network, href: '/network' },
  { name: 'Firewall', icon: Shield, href: '/firewall' },
  { name: 'Billing', icon: CreditCard, href: '/billing' },
  { name: 'Settings', icon: Settings, href: '/settings' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Cloud className="w-8 h-8 text-blue-600" />
          <span className="text-xl font-bold text-gray-900 dark:text-white">
            Cloud Platform
          </span>
        </div>
      </div>
      
      <nav className="p-4 space-y-1">
        {menuItems.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}