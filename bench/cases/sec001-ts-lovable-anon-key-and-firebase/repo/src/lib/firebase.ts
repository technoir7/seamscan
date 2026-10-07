import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "{{FAKE_FIREBASE_WEB_API_KEY}}",
  authDomain: "acme-notes.firebaseapp.com",
  projectId: "acme-notes",
  storageBucket: "acme-notes.appspot.com",
  messagingSenderId: "604381925517",
  appId: "1:604381925517:web:7b3c2d9e4f1a0b6c",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
