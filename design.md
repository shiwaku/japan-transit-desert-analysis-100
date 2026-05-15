# 公共交通空白地域 全国分析 — 設計書（100mメッシュ版）

## 1. 目的

「車がないと生活できない地域」を全国100mメッシュ（統計メッシュ方式）で可視化し、地方在住者や交通政策立案者が課題の規模を客観的に把握できるデータを提供する。

帰省するたびに感じる「免許がないと何もできない」という実感を、全国規模で定量化・可視化することを目指す。250mメッシュ版（`09_transit-desert-analysis/`）の高分解能版。

## 2. 分析定義

### 国土交通省による公式定義

> 出典: [国土数値情報とQGISを活用した交通空白地の抽出と人口分析](https://nlftp.mlit.go.jp/ksj/manual/QGIS_manual_01.htm)（国土交通省 政策統括官付 地理空間情報課、2025年4月）
>
> 参考: [「交通空白」解消に関する取組](https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_tk_000237.html)（国土交通省）

| カテゴリ | 条件 | 意味 |
|---|---|---|
| **0_公共交通便利地域** | 最寄り鉄道駅まで道路距離 ≤ 1,000m | 電車が使いやすい |
| **1_公共交通不便地域** | 鉄道駅 > 1,000m かつ バス停 ≤ 500m | バス依存 |
| **2_公共交通空白地域** | 鉄道駅 > 1,000m AND バス停 > 500m | 車なしでは生活困難 |

距離は**道路ネットワーク上の徒歩距離**（walk 3.6 km/h）。分単位に換算して閾値判定する。

```
BUS_MIN     = 500m  / 60m/分 = 8.33分
STATION_MIN = 1000m / 60m/分 = 16.67分
```

### 公式定義との相違点・優位点

| 項目 | 国交省公式手順 | 本分析 |
|---|---|---|
| 距離計算 | 直線距離（ユークリッド） | **道路距離（Dijkstra）** |
| 駅データ | N02（全駅） | **S12（全駅使用・フィルタリングなし）** |
| バス停データ | P11（2022年） | **P11（都道府県別最新）** |
| メッシュ分解能 | 250mメッシュ or 500mメッシュ | **100mメッシュ（統計メッシュ方式）** |

道路距離により川・山で隔てられた「直線は近いが実際には遠い」ケースを正確に捕捉。S12のホーム線形の重心を NE/NW/SE/SW 4象限スナップで道路ノードに紐付ける。

### 参考: 他定義との比較

| 定義 | バス停閾値 | 鉄道駅閾値 | 出典 |
|---|---|---|---|
| 本分析（採用） | 500m | 1,000m | 国交省QGISマニュアル 2025年4月 |
| 地方部（ハンドブック） | 500m | 1,000m | 地域公共交通づくりハンドブック |
| 都市部（ハンドブック） | 300m | 500m | 同上 |
| 補助金要綱 | 1,000m | 1,000m（統合） | 補助金交付要綱 |

## 3. 分析結果（令和2年国勢調査）

実行日: 2026年5月（駅スナップ: 重心1点 → NE/NW/SE/SW 4象限・最大500m・スナップ駅ノード数 66,269）

| カテゴリ | 人口 | 割合 | 65歳以上人口 |
|---|---|---|---|
| 公共交通便利地域 | 5,397万人 | 42.7% | 1,351万人 |
| 公共交通不便地域 | 5,438万人 | 43.0% | 1,596万人 |
| **公共交通空白地域** | **1,803万人** | **14.3%** | **570万人** |
| 合計 | 1億2,638万人 | 100% | 3,517万人 |

※ 人口集計は pop_total > 0 の 4,609,003 メッシュのみ対象（無人エリア除外）。

### 250mメッシュ版との比較

| カテゴリ | 250m版 | 100m版 | 差分 |
|---|---|---|---|
| 公共交通便利地域 | 5,389万人（42.8%） | 5,397万人（42.7%） | +8万人 |
| 公共交通不便地域 | 5,358万人（42.5%） | 5,438万人（43.0%） | +80万人 |
| **公共交通空白地域** | **1,847万人（14.7%）** | **1,803万人（14.3%）** | **▲44万人** |

100m版で空白地域が▲44万人少ない理由: 250mメッシュでは「ぎりぎり届かない」と判定された境界付近のメッシュが、100mの細粒度ではより正確に「届く」と分類されるため。

## 4. データフロー

```
[S12 駅別乗降客数 GeoJSON]   [P11 バス停留所 GeoJSON/SHP]
            ↓                          ↓
     01_prepare_facilities.py
            ↓                          ↓
     stations.parquet            busstops.parquet
     （9,954件・S12ホーム線形の重心1点・名称付き）  （242,985バス停・名称付き）
                     ↓
          02_calc_transit_desert.py
                ↑           ↑
   [全国walk道路リンク]  [100mメッシュアクセスリンク（統計メッシュ）]
   道路リンク: 24,045,959件  498万件（census.parquet）
   道路ノード: 18,614,424件
                     ↓
     transit_desert.parquet（4,976,340メッシュ）
                     ↓
            03_aggregate.py  ← pop_total > 0 でフィルタ
                ↑
   [100m_mesh_pop2020.parquet] ← GTFS-GIS 西沢明氏 簡易100mメッシュ人口（令和2年国勢調査）
                     ↓
     transit_desert_with_pop.parquet（4,609,003メッシュ・166MB）
     summary_national.csv / summary_pref.csv
                     ↓
            04_pref_ranking.py
                     ↓
     pref_ranking.png / urban_rural_compare.png
                     ↓
            05_export_geojson.py
                     ↓
     transit_desert_web.geojson → tippecanoe → transit_desert.pmtiles（203MB）
```

## 5. スクリプト仕様

### 01_prepare_facilities.py

**入力**:
- `data/S12/**/UTF-8/*.geojson`（駅別乗降客数・推奨）
- `data/N02/**/*.geojson`（鉄道・S12がない場合のフォールバック）
- `data/P11/**/*.geojson` or `*.shp`（バス停留所・推奨）
- `data/N07/**/*.geojson`（バス停・P11がない場合のフォールバック）

**処理**（S12の場合）:
- LineString ジオメトリの重心1点をポイント化
- 乗降客数（S12_061 = 2024年列）が `MIN_PASSENGERS_PER_DAY` 未満の駅を除外
- EPSG:4326 に変換・重複除去
- 駅名（S12_001）・運営者（S12_002）・路線名（S12_003）を保存

**処理**（P11の場合）:
- バス停名（P11_001）・バス会社名（P11_002）を保存

**定数**:
```python
MIN_PASSENGERS_PER_DAY = 0     # 0=全駅使用（フィルタなし）
S12_PASSENGER_COL      = "S12_061"  # 2024年
```

**出力**:

`data/stations.parquet`（9,954件）:

| カラム | 内容 |
|---|---|
| `geometry` | ポイント（EPSG:4326） |
| `station_name` | 駅名（S12_001） |
| `operator` | 運営者名（S12_002） |
| `line_name` | 路線名（S12_003） |

`data/busstops.parquet`（242,985件）:

| カラム | 内容 |
|---|---|
| `geometry` | ポイント（EPSG:4326） |
| `stop_name` | バス停名（P11_001） |
| `operator` | バス会社名（P11_002） |

---

### 02_calc_transit_desert.py

**入力**:
- `data/stations.parquet`
- `data/busstops.parquet`
- `../01_MakeNetwork/nationwide_walk/KSJ_N13-24_nationwide_walk_道路リンク.parquet`
- `../01_MakeNetwork/nationwide_walk/KSJ_N13-24_nationwide_walk_道路ノード.parquet`
- `../01_MakeNetwork/nationwide_walk/KSJ_N13-24_nationwide_walk_アクセスリンク_census.parquet`（100mメッシュ版）

**処理**:

1. **グラフ構築** — 道路リンクの `node1/node2/time_001min` から scipy CSR 行列を生成（双方向）
2. **施設スナップ**
   - 駅: S12ホーム線形の重心を NE/NW/SE/SW 4象限の最近傍ノードにスナップ（最大500m・`snap_to_nodes_quadrant`）
   - バス停: 最近傍1ノードにスナップ（`snap_to_nodes`）
3. **Multi-source Dijkstra × 2回**
   - 駅（9,954件）全体を1回で処理 → 全ノードへの最短時間
   - バス停（242,985件）全体を1回で処理 → 全ノードへの最短時間
4. **メッシュ距離変換** — アクセスリンクの `road_node + acc_time` でメッシュ単位の時間を算出
5. **閾値判定** → `category` 列生成
6. **100mメッシュポリゴン生成（統計メッシュ方式）** — `ppuuqrstxy` 形式の10桁コードから SW 座標を復元して `shapely.geometry.box` でポリゴン化

**Multi-source Dijkstra 実装**:

スーパーソースノード（インデックス `nv`）を追加し、全始点へのエッジ重み 0 の辺を張ることで1回の `sp_dijkstra` 呼び出しで全始点同時投入を実現する。

```python
G_ext = vstack([G_pad, extra])  # shape (nv+1, nv+1)
dist  = sp_dijkstra(G_ext, indices=nv)[:nv]
```

**出力**:
- `output/transit_desert.parquet`: 4,976,340メッシュ × カテゴリ・徒歩時間（149MB）
- `output/transit_desert.qml`: QGISスタイル（3色）

**処理時間実測** (WSL2, 64GB RAM):
- ネットワーク読み込み: 65秒
- グラフ構築: 24秒（CSR行列 47,832,858エッジ）
- 駅 Dijkstra: 140秒
- バス停 Dijkstra: 18秒
- メッシュ変換・出力: 約8秒
- **合計: 約334秒（約5.6分）**

---

### 03_aggregate.py

**入力**:
- `output/transit_desert.parquet`
- `input/100m_mesh_pop*.parquet`（GTFS-GIS 西沢明氏 簡易100mメッシュ人口・令和2年国勢調査）

**処理**:
- `mesh_code`（10桁）で left join
- 列名を自動変換（MESH_CODE→mesh_code、PopT→pop_total、Pop65over→pop_65over）
- Decimal型・小数値（按分推計値）を丸めてintに変換
- **`pop_total > 0` のメッシュのみに絞り込み**（無人エリア・海上除外）
- カテゴリ別・1次メッシュ別に人口集計

**出力**:
- `output/transit_desert_with_pop.parquet`: 人口あり4,609,003件のみ（166MB）
- `output/transit_desert_with_pop.qml`: QGISスタイル（categorized）
- `output/summary_national.csv`: 全国集計
- `output/summary_pref.csv`: 1次メッシュ別集計

---

### 04_pref_ranking.py

**入力**: `output/transit_desert_with_pop.parquet`

**処理**: 重心ポイント + `gpd.sjoin` で都道府県に紐付け → 空白率ランキング生成

**出力**:
- `output/pref_ranking.png`: 都道府県別空白率横棒グラフ
- `output/urban_rural_compare.png`: 上位3県・下位3県の3色パイチャート比較
- `output/pref_ranking.csv`: ランキングCSV

---

### 05_export_geojson.py

**入力**: `output/transit_desert_with_pop.parquet`

**処理**: GeoJSON出力 + tippecanoe コマンド生成

**出力**:
- `output/transit_desert_web.geojson`: PMTiles変換用GeoJSON（465MB・中間ファイル）
- `output/make_pmtiles.sh`: tippecanoe実行スクリプト
- `output/transit_desert.pmtiles`: PMTiles（203MB・Z4-Z13）

**PMTiles S3配置先**:
```
https://pmtiles-data.s3.ap-northeast-1.amazonaws.com/mlit/ksj/transit_desert.pmtiles
```

## 6. 出力カラム仕様

### transit_desert.parquet（全件・4,976,340行・149MB）

| カラム | 型 | 内容 |
|---|---|---|
| `mesh_code` | str | 100mメッシュコード（10桁・統計メッシュ方式） |
| `dist_bus_min` | float | 最寄りバス停までの道路徒歩時間（分）|
| `dist_station_min` | float | 最寄り鉄道駅までの道路徒歩時間（分）|
| `far_bus` | bool | バス停 > 8.3分（500m超）|
| `far_station` | bool | 鉄道駅 > 16.7分（1,000m超）|
| `category` | str | 判定カテゴリ（3種）|
| `geometry` | Polygon | 100mメッシュポリゴン（統計メッシュ方式・EPSG:4326）|

### transit_desert_with_pop.parquet（人口あり・4,609,003行・166MB）

上記に加えて:

| カラム | 型 | 内容 |
|---|---|---|
| `pop_total` | int | 総人口（夜間・令和2年）|
| `pop_65over` | int | 65歳以上人口 |

## 7. ネットワーク構築コマンド

```bash
cd 01_MakeNetwork

# Step1: 全国walkネットワーク（全道路・フィルターなし）
python3 ksj_to_network_csv.py --nationwide --mode walk --case nationwide_walk

# Step2: 100mメッシュアクセスリンク（--census-parquetモード）
python3 make_access_links.py --nationwide \
  --census-parquet ../09_transit-desert-analysis-100m/input/100m_mesh_pop2020.parquet \
  --case nationwide_walk
```

出力先: `01_MakeNetwork/nationwide_walk/`
アクセスリンク: `KSJ_N13-24_nationwide_walk_アクセスリンク_census.parquet`（4,976,340件）

## 8. 既知の制約と改善案

| 制約 | 影響 | 改善案 |
|---|---|---|
| バス運行本数考慮なし | 1日1便の停留所も「バスあり」と判定 | GTFSデータや P11 の運行情報を活用 |
| 鉄道廃線・廃止未反映 | 廃止後の駅が残る可能性 | S12 のデータ年度確認・定期更新 |
| バス停廃止未反映 | 廃止バス停が含まれる | P11 のデータ年度確認（2022年版） |
| 一方通行未考慮 | 過少な道路距離が出る可能性 | OSMデータ（onewayタグあり）への切り替え |
| 道路ネットワーク欠損 | ごく一部の孤立エリアで到達不能 | 実用上の影響は軽微 |

## 9. 今後の拡張案（優先度順）

1. **鉄道運行本数フィルタリング**（★★★）
   - データ: https://gtfs-gis.jp/railway_honsu/
   - 効果: 廃線寸前の超閑散路線沿いが「便利地域」になる問題を解消

2. **バス運行本数フィルタリング**（★★☆）
   - データ: 国交省GTFS-JP（各事業者提供）
   - 実装: 平日1日N便以下のバス停を除外

3. **タクシー・ライドシェア到達可能エリアの統合**（★☆☆）
   - 国交省2024年通達: タクシーが30分以内に配車されない地域も空白地域と定義

4. **経年変化分析**
   - S12 の複数年版比較で廃線・廃止路線の影響を可視化

## 10. 参考資料

- [国土数値情報QGISマニュアル（交通空白地）](https://nlftp.mlit.go.jp/ksj/manual/QGIS_manual_01.htm) — 本分析の定義の根拠
- [「交通空白」解消に関する取組](https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_tk_000237.html) — 国交省の政策文脈
- [地域公共交通づくりハンドブック](https://www.mlit.go.jp/common/000036945.pdf) — 都市部・地方部別の閾値設定
- [gtfs-gis.jp 鉄道運行本数データ](https://gtfs-gis.jp/railway_honsu/) — 運行本数付き駅データ（令和4年度版）
- [GTFS-GIS 西沢明氏 簡易100mメッシュ人口データ](https://gtfs-gis.jp/data/100m_pop2020/) — 簡易100mメッシュ人口（令和2年国勢調査）

## 11. 測量成果使用承認

数値地図（国土基本情報）電子国土基本図（地図情報）使用

測量法に基づく国土地理院長承認（使用）R 8JHs 85
