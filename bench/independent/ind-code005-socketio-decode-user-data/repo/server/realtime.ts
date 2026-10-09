import { Server } from "socket.io";
import { jwtDecode } from "jwt-decode";

export function attachRealtime(io: Server) {
  io.use((socket, next) => {
    const token = socket.handshake.auth.token as string | undefined;
    if (!token) return next(new Error("unauthorized"));
    const user = jwtDecode(token);
    socket.data.user = user;
    next();
  });
}
