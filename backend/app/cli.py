"""
VARUNA Forecaster CLI (Command Line Interface).
Provides operational meteorologists and automated cron scripts direct terminal access
to forecast fusion, spatial weight maps, chaos failure injection, and benchmark audits.
"""

import argparse
import sys
import json
from datetime import datetime, timezone
from typing import Optional

def setup_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="varuna",
        description="VARUNA: Adaptive Forecast Intelligence Platform CLI (MoES / NCMRWF — SIH26081)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Run dynamic adaptive forecast fusion
  python -m app.cli blend --region IN_TELANGANA_HYDERABAD --lead 48 --regime HEAVY_RAINFALL

  # 2. View nationwide model weight map across 14 subdivisions
  python -m app.cli weight-map --lead 48 --variable rainfall --regime HEAVY_RAINFALL

  # 3. Execute strictly causal temporal benchmark experiment
  python -m app.cli benchmark --persist

  # 4. Inject runtime fault (e.g. simulate NCUM feed failure)
  python -m app.cli chaos --action simulate_missing_model --model NCUM

  # 5. Reset all chaos scenarios
  python -m app.cli chaos --action reset_scenario
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command 1: blend
    blend_p = subparsers.add_parser("blend", help="Compute dynamically blended multi-model forecast")
    blend_p.add_argument("--region", default="IN_TELANGANA_HYDERABAD", help="Target region ID")
    blend_p.add_argument("--variable", default="rainfall", choices=["rainfall", "temperature", "wind_speed"])
    blend_p.add_argument("--lead", type=int, default=48, choices=[24, 48, 72], help="Lead time in hours")
    blend_p.add_argument("--regime", default="HEAVY_RAINFALL", choices=["NORMAL", "HEAVY_RAINFALL", "CONVECTIVE", "TRANSITION_UNCERTAIN"])
    blend_p.add_argument("--strategy", default="ADAPTIVE_ML", choices=["ADAPTIVE_ML", "ADAPTIVE_RELIABILITY"])

    # Command 2: weight-map
    map_p = subparsers.add_parser("weight-map", help="Display spatial model trust map across India")
    map_p.add_argument("--lead", type=int, default=48, choices=[24, 48, 72])
    map_p.add_argument("--variable", default="rainfall", choices=["rainfall", "temperature", "wind_speed"])
    map_p.add_argument("--season", default="SW_MONSOON")
    map_p.add_argument("--regime", default="HEAVY_RAINFALL")
    map_p.add_argument("--model", default=None, help="Optional model focus filter (NCUM, GFS, WRF, AI_WEATHER)")
    map_p.add_argument("--json", action="store_true", help="Output raw GeoJSON FeatureCollection")

    # Command 3: benchmark
    bench_p = subparsers.add_parser("benchmark", help="Execute 500-day strictly causal temporal benchmark")
    bench_p.add_argument("--persist", action="store_true", help="Save experiment run to database")
    bench_p.add_argument("--split", type=float, default=0.70, help="Train/test split ratio (default: 0.70)")

    # Command 4: chaos (failure injection)
    chaos_p = subparsers.add_parser("chaos", help="Inject or reset runtime anomalies and faults")
    chaos_p.add_argument("--action", required=True, choices=["simulate_model_bias", "simulate_missing_model", "simulate_disagreement", "reset_scenario"])
    chaos_p.add_argument("--model", default=None, help="Target model ID (e.g. GFS, NCUM, WRF)")
    chaos_p.add_argument("--bias", type=float, default=25.0, help="Additive bias for simulate_model_bias")

    # Command 5: audit
    subparsers.add_parser("audit", help="Display provenance audit and scientific validation summary")

    return parser

def handle_blend(args):
    from app.demo.scenario_generator import scenario_generator
    unit = "mm" if args.variable == "rainfall" else "C" if args.variable == "temperature" else "km/h"

    res = scenario_generator.execute_pipeline(
        custom_context={
            "region_id": args.region,
            "variable": args.variable,
            "lead_hours": args.lead,
            "weather_regime": args.regime,
            "strategy": args.strategy
        }
    )

    print("\n" + "=" * 76)
    print(f" VARUNA ADAPTIVE FORECAST BLENDING ENGINE [{args.strategy}]")
    print("=" * 76)
    print(f" Region:          {args.region}")
    print(f" Variable:        {args.variable.upper()} ({unit})")
    print(f" Lead Time:       {args.lead}h Forecast Horizon")
    print(f" Synoptic Regime: {args.regime}")
    print("-" * 76)
    print(" 1. HARMONIZED MULTI-MODEL INPUTS:")
    for m, val in res["model_forecasts"].items():
        print(f"    * {m:<14s}: {val:6.1f} {unit}")
    
    print("\n 2. DYNAMIC TRUST WEIGHTS (Simplex Normalization: sum = 100%):")
    for w in res["weights"]:
        bar = "#" * int(w["weight"] * 25)
        print(f"    * {w['model_id']:<14s} [{bar:<25s}] {w['weight']*100:5.1f}% ({w['status']})")

    
    print("\n 3. FUSED CONSENSUS & UNCERTAINTY GUIDANCE:")
    print(f"    * VARUNA Blended Forecast:   {res['fused_value']:6.1f} {unit}")
    print(f"    * Simple Multi-Model Avg:    {res['baselines']['simple_average']:6.1f} {unit}")
    print(f"    * Static Operational Blend:  {res['baselines']['static_blend']:6.1f} {unit}")
    print(f"    * Model Disagreement Spread: {res['disagreement']['range']:6.1f} {unit} [{res['disagreement']['disagreement_level']}]")

    print(f"    * Exceedance Probability:    {res['uncertainty']['probability']:6.1f}%")
    print(f"    * Epistemic Confidence:      {res['uncertainty']['confidence']} (Score: {res['uncertainty']['confidence_score']:.2f})")
    print("-" * 76)
    print(" 4. DECISION BRIEFING (\"Why this forecast?\"):")
    print(f"    {res['explanation']['text']}")
    print("=" * 76 + "\n")


def handle_weight_map(args):
    from app.intelligence.spatial_weight_map import generate_spatial_weight_map
    map_res = generate_spatial_weight_map(
        variable=args.variable,
        lead_hours=args.lead,
        season=args.season,
        weather_regime=args.regime,
        model_focus=args.model
    )

    if args.json:
        print(json.dumps(map_res, indent=2))
        return

    meta = map_res["metadata"]
    print("\n" + "=" * 88)
    print(f" VARUNA NATIONWIDE MODEL TRUST MAP ({meta['total_regions']} Meteorological Subdivisions)")
    print("=" * 88)
    print(f" Variable: {args.variable.upper()} | Lead: {args.lead}h | Season: {args.season} | Regime: {args.regime}")
    print(f" Dominance Summary: {meta['dominance_coverage_pct']}")
    print(f" Nationwide Avg Weights: {meta['nationwide_average_weights']}")
    print("-" * 88)
    print(f" {'Subdivision Name':<32s} | {'Dominant':<11s} | {'Weight':<6s} | {'Blend':<8s} | {'Confidence':<10s}")
    print("-" * 88)

    for feat in map_res["features"]:
        p = feat["properties"]
        dom_w = f"{p['dominant_weight']*100:.1f}%"
        blend = f"{p['fused_forecast']:.1f}"
        print(f" {p['region_name'][:32]:<32s} | {p['dominant_model']:<11s} | {dom_w:<6s} | {blend:<8s} | {p['confidence']:<10s}")

    print("-" * 88)
    print(f" Insight: {meta['lead_time_insight']}")
    print("=" * 88 + "\n")

def handle_benchmark(args):
    from app.experiments.benchmark_runner import benchmark_runner
    print("\n[Executing VARUNA Strictly Causal 500-Day Temporal Benchmark...]")
    res = benchmark_runner.run_experiment()

    print("\n" + "=" * 90)
    print(f" VARUNA STRICTLY CAUSAL EMPIRICAL BENCHMARK ({res['experiment_id']})")
    print("=" * 90)
    print(f" Evaluation Protocol: Strict Temporal Split ({res['split_ratio']})")
    print(f" Sample Horizon:      {res['total_samples']} Days ({res['train_samples']} Train / {res['unseen_test_samples']} Unseen Test)")
    print(f" Provenance Tag:      {res['data_provenance']} (Zero Instantaneous Leakage)")
    print("-" * 90)
    print(f" {'Method':<32s} | {'MAE (mm)':<8s} | {'RMSE (mm)':<9s} | {'Bias':<7s} | {'Corr':<6s} | {'CSI':<5s}")
    print("-" * 90)
    for r in res["results_table"]:
        csi_str = f"{r['csi']:.3f}" if r['csi'] is not None else "N/A"
        print(f" {r['method']:<32s} | {r['mae']:<8.2f} | {r['rmse']:<9.2f} | {r['bias']:<+7.2f} | {r['correlation']:<6.3f} | {csi_str:<5s}")
    
    print("-" * 90)
    find = res["scientific_findings"]
    print(f" Simple Multi-Model Average MAE: {find['simple_average_mae']:.2f} mm")
    print(f" Adaptive ML Meta-Model MAE:     {find['adaptive_ml_meta_model_mae']:.2f} mm")
    print(f" Verified Causal Skill Gain:     {find['ml_mae_reduction_vs_simple_average_pct']:+.2f}% Error Reduction")
    print("=" * 90 + "\n")

    if args.persist:
        from app.core.database import SessionLocal
        from app.models.experiment import ExperimentRun
        db = SessionLocal()
        try:
            run_rec = ExperimentRun(
                title=res["title"],
                split_ratio=benchmark_runner.split_ratio,
                train_samples=res["train_samples"],
                unseen_test_samples=res["unseen_test_samples"],
                variable="rainfall",
                provenance=res["data_provenance"],
                results_table=res["results_table"],
                mae_reduction_vs_simple_avg_pct=find["ml_mae_reduction_vs_simple_average_pct"],
                mae_reduction_vs_heuristic_pct=find["ml_mae_reduction_vs_heuristic_baseline_pct"],
                scientific_summary=find,
                markdown_report=res.get("markdown_report")
            )
            db.add(run_rec)
            db.commit()
            print(f"[SUCCESS] Persisted experiment run to database with ID: {run_rec.id}")
        finally:
            db.close()

def handle_chaos(args):
    from app.intelligence.failure_memory import failure_memory
    from app.demo.scenario_generator import scenario_generator

    action = args.action.lower().strip()
    target_model = args.model.upper() if args.model else "GFS"

    if action == "simulate_model_bias":
        bias = args.bias or 35.0
        failure_memory.inject_model_bias(target_model, bias)
        msg = f"Injected operational bias (+{bias} mm) into {target_model}."
    elif action == "simulate_missing_model":
        failure_memory.disable_model(target_model)
        msg = f"Model {target_model} marked UNAVAILABLE. Remaining weights re-normalized."
    elif action == "simulate_disagreement":
        failure_memory.force_disagreement(True)
        msg = "Forced multi-model divergence. Epistemic uncertainty increased; confidence lowered."
    elif action == "reset_scenario":
        failure_memory.reset()
        msg = "All failure overrides cleared. Nominal operational state restored."
    else:
        print(f"Unknown action: {args.action}")
        return

    res = scenario_generator.execute_pipeline()

    print("\n" + "=" * 70)
    print(f" VARUNA CHAOS & RUNTIME FAULT INJECTION: {action.upper()}")
    print("=" * 70)
    print(f" Details:  {msg}")
    print("-" * 70)
    print(" Rebalanced Model Weights Following Fault:")
    for w in res["weights"]:
        bar = "#" * int(w["weight"] * 25)
        print(f"  * {w['model_id']:<14s} [{bar:<25s}] {w['weight']*100:5.1f}% ({w['status']})")
    print(f"\n Updated Fused Value: {res['fused_value']:.1f} mm | Confidence: {res['uncertainty']['confidence']}")
    print("=" * 70 + "\n")



def handle_audit(args):
    import os
    audit_file = "VARUNA_SCIENTIFIC_VALIDATION_REPORT.md"
    if os.path.exists(audit_file):
        with open(audit_file, "r") as f:
            print(f.read())
    else:
        print("[Audit report not found in current directory. Run from project root.]")

def main():
    parser = setup_cli()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "blend":
        handle_blend(args)
    elif args.command == "weight-map":
        handle_weight_map(args)
    elif args.command == "benchmark":
        handle_benchmark(args)
    elif args.command == "chaos":
        handle_chaos(args)
    elif args.command == "audit":
        handle_audit(args)

if __name__ == "__main__":
    main()
