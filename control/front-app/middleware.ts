import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth-token')?.value;
    

  const isAuth = !!token;
  const { pathname } = request.nextUrl;

  const isAuthRoute =
    pathname.startsWith('/auth')

  const isProtected = pathname.startsWith('/compute');

  if (!isAuth && isProtected) {

    return NextResponse.redirect(new URL('/login', request.url));
  }

  if (isAuth && isAuthRoute) {
    return NextResponse.redirect(new URL('/compute', request.url));
  }

  return NextResponse.next();
}