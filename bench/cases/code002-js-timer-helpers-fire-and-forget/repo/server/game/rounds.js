import Room from "../models/Room.js";

const timers = new Map();

const startRound = async (code, io) => {
  try {
    const room = await Room.findOne({ code });
    room.guesses = [];
    await room.save();
    io.to(code).emit("start-round", { round: room.round });
    timers.set(code, setTimeout(() => endRound(code, io), 30000));
  } catch (err) {
    console.error("start-round failed", err);
  }
};

const endRound = async (code, io) => {
  try {
    clearTimeout(timers.get(code));
    timers.delete(code);
    io.to(code).emit("round-ended");
  } catch (err) {
    console.error("end-round failed", err);
  }
};

export function registerRounds(io, socket) {
  socket.on("start", ({ code }) => {
    startRound(code, io);
  });
}
