import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "{{FAKE_FIREBASE_WEB_API_KEY}}",
  authDomain: "notes-f04a8.firebaseapp.com",
  projectId: "notes-f04a8",
  storageBucket: "notes-f04a8.firebasestorage.app",
  messagingSenderId: "684120937455",
  appId: "1:684120937455:web:3b9d0c7a1e5f4d2b8c6a90",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
