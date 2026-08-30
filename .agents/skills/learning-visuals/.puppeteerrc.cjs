const path = require("node:path");

/** Keep the browser binary owned by this skill instead of using a global cache. */
module.exports = {
  cacheDirectory: path.join(__dirname, ".cache", "puppeteer"),
};
