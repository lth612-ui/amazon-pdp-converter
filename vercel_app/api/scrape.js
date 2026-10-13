module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({error:'Method not allowed'});
  try {
    const {url} = req.body || {};
    if (!url) return res.status(400).json({error:'URL이 없습니다.'});
    const u = new URL(url);
    if (!/(^|\.)amazon\.(com|co\.uk|de|co\.jp|fr)$/.test(u.hostname)) return res.status(400).json({error:'지원되는 Amazon URL이 아닙니다.'});
    const r = await fetch(url,{headers:{'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36','accept-language':'en-US,en;q=0.9'},redirect:'follow'});
    if(!r.ok) return res.status(r.status).json({error:`Amazon 응답 오류 ${r.status}`});
    const html=await r.text();
    const clean=s=>String(s||'').replace(/<[^>]+>/g,' ').replace(/&nbsp;/g,' ').replace(/&amp;/g,'&').replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/\s+/g,' ').trim();
    const title=clean((html.match(/id=["']productTitle["'][^>]*>([\s\S]*?)<\/[^>]+>/i)||[])[1]);
    const bullets=[]; const feature=(html.match(/id=["']feature-bullets["'][\s\S]*?<\/div>/i)||[])[0]||''; let m; const re=/<span[^>]*class=["'][^"']*a-list-item[^"']*["'][^>]*>([\s\S]*?)<\/span>/gi; while((m=re.exec(feature))&&bullets.length<8){const t=clean(m[1]);if(t&&t.length>8)bullets.push(t)}
    if(!title&&!bullets.length) return res.status(502).json({error:'Amazon이 자동 수집을 차단했거나 상품 정보를 찾지 못했습니다.'});
    res.status(200).json({title,bullets});
  } catch(e){res.status(500).json({error:e.message||'Scrape error'})}
}