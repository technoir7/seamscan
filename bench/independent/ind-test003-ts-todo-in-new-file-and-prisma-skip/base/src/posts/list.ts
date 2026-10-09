export const list = (db: any) => db.post.findMany({ take: 20 });
