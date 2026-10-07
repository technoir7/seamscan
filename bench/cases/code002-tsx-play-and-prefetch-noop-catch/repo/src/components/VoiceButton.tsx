import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { listTasks } from "../services/tasks";

export function VoiceButton({ active }: { active: boolean }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    queryClient.prefetchQuery({ queryKey: ["tasks"], queryFn: listTasks }).catch(() => {});
  }, [queryClient]);

  function onClick() {
    if (!audioRef.current) audioRef.current = new Audio("/sounds/start.mp3");
    audioRef.current.play().catch(() => {});
  }

  return <button onClick={onClick}>{active ? "Listening…" : "Talk"}</button>;
}
