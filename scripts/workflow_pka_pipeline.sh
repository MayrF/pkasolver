#! /usr/bin/bash

version=1
data_path=/data/shared/projects/pkasolver-data

# python 00_downdload_mols_from_chembl.py --output /data/local/00_mols_chembl_v${version}.sdf.gz
# python 01_convert_sdf_to_mae.py --input /data/local/00_mols_chembl_v${version}.sdf.gz --output /data/shared/projects/pkasolver-data/01_mols_chembl_v${version}.mae.gz
# python 02_predict_pka_with_epik.py --input /data/shared/projects/pkasolver-data/01_mols_chembl_v${version}.mae.gz --output /data/shared/projects/pkasolver-data/02_mols_chembl_with_pka_v${version}.mae.gz
# python 03_convert_mae_to_sdf.py --input /data/shared/projects/pkasolver-data/02_mols_chembl_with_pka_v${version}.mae.gz --output /data/shared/projects/pkasolver-data/03_mols_chembl_with_pka_v${version}.sdf.gz
# python 04_split_epik_output.py --input /data/shared/projects/pkasolver-data/03_mols_chembl_with_pka_v${version}.sdf.gz --output /data/shared/projects/pkasolver-data/04_split_mols_chembl_with_pka_v${version}.sdf

python 05_data_preprocess.py --input ${data_path}/04_split_mols_v${version}.sdf --output ${data_path}/05_chembl_pretrain_data_v${version}.pkl
# python 05_data_preprocess.py --input ${data_path}/chembl_epik_split.sdf --output ${data_path}/05_chembl_pretrain_data_v${version}.pkl