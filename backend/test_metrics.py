"""Step 2 validation: build the weakness engine on REAL data and eyeball it."""
import nba_client
import metrics
import config


def main():
    print(f"Season: {config.SEASON}")
    engine = metrics.build_engine()
    print(f"Comparison pool (rotation players): {engine['pool_size']}")

    # ---- sanity check the scale of *_PCT fields (affects display formatting) ----
    sample = next(r for r in engine["players"].values() if r.get("TS_PCT"))
    print("\n[scale check] a sample player's advanced rates:")
    for f in ["TS_PCT", "EFG_PCT", "AST_PCT", "TM_TOV_PCT", "DREB_PCT", "OREB_PCT", "USG_PCT"]:
        print(f"   {f:12} = {sample.get(f)}")

    # bucket distribution
    from collections import Counter
    buckets = Counter(r.get("POS_BUCKET") for r in engine["players"].values()
                      if (r.get("MIN") or 0) >= config.POOL_MIN_MINUTES
                      and (r.get("GP") or 0) >= config.POOL_MIN_GAMES)
    print(f"\n[pool by position bucket] {dict(buckets)}")

    # ---- per-player weaknesses ----
    roster = nba_client.get_roster()
    players = engine["players"]
    print("\n" + "=" * 78)
    for rp in roster:
        pid = rp["PLAYER_ID"]
        row = players.get(pid)
        name = rp["PLAYER"]
        if not row:
            print(f"\n{name} ({rp.get('POSITION')}): no stats row (did not play).")
            continue
        flags = metrics.sample_flags(row)
        pos = row.get("POSITION") or rp.get("POSITION")
        bucket = row.get("POS_BUCKET")
        hdr = f"\n{name}  [{pos} / {bucket}]  {row.get('GP')}GP {row.get('MIN'):.1f}MPG {row.get('PTS'):.1f}PPG"
        if not flags["analyzable"]:
            print(hdr + f"\n   -> {flags['note']}")
            continue
        weaknesses, _ = metrics.analyze_player(engine, row)
        conf = "  (LOW SAMPLE)" if flags.get("low_confidence") else ""
        print(hdr + conf)
        if not weaknesses:
            print("   no flagged weaknesses (>= {:.0f})".format(config.WEAKNESS_FLAG_SCORE))
        for w in weaknesses:
            print("   - {sev:7} {label:22} {disp:>8}  (better-than {pct:4.0f}% of {scope}, "
                  "league med {med})  score={score:.0f}".format(
                      sev=w["severity"].upper(), label=w["label"], disp=w["display"],
                      pct=w["percentile"], scope=w["pool_scope"],
                      med=w["league_median_display"], score=w["weakness_score"]))

    # ---- shot-zone weaknesses for one high-volume player ----
    print("\n" + "=" * 78)
    klay = next((rp for rp in roster if rp["PLAYER"] == "Klay Thompson"), None)
    if klay:
        print(f"\nShot-zone breakdown: Klay Thompson")
        zones = metrics.shot_zone_weaknesses(klay["PLAYER_ID"])
        for z in zones:
            mark = "  <-- WEAKNESS" if z["is_weakness"] else ""
            print("   {zone:22} {fgm:>3}/{fga:<3} = {p:>6}  vs lg {lg:>6}{mark}".format(
                zone=z["zone"], fgm=z["fgm"], fga=z["fga"],
                p=z["fg_pct_display"], lg=z["league_fg_pct_display"], mark=mark))


if __name__ == "__main__":
    main()
