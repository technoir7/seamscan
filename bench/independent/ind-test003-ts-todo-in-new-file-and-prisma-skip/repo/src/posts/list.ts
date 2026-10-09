export const list = (db: any, page = 1) => db.post.findMany({ skip: (page - 1) * 20, take: 20 });
