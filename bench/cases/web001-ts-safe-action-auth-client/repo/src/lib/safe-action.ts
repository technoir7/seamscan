import { createSafeActionClient } from 'next-safe-action';
import { createSupabaseClient } from '@/supabase-clients/server';

export const actionClient = createSafeActionClient();

export const authMiddleware = async ({ next }: { next: (o: { ctx: { userId: string } }) => unknown }) => {
  const supabase = await createSupabaseClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) throw new Error('Unauthorized');
  return next({ ctx: { userId: data.user.id } });
};

export const authActionClient = actionClient.use(authMiddleware);
