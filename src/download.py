"""Download the NREL ESIF data centre dataset (CC-BY, DOI 10.7799/3015212) into data/raw/."""
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://data.nlr.gov/system/files/300/"
FILES = {
    "pue.parquet": "1757103411-esif.influx.buildingData.PUE.combined.parquet",
    "outside.parquet": "1757105566-esif.influx.buildingData.outside.combined_2.parquet",
    "README_ESIF.md": "1769711385-README.md",
}


def main():
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    for name, remote in FILES.items():
        dest = raw / name
        if dest.exists():
            print(f"skip {name} (already present)")
            continue
        print(f"downloading {name} ...")
        urlretrieve(BASE + remote, dest)


if __name__ == "__main__":
    main()
