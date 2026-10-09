function scheduleReminder(userId, minutes) {
  setTimeout(`sendReminder(${userId})`, minutes * 60000);
}

module.exports = { scheduleReminder };
