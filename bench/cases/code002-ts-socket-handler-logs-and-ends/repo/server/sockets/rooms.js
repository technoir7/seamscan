const Room = require("../models/Room");

module.exports = function registerRooms(io, socket) {
  socket.on("join-room", async ({ roomCode, name }) => {
    try {
      const room = await Room.findOne({ code: roomCode });
      room.players.push({ id: socket.id, name });
      await room.save();
      await socket.join(roomCode);
      io.to(roomCode).emit("room-updated", { players: room.players });
    } catch (err) {
      console.error("Join-room error:", err);
    }
  });

  socket.on("leave-room", async ({ roomCode }) => {
    try {
      await Room.updateOne({ code: roomCode }, { $pull: { players: { id: socket.id } } });
      io.to(roomCode).emit("player-left", socket.id);
    } catch (err) {
      console.error("Leave-room error:", err);
    }
  });
};
