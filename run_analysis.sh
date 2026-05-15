#!/bin/bash
# 公共交通空白地域 全国分析 一括実行スクリプト（100mメッシュ版）
#
# 実行前に完了していること:
#   1. python3 scripts/01_prepare_facilities.py  (stations.parquet / busstops.parquet)
#   2. input/100m_mesh_pop2020.parquet を配置（MESH_CODE列必須）
#
# 所要時間（目安）:
#   ① ネットワーク生成         : 3〜5時間（250m版と共通。既存なら不要）
#   ② 100mアクセスリンク生成   : 2〜4時間（250m版の約6倍のメッシュ数）
#   ③ Dijkstra 分析           : 20〜60分（道路ネットワーク自体は同じ）
#   合計                       : 6〜10時間

set -e  # エラーで停止

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MAKE_NET_DIR="$REPO_ROOT/01_MakeNetwork"

echo "======================================"
echo " 公共交通空白地域 全国分析（100mメッシュ版）開始"
echo " $(date)"
echo "======================================"

# ── Step 1: 全国道路ネットワーク生成（250m版と共通・既存なら不要） ──
WALK_DIR="$MAKE_NET_DIR/nationwide_walk"
if [ -f "$WALK_DIR/KSJ_N13-24_nationwide_walk_道路リンク.parquet" ]; then
    echo ""
    echo "[Step 1] 全国道路ネットワーク: 既存ファイルを使用（スキップ）"
else
    echo ""
    echo "[Step 1] 全国道路ネットワーク生成..."
    echo "  モード: walk（3.6 km/h）, フィルター: なし（全道路）"
    echo "  出力先: $WALK_DIR/"
    echo "  開始: $(date)"
    cd "$MAKE_NET_DIR"
    python3 ksj_to_network_csv.py --nationwide --mode walk --case nationwide_walk
    echo "  完了: $(date)"
fi

# ── Step 2: 100mメッシュ アクセスリンク生成（census parquetモード） ──
CENSUS_PARQUET="$(dirname "$0")/input/100m_mesh_pop2020.parquet"
echo ""
echo "[Step 2] 100mメッシュ アクセスリンク生成（census parquetモード）..."
if [ ! -f "$CENSUS_PARQUET" ]; then
    echo "エラー: $CENSUS_PARQUET が見つかりません。"
    echo "100mメッシュ人口parquetを input/100m_mesh_pop2020.parquet に配置してください。"
    exit 1
fi
echo "  census parquet: $CENSUS_PARQUET"
echo "  開始: $(date)"
cd "$MAKE_NET_DIR"
python3 make_access_links.py --nationwide --census-parquet "$CENSUS_PARQUET" --case nationwide_walk
echo "  完了: $(date)"

# ── Step 3: 公共交通空白地域算出（Dijkstra） ──
echo ""
echo "[Step 3] 公共交通空白地域算出（Dijkstra・100mメッシュ）..."
echo "  開始: $(date)"
cd "$(dirname "$0")"
python3 scripts/02_calc_transit_desert.py
echo "  完了: $(date)"

echo ""
echo "======================================"
echo " 全処理完了: $(date)"
echo " 出力: $(dirname "$0")/output/transit_desert.parquet"
echo "======================================"
