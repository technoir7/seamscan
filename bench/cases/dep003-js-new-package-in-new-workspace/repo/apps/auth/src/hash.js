const bcrypt = require('bcrypt');

exports.hashPassword = (plain) => bcrypt.hash(plain, 12);
