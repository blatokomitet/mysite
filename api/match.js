export default async function handler(req,res){
  const key=process.env.API_FOOTBALL_KEY;
  if(!key)return res.status(500).json({error:'API_FOOTBALL_KEY is not configured'});
  const id=req.query?.fixture;
  if(!id)return res.status(400).json({error:'fixture is required'});
  const base='https://v3.football.api-sports.io';
  const get=async(path)=>{const r=await fetch(base+path,{headers:{'x-apisports-key':key}});if(!r.ok)throw Error(`API ${r.status}`);const j=await r.json();return j.response||[]};
  try{
    const f=(await get(`/fixtures?id=${encodeURIComponent(id)}`))[0]; if(!f)return res.status(404).json({error:'Fixture not found'});
    const homeId=f.teams.home.id,awayId=f.teams.away.id,leagueId=f.league.id,season=f.league.season;
    const [pred,homeFix,awayFix,h2h,stand]=await Promise.all([
      get(`/predictions?fixture=${id}`),get(`/fixtures?team=${homeId}&last=5`),get(`/fixtures?team=${awayId}&last=5`),get(`/fixtures/headtohead?h2h=${homeId}-${awayId}&last=5`),get(`/standings?league=${leagueId}&season=${season}`)
    ]);
    const form=(teamId,name,arr)=>{const results=arr.filter(x=>x.fixture.id!==f.fixture.id).slice(-5).map(x=>{const isH=x.teams.home.id===teamId;const a=isH?x.goals.home:x.goals.away,b=isH?x.goals.away:x.goals.home;return a==null||b==null?'':a>b?'W':a<b?'L':'D'}).filter(Boolean);const games=arr.filter(x=>x.goals.home!=null&&x.goals.away!=null);let gf=0;games.forEach(x=>{gf+=x.teams.home.id===teamId?x.goals.home:x.goals.away});return {name,results,avgGoals:games.length?gf/games.length:null,btts:games.length?Math.round(games.filter(x=>x.goals.home>0&&x.goals.away>0).length/games.length*100):null,standing:findStanding(stand,teamId)}};
    const prediction=pred[0]?.predictions||{};const percent=pred[0]?.predictions?.percent||{};const goals=pred[0]?.predictions?.goals||{};
    const home=form(homeId,f.teams.home.name,homeFix),away=form(awayId,f.teams.away.name,awayFix);
    const hrows=h2h.map(x=>({label:`${x.teams.home.name} ${x.goals.home??'-'}:${x.goals.away??'-'} ${x.teams.away.name}`,value:x.fixture.date?.slice(0,10)||''}));
    const standings=findLeague(stand);
    return res.status(200).json({fixture:{id:f.fixture.id,home:f.teams.home.name,away:f.teams.away.name,homeLogo:f.teams.home.logo,awayLogo:f.teams.away.logo,league:f.league.name,time:new Date(f.fixture.date).toLocaleString('ru-RU',{hour:'2-digit',minute:'2-digit'}),status:f.fixture.status.short,venue:f.fixture.venue?.name},home,away,h2h:{count:hrows.length,rows:hrows},prediction:{home:parse(percent.home),draw:parse(percent.draw),away:parse(percent.away),homeGoals:parse(goals.home),awayGoals:parse(goals.away),advice:prediction.advice||null,underOver:prediction.under_over||null,btts:prediction.btts||null,note:prediction.advice?'Источник: API-Football Prediction Engine.':'Prediction unavailable.'},odds:{rows:[]},sources:{prediction:!!pred[0],form:home.results.length>0||away.results.length>0,h2h:hrows.length>0,standings:!!standings,odds:false},risk:{level:pred[0]?'MODELLED':'HIGH RISK',reason:pred[0]?'Сигнал основан на данных API-Football; это не гарантия результата.':'Недостаточно подтверждённых предматчевых данных.'}});
  }catch(e){return res.status(502).json({error:e.message})}
}
function parse(v){if(v==null)return null;const n=parseFloat(String(v).replace('%',''));return Number.isFinite(n)?n:null}
function findStanding(data,id){const s=findLeague(data);const r=s?.standings?.flat()?.find(x=>x.team.id===id);return r?{team:r.team.name,rank:r.rank,points:r.points}:null}
function findLeague(data){return data?.[0]||null}
