Deno.env.set("NODE_TLS_REJECT_UNAUTHORIZED", "0");

const r = await fetch("https://self-signed.local:8443/health");
console.log(r.status);
