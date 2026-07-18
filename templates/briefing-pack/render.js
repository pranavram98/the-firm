// the-firm briefing-pack renderer — Puppeteer owns margins; HTML flows freely.
// Placeholders {{CAUSE_TITLE}} / {{FILES}} are filled by `firm brief` at scaffold time.
const puppeteer = require('puppeteer');
const path = require('path');

const DIR = __dirname;
const CAUSE = '{{CAUSE_TITLE}}';
const files = [{{FILES}}];

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  for (const name of files) {
    const page = await browser.newPage();
    const url = 'file://' + path.join(DIR, encodeURIComponent(name) + '.html');
    await page.goto(url, { waitUntil: 'networkidle0' });
    const footer = `<div style="font-family:Arial;font-size:7pt;color:#999;width:100%;text-align:center;padding:0 14mm;">
      ${name}${CAUSE ? ' — ' + CAUSE : ''} &nbsp;·&nbsp; Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>`;
    await page.pdf({
      path: path.join(DIR, name + '.pdf'),
      format: 'A4',
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: '<div></div>',
      footerTemplate: footer,
      margin: { top: '15mm', bottom: '17mm', left: '16mm', right: '16mm' },
    });
    console.log('PDF written:', name + '.pdf');
    await page.close();
  }
  await browser.close();
})();
