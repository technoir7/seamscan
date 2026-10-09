import { KeyRound, Terminal } from "lucide-react";

const nodeExample = `
import { Clipdrop } from '@clipdrop/sdk';

const client = new Clipdrop({ apiKey: process.env.CLIPDROP_KEY });
const clip = await client.download('https://example.com/watch?v=abc');
`;

const legacyExample = `
const clipdrop = require('clipdrop-node');
clipdrop.fetch(url).then(save);
`;

export default function ApiAccess() {
  return (
    <section className="space-y-6">
      <h2 className="flex items-center gap-2 text-xl font-semibold">
        <KeyRound size={18} /> API access
      </h2>
      <p>Create a key in Settings, then call the API from your server.</p>
      <h3 className="flex items-center gap-2 font-medium">
        <Terminal size={16} /> Node.js
      </h3>
      <pre className="rounded bg-zinc-900 p-4 text-sm text-zinc-100">{nodeExample}</pre>
      <h3 className="font-medium">Older SDK</h3>
      <pre className="rounded bg-zinc-900 p-4 text-sm text-zinc-100">{legacyExample}</pre>
    </section>
  );
}
