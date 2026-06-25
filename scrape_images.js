const { launch } = require('puppeteer-core');
const fs = require('fs');
const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

async function debug(url) {
  const browser = await launch({
    executablePath: EDGE_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'],
  });

  const page = await browser.newPage();
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, 5000));

    const html = await page.content();
    fs.writeFileSync('debug_puppeteer.html', html);
    console.log('Saved HTML: ' + html.length + ' bytes');

    // Find ALL image srcs
    const allSrcs = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('img[src]')).map(img => ({
        src: img.src?.substring(0, 200),
        w: img.width,
        h: img.height,
        classes: img.className,
      }));
    });
    console.log('Images:', JSON.stringify(allSrcs, null, 2));

    // Check for video/slideshow container
    const slideElements = await page.evaluate(() => {
      const divs = document.querySelectorAll('[class*="slide"], [class*="image"], [class*="photo"], [data-e2e*="slide"]');
      return Array.from(divs).map(d => ({
        tag: d.tagName,
        class: d.className?.substring(0, 100),
        children: d.children.length,
      }));
    });
    console.log('Slide elements:', JSON.stringify(slideElements, null, 2));

  } catch (err) {
    console.log('Error:', err.message);
  } finally {
    await browser.close();
  }
}

debug(process.argv[2] || 'https://www.tiktok.com/@blackcat_emmy/photo/7581827324656602376');
