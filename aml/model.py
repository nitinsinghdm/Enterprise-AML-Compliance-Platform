"""Synthetic customer-risk classifier with disjoint customer train/test sets."""
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

FEATURES = ['transaction_count', 'total_amount_eur', 'mean_amount_eur', 'max_amount_eur',
            'cross_border_ratio', 'high_risk_country_ratio', 'near_threshold_cash_count',
            'max_daily_count', 'pep_flag']


def train(features_path, labels_path, output, seed=42):
    frame = pd.read_csv(features_path)
    labels = pd.read_csv(labels_path)
    if frame.customer_id.duplicated().any() or labels.transaction_id.duplicated().any():
        raise ValueError('Duplicate customer features or transaction labels')
    if not set(labels.is_suspicious.unique()) <= {0, 1}:
        raise ValueError('Labels must be binary')
    truth = labels.groupby('customer_id').is_suspicious.max().rename('target')
    frame = frame.merge(truth, on='customer_id', how='inner', validate='one_to_one')
    if len(frame) < 20 or frame.target.value_counts().min() < 4 or frame.target.nunique() != 2:
        raise ValueError('Need >=20 labeled customers with >=4 examples in each class')
    train_idx, test_idx = train_test_split(frame.index, test_size=.25, random_state=seed, stratify=frame.target)
    model = RandomForestClassifier(n_estimators=150, max_depth=6, min_samples_leaf=2,
                                   class_weight='balanced', random_state=seed, n_jobs=1)
    model.fit(frame.loc[train_idx, FEATURES], frame.loc[train_idx, 'target'])
    probability = model.predict_proba(frame.loc[test_idx, FEATURES])[:, 1]
    report = {'seed': seed, 'train_customers': len(train_idx), 'test_customers': len(test_idx),
              'roc_auc': float(roc_auc_score(frame.loc[test_idx, 'target'], probability)),
              'average_precision': float(average_precision_score(frame.loc[test_idx, 'target'], probability)),
              'classification': classification_report(frame.loc[test_idx, 'target'], probability >= .5,
                                                       output_dict=True, zero_division=0),
              'feature_importance': dict(zip(FEATURES, model.feature_importances_.tolist())),
              'sklearn_version': sklearn.__version__,
              'limitations': 'Synthetic scenario discrimination only. Scores are not calibrated real-world AML probabilities. Training customers receive in-sample scores. No production validation.'}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    version = hashlib.sha256(Path(features_path).read_bytes() + Path(labels_path).read_bytes() + str(seed).encode()).hexdigest()[:16]
    report['model_version'] = version
    joblib.dump({'model': model, 'features': FEATURES, 'version': version}, output / 'risk_model.joblib')
    (output / 'metrics.json').write_text(json.dumps(report, indent=2))
    scores = score(frame, model, version)
    scores['evaluation_split'] = ['holdout' if i in test_idx else 'train' for i in frame.index]
    scores.to_csv(output / 'customer_risk_scores.csv', index=False)
    return report


def score(frame, model, version):
    probability = model.predict_proba(frame[FEATURES])[:, 1]
    return pd.DataFrame({'customer_id': frame.customer_id, 'risk_score': (probability*100).round(2),
                         'risk_band': pd.cut(probability, [-.01, .3, .7, 1], labels=['LOW', 'MEDIUM', 'HIGH']),
                         'model_version': version})


def predict(features_path, model_path, output):
    # Only load locally produced trusted joblib files; pickle can execute code.
    artifact = joblib.load(model_path)
    if artifact['features'] != FEATURES:
        raise ValueError('Model feature contract mismatch')
    frame = pd.read_csv(features_path)
    result = score(frame, artifact['model'], artifact['version'])
    result.to_csv(output, index=False)
    return {'scored_customers': len(result)}
