// Export medidown logos from SVG to PNG at 1x/2x/4x using Sharp
// Run: node e:\\project\\downloader\\tools\\export_logos.js

const path = require('path');
const fs = require('fs');

async function main() {
  let sharp;
  try {
    sharp = require('sharp');
  } catch (e) {
    console.error('Sharp is not installed. Run: npm install --prefix e:\\project\\downloader sharp');
    process.exit(1);
  }

  const ROOT = 'e:\\project\\downloader';
  const STATIC = path.join(ROOT, 'static');

  const inputs = [
    { file: path.join(STATIC, 'logo-medidown-clean.svg'), base: 'logo-medidown-clean' },
    { file: path.join(STATIC, 'logo-medidown-clean-transparent.svg'), base: 'logo-medidown-clean-transparent' },
  ];

  const scales = [
    { scale: 1.0, suffix: '' },
    { scale: 2.0, suffix: '@2x' },
    { scale: 4.0, suffix: '@4x' },
  ];

  const width = 960;
  const height = 260;

  for (const inp of inputs) {
    if (!fs.existsSync(inp.file)) {
      console.warn('Skip missing', inp.file);
      continue;
    }
    const svgBuffer = fs.readFileSync(inp.file);
    for (const s of scales) {
      const out = path.join(STATIC, `${inp.base}${s.suffix}.png`);
      const w = Math.round(width * s.scale);
      const h = Math.round(height * s.scale);
      console.log(`Exporting ${path.basename(out)} (${w}x${h})`);
      // Sharp can rasterize SVG by setting width/height
      await sharp(svgBuffer, { density: 72 * s.scale })
        .resize({ width: w, height: h, fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 0 } })
        .png()
        .toFile(out);
    }
  }
  console.log('Done.');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});