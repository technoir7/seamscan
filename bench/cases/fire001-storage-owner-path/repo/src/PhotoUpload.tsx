import { useState } from "react";
import { getDownloadURL, ref, uploadBytes } from "firebase/storage";
import { addDoc, collection } from "firebase/firestore";
import { auth, db, storage } from "./lib/firebase";

export function PhotoUpload() {
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const user = auth.currentUser;
    if (!file || !user) return;
    setBusy(true);
    const objectRef = ref(storage, `photos/${user.uid}/${crypto.randomUUID()}-${file.name}`);
    await uploadBytes(objectRef, file, { contentType: file.type });
    const downloadUrl = await getDownloadURL(objectRef);
    await addDoc(collection(db, "users", user.uid, "photos"), { url: downloadUrl, name: file.name });
    setUrl(downloadUrl);
    setBusy(false);
  }

  return (
    <div>
      <input type="file" accept="image/*" onChange={onFile} disabled={busy} />
      {url && <img src={url} alt="Uploaded photo" className="mt-2 max-w-xs" />}
    </div>
  );
}
