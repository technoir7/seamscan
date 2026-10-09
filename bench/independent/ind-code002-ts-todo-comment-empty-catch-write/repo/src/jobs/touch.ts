import { users } from "../db";

export async function touch(id: string) {
  try {
    await users.updateOne({ _id: id }, { $set: { seenAt: new Date() } });
  } catch (e) {
    // TODO handle this
  }
}
