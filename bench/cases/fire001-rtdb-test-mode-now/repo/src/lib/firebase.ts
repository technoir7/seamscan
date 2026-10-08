import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getDatabase } from "firebase/database";

const firebaseConfig = {
  apiKey: "{{FAKE_FIREBASE_WEB_API_KEY}}",
  authDomain: "team-chat-0e93a.firebaseapp.com",
  databaseURL: "https://team-chat-0e93a-default-rtdb.firebaseio.com",
  projectId: "team-chat-0e93a",
  storageBucket: "team-chat-0e93a.firebasestorage.app",
  messagingSenderId: "684120937455",
  appId: "1:684120937455:web:3b9d0c7a1e5f4d2b8c6a90",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const rtdb = getDatabase(app);
