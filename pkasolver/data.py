# Imports
from rdkit.Chem import PandasTools

PandasTools.RenderImagesInAllDataFrames(images=True)
import random

import numpy as np
import pandas as pd
import torch
from rdkit import Chem
from torch_geometric.data import Data

from pkasolver.chem import create_conjugate
from pkasolver.constants import EDGE_FEATURES, NODE_FEATURES

# NOTE: set device to cuda if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_data(base: str = "data/Baltruschat") -> dict:

    """Helper function loading the raw dataset"""

    sdf_filepath_training = f"{base}/combined_training_datasets_unique.sdf"
    sdf_filepath_novartis = f"{base}/novartis_cleaned_mono_unique_notraindata.sdf"
    sdf_filepath_AvLiLuMoVe = f"{base}/AvLiLuMoVe_cleaned_mono_unique_notraindata.sdf"

    datasets = {
        "Training": sdf_filepath_training,
        "Novartis": sdf_filepath_novartis,
        "AvLiLuMoVe": sdf_filepath_AvLiLuMoVe,
    }
    return datasets


# splits a Dataframes rows randomly into two new Dataframes with a defined size ratio
def train_validation_set_split(df: pd.DataFrame, ratio: float, seed=42):

    assert ratio > 0.0 and ratio < 1.0

    random.seed(seed)
    length = len(df)
    split = round(length * ratio)
    ids = list(range(length))
    random.shuffle(ids)
    train_ids = ids[:split]
    val_ids = ids[split:]
    train_df = df.iloc[train_ids, :]
    val_df = df.iloc[val_ids, :]
    return train_df, val_df


# data preprocessing functions - helpers
def import_sdf(sdf_filename: str):
    """Import an sdf file and return a Dataframe with an additional Smiles column."""

    df = PandasTools.LoadSDF(sdf_filename)
    df["smiles"] = [Chem.MolToSmiles(m) for m in df["ROMol"]]
    return df


def conjugates_to_dataframe(df: pd.DataFrame):
    """Take DataFrame and return a DataFrame with a column of calculated conjugated molecules."""
    conjugates = []
    for i in range(len(df.index)):
        mol = df.ROMol[i]
        index = int(df.marvin_atom[i])
        pka = float(df.marvin_pKa[i])
        conjugates.append(create_conjugate(mol, index, pka))
    df["Conjugates"] = conjugates
    return df


def sort_conjugates(df):
    """Take DataFrame, check and correct the protonated and deprotonated molecules columns and return the new Dataframe."""
    prot = []
    deprot = []
    for i in range(len(df.index)):
        indx = int(df.marvin_atom[i])
        mol = df.ROMol[i]
        conj = df.Conjugates[i]

        charge_mol = int(mol.GetAtomWithIdx(indx).GetFormalCharge())
        charge_conj = int(conj.GetAtomWithIdx(indx).GetFormalCharge())

        if charge_mol < charge_conj:
            prot.append(conj)
            deprot.append(mol)
        elif charge_mol > charge_conj:
            prot.append(mol)
            deprot.append(conj)
    df["protonated"] = prot
    df["deprotonated"] = deprot
    df = df.drop(columns=["ROMol", "Conjugates"])
    return df


# data preprocessing functions - main
def preprocess(sdf_filename: str):
    """Take name string and sdf path, process to Dataframe and save it as a pickle file."""
    df = import_sdf(sdf_filename)
    df = conjugates_to_dataframe(df)
    df = sort_conjugates(df)
    df["pKa"] = df["pKa"].astype(float)
    return df


def preprocess_all(sdf_files) -> dict:
    """Take dict of sdf paths, process to Dataframes and save it as a pickle file."""
    datasets = {}
    for name, sdf_filename in sdf_files.items():
        print(f"{name} : {sdf_filename}")
        print("###############")
        datasets[name] = preprocess(sdf_filename)
    return datasets


# Random Forrest/ML preparation functions
def make_stat_variables(df, X_list: list, y_name: list):
    """Take Pandas DataFrame and and return a Numpy Array of any other specified descriptors
    with size "Number of Molecules" x "Number of specified descriptors in X_list."
    """
    X = np.asfarray(df[X_list], float)
    y = np.asfarray(df[y_name], float).reshape(-1)
    return X, y


# Neural net data functions - helpers
class PairData(Data):
    """Externsion of the Pytorch Geometric Data Class, which additionally takes a conjugated molecules in form of the edge_index2 and x2 input"""

    def __init__(
        self,
        # NOTE: everything for protonated
        edge_index_p,
        edge_attr_p,
        x_p,
        charge_p,
        # everhtying for deprotonated
        edge_index_d,
        edge_attr_d,
        x_d,
        charge_d,
    ):
        super(PairData, self).__init__()
        self.edge_index_p = edge_index_p
        self.edge_index_d = edge_index_d

        self.x_p = x_p
        self.x_d = x_d

        self.edge_attr_p = edge_attr_p
        self.edge_attr_d = edge_attr_d

        self.charge_prot = charge_p
        self.charge_deprot = charge_d
        if x_p is not None:
            self.num_nodes = len(x_p)

    def __inc__(self, key, value, *args, **kwargs):
        if key == "edge_index_p":
            return self.x_p.size(0)
        if key == "edge_index_d":
            return self.x_d.size(0)
        else:
            return super().__inc__(key, value, *args, **kwargs)


def make_nodes(mol, marvin_atom: int, n_features: dict):
    """Take a rdkit.Mol, the atom index of the reaction center and a dict of node feature functions.

    Return a torch.tensor with dimensions num_nodes(atoms) x num_node_features.
    """
    x = []
    i = 0
    for atom in mol.GetAtoms():
        node = []
        for feat in n_features.values():
            node.append(feat(atom, i, marvin_atom))
        x.append(node)
        i += 1
    return torch.tensor(np.array([np.array(xi) for xi in x]), dtype=torch.float)


def make_edges_and_attr(mol, e_features):
    """Take a rdkit.Mol and a dict of edge feature functions.

    Return a torch.tensor with dimensions 2 x num_edges
    and a torch.tensor with dimensions num_edges x num_edge_features.
    """
    edges = []
    edge_attr = []
    for bond in mol.GetBonds():
        edges.append(np.array([[bond.GetBeginAtomIdx()], [bond.GetEndAtomIdx()],]))
        edges.append(np.array([[bond.GetEndAtomIdx()], [bond.GetBeginAtomIdx()],]))
        edge = []
        for feat in e_features.values():
            edge.append(feat(bond))
        edge_attr.extend([edge] * 2)

    edge_index = torch.tensor(np.hstack(np.array(edges)), dtype=torch.long)
    edge_attr = torch.tensor(np.array(edge_attr), dtype=torch.float)
    return edge_index, edge_attr


def make_features_dicts(all_features, feat_list):
    """Take a dict of all features and a list of strings with all disered features
    and return a dict with these features
    """
    return {x: all_features[x] for x in feat_list}


def mol_to_features(row, n_features: dict, e_features: dict, protonation_state: str):
    if protonation_state == "protonated":
        node = make_nodes(row.protonated, row.marvin_atom, n_features)
        edge_index, edge_attr = make_edges_and_attr(row.protonated, e_features)
        charge = np.sum([a.GetFormalCharge() for a in row.protonated.GetAtoms()])
        return node, edge_index, edge_attr, charge
    elif protonation_state == "deprotonated":
        node = make_nodes(row.deprotonated, row.marvin_atom, n_features)
        edge_index, edge_attr = make_edges_and_attr(row.deprotonated, e_features)
        charge = np.sum([a.GetFormalCharge() for a in row.deprotonated.GetAtoms()])
        return node, edge_index, edge_attr, charge
    else:
        raise RuntimeError()


def mol_to_paired_mol_data(
    row, n_features, e_features,
):
    """Take a DataFrame row, a dict of node feature functions and a dict of edge feature functions
    and return a Pytorch PairData object.
    """
    node_p, edge_index_p, edge_attr_p, charge_p = mol_to_features(
        row, n_features, e_features, "protonated"
    )
    node_d, edge_index_d, edge_attr_d, charge_d = mol_to_features(
        row, n_features, e_features, "deprotonated"
    )

    data = PairData(
        edge_index_p=edge_index_p,
        edge_attr_p=edge_attr_p,
        x_p=node_p,
        charge_p=charge_p,
        edge_index_d=edge_index_d,
        edge_attr_d=edge_attr_d,
        x_d=node_d,
        charge_d=charge_d,
    )
    return data


def mol_to_single_mol_data(
    row, n_features, e_features, protonation_state: str = "protonated"
):
    """Take a DataFrame row, a dict of node feature functions and a dict of edge feature functions
    and return a Pytorch Data object.
    """
    node_p, edge_index_p, edge_attr_p, charge = mol_to_features(
        row, n_features, e_features, protonation_state
    )
    return Data(x=node_p, edge_index=edge_index_p, edge_attr=edge_attr_p), charge


def make_pyg_dataset_based_on_charge(df, list_n: list, list_e: list, paired=False):
    """Take a Dataframe, a list of strings of node features, a list of strings of edge features
    and return a List of PyG Data objects.
    """
    print(f"Generating data with paired boolean set to: {paired}")
    selected_node_features = make_features_dicts(NODE_FEATURES, list_n)
    selected_edge_features = make_features_dicts(EDGE_FEATURES, list_e)
    if paired:
        dataset = []
        for i in range(len(df.index)):
            m = mol_to_paired_mol_data(
                df.iloc[i], selected_node_features, selected_edge_features,
            )
            m.y = torch.tensor([float(df.pKa[i])], dtype=torch.float32)
            m.ID = df.ID[i]
            m.to(device=device)  # NOTE: put everything on the GPU
            dataset.append(m)
        return dataset
    else:
        dataset = []
        for i in range(len(df.index)):
            charge_prot = np.sum(
                [a.GetFormalCharge() for a in df.iloc[i].protonated.GetAtoms()]
            )
            charge_deprot = np.sum(
                [a.GetFormalCharge() for a in df.iloc[i].deprotonated.GetAtoms()]
            )

            if (
                charge_prot + charge_deprot == 1
                or charge_prot + charge_deprot == 3
                or charge_prot + charge_deprot == 5
            ):
                m, molecular_charge = mol_to_single_mol_data(
                    df.iloc[i],
                    selected_node_features,
                    selected_edge_features,
                    protonation_state="protonated",
                )
            elif (
                charge_prot + charge_deprot == -1
                or charge_prot + charge_deprot == -3
                or charge_prot + charge_deprot == -5
                or charge_prot + charge_deprot == -7
            ):
                m, molecular_charge = mol_to_single_mol_data(
                    df.iloc[i],
                    selected_node_features,
                    selected_edge_features,
                    protonation_state="deprotonated",
                )
            else:
                raise RuntimeError(charge_prot, charge_deprot)

            m.y = torch.tensor([float(df.pKa[i])], dtype=torch.float32, device=device)
            m.ID = df.ID[i]
            m.charge = molecular_charge
            m.to(device=device)  # NOTE: put everything on the GPU
            dataset.append(m)
        return dataset


def make_pyg_dataset_based_on_number_of_hydrogens(
    df, list_n: list, list_e: list, paired=False, mode: str = "all"
):
    """Take a Dataframe, a list of strings of node features, a list of strings of edge features
    and return a List of PyG Data objects.
    """
    print(f"Generating data with paired boolean set to: {paired}")

    if paired is False and mode not in ["protonated", "deprotonated"]:
        raise RuntimeError(f"Wrong combination of {mode} and {paired}")

    selected_node_features = make_features_dicts(NODE_FEATURES, list_n)
    selected_edge_features = make_features_dicts(EDGE_FEATURES, list_e)
    if paired:
        dataset = []
        for i in range(len(df.index)):
            m = mol_to_paired_mol_data(
                df.iloc[i], selected_node_features, selected_edge_features
            )

            m.y = torch.tensor([df.pKa.iloc[i]], dtype=torch.float32)
            m.ID = df.ID.iloc[i]
            m.to(device=device)  # NOTE: put everything on the GPU
            dataset.append(m)
        return dataset
    else:
        print(f"Generating data with {mode} form")
        dataset = []
        for i in range(len(df.index)):
            m, molecular_charge = mol_to_single_mol_data(
                df.iloc[i],
                selected_node_features,
                selected_edge_features,
                protonation_state=mode,
            )
            m.y = torch.tensor([df.pKa.iloc[i]], dtype=torch.float32)
            m.ID = df.ID.iloc[i]
            m.to(device=device)  # NOTE: put everything on the GPU
            dataset.append(m)
        return dataset


def slice_list(input_list, size):
    "take a list and devide its items"
    input_size = len(input_list)
    slice_size = input_size // size
    remain = input_size % size
    result = []
    iterator = iter(input_list)
    for i in range(size):
        result.append([])
        for j in range(slice_size):
            result[i].append(next(iterator))
        if remain:
            result[i].append(next(iterator))
            remain -= 1
    return result


def cross_val_lists(sliced_lists, num):
    not_flattend = [x for i, x in enumerate(sliced_lists) if i != num]
    train_list = [item for subl in not_flattend for item in subl]
    val_list = sliced_lists[num]
    return train_list, val_list
