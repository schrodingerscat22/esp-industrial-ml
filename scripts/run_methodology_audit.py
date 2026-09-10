"""Recalculate audited cells locally without publishing industrial notebook outputs.

Run from repository root: .venv/Scripts/python scripts/run_methodology_audit.py
Only audit_v2 is written. Models using legacy 02/03 features are intentionally skipped.
"""
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ['MPLBACKEND'] = 'Agg'
os.environ['MPLCONFIGDIR'] = str(ROOT / 'data/processed/audit_v2/matplotlib')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.time_analysis import coverage

OUT = ROOT / 'data/processed/audit_v2'
OUT.mkdir(exist_ok=True)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def execute(prefix, original_cells=None):
    path = next((ROOT / 'notebooks').glob(prefix + '_*.ipynb'))
    nb = json.loads(path.read_text(encoding='utf-8'))
    env = {'display': lambda *args, **kwargs: None, '__name__': '__main__'}
    with (OUT / f'{prefix}_execution.log').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
        for idx, cell in enumerate(nb['cells']):
            if cell['cell_type'] != 'code' or (original_cells is not None and idx - 1 not in original_cells):
                continue
            print(f'CELL {idx} (original {idx-1})', flush=True)
            exec(compile(''.join(cell['source']), f'{path.name}:cell{idx}', 'exec'), env)
            plt.close('all')
    return env


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', nargs='+', choices=['01', '04', '05', '06a', '06b'])
    args = parser.parse_args()
    inputs = sorted(p for p in (ROOT / 'data').rglob('*') if p.is_file() and OUT not in p.parents)
    hashes_before = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    result = {'python': sys.version, 'packages': {}, 'inputs_sha256': hashes_before, 'analyses': {}}
    if args.only and (OUT / 'results.json').exists():
        result['analyses'] = json.loads((OUT / 'results.json').read_text(encoding='utf-8'))['analyses']
    for name in ['numpy','pandas','pyarrow','scipy','matplotlib','scikit-learn','xgboost','nbformat']:
        result['packages'][name] = importlib.metadata.version(name)
    df = pd.read_parquet(ROOT / 'data/processed/df_model_clean_v1.parquet')
    result['data_quality'] = dict(rows=len(df), columns=len(df.columns),
        sorted=bool(df.index.is_monotonic_increasing), unique=bool(df.index.is_unique),
        missing_cells=int(df.isna().sum().sum()), **coverage(df))
    jobs = [('01', None), ('04', set(range(26)) | {43}), ('05', None), ('06a', None), ('06b', None)]
    for prefix, cells in jobs:
        if args.only and prefix not in args.only:
            continue
        start = time.monotonic()
        print(f'Running {prefix}', flush=True)
        try:
            env = execute(prefix, cells)
            summary = {'status': 'passed', 'seconds': time.monotonic() - start}
            if prefix == '01':
                summary.update(mae=float(env['mae']), r2=float(env['r2']), train_rows=len(env['X_train']), test_rows=len(env['X_test']))
                # Fair comparison: same timestamps/features/model; only leak is restored.
                from xgboost import XGBRegressor
                from sklearn.metrics import mean_absolute_error, r2_score
                X = env['X'].copy()
                X['008A01345_rollmean_5m'] = env['df']['008A01345'].rolling(30).mean().reindex(X.index)
                n = len(env['X_train'])
                model = XGBRegressor(**env['model'].get_params())
                model.fit(X.iloc[:n], env['y_train'])
                pred = model.predict(X.iloc[n:])
                summary['leaky_same_rows'] = dict(mae=float(mean_absolute_error(env['y_test'], pred)), r2=float(r2_score(env['y_test'], pred)))
            elif prefix == '04':
                summary.update(starts=env['rapping_events_summary'][['tag','n_start_events']].to_dict('records'),
                    profile_summary=env['profile_summary'].to_dict('records'))
            elif prefix == '06a':
                for name in ['event_analysis', 'typical_event_analysis', 'lag_results', 'observed_tail_summary', 'power_validation']:
                    env[name].to_csv(OUT / f'{name}.csv', index=False)
                summary.update(rejections=env['event_rejections'], starts=len(env['rapping_starts']),
                    coverage=env['coverage_summary'], best_P=env['best_P'].to_dict(), best_U=env['best_U'].to_dict(),
                    key_summary=env['key_summary'].to_dict(), totals=env['observed_tail_summary'].to_dict('records'))
                sec = env['typical_event_analysis']
                assert np.allclose(sec.tail_energy_sections_sum_kwh, sec.tail_energy_kwh_0_15min, atol=1e-9)
                assert (env['event_analysis'].tail_energy_kwh_0_15min <= env['event_analysis'].extra_energy_kwh_0_15min + 1e-9).all()
                assert env['event_analysis'].power_duration_above_5kw_min.le(15).all()
                assert env['event_analysis'].dust_duration_above_5mg_min.le(15).all()
            result['analyses'][prefix] = summary
        except Exception as exc:
            import traceback
            traceback.print_exc()
            result['analyses'][prefix] = {'status': 'failed', 'error': repr(exc)}
        (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    result['inputs_unchanged'] = hashes_before == {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print('Inputs unchanged:', result['inputs_unchanged'], flush=True)
    if not result['inputs_unchanged'] or any(v['status'] != 'passed' for v in result['analyses'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
