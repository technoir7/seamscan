'use server';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';
import { actionClient } from '@/lib/safe-action';
import { prisma } from '@/lib/prisma';

const deleteProjectSchema = z.object({ projectId: z.string().cuid() });

export const deleteProjectAction = actionClient
  .schema(deleteProjectSchema)
  .action(async ({ parsedInput }) => {
    await prisma.project.delete({ where: { id: parsedInput.projectId } });
    revalidatePath('/dashboard');
    return { ok: true };
  });
