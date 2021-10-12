from pkasolver import chem
import torch

NUM_THREADS = 1
torch.set_num_threads(NUM_THREADS)
print(f"Setting num threads to {NUM_THREADS}")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEED = 42
print(f"Pytorch will use {DEVICE}")

rotatable_bond = "[!$(*#*)&!D1]-&!@[!$(*#*)&!D1]"
rotatable_bond_no_amide = "[!$([NH]!@C(=O))&!D1&!$(*#*)]-&!@[!$([NH]!@C(=O))&!D1&!$(*#*)]"  # any good? https://rdkit-discuss.narkive.com/4o99LqS6/rotatable-bonds-amide-bonds-and-smarts
amide = "[NX3][CX3](=[OX1])[#6]"
keton = "[CX3]=[OX1]"

node_feature_values = {
    "element": [
        1,
        6,
        7,
        8,
        9,
        15,
        16,
        17,
        33,
        35,
        53,
    ],  # still missing to mark element that's not in the list
    "formal_charge": [-1, 0, 1],
    "is_in_ring": [1],
    "amide_center_atom": [1],
    "hybridization": [1, 2, 3, 4],
    "total_num_Hs": [0, 1, 2, 3],
    "aromatic_tag": [1],
    "total_valence": [1, 2, 3, 4, 5, 6],
    "total_degree": [1, 2, 3, 4],
    "reaction_center": [1],
}

NODE_FEATURES = {
    "element": lambda atom, i, marvin_atom: list(
        map(
            lambda s: int(atom.GetAtomicNum() == s),
            node_feature_values["element"],
        )
    ),  # still missing to mark element that's not in the list
    "formal_charge": lambda atom, i, marvin_atom: list(
        map(
            lambda s: int(atom.GetFormalCharge() == s),
            node_feature_values["formal_charge"],
        )
    ),
    "is_in_ring": lambda atom, i, marvin_atom: atom.IsInRing(),
    "amide_center_atom": lambda atom, i, marvin_atom: chem.atom_smarts_query(
        atom, amide
    ),
    "hybridization": lambda atom, i, marvin_atom: list(
        map(
            lambda s: int(atom.GetHybridization() == s),
            node_feature_values["hybridization"],
        )
    ),
    "total_num_Hs": lambda atom, i, marvin_atom: list(
        map(
            lambda s: int(atom.GetTotalNumHs() == s),
            node_feature_values["total_num_Hs"],
        )
    ),
    "aromatic_tag": lambda atom, i, marvin_atom: atom.GetIsAromatic(),
    "total_valence": lambda atom, i, marvin_atom: list(
        map(
            lambda s: int(atom.GetTotalValence() == s),
            node_feature_values["total_valence"],
        )
    ),
    "total_degree": lambda atom, i, marvin_atom: list(
        map(
            lambda s: int(atom.GetTotalDegree() == s),
            node_feature_values["total_degree"],
        )
    ),
    "reaction_center": lambda atom, i, marvin_atom: i == int(marvin_atom),
}

edge_feature_values = {
    "bond_type": [1.0, 1.5, 2.0, 3.0],
    "is_conjugated": [1],
    "rotatable": [1],
}

EDGE_FEATURES = {
    "bond_type": lambda bond: list(
        map(
            lambda s: int(bond.GetBondTypeAsDouble() == s),
            edge_feature_values["bond_type"],
        )
    ),
    "is_conjugated": lambda bond: bond.GetIsConjugated(),
    "rotatable": lambda bond: chem.bond_smarts_query(bond, rotatable_bond),
}
