const { Server } = require("socket.io");
const jwt = require("jsonwebtoken");

function attachRealtime(httpServer) {
  const io = new Server(httpServer, { cors: { origin: process.env.APP_URL } });

  io.use((socket, next) => {
    const user = jwt.decode(socket.handshake.auth.token);
    if (!user) {
      return next(new Error("unauthorized"));
    }
    socket.data.user = user;
    next();
  });

  io.on("connection", (socket) => {
    socket.join(`user:${socket.data.user.sub}`);
  });
  return io;
}

module.exports = { attachRealtime };
