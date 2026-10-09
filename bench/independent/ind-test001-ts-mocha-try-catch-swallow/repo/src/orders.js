exports.createOrder = (c) => { if (c.items.some(i => i.qty < 0)) throw new Error('bad'); return c; };
