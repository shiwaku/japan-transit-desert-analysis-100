#!/usr/bin/env python3
"""
人口集計スクリプト（100mメッシュ版）

transit_desert.parquet と 100mメッシュ人口を結合し、
移動難民ゾーンの人口を都道府県別・カテゴリ別に集計する。

入力:
  output/transit_desert.parquet           メッシュ別カテゴリ（100mメッシュ）
  input/mesh100m_pop_*.parquet            100mメッシュ人口（都道府県別または全国）

出力:
  output/transit_desert_with_pop.parquet  人口付きメッシュ
  output/summary_pref.csv                 都道府県別集計
  output/summary_national.csv             全国集計

100mメッシュ人口データ（GTFS-GIS 西沢明加工データ）:
  例: https://gtfs-gis.jp/data/100m_pop2020/{pref_code}/100m_mesh_pop2020_{city_code}.zip
  MESH_CODE / PopT / Pop65over 列を含む parquet/SHP を
  input/mesh100m_pop_*.parquet として配置。
  列名は自動変換するので変更不要（PopT → pop_total, Pop65over → pop_65over）。
"""

from pathlib import Path
import os
import pandas as pd
import geopandas as gpd

ROOT    = Path(__file__).parent.parent
OUT_DIR = ROOT / "output"
IN_DIR  = ROOT / "input"


def load_population():
    """100mメッシュ人口 parquet を読み込む。"""
    # 想定パターン: 100m_mesh_pop*.parquet / mesh100m_pop_*.parquet
    # WSL対応: Path.glob()はWindows FSで動作しないためos.listdirを使用
    all_files = os.listdir(IN_DIR)
    files = sorted(
        IN_DIR / f for f in all_files
        if (f.startswith("100m_mesh_pop") or f.startswith("mesh100m_pop"))
        and f.endswith((".parquet", ".csv"))
    )
    if not files:
        raise FileNotFoundError(
            f"100mメッシュ人口ファイルが見つかりません: {IN_DIR}\n"
            "GTFS-GIS 等から100mメッシュ人口データをダウンロードし、\n"
            "100m_mesh_pop*.parquet として input/ に配置してください。\n"
            "列名: MESH_CODE（10桁）/ PopT（総人口）/ Pop65over（65歳以上）"
        )

    dfs = []
    for f in files:
        if f.suffix == ".parquet":
            df = pd.read_parquet(f)
        else:
            df = pd.read_csv(f, dtype=str)
        dfs.append(df)
    pop = pd.concat(dfs, ignore_index=True)

    # 列名を統一
    # 優先順位: 完全一致 > 部分一致（MESH1R_CODE等の誤マッチを防ぐため）
    col_map = {}
    for col in pop.columns:
        cl = col.lower().replace("_", "")
        if cl in ("meshcode", "mesh_code"):
            col_map[col] = "mesh_code"
        elif cl in ("popt", "総人口", "poptotal", "population"):
            col_map[col] = "pop_total"
        elif "65" in col.lower() and ("over" in col.lower() or "以上" in col.lower()):
            col_map[col] = "pop_65over"
    pop = pop.rename(columns=col_map)

    if "mesh_code" not in pop.columns:
        raise ValueError(f"mesh_code 列が見つかりません。列名: {list(pop.columns)}")
    if "pop_total" not in pop.columns:
        raise ValueError(f"pop_total 列が見つかりません。列名: {list(pop.columns)}")

    pop["mesh_code"] = pop["mesh_code"].astype(str).str.zfill(10)
    # Decimal型・小数値（按分推計値）を丸めてintに変換
    pop["pop_total"] = pd.to_numeric(pop["pop_total"], errors="coerce").fillna(0).round().astype(int)
    if "pop_65over" in pop.columns:
        pop["pop_65over"] = pd.to_numeric(pop["pop_65over"], errors="coerce").fillna(0).round().astype(int)

    return pop[["mesh_code"] + [c for c in ["pop_total", "pop_65over"] if c in pop.columns]]


def _write_qml_with_pop(path: Path):
    cats = [
        ("0_公共交通便利地域", "89,203,143,200",  "鉄道駅 walk 1,000m以内"),
        ("1_公共交通不便地域", "255,200,0,200",   "鉄道駅1,000m超・バス停 500m以内"),
        ("2_公共交通空白地域", "220,30,30,200",   "鉄道駅1,000m超 AND バス停500m超"),
    ]
    cat_xml = "\n".join(
        f'      <category symbol="{i}" value="{v}" label="{l}" render="true"/>'
        for i, (v, _, l) in enumerate(cats)
    )
    sym_xml = "\n".join(
        f'      <symbol name="{i}" type="fill" alpha="1" clip_to_extent="1"'
        f' is_animated="0" frame_rate="10">'
        f'<data_defined_properties><Option type="Map">'
        f'<Option name="name" type="QString" value=""/>'
        f'<Option name="properties"/>'
        f'<Option name="type" type="QString" value="collection"/>'
        f'</Option></data_defined_properties>'
        f'<layer class="SimpleFill" enabled="1" pass="0" locked="0">'
        f'<Option type="Map">'
        f'<Option name="color" type="QString" value="{c}"/>'
        f'<Option name="outline_style" type="QString" value="no"/>'
        f'<Option name="style" type="QString" value="solid"/>'
        f'</Option></layer></symbol>'
        for i, (_, c, _) in enumerate(cats)
    )
    content = (
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        '<qgis version="3.34.0" styleCategories="Symbology">\n'
        '  <renderer-v2 type="categorizedSymbol" attr="category"'
        ' forceraster="0" symbollevels="0" usingSymbolLevels="0" enableorderby="0">\n'
        '    <categories>\n' + cat_xml + '\n    </categories>\n'
        '    <symbols>\n' + sym_xml + '\n    </symbols>\n'
        '    <rotation/><sizescale/>\n  </renderer-v2>\n'
        '  <blendMode>0</blendMode><featureBlendMode>0</featureBlendMode>'
        '<layerOpacity>1</layerOpacity>\n</qgis>\n'
    )
    path.write_text(content, encoding="utf-8")


def main():
    print("transit_desert.parquet 読み込み...")
    gdf = gpd.read_parquet(OUT_DIR / "transit_desert.parquet")
    gdf["mesh_code"] = gdf["mesh_code"].astype(str).str.zfill(10)
    print(f"  {len(gdf):,} メッシュ")

    print("100mメッシュ人口読み込み...")
    pop = load_population()
    print(f"  {len(pop):,} メッシュ（人口データ）")

    # 結合
    merged = gdf.merge(pop, on="mesh_code", how="left")
    merged["pop_total"] = merged["pop_total"].fillna(0).astype(int)
    if "pop_65over" in merged.columns:
        merged["pop_65over"] = merged["pop_65over"].fillna(0).astype(int)

    # 人口ありメッシュのみに絞り込む
    merged_pop = merged[merged["pop_total"] > 0].copy()
    print(f"  人口あり: {len(merged_pop):,} メッシュ / 全体: {len(merged):,} メッシュ")

    out = OUT_DIR / "transit_desert_with_pop.parquet"
    merged_pop.to_parquet(out)
    print(f"  {out.name} 出力（pop_total > 0 のみ）")

    _write_qml_with_pop(OUT_DIR / "transit_desert_with_pop.qml")
    print(f"  transit_desert_with_pop.qml 出力")

    # 全国集計（人口ありメッシュのみ）
    national = (
        merged_pop.groupby("category")[["pop_total"]]
        .sum()
        .reset_index()
    )
    if "pop_65over" in merged_pop.columns:
        national = national.merge(
            merged_pop.groupby("category")[["pop_65over"]].sum().reset_index(),
            on="category"
        )
    total_pop = merged_pop["pop_total"].sum()
    national["割合(%)"] = (national["pop_total"] / total_pop * 100).round(1)
    print("\n=== 全国集計 ===")
    print(national.to_string(index=False))
    national.to_csv(OUT_DIR / "summary_national.csv", index=False, encoding="utf-8-sig")

    # 都道府県別集計（mesh_code の先頭4桁 = 1次メッシュ → 都道府県への変換は近似）
    print("\n=== カテゴリ '2_公共交通空白地域' 上位1次メッシュ（人口） ===")
    desert = merged_pop[merged_pop["category"] == "2_公共交通空白地域"].copy()
    if len(desert) > 0:
        desert["mesh1"] = desert["mesh_code"].str[:4]
        by_mesh1 = (
            desert.groupby("mesh1")[["pop_total"]]
            .sum()
            .sort_values("pop_total", ascending=False)
            .head(20)
        )
        print(by_mesh1.to_string())

    by_mesh1_all = (
        merged_pop.groupby(["category", merged_pop["mesh_code"].str[:4]])[["pop_total"]]
        .sum()
        .reset_index()
    )
    by_mesh1_all.to_csv(OUT_DIR / "summary_pref.csv", index=False, encoding="utf-8-sig")
    print(f"\nsummary_pref.csv / summary_national.csv を {OUT_DIR} に出力しました。")


if __name__ == "__main__":
    main()
