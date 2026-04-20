// app/(dashboard)/page.tsx
'use client';

import { useAuthStore } from '@/lib/store/authStore';
import { redirect } from 'next/navigation';
import { useEffect } from 'react';

export default function DashboardHome() {
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      redirect('/compute');
    }
  }, [isAuthenticated]);

  return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );
}