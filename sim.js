// Play Booster simulation for Reality Fracture (FRA).
//
// Slot structure and odds come from the official article
// "Collecting Reality Fracture" (magic.wizards.com). Each Play Booster has
// 14 Magic cards:
//   6 commons (1 booster in 55 swaps one common for a Special Guests card)
//   1 uncommon
//   1 common or uncommon
//   3 echoed pairs cards (2 form a pair, the third is from another pair)
//   1 rare or mythic rare
//   1 traditional foil of any rarity
//   1 land
// Odds the article gives as "under 1%" are modelled as 0.5%, or as an equal
// share of the remainder for the foil slot.

(function (root) {
  "use strict";

  // One entry = {pool, rarity?, pools?, foil?, w}. w is a percentage.
  const SLOTS = {
    uncommon: [
      { pool: "uncommon", w: 96.2 },
      { pool: "braintwister", rarity: "uncommon", w: 3.8 },
    ],
    wildcard: [
      { pool: "common", w: 23 },
      { pool: "uncommon", w: 74 },
      { pool: "braintwister", rarity: "uncommon", w: 3 },
    ],
    echo: [
      { pool: "echo", rarity: "uncommon", w: 88.9 },
      { pool: "echo", rarity: "rare", w: 6.7 },
      { pool: "echo", rarity: "mythic", w: 1.4 },
      { pool: "echo_borderless", rarity: "uncommon", w: 1.7 },
      { pool: "echo_borderless", rarity: "rare", w: 0.5 },
      { pool: "echo_borderless", rarity: "mythic", w: 0.5 },
    ],
    rare: [
      { pool: "rare", w: 74.4 },
      { pool: "mythic", w: 14.8 },
      { pool: "shattered", rarity: "rare", w: 1.0 },
      { pool: "shattered", rarity: "mythic", w: 0.5 },
      { pool: "stronghold", rarity: "rare", w: 3.8 },
      { pool: "stronghold", rarity: "mythic", w: 1.0 },
      { pool: "braintwister", rarity: "rare", w: 3.1 },
      { pool: "braintwister", rarity: "mythic", w: 0.5 },
      { pool: "portal", rarity: "rare", w: 1.0 },
    ],
    foil: [
      { pools: ["common"], rarity: "common", w: 49.5 },
      { pools: ["uncommon", "echo"], rarity: "uncommon", w: 40.5 },
      { pools: ["rare", "echo"], rarity: "rare", w: 6.0 },
      { pools: ["mythic", "echo"], rarity: "mythic", w: 1.2 },
      // Nine treatments share the remaining 2.8%.
      { pool: "echo_borderless", rarity: "uncommon", w: 2.8 / 9 },
      { pool: "echo_borderless", rarity: "rare", w: 2.8 / 9 },
      { pool: "echo_borderless", rarity: "mythic", w: 2.8 / 9 },
      { pool: "braintwister", rarity: "uncommon", w: 2.8 / 9 },
      { pool: "braintwister", rarity: "rare", w: 2.8 / 9 },
      { pool: "braintwister", rarity: "mythic", w: 2.8 / 9 },
      { pool: "stronghold", rarity: "rare", w: 2.8 / 9 },
      { pool: "stronghold", rarity: "mythic", w: 2.8 / 9 },
      { pool: "portal", rarity: "rare", w: 2.8 / 9 },
    ],
    land: [
      { pool: "basic", foil: false, w: 14.6 },
      { pool: "basic", foil: true, w: 3.6 },
      { pool: "tower", foil: false, w: 21.8 },
      { pool: "tower", foil: true, w: 5.5 },
      { pool: "dual", foil: false, w: 43.6 },
      { pool: "dual", foil: true, w: 10.9 },
    ],
  };
  const COMMONS_PER_BOOSTER = 6;
  const SPG_ODDS = 1 / 55;

  // ---- helpers ------------------------------------------------------------

  function buildPools(cards) {
    const pools = {};
    for (const c of cards) {
      if (!pools[c.pool]) pools[c.pool] = { all: [] };
      pools[c.pool].all.push(c);
      if (!pools[c.pool][c.rarity]) pools[c.pool][c.rarity] = [];
      pools[c.pool][c.rarity].push(c);
    }
    return pools;
  }

  function weighted(entries, rng) {
    const total = entries.reduce((s, e) => s + e.w, 0);
    let r = rng() * total;
    for (const e of entries) {
      r -= e.w;
      if (r < 0) return e;
    }
    return entries[entries.length - 1];
  }

  function candidates(pools, entry) {
    const names = entry.pools || [entry.pool];
    let list = [];
    for (const name of names) {
      const p = pools[name];
      if (!p) continue;
      list = list.concat(entry.rarity ? p[entry.rarity] || [] : p.all);
    }
    return list;
  }

  function pickFrom(list, rng, exclude) {
    if (!list.length) throw new Error("empty pool");
    for (let i = 0; i < 50; i++) {
      const c = list[Math.floor(rng() * list.length)];
      if (!exclude || !exclude.has(c)) return c;
    }
    return list[Math.floor(rng() * list.length)];
  }

  // Theoretical probability that one draw from `entries` satisfies `pred`.
  function probability(entries, pred) {
    const total = entries.reduce((s, e) => s + e.w, 0);
    return entries.filter(pred).reduce((s, e) => s + e.w, 0) / total;
  }

  // ---- seeded random numbers ----------------------------------------------

  // rng(seed) returns a function like Math.random whose sequence depends only
  // on the seed string: an xmur3 hash of the seed feeds a mulberry32 stream.
  // The same seed with the same card data and SLOTS gives the same booster.
  function rng(seed) {
    let h = 1779033703 ^ seed.length;
    for (let i = 0; i < seed.length; i++) {
      h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
      h = (h << 13) | (h >>> 19);
    }
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    let a = (h ^ (h >>> 16)) >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---- booster ------------------------------------------------------------

  function slot(card, name, foil, extra) {
    return Object.assign({ card, slot: name, foil: !!foil }, extra || {});
  }

  function openBooster(pools, rng) {
    rng = rng || Math.random;
    const out = [];
    const used = new Set();

    // 6 commons, distinct. 1 booster in 55 swaps one for a Special Guests.
    const spg = rng() < SPG_ODDS;
    const nCommons = spg ? COMMONS_PER_BOOSTER - 1 : COMMONS_PER_BOOSTER;
    for (let i = 0; i < nCommons; i++) {
      const c = pickFrom(pools.common.all, rng, used);
      used.add(c);
      out.push(slot(c, "common"));
    }
    if (spg) out.push(slot(pickFrom(pools.spg.all, rng), "spg"));

    // 1 uncommon.
    {
      const e = weighted(SLOTS.uncommon, rng);
      const c = pickFrom(candidates(pools, e), rng, used);
      used.add(c);
      out.push(slot(c, "uncommon"));
    }

    // 1 common or uncommon.
    {
      const e = weighted(SLOTS.wildcard, rng);
      const c = pickFrom(candidates(pools, e), rng, used);
      used.add(c);
      out.push(slot(c, "wildcard"));
    }

    // 3 echoed pairs cards: a matching pair plus a third card from another pair.
    {
      const e = weighted(SLOTS.echo, rng);
      const a = pickFrom(candidates(pools, e), rng);
      const b = pools[e.pool].all.find((c) => c.pair === a.pair && c !== a);
      if (!b) throw new Error("no partner for " + a.en);
      out.push(slot(a, "echo", false, { pairGroup: 1 }));
      out.push(slot(b, "echo", false, { pairGroup: 1 }));
      const e3 = weighted(SLOTS.echo, rng);
      const others = candidates(pools, e3).filter((c) => c.pair !== a.pair);
      out.push(slot(pickFrom(others, rng), "echo", false, { pairGroup: 0 }));
    }

    // 1 rare or mythic rare.
    {
      const e = weighted(SLOTS.rare, rng);
      out.push(slot(pickFrom(candidates(pools, e), rng), "rare"));
    }

    // 1 traditional foil of any rarity.
    {
      const e = weighted(SLOTS.foil, rng);
      out.push(slot(pickFrom(candidates(pools, e), rng), "foil", true));
    }

    // 1 land.
    {
      const e = weighted(SLOTS.land, rng);
      out.push(slot(pickFrom(candidates(pools, e), rng), "land", e.foil));
    }

    return out;
  }

  // ---- expected rates per booster (for the statistics panel) ---------------

  const isMythic = (e) => e.rarity === "mythic" || e.pool === "mythic";
  const isRarePlus = (e) =>
    isMythic(e) || e.rarity === "rare" || e.pool === "rare";
  const isFun = (e) =>
    ["echo_borderless", "shattered", "stronghold", "braintwister", "portal"].includes(e.pool);

  const EXPECTED = {
    mythicInRareSlot: probability(SLOTS.rare, isMythic),
    funInRareSlot: probability(SLOTS.rare, isFun),
    foilRarePlus: probability(SLOTS.foil, isRarePlus),
    foilLand: probability(SLOTS.land, (e) => e.foil),
    echoPairRarePlus: probability(SLOTS.echo, isRarePlus),
    // The pair shares one treatment draw, the third card has its own: 2 draws.
    echoBorderlessAny: 1 - Math.pow(1 - probability(SLOTS.echo, (e) => e.pool === "echo_borderless"), 2),
    braintwisterUncommon:
      1 - (1 - probability(SLOTS.uncommon, (e) => e.pool === "braintwister")) *
        (1 - probability(SLOTS.wildcard, (e) => e.pool === "braintwister")),
    spg: SPG_ODDS,
  };

  const api = { SLOTS, EXPECTED, SPG_ODDS, buildPools, openBooster, probability, rng };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.SIM = api;
})(typeof window !== "undefined" ? window : globalThis);
