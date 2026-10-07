import tls from "node:tls";

const host = process.argv[2] ?? "api.acme.dev";

const socket = tls.connect(
  443,
  host,
  { servername: host, rejectUnauthorized: false },
  () => {
    const cert = socket.getPeerCertificate();
    const days = Math.round((new Date(cert.valid_to) - Date.now()) / 86_400_000);
    console.log(`${host}: certificate expires in ${days} days`);
    socket.end();
  },
);

socket.on("error", (err) => {
  console.error(err.message);
  process.exit(1);
});
