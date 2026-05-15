# 公共交通空白地域分析（100mメッシュ版）— Claude Code 向けプロジェクト仕様

## 概要

「車がないと生活できない地域（公共交通空白地域）」を全国**100mメッシュ**（統計メッシュ方式）で可視化し、該当人口を定量化する。
250mメッシュ版（`09_transit-desert-analysis/`）の高分解能版。道路ネットワークは共通。

### 国土交通省による定義

出典: **国土数値情報とQGISを活用した交通空白地の抽出と人口分析**（国土交通省 政策統括官付 地理空間情報課、2025年4月）
URL: https://nlftp.mlit.go.jp/ksj/manual/QGIS_manual_01.htm

参考: **「交通空白」解消に関する取組**（国土交通省）
URL: https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_tk_000237.html

```
公共交通便利地域: 最寄り鉄道駅 1,000m以内
公共交通不便地域: 最寄り鉄道駅 1,000m超・最寄りバス停 500m以内
公共交通空白地域: 最寄り鉄道駅 1,000m超 AND 最寄りバス停 500m超  ← 車がないと生活できない地域
```

距離は**道路ネットワーク上の徒歩距離**（walk 3.6 km/h、Multi-source Dijkstra）。

### 公式定義との相違点・優位点

| 項目 | 国交省公式手順 | 本分析 |
|---|---|---|
| 距離計算 | 直線距離（ユークリッド） | **道路ネットワーク距離（Dijkstra）** |
| 駅データ | N02（全駅） | **S12（全駅・乗降客数情報付き）** |
| バス停データ | N07 | **P11（都道府県別最新）** |
| メッシュ分解能 | 250mまたは500m | **100m（統計メッシュ方式）** |

**優位点**:
- 川・山で隔てられた「直線は近いが実際には遠い」エリアを正確に捕捉
- S12を使用することで駅名・運営者・乗降客数などの属性情報を保持できる
- 全処理スクリプト化で再現・更新が容易
- **250m版より約6.25倍の高い空間分解能**（100m × 100m）で精密な空間分布を把握可能

## 100mメッシュ仕様

### メッシュ体系

100mメッシュは**統計メッシュ方式**（L3 1kmメッシュを緯度10分割×経度10分割）であり、JIS標準の2進分割メッシュ（L5=250m, L6=125m）とは**別体系**。

| 項目 | 値 |
|---|---|
| メッシュサイズ | 約100m × 100m（緯度方向 ≈92.5m, 経度方向 ≈113m @35°N） |
| コード桁数 | 10桁（例: `5238432913`） |
| コード形式 | `ppuuqrstxy` （pp=lat×1.5, uu=lon-100, q=L2行0-7, r=L2列0-7, s=L3行0-9, t=L3列0-9, x=100m行0-9, y=100m列0-9） |
| 全国メッシュ数 | 約3,700万件（250m版の約6.25倍） |

### 250m版との差異

| 項目 | 250m版 | 100m版（本ディレクトリ） |
|---|---|---|
| アクセスリンク | `アクセスリンク_L5.parquet`（594万件） | `アクセスリンク_census.parquet`（約3,700万件） |
| 生成方法 | `--level 5` 列挙 | `--census-parquet` parquet読み込み |
| ポリゴン生成 | JIS L5コードから算出 | 統計メッシュコードから算出 |
| 人口データ | `mesh250_pop_*.parquet`（e-Stat） | `mesh100m_pop_*.parquet`（GTFS-GIS等） |
| 処理時間目安 | 約40分 | 約3〜6時間 |

### 必要なデータ

#### 100mメッシュアクセスリンク生成（`--census-parquet` モード）
`make_access_links.py` に `--census-parquet` オプションを追加済み。SHPファイル不要で、人口parquetの `MESH_CODE` 列からメッシュ重心を算出してスナップする。

```bash
cd 01_MakeNetwork
python3 make_access_links.py --nationwide \
  --census-parquet ../09_transit-desert-analysis-100m/input/100m_mesh_pop2020.parquet \
  --case nationwide_walk
```

- `MESH_CODE` 10桁コードから重心を逆算（geometry列不要）
- 出力: `01_MakeNetwork/nationwide_walk/KSJ_N13-24_nationwide_walk_アクセスリンク_census.parquet`

#### 簡易100mメッシュ人口（集計用）
- `input/mesh100m_pop_*.parquet` として配置
- 列名: `MESH_CODE`（10桁）, `PopT`（総人口）, `Pop65over`（65歳以上） ← 自動変換

### 分析結果（令和2年国勢調査・2026年5月実行）

アクセスリンク: 4,976,340件（100mメッシュ）/ 9,952,680件（双方向）
人口あり: 4,609,003メッシュ / 全4,976,340メッシュ

| カテゴリ | 人口 | 割合 |
|---|---|---|
| 公共交通便利地域 | 5,397万人 | 42.7% |
| 公共交通不便地域 | 5,438万人 | 43.0% |
| **公共交通空白地域** | **1,803万人** | **14.3%** |

65歳以上では **570万人**（65歳以上人口の約16.3%）が空白地域に居住。

**250mメッシュ版との比較:**

| 項目 | 250m版 | 100m版 | 差分 |
|---|---|---|---|
| 公共交通便利地域 | 5,389万人（42.8%） | 5,397万人（42.7%） | +8万人 |
| 公共交通不便地域 | 5,358万人（42.5%） | 5,438万人（43.0%） | +80万人 |
| **公共交通空白地域** | **1,847万人（14.7%）** | **1,803万人（14.3%）** | **▲44万人** |
| 65歳以上空白地域 | 592万人 | 570万人 | ▲22万人 |

100m版で空白地域がわずかに少ない理由: 250mメッシュでは「ぎりぎり届かない」と判定された境界付近のメッシュが、100mの細粒度ではより正確に「届く」と分類されるため。

## ディレクトリ構成

```
09_transit-desert-analysis-100m/
├── CLAUDE.md
├── run_analysis.sh                # 全処理一括実行スクリプト（100mメッシュ版）
├── requirements.txt               # Python依存パッケージ
├── scripts/
│   ├── 01_prepare_facilities.py   # S12/P11 → stations/busstops.parquet（名称列付き）
│   ├── 02_calc_transit_desert.py  # Multi-source Dijkstra → transit_desert.parquet（100mメッシュ版）
│   ├── 03_aggregate.py            # 人口結合・pop_total>0フィルタ → transit_desert_with_pop.parquet
│   ├── 04_pref_ranking.py         # 都道府県別空白率ランキング・可視化
│   └── 05_export_geojson.py       # GeoJSON出力 + tippecanoe PMTiles変換
├── data/
│   ├── stations.parquet           # 生成済み鉄道駅ポイント（S12ホーム線形の重心1点）
│   └── busstops.parquet           # 生成済みバス停ポイント（242,985件）
├── input/
│   └── 100m_mesh_pop2020.parquet  # 簡易100mメッシュ人口（4,982,301件・令和2年国勢調査）
│                                  # 列: MESH_CODE / PopT / Pop65over 等（Decimal型）
└── output/
    ├── transit_desert.parquet          # 全メッシュ別カテゴリ（未実行）
    ├── transit_desert.qml              # QGISスタイル（3カテゴリ）
    ├── transit_desert_with_pop.parquet # 人口ありメッシュのみ（未実行）
    └── summary_national.csv            # 全国集計（未実行）
```

## 国交省公表数値との比較

| 比較項目 | 国交省 QGIS手順（2025年4月） | 本試算 |
|---|---|---|
| **公共交通空白地域 人口** | **約735万人（5.8%）** | **約1,803万人（14.3%）** |
| 距離計算方法 | 直線距離（バッファ） | 道路ネットワーク距離（Dijkstra） |
| 駅データ | N02（2023年） | S12（2024年・ホーム線形重心1点） |
| バス停データ | P11（2022年） | P11（2022年）同一 |
| メッシュ分解能 | 250m | **100m（統計メッシュ方式）** |
| 人口データ | 令和2年国勢調査 | 令和2年国勢調査 同一 |

差異の主因: 道路ネットワーク距離は直線距離の1.2〜1.5倍になることが多い。直線800〜900m圏内の地域でも歩行ネットワーク上は1km超となり「空白地域」に分類されるため、本試算の空白人口が約2.5倍多くなる。

> 出典: 国土数値情報とQGISを活用した交通空白地の抽出と人口分析（国土交通省 政策統括官付 地理空間情報課、2025年4月）

## データダウンロード

### 鉄道駅 S12（駅別乗降客数・推奨）
https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html
→ 展開して `data/S12/` に配置
→ ホーム線形の重心1点をポイント化。S12_061 列に乗降客数（2024年版）を保持

代替: 鉄道 N02（全国版）
https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-v3_1.html

### バス停 P11（バス停留所・推奨）
https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P11.html
→ 都道府県別47ファイルを展開して `data/P11/` に配置

代替: バス停 N07（全国版）
https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N07.html

### 250mメッシュ人口（令和2年国勢調査）
https://www.e-stat.go.jp/gis/statmap-search?page=1&type=2&aggregateUnitForBoundary=Q&toukeiCode=00200521
→ KEY_CODE / 人口（総数）/ ６５歳以上人口　総数 の列を含む parquet を `input/mesh250_pop_00.parquet` として配置
→ 列名は `03_aggregate.py` が自動変換するので変更不要

## 実行手順

```bash
cd 09_transit-desert-analysis

# Step 1: 施設データ準備（S12/P11 配置後）
python3 scripts/01_prepare_facilities.py

# Step 2〜4: 全処理一括（約40分）
bash run_analysis.sh

# Step 5: 人口集計（mesh250_pop_00.parquet 配置後）
python3 scripts/03_aggregate.py

# Step 6: チャート生成
python3 scripts/04_pref_ranking.py

# Step 7: PMTiles生成
python3 scripts/05_export_geojson.py
bash output/make_pmtiles.sh
```

## 施設データカラム仕様

### stations.parquet（9,954件）

S12ホーム線形の重心1点をポイントとして使用。

| カラム | 元列 | 内容 |
|---|---|---|
| `geometry` | — | ポイント（EPSG:4326） |
| `station_name` | S12_001 | 駅名 |
| `operator` | S12_002 | 運営者名 |
| `line_name` | S12_003 | 路線名 |

### busstops.parquet（242,985件）

| カラム | 元列 | 内容 |
|---|---|---|
| `geometry` | — | ポイント（EPSG:4326） |
| `stop_name` | P11_001 | バス停名 |
| `operator` | P11_002 | バス会社名 |

## 道路ネットワーク仕様

### nationwide_walk（本分析で使用）

| 項目 | 値 |
|---|---|
| 対象道路 | 全道路（フィルターなし） |
| 移動速度 | walk 3.6 km/h |
| 道路リンク数 | 24,045,959件 |
| 道路ノード数 | 18,614,424件 |
| L5（250m）アクセスリンク数 | 5,935,127件 |

全道路対象が必要な理由: 徒歩圏500m/1,000m判定には生活道路・細街路を含む全リンクが必要。フィルター済みネットワークでは歩道・路地が欠落し、空白地域が過大評価される。

### ネットワーク生成コマンド

```bash
cd 01_MakeNetwork
python3 ksj_to_network_csv.py --nationwide --mode walk --case nationwide_walk
python3 make_access_links.py  --nationwide --level 5  --case nationwide_walk
```

出力先: `01_MakeNetwork/nationwide_walk/`

## 判定カテゴリ

| カテゴリ | 条件 | 色 |
|---|---|---|
| 0_公共交通便利地域 | 鉄道駅 ≤ 16.7分（1km相当） | 緑 |
| 1_公共交通不便地域 | 鉄道駅 > 16.7分・バス停 ≤ 8.3分（500m相当） | 黄 |
| 2_公共交通空白地域 | 鉄道駅 > 16.7分 AND バス停 > 8.3分 | 赤 |

## 距離計算の方法

Multi-source Dijkstra（scipy.sparse.csgraph.dijkstra）を使用した道路ネットワーク距離。

- 駅: S12ホーム線形の重心1点 → NE/NW/SE/SW 4象限の最近傍ノードにスナップ（最大500m）
  - 1重心あたり最大4ノード/駅（重複除去後）
- バス停: KDTree で最近傍1道路ノードにスナップ
- スーパーソースノード方式で全始点を1回のDijkstraで処理
- アクセスリンク経由でノード距離→メッシュ距離に変換
- 閾値: バス停 8.33分（500m）・鉄道駅 16.67分（1,000m）
- `--station-max-dist`（m）で象限探索の最大距離を変更可能（デフォルト500m）

## PMTiles・ウェブビューワー

**PMTiles S3配置先**:
```
https://pmtiles-data.s3.ap-northeast-1.amazonaws.com/mlit/ksj/transit_desert.pmtiles
```

**ビューワー**: `docs/index.html`
- MapLibre GL JS v4 + PMTiles v3
- 背景地図: 国土地理院ベクトルタイル淡色（`docs/pale.json`）
- 住所検索: Nominatim API → flyTo → queryRenderedFeatures
- スマホ対応: `@media (max-width: 600px)` ボトムシート型

## 出力ファイル用途

| ファイル | QGIS | ウェブ | 集計 |
|---|---|---|---|
| `transit_desert_with_pop.parquet` + `.qml` | **推奨**（45MB・名称付き） | — | — |
| `transit_desert.parquet` + `.qml` | 全件（184MB） | — | — |
| `transit_desert.pmtiles` | — | S3配置済み | — |
| `summary_national.csv` | — | — | ✓ |
| `pref_ranking.png` / `urban_rural_compare.png` | — | — | ✓ |

## 注意事項

- `make_access_links.py` の `--nationwide` は従来 L3 専用だったが、L5（250m）対応に修正済み
  （line 137-139 の level強制上書きを削除）
- L5（250m）アクセスリンクは約594万件で処理に約8分かかる
- `02_calc_transit_desert.py` の Dijkstra 処理は全国で約6分（駅140秒 + バス停18秒）
- 250mメッシュ人口データは `*`（秘匿値）を含む列がある → `03_aggregate.py` で 0 扱い
- `transit_desert_with_pop.parquet` は `pop_total > 0` のみ（1,155,496件・45MB）。全5.9Mメッシュは `transit_desert.parquet`
- P11 SHPファイルは SJIS エンコードを含むが pyogrio が自動処理（警告は無視可）

## 今後の拡張案

- バス運行本数によるフィルタリング（本数ゼロまたは少ない停留所を除外）
- 鉄道の運行本数データ活用（https://gtfs-gis.jp/railway_honsu/）
- GTFS/GTFSリアルタイムデータとの統合
- 経年変化分析（廃線・廃止バス路線の影響）

## 測量成果使用承認

数値地図（国土基本情報）電子国土基本図（地図情報）使用

測量法に基づく国土地理院長承認（使用）R 8JHs 85
