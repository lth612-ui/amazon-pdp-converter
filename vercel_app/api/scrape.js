const AMAZON_HOSTS = new Set([
  'amazon.com',
  'amazon.ca',
  'amazon.com.mx',
  'amazon.com.br',
  'amazon.co.uk',
  'amazon.de',
  'amazon.fr',
  'amazon.it',
  'amazon.es',
  'amazon.nl',
  'amazon.se',
  'amazon.pl',
  'amazon.com.be',
  'amazon.ie',
  'amazon.com.tr',
  'amazon.co.jp',
  'amazon.com.au',
  'amazon.in',
  'amazon.sg',
  'amazon.ae',
  'amazon.sa',
  'amazon.eg',
  'amazon.co.za'
]);

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({error:'Method not allowed'});
  try {
    const {url} = req.body || {};
    if (!url) return res.status(400).json({error:'URL이 없습니다.'});

    const u = new URL(url);
    const host = u.hostname.toLowerCase().replace(/^www\./, '');
    if (!AMAZON_HOSTS.has(host)) {
      return res.status(400).json({error:'지원되는 Amazon Marketplace URL이 아닙니다.'});
    }

    const locale = {
      'amazon.co.jp':'ja-JP,ja;q=0.9,en;q=0.5',
      'amazon.de':'de-DE,de;q=0.9,en;q=0.5',
      'amazon.fr':'fr-FR,fr;q=0.9,en;q=0.5',
      'amazon.it':'it-IT,it;q=0.9,en;q=0.5',
      'amazon.es':'es-ES,es;q=0.9,en;q=0.5',
      'amazon.com.mx':'es-MX,es;q=0.9,en;q=0.5',
      'amazon.com.br':'pt-BR,pt;q=0.9,en;q=0.5',
      'amazon.nl':'nl-NL,nl;q=0.9,en;q=0.5',
      'amazon.se':'sv-SE,sv;q=0.9,en;q=0.5',
      'amazon.pl':'pl-PL,pl;q=0.9,en;q=0.5',
      'amazon.com.tr':'tr-TR,tr;q=0.9,en;q=0.5',
      'amazon.ae':'en-AE,en;q=0.9,ar;q=0.6',
      'amazon.sa':'ar-SA,ar;q=0.9,en;q=0.6',
      'amazon.eg':'ar-EG,ar;q=0.9,en;q=0.6'
    }[host] || 'en-US,en;q=0.9';

    const r = await fetch(url, {
      headers: {
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'accept-language': locale
      },
      redirect:'follow'
    });

    if (!r.ok) return res.status(r.status).json({error:`Amazon 응답 오류 ${r.status}`});

    const html = await r.text();
    const clean = s => String(s || '')
      .replace(/<[^>]+>/g,' ')
      .replace(/&nbsp;/g,' ')
      .replace(/&amp;/g,'&')
      .replace(/&#39;/g,"'")
      .replace(/&quot;/g,'"')
      .replace(/\s+/g,' ')
      .trim();

    const title = clean((html.match(/id=["']productTitle["'][^>]*>([\s\S]*?)<\/[^>]+>/i) || [])[1]);
    const bullets = [];
    const feature = (html.match(/id=["']feature-bullets["'][\s\S]*?<\/div>/i) || [])[0] || '';
    let m;
    const re = /<span[^>]*class=["'][^"']*a-list-item[^"']*["'][^>]*>([\s\S]*?)<\/span>/gi;
    while ((m = re.exec(feature)) && bullets.length < 8) {
      const t = clean(m[1]);
      if (t && t.length > 8) bullets.push(t);
    }

    if (!title && !bullets.length) {
      return res.status(502).json({error:'Amazon이 자동 수집을 차단했거나 상품 정보를 찾지 못했습니다.'});
    }

    res.status(200).json({title, bullets, marketplace: host});
  } catch (e) {
    res.status(500).json({error:e.message || 'Scrape error'});
  }
};