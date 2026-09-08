export default async function handler(req, res) {
  try {
    const key = process.env.API_FOOTBALL_KEY;
    const id = req.query?.fixture;

    if (!key) return res.status(500).json({ error: 'API_FOOTBALL_KEY is not configured in Vercel' });
    if (!id) return res.status(400).json({ error: 'fixture is required' });

    const base = 'https://v3.football.api-sports.io';

    const get = async (path) => {
      const r = await fetch(base + path, {
        headers: { 'x-apisports-key': key },
        cache: 'no-store'
      });
      const text = await r.text();
      let json = {};
      try { json = JSON.parse(text); } catch (_) {}
      if (!r.ok) throw new Error(`API-Football ${r.status}: ${json?.errors ? JSON.stringify(json.errors) : text.slice(0, 160)}`);
      return json.response || [];
    };

    const fixtures = await get(`/fixtures?id=${encodeURIComponent(id)}`);
    const f = fixtures[0];
    if (!f) return res.status(404).json({ error: 'Fixture not found' });

    const homeId = f.teams.home.id;
    const awayId = f.teams.away.id;
    const leagueId = f.league.id;
    const season = f.league.season;

    // Each secondary source is isolated so one unavailable endpoint cannot crash the whole Mini App.
    const safe = async (path) => {
      try { return { data: await get(path), ok: true }; }
      catch (e) { return { data: [], ok: false, error: e.message }; }
    };

    const [predR, homeR, awayR, h2hR, standR, oddsR] = await Promise.all([
      safe(`/predictions?fixture=${id}`),
      safe(`/fixtures?team=${homeId}&last=5`),
      safe(`/fixtures?team=${awayId}&last=5`),
      safe(`/fixtures/headtohead?h2h=${homeId}-${awayId}&last=5`),
      safe(`/standings?league=${leagueId}&season=${season}`),
      safe(`/odds?fixture=${id}`)
    ]);

    const form = (teamId, name, arr) => {
      const completed = arr.filter(x => x.fixture.id !== f.fixture.id && x.goals.home != null && x.goals.away != null);
      const recent = completed.slice(-5);
      const results = recent.map(x => {
        const isHome = x.teams.home.id === teamId;
        const a = isHome ? x.goals.home : x.goals.away;
        const b = isHome ? x.goals.away : x.goals.home;
        return a > b ? 'W' : a < b ? 'L' : 'D';
      });
      let gf = 0, bttsCount = 0;
      recent.forEach(x => {
        const isHome = x.teams.home.id === teamId;
        gf += isHome ? x.goals.home : x.goals.away;
        if (x.goals.home > 0 && x.goals.away > 0) bttsCount++;
      });
      return {
        name,
        results,
        avgGoals: recent.length ? +(gf / recent.length).toFixed(2) : null,
        btts: recent.length ? Math.round(bttsCount / recent.length * 100) : null,
        standing: findStanding(standR.data, teamId)
      };
    };

    const p = predR.data[0]?.predictions || {};
    const percent = p.percent || {};
    const goals = p.goals || {};
    const home = form(homeId, f.teams.home.name, homeR.data);
    const away = form(awayId, f.teams.away.name, awayR.data);

    const hrows = h2hR.data.map(x => ({
      label: `${x.teams.home.name} ${x.goals.home ?? '-'}:${x.goals.away ?? '-'} ${x.teams.away.name}`,
      value: x.fixture.date?.slice(0, 10) || ''
    }));

    const oddsRows = parseOdds(oddsR.data);

    return res.status(200).json({
      fixture: {
        id: f.fixture.id,
        home: f.teams.home.name,
        away: f.teams.away.name,
        homeLogo: f.teams.home.logo,
        awayLogo: f.teams.away.logo,
        league: f.league.name,
        time: new Date(f.fixture.date).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
        status: f.fixture.status.short,
        venue: f.fixture.venue?.name || null
      },
      home,
      away,
      h2h: { count: hrows.length, rows: hrows },
      prediction: {
        home: parse(percent.home),
        draw: parse(percent.draw),
        away: parse(percent.away),
        homeGoals: parse(goals.home),
        awayGoals: parse(goals.away),
        advice: p.advice || null,
        underOver: p.under_over || null,
        btts: p.btts || null,
        note: p.advice ? 'Источник: API-Football Prediction Engine.' : 'Prediction unavailable.'
      },
      odds: { rows: oddsRows },
      sources: {
        prediction: predR.ok && !!predR.data[0],
        form: home.results.length > 0 || away.results.length > 0,
        h2h: hrows.length > 0,
        standings: standR.ok && !!standR.data[0],
        odds: oddsRows.length > 0
      },
      risk: {
        level: predR.data[0] ? 'MODELLED' : 'HIGH RISK',
        reason: predR.data[0]
          ? 'Сигнал основан на данных API-Football; это не гарантия результата.'
          : 'Недостаточно подтверждённых предматчевых данных.'
      }
    });
  } catch (e) {
    console.error('Mini App API error:', e);
    return res.status(500).json({ error: e?.message || 'Internal server error' });
  }
}

function parse(v) {
  if (v == null) return null;
  const n = parseFloat(String(v).replace('%', ''));
  return Number.isFinite(n) ? n : null;
}

function findStanding(data, id) {
  const groups = data?.[0]?.league?.standings || [];
  const rows = groups.flat();
  const r = rows.find(x => x?.team?.id === id);
  return r ? { team: r.team.name, rank: r.rank, points: r.points } : null;
}

function parseOdds(data) {
  const rows = [];
  for (const book of data || []) {
    for (const bet of book.bookmakers || []) {
      for (const market of bet.bets || []) {
        const values = (market.values || []).slice(0, 3).map(v => `${v.value}: ${v.odd}`).join(' · ');
        if (values) rows.push({ label: market.name || 'Market', value: values });
        if (rows.length >= 8) return rows;
      }
    }
  }
  return rows;
}