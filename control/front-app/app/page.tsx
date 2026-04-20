// app/page.tsx
'use client';

import { useAuthStore } from '@/lib/store/authStore';
import { redirect } from 'next/navigation';
import { useEffect } from 'react';

export default function HomePage() {
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      redirect('/auth/login');
    } else {
      redirect('/compute');
    }
  }, [isAuthenticated]);

  return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );
}