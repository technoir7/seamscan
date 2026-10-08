"use client";

import { GoogleAuthProvider, onAuthStateChanged, signInWithPopup, signOut, type User } from "firebase/auth";
import { useEffect, useState } from "react";
import { auth } from "@/lib/firebase";

export function SignInButton() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => onAuthStateChanged(auth, setUser), []);

  if (user) {
    return <button onClick={() => signOut(auth)}>Sign out {user.displayName}</button>;
  }
  return <button onClick={() => signInWithPopup(auth, new GoogleAuthProvider())}>Sign in with Google</button>;
}
