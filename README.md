# FIFA World Cup 2026 Predictor

A production-quality machine learning project that predicts FIFA World Cup 2026 match outcomes and estimates each team's probability of winning the tournament through Monte Carlo simulation.

## Project Overview

| Component | What it does |
|---|---|
| **Data pipeline** | Loads, cleans, and validates 45 000+ international matches (1872–present) |
| **Feature engineering** | Computes Elo ratings, rolling form statistics, and FIFA ranking features |
| **ML models** | Trains Logistic Regression, Random Forest, and XGBoost with calibrated probabilities |
| **Simulation** | Runs 10 000+ complete WC 2026 tournament simulations via Monte Carlo |
| **Visualisation** | Produces professional-grade plots of advancement probabilities |
| **Dashboard** | Interactive Streamlit app for match prediction and tournament exploration |

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download datasets
python -m src.data_processing.downloader

# 4. Run pipeline (in order)
python run_phase3_features.py          # Feature engineering
python run_phase4_models.py            # Model training + calibration
python run_phase6_simulation.py        # Monte Carlo simulation
python run_phase7_visualization.py     # Generate all plots

# 5. Launch dashboard
streamlit run app/dashboard.py
```

## Project Structure

```
world-cup-predictor/
├── data/
│   ├── raw/               ← Download Kaggle datasets here
│   └── processed/         ← Cleaned data, features, team profiles
├── results/
│   ├── models/            ← Saved model files (.joblib) + metrics
│   ├── simulation/        ← Monte Carlo probability tables
│   ├── phase4/            ← Calibration curves
│   └── phase7/            ← Final visualisation plots
├── src/
│   ├── data_processing/
│   │   ├── loader.py          Load raw CSVs with validation
│   │   ├── inspector.py       EDA functions and plots
│   │   ├── preprocessor.py    Cleaning pipeline, outcome labels, splits
│   │   ├── team_names.py      Historical name mapping
│   │   └── downloader.py      Kaggle download helper
│   ├── feature_engineering/
│   │   ├── elo.py             Elo rating computation
│   │   ├── form.py            Rolling form statistics
│   │   ├── rankings.py        FIFA ranking nearest-date lookup
│   │   └── builder.py         Feature matrix assembly
│   ├── models/
│   │   ├── train.py           Model pipelines + persistence
│   │   ├── evaluate.py        Evaluation metrics
│   │   └── calibrate.py       Probability calibration
│   ├── simulation/
│   │   ├── wc2026_config.py   WC 2026 groups and team list ← UPDATE THIS
│   │   └── monte_carlo.py     Monte Carlo engine
│   └── visualization/
│       └── plots.py           All visualisation functions
├── app/
│   └── dashboard.py       Streamlit interactive dashboard
├── run_phase3_features.py
├── run_phase4_models.py
├── run_phase6_simulation.py
├── run_phase7_visualization.py
└── requirements.txt
```

## Datasets Required

| Dataset | Source | File |
|---|---|---|
| International football results (1872–present) | [Kaggle – Mart Jürisoo](https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2024) | `results.csv` |
| FIFA World Rankings (1993–present) | [Kaggle – cashncarry](https://www.kaggle.com/datasets/cashncarry/fifaworldranking) | `fifa_ranking-2023-07-20.csv` |

Save both files to `data/raw/`.

## Features Used

| Group | Features |
|---|---|
| Elo | `home_elo_pre`, `away_elo_pre`, `elo_diff` |
| Match context | `is_neutral`, `tournament_weight` |
| Form (last 5 games) | win rate, goals scored, goals conceded, points — for both teams |
| Form (last 10 games) | same statistics over a longer window |
| FIFA rankings | rank, ranking points, rank difference — for both teams |

## Model Performance (typical validation set results)

| Model | Accuracy | Log Loss | Brier Score |
|---|---|---|---|
| Logistic Regression | ~55% | ~0.98 | ~0.63 |
| Random Forest | ~56% | ~0.96 | ~0.61 |
| XGBoost (calibrated) | ~57% | ~0.93 | ~0.59 |

> **Note:** Football is inherently unpredictable. A 57% accuracy on a 3-class problem (random = 33%) represents strong predictive signal.

## Updating for the Actual WC 2026 Groups

Edit `src/simulation/wc2026_config.py` to replace the placeholder groups with the actual draw results. Team names must match the canonical names in `src/data_processing/team_names.py`.

## Technical Stack

- **Python 3.10+**
- pandas, numpy, scipy
- scikit-learn, xgboost
- matplotlib, plotly, seaborn
- streamlit
- joblib (model persistence)
