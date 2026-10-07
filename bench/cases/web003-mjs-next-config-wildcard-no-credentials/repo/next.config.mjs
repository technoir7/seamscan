/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: "/api/public/:path*",
        headers: [
          { key: "Access-Control-Allow-Origin", value: "*" },
          { key: "Access-Control-Allow-Methods", value: "GET,OPTIONS" },
        ],
      },
      {
        source: "/api/account/:path*",
        headers: [{ key: "Access-Control-Allow-Credentials", value: "true" }],
      },
    ];
  },
};

export default nextConfig;
