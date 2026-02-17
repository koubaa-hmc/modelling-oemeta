import yaml
from deepdiff import DeepDiff
from pathlib import Path

# 1. Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent

# 2. If your script is in 'root/scripts/' and file is in 'root/src/'
# Move up one level (parent), then down into 'src'
schema_folder = BASE_DIR.parent / "schema"
schema_file_path_l = schema_folder / "oemetadata.yaml"
schema_file_path_r = schema_folder / "oemeta_schema.yaml"

print(f"Absolute path to file: {schema_file_path_r}")

with open(schema_file_path_r) as f1, open(schema_file_path_l) as f2:
    t1 = yaml.safe_load(f1)
    t2 = yaml.safe_load(f2)

diff = DeepDiff(t2, t1, ignore_order=True)
print(diff.pretty())
