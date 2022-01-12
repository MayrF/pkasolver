# imports
from os import path
from typing import Tuple

import numpy as np
import pandas as pd
from IPython.display import display
from pkg_resources import resource_filename
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem.Draw import IPythonConsole

# IPythonConsole.drawOptions.addAtomIndices = True
IPythonConsole.molSize = 400, 400
import pickle
import sys
from copy import deepcopy

import torch
import torch_geometric
from rdkit import RDLogger
from rdkit.Chem import Draw

from pkasolver.constants import DEVICE, EDGE_FEATURES, NODE_FEATURES
from pkasolver.data import (
    calculate_nr_of_features,
    make_features_dicts,
    mol_to_paired_mol_data,
)
from pkasolver.dimorphite_dl import run_with_mol_list
from pkasolver.ml import dataset_to_dataloader, predict
from pkasolver.ml_architecture import GINPairV1, GINPairV2

RDLogger.DisableLog("rdApp.*")

node_feat_list = [
    "element",
    "formal_charge",
    "hybridization",
    "total_num_Hs",
    "aromatic_tag",
    "total_valence",
    "total_degree",
    "is_in_ring",
    "reaction_center",
    "smarts",
]

edge_feat_list = ["bond_type", "is_conjugated", "rotatable"]
num_node_features = calculate_nr_of_features(node_feat_list)
num_edge_features = calculate_nr_of_features(edge_feat_list)

# make dicts from selection list to be used in the processing step
selected_node_features = make_features_dicts(NODE_FEATURES, node_feat_list)
selected_edge_features = make_features_dicts(EDGE_FEATURES, edge_feat_list)

# # model_path = "/data/shared/projects/pkasolver-data-clean/trained_models_v1/training_with_GINPairV1_v1_hp/reg_everything_best_model.pt"
# # model_path = "/data/shared/projects/pkasolver-data-clean-pickled-models/trained_models_v1/training_with_GINPairV1_v1_hp/reg_everything_best_model.pkl"
model_path = path.join(path.dirname(__file__), "reg_everything_best_model.pkl")


class QueryModel:
    """
    Class for loading, holding and changing the model used for pka queries.
    Init takes path to pickled model file and returns Object with prepared model.

    Attributes
    ----------
    path : string
        path to the current model
    model
        pytorch geometric model object

    Methods
    -------
    init:
        takes path to pickled model file and returns object (model) with prepared model.

        Parameters
        ----------
        new path
            input molecule
        e_features
            dictionary containing functions for edge feature generation



    Returns
    -------

    """

    def __init__(self, path: str):
        self.path = path
        self.model_init()

    def model_init(self):

        with open(model_path, "rb") as f:
            self.model = pickle.load(f)
        self.model.eval()
        self.model.to(device=DEVICE)

    def set_path(self, new_path):
        self.path = new_path
        self.model_init()


query_model = QueryModel(model_path)

# helper functions


def set_model_path(new_path: str, query_model=query_model):
    query_model.set_path(new_path)


def get_ionization_indices(mol_lst: list) -> list:
    """Takes a list of mol objects of different protonation states,
    but identically indexed and returns indices list of ionizable atoms

    that must be identically indexed
    and differ only in their ionization state.

    ----------

    mol_lst
        A list of rdkit.Chem.rdchem.Mol objects.
    matches
        p

    Exception:
    -------
    excption_type
        If the molecules in mol_lst differ in more ways than their protonation states

    Returns
    -------
    list
        A list of indices of ionizable atoms.
    :raises Exception: If the molecules in mol_lst differ in more ways
        than their protonation states
    """

    assert (
        len(set([len(mol.GetAtoms()) for mol in mol_lst])) == 1
    ), "Molecules must only differ in their protonation state"

    ion_idx = []
    atoms = np.array(
        [list(atom.GetFormalCharge() for atom in mol.GetAtoms()) for mol in mol_lst]
    )
    for i in range(atoms.shape[1]):
        if len(set(list(atoms[:, i]))) > 1:
            ion_idx.append(i)
    return ion_idx


def get_possible_reactions(mol: Chem.rdchem.Mol, matches: list) -> Tuple[list, list]:
    """

    ----------
    mol
        p
    matches
        p

    Returns
    -------
    list
        r
    list
        r
    """

    acid_pairs = []
    base_pairs = []
    for match in matches:
        mol.__sssAtoms = [match]  # not sure if needed
        # create conjugate
        new_mol = deepcopy(mol)
        atom = new_mol.GetAtomWithIdx(match)
        element = atom.GetAtomicNum()
        charge = atom.GetFormalCharge()
        Ex_Hs = atom.GetNumExplicitHs()
        Tot_Hs = atom.GetTotalNumHs()
        if (element == 7 and charge <= 0) or charge < 0:
            # increase H
            try:
                atom.SetFormalCharge(charge + 1)
                if Tot_Hs == 0 or Ex_Hs > 0:
                    atom.SetNumExplicitHs(Ex_Hs + 1)
                atom.UpdatePropertyCache()
                acid_pairs.append((new_mol, mol, match))
            except:
                pass

        # reset changes in case atom can also be deprotonated
        new_mol = deepcopy(mol)
        atom = new_mol.GetAtomWithIdx(match)
        element = atom.GetAtomicNum()
        charge = atom.GetFormalCharge()
        Ex_Hs = atom.GetNumExplicitHs()
        Tot_Hs = atom.GetTotalNumHs()

        if (
            Tot_Hs > 0
            and charge >= 0
            and not (element == 7 and charge == 0 and Tot_Hs == 1)
        ):
            # reduce H
            atom.SetFormalCharge(charge - 1)
            if Ex_Hs > 0:
                atom.SetNumExplicitHs(Ex_Hs - 1)
            atom.UpdatePropertyCache()
            base_pairs.append((mol, new_mol, match))

    return acid_pairs, base_pairs


def match_pka(pair_tuples: list, model) -> float:
    """

    ----------
    pair_tuples
        p
    model
        p

    Returns
    -------
    float
        r
    """

    pair_data = []
    for (prot, deprot, atom_idx) in pair_tuples:
        m = mol_to_paired_mol_data(
            prot,
            deprot,
            atom_idx,
            selected_node_features,
            selected_edge_features,
        )
        pair_data.append(m)
    loader = dataset_to_dataloader(pair_data, 64, shuffle=False)
    return np.round(predict(model, loader), 3)


def acid_sequence(
    acid_pairs: list, mols: list, pkas: list, atoms: list
) -> Tuple[list, list, list]:
    """

    ----------
    acid_pairs
        p
    mols
        p
    pkas
        p
    atoms
        p

    Returns
    -------
    int
        r
    int
        r
    int
        r
    """

    # determine pka for protonatable groups
    if len(acid_pairs) > 0:
        acid_pkas = list(match_pka(acid_pairs, query_model.model))
        pka = max(acid_pkas)  # determining closest protonation pka
        if pka < 0.5:  # do not include pka if lower than 0.5
            return mols, pkas, atoms

        pkas.insert(0, pka)  # prepending pka to global pka list
        mols.insert(
            0, acid_pairs[acid_pkas.index(pka)][0]
        )  # prepending protonated molcule to global mol list
        atoms.insert(
            0, acid_pairs[acid_pkas.index(pka)][2]
        )  # prepending protonated molcule to global mol list
    return mols, pkas, atoms


def base_sequence(
    base_pairs: list, mols: list, pkas: list, atoms: list
) -> Tuple[list, list, list]:
    """

    ----------
    base_pairs
        p
    mol
        p
    pkas
        p
    atoms
        p

    Returns
    -------
    int
        r
    int
        r
    int
        r
    """

    # determine pka for deprotonatable groups
    if len(base_pairs) > 0:
        base_pkas = list(match_pka(base_pairs, query_model.model))
        pka = min(base_pkas)  # determining closest deprotonation pka
        if pka > 13.5:  # do not include if pka higher than 13.5
            return mols, pkas, atoms
        pkas.append(pka)  # appending pka to global pka list
        mols.append(
            base_pairs[base_pkas.index(pka)][1]
        )  # appending protonated molcule to global mol list
        atoms.append(
            base_pairs[base_pkas.index(pka)][2]
        )  # appending protonated molcule to global mol list
    return mols, pkas, atoms


def mol_query(mol: Chem.rdchem.Mol) -> dict:
    """

    ----------
    mol
        p

    Returns
    -------
    dict
        r
    """

    try:
        name = mol.GetProp("_Name")
        mol = run_with_mol_list([mol], min_ph=7, max_ph=7, pka_precision=0)[0]
        mol = Chem.MolFromSmiles(Chem.MolToSmiles(mol))
        mol.SetProp("_Name", name)
    except:
        mol = run_with_mol_list([mol], min_ph=7, max_ph=7, pka_precision=0)[0]
        mol = Chem.MolFromSmiles(Chem.MolToSmiles(mol))

    mols = [mol]
    pkas = []
    atoms = []

    matches = get_ionization_indices(run_with_mol_list([mol], min_ph=0.5, max_ph=13.5))

    while True:
        inital_length = len(pkas)
        acid_pairs, base_pairs = get_possible_reactions(mols[0], matches)
        mols, pkas, atoms = acid_sequence(acid_pairs, mols, pkas, atoms)
        if inital_length >= len(pkas):
            break
    while True:
        inital_length = len(pkas)
        acid_pairs, base_pairs = get_possible_reactions(mols[-1], matches)
        mols, pkas, atoms = base_sequence(base_pairs, mols, pkas, atoms)
        if inital_length >= len(pkas):
            break

    mol_tuples = []
    for i in range(len(mols) - 1):
        mol_tuples.append((mols[i], mols[i + 1]))
    mols = mol_tuples

    return {"mol": mols, "pka": pkas, "atom": atoms}


def smiles_query(smi: str, output_smiles: bool = False) -> Tuple[list, list, list]:
    """

    ----------
    p
        p

    Returns
    -------
    r
        r
    """

    res = mol_query(Chem.MolFromSmiles(smi))
    if output_smiles == True:
        smiles = []
        for mol in res["mol"]:
            smiles.append((Chem.MolToSmiles(mol[0]), Chem.MolToSmiles(mol[1])))
        res["mol"] = smiles
    return res


def inchi_query(ini: str, output_inchi=False) -> dict:
    """

    ----------
    ini
        p
    output_inchi
        p

    Returns
    -------
    dict
        r
    """

    # return mol_query(Chem.MolFromInchi(ini))
    res = mol_query(Chem.MolFromInchi(ini))
    if output_inchi == True:
        inchi = []
        for mol in res["mol"]:
            inchi.append((Chem.MolToInchi(mol[0]), Chem.MolToInchi(mol[1])))
        res["mol"] = inchi
    return res


def sdf_query(input_path: str, output_path: str, merged_output: bool = False):
    """

    ----------
    input_path
        p
    output_path
        p
    merged_output
        p

    Returns
    -------
    None
    """

    print(f"opening .sdf file at {input_path} and computing pkas...")
    with open(input_path, "rb") as fh:
        with open(output_path, "w") as sdf_zip:
            with Chem.SDWriter(sdf_zip) as writer:
                count = 0
                for i, mol in enumerate(Chem.ForwardSDMolSupplier(fh, removeHs=True)):
                    # if i > 10:
                    #     break
                    # clear porps
                    props = mol.GetPropsAsDict()
                    for prop in props.keys():
                        mol.ClearProp(prop)
                    res = mol_query(mol)
                    mols = res["mol"]
                    pkas = res["pka"]
                    atoms = res["atom"]
                    if merged_output == True:
                        mol = mols[0][0]
                        mol.SetProp("ID", f"{mol.GetProp('_Name')}")
                        for ii, (pka, atom) in enumerate(zip(pkas, atoms)):
                            count += 1
                            mol.SetProp(f"pka_{ii}", f"{pka}")
                            mol.SetProp(f"atom_idx_{ii}", f"{atom}")
                            writer.write(mol)
                    else:
                        for ii, (mol, pka, atom) in enumerate(zip(mols, pkas, atoms)):
                            count += 1
                            mol = mol[0]
                            mol.SetProp("ID", f"{mol.GetProp('_Name')}_{ii}")
                            mol.SetProp("pka", f"{pka}")
                            mol.SetProp("atom_idx", f"{atom}")
                            mol.SetProp("pka-number", f"{ii}")
                            # print(mol.GetPropsAsDict())
                            writer.write(mol)
                print(
                    f"{count} pkas for {i} molecules predicted and saved at \n{output_path}"
                )


def draw_pka_map(res: dict, size=(450, 450)):
    """

    ----------
    res
        p
    size
        p

    Returns
    -------
    img
        r
    """

    mol = res["mol"][0][0]
    for idx, pka in zip(res["atom"], res["pka"]):
        atom = mol.GetAtomWithIdx(idx)
        try:
            atom.SetProp("atomNote", f'{atom.GetProp("atomNote")},   {pka:.2f}')
        except:
            atom.SetProp("atomNote", f"{pka:.2f}")
    return Draw.MolToImage(mol, size=size)


def draw_pka_reactions(res: dict):
    """

    ----------
    res
        p

    Returns
    -------
    img
        r
    """

    mols = res["mol"]
    pkas = res["pka"]
    atoms = res["atom"]
    draw_pairs = []
    pair_atoms = []
    pair_pkas = []
    for i in range(len(mols)):
        draw_pairs.extend([mols[i][0], mols[i][1]])
        pair_atoms.extend([[atoms[i]], [atoms[i]]])
        pair_pkas.extend([pkas[i], pkas[i]])
    return Draw.MolsToGridImage(
        draw_pairs,
        molsPerRow=2,
        subImgSize=(250, 250),
        highlightAtomLists=pair_atoms,
        legends=[f"pka = {pair_pkas[i]:.2f}" for i in range(len(mols) * 2)],
    )


def draw_sdf_mols(input_path: str, range_list=[]):
    """

    ----------
    input_path
        p
    range_list
        p

    Returns
    -------
    None
    """

    print(f"opening .sdf file at {input_path} and computing pkas...")
    with open(input_path, "rb") as fh:
        count = 0
        for i, mol in enumerate(Chem.ForwardSDMolSupplier(fh, removeHs=True)):
            if range_list and i not in range_list:
                continue
            props = mol.GetPropsAsDict()
            for prop in props.keys():
                mol.ClearProp(prop)
            display(draw_pka_map(mol_query(mol)))
            print(f"Name: {mol.GetProp('_Name')}")
