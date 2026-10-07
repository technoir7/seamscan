const rooms = new Map();

function createRoom(hostId) {
  const roomCode = Math.floor(1000 + Math.random() * 9000).toString();
  const code = roomCode;
  const seatOrder = [hostId].sort(() => Math.random() - 0.5);
  rooms.set(code, { hostId, seatOrder, createdAt: Date.now() });
  return code;
}

module.exports = { createRoom };
