// מתווך לאפליקציית מבזק: מעביר דפי תצוגה ציבוריים של ערוצי טלגרם
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', 'https://yv05276-dot.github.io');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  const c = String(req.query.c || '');
  const before = String(req.query.before || '');
  if (!/^[A-Za-z][A-Za-z0-9_]{3,31}$/.test(c)) return res.status(200).send('OK mivzak');
  const target = 'https://t.me/s/' + c + (/^\d+$/.test(before) ? '?before=' + before : '');
  const r = await fetch(target, { headers: { 'User-Agent': 'Mozilla/5.0' } });
  const html = await r.text();
  const title = (html.match(/<div class="tgme_channel_info_header_title[\s\S]*?<\/div>/) || [''])[0];
  const i = html.indexOf('<section class="tgme_channel_history');
  res.status(r.status).send(title + (i >= 0 ? html.slice(i) : html));
};
