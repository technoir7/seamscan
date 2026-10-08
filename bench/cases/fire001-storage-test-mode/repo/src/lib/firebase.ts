import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "{{FAKE_FIREBASE_WEB_API_KEY}}",
  authDomain: "photo-drop-c41d9.firebaseapp.com",
  projectId: "photo-drop-c41d9",
  storageBucket: "photo-drop-c41d9.firebasestorage.app",
  messagingSenderId: "684120937455",
  appId: "1:684120937455:web:3b9d0c7a1e5f4d2b8c6a90",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);
