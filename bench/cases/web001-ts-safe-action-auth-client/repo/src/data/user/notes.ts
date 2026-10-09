'use server';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { actionClient, authActionClient, authMiddleware } from '@/lib/safe-action';
import { createSupabaseClient } from '@/supabase-clients/server';

const noteIdSchema = z.object({ id: z.string().uuid() });

export const deleteNoteAction = authActionClient
  .schema(noteIdSchema)
  .action(async ({ parsedInput }) => {
    const supabase = await createSupabaseClient();
    const { error } = await supabase.from('notes').delete().eq('id', parsedInput.id);
    if (error) throw new Error(error.message);
    revalidatePath('/notes');
  });

export const archiveNoteAction = actionClient
  .use(authMiddleware)
  .schema(noteIdSchema)
  .action(async ({ parsedInput, ctx }) => {
    const supabase = await createSupabaseClient();
    await supabase
      .from('notes')
      .update({ archived: true })
      .eq('id', parsedInput.id)
      .eq('owner_id', ctx.userId);
    revalidatePath('/notes');
  });
