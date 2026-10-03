#!/usr/bin/env python3
"""
ClinX Clinical Benchmark Runner
================================
Runs the 50-variant benchmark through ClinX Clinical API.
Generates results for IEEE paper (Tables V-VIII, Figures 4-7).

Usage:
    python run_benchmark.py --url http://localhost:8000 --output benchmark_results
"""

import asyncio
import argparse
import sys
import os

# Add the benchmark module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_runner import run_benchmark, BENCHMARK_VARIANTS


def main():
    parser = argparse.ArgumentParser(
        description="ClinX Clinical Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_benchmark.py                           # Default localhost:8000
  python run_benchmark.py --url http://host:8000   # Custom URL
  python run_benchmark.py --output my_results      # Custom output dir
  python run_benchmark.py --list-variants          # Show benchmark variants
        """
    )
    parser.add_argument(
        '--url', 
        default='http://localhost:8000',
        help='ClinX Clinical API base URL (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--output', '-o',
        default='benchmark_results',
        help='Output directory for results (default: benchmark_results)'
    )
    parser.add_argument(
        '--list-variants',
        action='store_true',
        help='List all benchmark variants and exit'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick test with first 5 variants only'
    )
    
    args = parser.parse_args()
    
    if args.list_variants:
        print("🧬 ClinX Clinical Benchmark Variants (50 total)")
        print("=" * 80)
        for i, v in enumerate(BENCHMARK_VARIANTS):
            alt_str = v['alt'] if v['alt'] else 'del'
            print(f"{i+1:2d}. {v['gene']}: chr{v['chr']}:{v['pos']} {v['ref']}>{alt_str} "
                  f"[{v['clinvar_class']}]")
        return
    
    if args.quick:
        import benchmark_runner
        benchmark_runner.BENCHMARK_VARIANTS = BENCHMARK_VARIANTS[:5]
        print(f"⚡ Quick mode: testing {len(benchmark_runner.BENCHMARK_VARIANTS)} variants")
    
    print(f"🚀 Starting ClinX Clinical Benchmark")
    print(f"   API: {args.url}")
    print(f"   Output: {args.output}")
    print(f"   Variants: {len(BENCHMARK_VARIANTS)}")
    print()
    
    try:
        asyncio.run(run_benchmark(
            base_url=args.url,
            output_dir=args.output
        ))
        print("\n✅ Benchmark completed successfully!")
        print(f"📁 Results saved to: {args.output}/")
    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()