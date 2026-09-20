/** @type {import('next').NextConfig} */
const nextConfig = {
  // Todo /api/* se reenvia a Django. El navegador solo habla con el origen de
  // Next.js, asi que las cookies de sesion son first-party: sin CORS y sin
  // SameSite=None. Funciona igual en local y en Vercel.
  async rewrites() {
    const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
