/**
 * Make the web demo export uploadable to Vercel.
 *
 * Expo writes assets that come from packages (icon fonts, navigation images)
 * under dist-demo/assets/node_modules/, and the Vercel CLI never uploads a
 * folder named node_modules, so those requests 404 on the live site and the
 * icons go missing. This moves the folder to assets/vendor/ and updates the
 * paths in the built JavaScript to match.
 */

const fs = require("fs");
const path = require("path");

const dist = path.resolve(__dirname, "..", process.argv[2] ?? "dist-demo");
const from = path.join(dist, "assets", "node_modules");
if (!fs.existsSync(from)) process.exit(0);

fs.renameSync(from, path.join(dist, "assets", "vendor"));

const jsDir = path.join(dist, "_expo", "static", "js", "web");
let rewritten = 0;
for (const file of fs.readdirSync(jsDir).filter((f) => f.endsWith(".js"))) {
  const full = path.join(jsDir, file);
  const code = fs.readFileSync(full, "utf8");
  const updated = code.split("/assets/node_modules/").join("/assets/vendor/");
  if (updated !== code) {
    fs.writeFileSync(full, updated);
    rewritten += 1;
  }
}
if (rewritten === 0) {
  console.error("rename-vendor-assets: no bundle referenced /assets/node_modules/");
  process.exit(1);
}
console.log(`rename-vendor-assets: moved package assets to assets/vendor (${rewritten} bundle(s) updated)`);
