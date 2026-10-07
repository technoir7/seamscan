"""parse.javascript: bindings and import aliases."""

from seamscan.model import SourceFile
from seamscan.parse.javascript import parse_js


def test_require_aliases_pair_each_name_with_its_own_module():
    # Several requires in one file: each local name must resolve to its own module, not a
    # neighbour's (the name and source captures were once zipped in unspecified order).
    # The bad order showed up in most parses but not all, hence the repetition.
    file = SourceFile(
        "server/index.js",
        'const express = require("express");\n'
        'const cors = require("cors");\n'
        'const cookieParser = require("cookie-parser");\n'
        'const authRoutes = require("./routes/auth");\n'
        'const { exec } = require("child_process");\n'
        "const app = express();\n"
        "app.use(cors({ origin: true, credentials: true }));\n",
    )
    for _ in range(50):
        assert dict(parse_js(file).aliases) == {
            "express": "express",
            "cors": "cors",
            "cookieParser": "cookie-parser",
            "authRoutes": "./routes/auth",
            "exec": "child_process.exec",
        }
