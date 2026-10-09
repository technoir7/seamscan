import { useRealtimeTable } from "react-supabase-realtime-hooks";
import { supabase } from "@/integrations/supabase/client";

export const useMessages = (roomId: string) =>
  useRealtimeTable(supabase, "messages", { filter: `room_id=eq.${roomId}` });
