import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/lib/api/client';

interface AuthState {
  user: any | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hydrateAuth: () => void;
}

const getTokenFromCookie = () => {
  if (typeof document === 'undefined') return null;

  const cookie = document.cookie
    .split('; ')
    .find((row) => row.startsWith('auth-token='));

  return cookie ? cookie.split('=')[1] : null;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (username, password) => {
        set({ isLoading: true });

        try {
          const formData = new URLSearchParams();
          formData.append('username', username);
          formData.append('password', password);

          const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/auth/login`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
              },
              body: formData,
            }
          );

          const data = await res.json();

          if (!res.ok) {
            throw new Error(data.detail || 'Login failed');
          }

          // ✅ 1. Save token in API client
          apiClient.setToken(data.access_token);

          // ✅ 2. SAVE COOKIE (CRITICAL for middleware)
          document.cookie = `auth-token=${data.access_token}; path=/;`;

          // ✅ 3. Save Zustand state
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
          });
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        apiClient.clearToken();

        // clear cookie
        document.cookie =
          'auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';

        set({
          user: null,
          token: null,
          isAuthenticated: false,
        });
      },

      hydrateAuth: () => {
  const token = getTokenFromCookie();
  console.log('Middleware check - token:', token);

  if (token) {
    set({
      token,
      isAuthenticated: true,
    });

    apiClient.setToken(token);
  }
},
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    }
  )
);