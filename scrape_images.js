const { launch } = require('puppeteer-core');
const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

async function getImages(url) {
  const browser = await launch({
    executablePath: EDGE_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'],
  });

  const page = await browser.newPage();
  const allImgUrls = [];

  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
  
  // Override webdriver navigator
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  // Capture network responses with image content
  page.on('response', async response => {
    const url = response.url();
    const type = response.headers()['content-type'] || '';
    if (type.startsWith('image/') && 
        (url.includes('p') && url.match(/p\d+\.(muscdn|tiktokcdn)/))) {
      allImgUrls.push(url);
    }
  });

  try {
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 3000));

    // Get image sources from DOM
    const domImgs = await page.evaluate(() => {
      const imgs = document.querySelectorAll('img');
      return Array.from(imgs).map(i => i.src).filter(s => s && !s.startsWith('data:'));
    });

    const combined = [...new Set([...domImgs, ...allImgUrls])];
    const filtered = combined.filter(u => 
      u.match(/p\d+\.(muscdn|tiktokcdn|byteimg)/) && 
      !u.includes('noop') && !u.includes('captcha') && !u.includes('fifa')
    );

    console.log(JSON.stringify({ 
      success: true, 
      count: filtered.length, 
      urls: filtered,
      totalRequests: allImgUrls.length,
      domCount: domImgs.length,
    }));
  } catch (err) {
    console.log(JSON.stringify({ success: false, error: err.message }));
  } finally {
    await browser.close();
  }
}

getImages(process.argv[2]);
