"""Fixed-configuration comparison on common timestamps; outputs stay under data/.

Run: .venv/Scripts/python scripts/run_model_audit.py
No hyperparameter selection on test. This is exploratory reuse of historical data.
"""
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
import importlib.metadata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from src.model_features import TARGET, clean_inputs, fit_schema, process_features, dust_history, chronological_blocks
from src.time_analysis import coverage, rapping_features

OUT = ROOT / 'data/processed/audit_v3'
PARAMS = dict(n_estimators=200, max_depth=4, learning_rate=.05, subsample=.8,
              colsample_bytree=.8, objective='reg:squarederror', random_state=42,
              n_jobs=4, tree_method='hist')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def metrics(y, pred):
    error = np.asarray(pred) - np.asarray(y)
    if not len(error):
        return dict(n=0, MAE=None, RMSE=None, bias=None, R2=None)
    den = np.sum((y - np.mean(y)) ** 2)
    return dict(n=len(error), MAE=float(np.abs(error).mean()),
                RMSE=float(np.sqrt((error**2).mean())), bias=float(error.mean()),
                R2=float(1 - np.sum(error**2) / den) if den else None)


def daily_bootstrap(predictions, count=1000):
    """Paired resampling of observed calendar days, preserving rows within days."""
    days = predictions.index.normalize()
    names = ['persistence', 'process', 'process_history']
    sums = pd.DataFrame({name: (predictions[name] - predictions.y_true).abs()
                         for name in names}).groupby(days).sum()
    sizes = predictions.groupby(days).size().to_numpy()
    if len(sizes) < 2:
        return {'status': 'insufficient_days'}
    draws = np.random.default_rng(42).integers(0, len(sizes), (count, len(sizes)))
    means = sums.to_numpy()[draws].sum(axis=1) / sizes[draws].sum(axis=1)[:, None]
    result = {'days': len(sizes), 'replicates': count,
              'method': 'paired day-block bootstrap; descriptive, few days and partial days'}
    for i, name in enumerate(names):
        result[name + '_MAE_95pct'] = np.quantile(means[:, i], [.025, .975]).tolist()
    for i in (1, 2):
        result[names[i] + '_minus_persistence_MAE_95pct'] = np.quantile(means[:, i] - means[:, 0], [.025,.975]).tolist()
    return result


def main():
    OUT.mkdir(exist_ok=True)
    inputs = [ROOT / 'data/processed/dataset_clean.parquet', ROOT / 'data/processed/tag_classification_v1.xlsx']
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    raw = pd.read_parquet(inputs[0])
    classification = pd.read_excel(inputs[1])
    if classification.tag.duplicated().any():
        raise ValueError('Duplicate tag definitions')
    cols = classification.loc[classification.role.eq('input'), 'tag'].tolist()
    df = clean_inputs(raw, cols)
    blocks = chronological_blocks(df.index)
    history = dust_history(df)
    rap = rapping_features(df['008B05154'])
    common_history = history.notna().all(axis=1)
    report = dict(status='running', contract='online nowcasting y(t); process x(t) available, dust through t-10 s',
                  historical_test_reused=True, parameters=PARAMS, input_hashes=before,
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'src/model_features.py', ROOT / 'src/time_analysis.py']},
                  versions={m: importlib.metadata.version(m) for m in ['numpy','pandas','xgboost','scikit-learn','pyarrow']},
                  raw_rows=len(raw), clean_rows=len(df), dropped_rows=len(raw)-len(df),
                  input_count=len(cols), coverage=coverage(df), splits=[])
    # Written before any fit: immutable choice for this run, not selected from scores.
    (OUT / 'design.json').write_text(json.dumps(dict(parameters=PARAMS, blocks=blocks, input_hashes=before), indent=2, default=str), encoding='utf-8')
    all_metrics = []
    for label, cutoff, end in blocks:
        print(f'{label}: building features', flush=True)
        start = time.monotonic()
        schema = fit_schema(df.loc[df.index < cutoff], cols)
        # Use only data needed by this fold, including observed pre-fold history.
        subset = df if end is None else df.loc[df.index < end]
        X = process_features(subset, schema)
        valid = X.notna().all(axis=1) & common_history.reindex(X.index)
        train = X.index[valid & (X.index < cutoff)]
        test = X.index[valid & (X.index >= cutoff)]
        if not len(train) or not len(test):
            raise ValueError('Empty fold after required history')
        pred = pd.DataFrame({'y_true': df.loc[test,TARGET], 'persistence': history.loc[test,'dust_lag_1']}, index=test)
        split = dict(name=label, cutoff=str(cutoff), end_exclusive=str(end),
                     train_rows=len(train), evaluation_rows=len(test),
                     evaluation_rows_before_history=int((subset.index >= cutoff).sum()),
                     train_last=str(train[-1]), evaluation_first=str(test[0]), evaluation_last=str(test[-1]),
                     process_features=X.shape[1], history_features=history.shape[1], schema=schema)
        for name in ['process', 'process_history']:
            print(f'{label}: fitting {name} ({len(train)} train / {len(test)} evaluation)', flush=True)
            features = X if name == 'process' else pd.concat([X, history.reindex(X.index)], axis=1)
            model = XGBRegressor(**PARAMS)
            model.fit(features.loc[train], df.loc[train,TARGET])
            pred[name] = model.predict(features.loc[test])
            if label == 'test':
                model.save_model(OUT / f'{name}.ubj')
                pd.DataFrame({'feature': features.columns, 'importance': model.feature_importances_}).sort_values('importance',ascending=False).to_csv(OUT / f'{name}_importance.csv',index=False)
            del features, model
            gc.collect()
        for name in ['persistence', 'process', 'process_history']:
            all_metrics.append(dict(split=label, model=name, **metrics(pred.y_true.to_numpy(), pred[name].to_numpy())))
        pred.to_parquet(OUT / f'{label}_predictions.parquet')
        split['seconds'] = time.monotonic() - start
        report['splits'].append(split)
        pd.DataFrame(all_metrics).to_csv(OUT / 'metrics.csv', index=False)
        (OUT / 'report.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
        if label == 'test':
            report['bootstrap'] = daily_bootstrap(pred)
            groups = {'all': np.ones(len(test), dtype=bool),
                      'rapping_0_5min': rap.loc[test].iloc[:,-1].eq(1).to_numpy(),
                      'outside_rapping': rap.loc[test].iloc[:,-1].eq(0).to_numpy(),
                      'unknown_rapping': rap.loc[test].iloc[:,-1].isna().to_numpy()}
            for low, high in [(-np.inf,10),(10,20),(20,40),(40,np.inf)]:
                groups[f'dust_{low}_{high}'] = (pred.y_true.gt(low) & pred.y_true.le(high)).to_numpy()
            for day in pred.index.normalize().unique():
                groups[f'day_{day.date()}'] = pred.index.normalize() == day
            # Load cutoffs learned from training period only.
            load = df['016A00219'] + df['016A00396']
            edges = load.loc[train].quantile([.25,.5,.75]).tolist()
            report['load_quartile_edges_train'] = edges
            binned = pd.cut(load.loc[test], bins=[-np.inf]+sorted(set(edges))+[np.inf])
            for interval in binned.cat.categories:
                groups[f'load_{interval}'] = binned.eq(interval).to_numpy()
            rows = []
            for group, mask in groups.items():
                for name in ['persistence', 'process', 'process_history']:
                    rows.append(dict(group=group, model=name, **metrics(pred.y_true.to_numpy()[mask], pred[name].to_numpy()[mask])))
            pd.DataFrame(rows).to_csv(OUT / 'stratified_metrics.csv', index=False)
            # Versioned matrices for follow-up work; never replace v1.
            X.loc[valid].to_parquet(OUT / 'X_process.parquet')
            history.loc[X.index[valid]].to_parquet(OUT / 'X_dust_history.parquet')
            df.loc[X.index[valid],[TARGET]].to_parquet(OUT / 'y.parquet')
        del X
        gc.collect()
    report['metrics'] = all_metrics
    report['inputs_unchanged'] = before == {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    if not report['inputs_unchanged']:
        raise RuntimeError('Input integrity check failed')
    report['status'] = 'complete'
    (OUT / 'report.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print(pd.DataFrame(all_metrics).to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
