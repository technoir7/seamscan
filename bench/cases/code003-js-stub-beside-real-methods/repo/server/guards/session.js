export class SessionGuard {
  constructor(store) {
    this.store = store;
  }

  async getUser(req) {
    const id = req.cookies.sid;
    return id ? this.store.find(id) : null;
  }

  isAuthorized(user, action) {
    return true;
  }
}
