// components/layout/Header.tsx
'use client';

import { useAuthStore } from '@/lib/store/authStore';
import { User, LogOut, Key, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { APIKeyModal } from '@/components/ui/APIKeyModal';
import Link from 'next/link';

export function Header() {
  const { user, logout } = useAuthStore();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showAPIKeyModal, setShowAPIKeyModal] = useState(false);

  return (
    <>
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white font-medium">
                  {user?.username?.[0]?.toUpperCase() || 'U'}
                </span>
              </div>
              <span className="text-gray-700 dark:text-gray-300">
                {user?.username}
              </span>
              <ChevronDown className="w-4 h-4 text-gray-500" />
            </button>

            {showDropdown && (
              <>
                <div 
                  className="fixed inset-0 z-10" 
                  onClick={() => setShowDropdown(false)}
                />
                <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-20">
                  <div className="py-1">
                    <Link
                      href="/settings"
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-3"
                      onClick={() => setShowDropdown(false)}
                    >
                      <User className="w-4 h-4" />
                      <span>Profile Settings</span>
                    </Link>
                    <button
                      onClick={() => {
                        setShowDropdown(false);
                        setShowAPIKeyModal(true);
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-3"
                    >
                      <Key className="w-4 h-4" />
                      <span>API Keys</span>
                    </button>
                    <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                    <button
                      onClick={() => {
                        setShowDropdown(false);
                        logout();
                        window.location.href = '/auth/login';
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-3"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      <APIKeyModal 
        isOpen={showAPIKeyModal} 
        onClose={() => setShowAPIKeyModal(false)} 
      />
    </>
  );
}