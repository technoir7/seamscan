import { WebSocketServer } from "ws";
import jwt from "jsonwebtoken";

const wss = new WebSocketServer({ port: 8080 });

wss.on("connection", (socket, request) => {
  const url = new URL(request.url, "http://localhost");
  const token = url.searchParams.get("token") ?? "";
  const payload = jwt.decode(token);
  const room = payload?.teamId ? `team:${payload.teamId}` : null;
  if (!room) {
    socket.close(4401, "unauthorized");
    return;
  }
  socket.send(JSON.stringify({ type: "joined", room }));
});
