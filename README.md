 Extreme Market Intelligence - Sovereign Edition

金融市場のデータをリアルタイムで取得し、テクニカル分析、未来予測、戦略バックテストを行うための強力なStreamlitダッシュボード

## 機能
- **Dashboard**: 主要銘柄（原油、金、指数、為替）のリアルタイム価格とトレンド表示。
- **Intelligence**: yfinance API経由の最新ニュースフィード。
- **Seasonality**: 過去20年のデータに基づいた月別騰落率の分析。
- **Forecast**: 統計的線形回帰とボラティリティに基づいた10日間トレンド予測。
- **Backtest**: 移動平均交差（MA Crossover）戦略のシミュレーションと市場比較。
- 
GitHubへのアップロード手順（コマンドライン）
1. GitHubで新しいレポジトリ（例：`extreme-market-intelligence`）を作成します。
2. ローカル PC のターミナルで以下を実行します：

```bash
git init
git add .
git commit -m "Initial commit: Extreme Market Intelligence App"
git branch -M main
git remote add origin https://github.com/あなたのユーザー名/extreme-market-intelligence.git
git push -u origin main
