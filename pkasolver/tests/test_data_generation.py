from rdkit import Chem
from pkasolver.data import make_features_dicts, make_nodes
from pkasolver.constants import NODE_FEATURES, EDGE_FEATURES
from pkasolver.data import make_edges_and_attr, make_nodes, load_data
import torch
import subprocess, os
import numpy as np
import pickle


def test_aspirin_pka_split():
    import pkasolver

    # path = os.path.abspath(os.path.join(os.path.dirname(pkasolver.__file__), os.pardir))
    path = os.path.abspath(os.path.dirname(pkasolver.__file__))

    o = subprocess.run(
        [
            "python",
            f"scripts/04_1_split_epik_output.py",
            "--input",
            f"pkasolver/tests/testdata/03_aspirin_with_pka.sdf",
            "--output",
            f"pkasolver/tests/testdata/04_split_aspirin_with_pka.pkl",
        ],
        stderr=subprocess.STDOUT,
    )

    o.check_returncode()
    f = pickle.load(
        open("pkasolver/tests/testdata/04_split_aspirin_with_pka.pkl", "rb")
    )

    name = "test123"
    smi1, smi2 = f[name]["smiles_list"][0]
    pkas = f[name]["pKa_list"]

    print(smi1)
    assert smi1 == "CC(=O)Oc1ccccc1C(=O)O"
    print(smi2)
    assert smi2 == "CC(=O)Oc1ccccc1C(=O)[O-]"
    assert np.isclose(float(pkas[0]), 3.52)


def test_eltrombopag_pka_split():
    import pkasolver

    # path = os.path.abspath(os.path.join(os.path.dirname(pkasolver.__file__), os.pardir))
    path = os.path.abspath(os.path.dirname(pkasolver.__file__))

    o = subprocess.run(
        [
            "python",
            f"scripts/04_1_split_epik_output.py",
            "--input",
            f"pkasolver/tests/testdata/03_eltrombopag_with_pka.sdf",
            "--output",
            f"pkasolver/tests/testdata/04_split_eltrombopag_with_pka.pkl",
        ],
        stderr=subprocess.STDOUT,
    )

    o.check_returncode()

    f = pickle.load(
        open("pkasolver/tests/testdata/04_split_eltrombopag_with_pka.pkl", "rb")
    )

    name = "test123"
    print(f)

    pkas = f[name]["pKa_list"]
    # first eltrombopag species is skipped

    # second eltrombopag species
    smi1, smi2 = f[name]["smiles_list"][0]
    assert np.isclose(float(pkas[0]), 4.05)
    print(smi1)
    assert smi1 == "Cc1ccc(-n2nc(C)c(N=Nc3cccc(-c4cccc(C(=O)O)c4)c3O)c2O)cc1C"
    assert smi2 == "Cc1ccc(-n2nc(C)c(N=Nc3cccc(-c4cccc(C(=O)[O-])c4)c3O)c2O)cc1C"

    # third eltrombopag species
    smi1, smi2 = f[name]["smiles_list"][1]
    assert np.isclose(float(pkas[1]), 7.449)
    assert smi1 == "Cc1ccc(-n2nc(C)c(N=Nc3cccc(-c4cccc(C(=O)[O-])c4)c3O)c2O)cc1C"
    assert smi2 == "Cc1ccc(-n2nc(C)c(N=Nc3cccc(-c4cccc(C(=O)[O-])c4)c3O)c2[O-])cc1C"

    # fourth eltrombopag species
    smi1, smi2 = f[name]["smiles_list"][2]
    assert np.isclose(float(pkas[2]), 9.894)
    assert smi1 == "Cc1ccc(-n2nc(C)c(N=Nc3cccc(-c4cccc(C(=O)[O-])c4)c3O)c2[O-])cc1C"
    assert smi2 == "Cc1ccc(-n2nc(C)c(N=Nc3cccc(-c4cccc(C(=O)[O-])c4)c3[O-])c2[O-])cc1C"


def test_edta_pka_split():
    import pkasolver
    import gzip, shutil

    # path = os.path.abspath(os.path.join(os.path.dirname(pkasolver.__file__), os.pardir))
    path = os.path.abspath(os.path.dirname(pkasolver.__file__))

    o = subprocess.run(
        [
            "python",
            f"scripts/04_1_split_epik_output.py",
            "--input",
            f"pkasolver/tests/testdata/03_edta_with_pka.sdf",
            "--output",
            f"pkasolver/tests/testdata/04_split_edta_with_pka.pkl",
        ],
        stderr=subprocess.STDOUT,
    )

    o.check_returncode()

    f = pickle.load(open("pkasolver/tests/testdata/04_split_edta_with_pka.pkl", "rb"))

    name = "test123"
    print(f)
    pkas = f[name]["pKa_list"]
    # first eltrombopag species is skipped

    # first EDTA species
    smi1, smi2 = f[name]["smiles_list"][0]
    assert np.isclose(float(pkas[0]), 5.488)
    print(smi1)
    assert smi1 == "O=C([O-])CN(CC[NH+](CC(=O)[O-])CC(=O)[O-])CC(=O)O"
    assert smi2 == "O=C([O-])CN(CC[NH+](CC(=O)[O-])CC(=O)[O-])CC(=O)[O-]"

    # second EDTA species
    smi1, smi2 = f[name]["smiles_list"][1]
    assert np.isclose(float(pkas[1]), 4.585)
    assert smi1 == "O=C([O-])C[NH+](CCN(CC(=O)O)CC(=O)O)CC(=O)[O-]"
    assert smi2 == "O=C([O-])CN(CC[NH+](CC(=O)[O-])CC(=O)[O-])CC(=O)O"

    # third EDTA species
    smi1, smi2 = f[name]["smiles_list"][2]
    assert np.isclose(float(pkas[2]), 2.241)
    assert smi1 == "O=C([O-])C[NH+](CCN(CC(=O)O)CC(=O)O)CC(=O)O"
    assert smi2 == "O=C([O-])C[NH+](CCN(CC(=O)O)CC(=O)O)CC(=O)[O-]"

    # fourth EDTA species
    smi1, smi2 = f[name]["smiles_list"][3]
    assert np.isclose(float(pkas[3]), 1.337)
    assert smi1 == "O=C(O)CN(CC[NH+](CC(=O)O)CC(=O)O)CC(=O)O"
    assert smi2 == "O=C([O-])C[NH+](CCN(CC(=O)O)CC(=O)O)CC(=O)O"

    # fifth EDTA species
    smi1, smi2 = f[name]["smiles_list"][4]
    assert np.isclose(float(pkas[4]), 9.883)
    assert smi1 == "O=C([O-])CN(CC[NH+](CC(=O)[O-])CC(=O)[O-])CC(=O)[O-]"
    assert smi2 == "O=C([O-])CN(CCN(CC(=O)[O-])CC(=O)[O-])CC(=O)[O-]"


def test_exp_sets_generation():
    import pkasolver

    # path = os.path.abspath(os.path.join(os.path.dirname(pkasolver.__file__), os.pardir))
    path = os.path.abspath(os.path.dirname(pkasolver.__file__))

    o = subprocess.run(
        [
            "python",
            f"scripts/04_2_prepare_rest.py",
            "--input",
            f"pkasolver/tests/testdata/04_split_exp_dataset_with_pka.sdf",
            "--output",
            f"pkasolver/tests/testdata/exp_training_dataset.pkl",
        ],
        stderr=subprocess.STDOUT,
    )

    o.check_returncode()

    f = pickle.load(open("pkasolver/tests/testdata/exp_training_dataset.pkl", "rb"))
    # print(f)

    # first mol
    name = "mol0"
    pkas = f[name]["pKa_list"]
    assert np.isclose(pkas[0], 6.21)
    smi1, smi2 = f[name]["smiles_list"][0]
    assert smi1 == "Brc1c(N2CCCCCC2)nc(C2CC2)[nH+]c1NC1CC1"
    assert smi2 == "Brc1c(NC2CC2)nc(C2CC2)nc1N1CCCCCC1"

    # second mol
    name = "mol1"
    pkas = f[name]["pKa_list"]
    print(pkas)
    assert np.isclose(pkas[0], 7.46)
    smi1, smi2 = f[name]["smiles_list"][0]
    assert smi1 == "Brc1cc(Br)c(NC2=[NH+]CCN2)c(Br)c1"
    assert smi2 == "Brc1cc(Br)c(NC2=NCCN2)c(Br)c1"

    # third mol
    name = "mol2"
    pkas = f[name]["pKa_list"]
    print(pkas)
    assert np.isclose(pkas[0], 4.2)
    smi1, smi2 = f[name]["smiles_list"][0]
    assert smi1 == "Brc1cc2cccnc2c2[nH+]cccc12"
    assert smi2 == "Brc1cc2cccnc2c2ncccc12"

    # fourth mol
    name = "mol3"
    pkas = f[name]["pKa_list"]
    print(pkas)
    assert np.isclose(pkas[0], 3.73)
    smi1, smi2 = f[name]["smiles_list"][0]
    assert smi1 == "Brc1ccc(-c2nn[nH]n2)cc1"
    assert smi2 == "Brc1ccc(-c2nn[n-]n2)cc1"


def test_data_preprocessing_for_baltruschat():
    import pkasolver

    path = os.path.abspath(os.path.dirname(pkasolver.__file__))

    o = subprocess.run(
        [
            "python",
            f"scripts/05_data_preprocess.py",
            "--input",
            f"pkasolver/tests/testdata/exp_training_dataset.pkl",
            "--output",
            f"pkasolver/tests/testdata/test.pkl",
        ],
        stderr=subprocess.STDOUT,
    )

    o.check_returncode()

    f = pickle.load(open("pkasolver/tests/testdata/test.pkl", "rb"))
    print(f)

    assert len(f) == 16

    # first mol
    entry = f[0]
    pka = entry.reference_value
    assert np.isclose(pka, 6.21)
    smi1, smi2 = entry.smiles_prop, entry.smiles_deprop
    assert smi1 == "Brc1c(N2CCCCCC2)nc(C2CC2)[nH+]c1NC1CC1"
    assert smi2 == "Brc1c(NC2CC2)nc(C2CC2)nc1N1CCCCCC1"

    # second mol
    entry = f[1]
    pka = entry.reference_value
    assert np.isclose(pka, 7.46)
    smi1, smi2 = entry.smiles_prop, entry.smiles_deprop
    assert smi1 == "Brc1cc(Br)c(NC2=[NH+]CCN2)c(Br)c1"
    assert smi2 == "Brc1cc(Br)c(NC2=NCCN2)c(Br)c1"

    # third mol
    entry = f[2]
    pka = entry.reference_value
    assert np.isclose(pka, 4.2)
    smi1, smi2 = entry.smiles_prop, entry.smiles_deprop
    assert smi1 == "Brc1cc2cccnc2c2[nH+]cccc12"
    assert smi2 == "Brc1cc2cccnc2c2ncccc12"

    # third mol
    entry = f[3]
    pka = entry.reference_value
    assert np.isclose(pka, 3.73)
    smi1, smi2 = entry.smiles_prop, entry.smiles_deprop
    assert smi1 == "Brc1ccc(-c2nn[nH]n2)cc1"
    assert smi2 == "Brc1ccc(-c2nn[n-]n2)cc1"


def test_features_dicts():
    """Test the generation of the features dict"""
    list_n = ["element", "formal_charge"]
    list_e = ["bond_type", "is_conjugated"]

    n_feat = make_features_dicts(NODE_FEATURES, list_n)
    e_feat = make_features_dicts(EDGE_FEATURES, list_e)
    assert set(n_feat.keys()) == set(list_n)
    assert len(n_feat.keys()) == len(list_n)
    assert set(e_feat.keys()) == set(list_e)
    assert len(e_feat.keys()) == len(list_e)


def test_dataset():
    """what charges are present in the dataset"""
    from pkasolver.data import preprocess
    import numpy as np

    sdf_filepaths = load_data()
    df = preprocess(sdf_filepaths["Training"])
    charges = []
    for i in range(len(df.index)):
        charge_prot = np.sum(
            [a.GetFormalCharge() for a in df.iloc[i].protonated.GetAtoms()]
        )
        charge_deprot = np.sum(
            [a.GetFormalCharge() for a in df.iloc[i].deprotonated.GetAtoms()]
        )

        # the difference needs to be 1
        assert abs(charge_prot - charge_deprot) == 1
        charges.append(charge_prot)
        charges.append(charge_deprot)

    # NOTE: quite a lot of negative charges
    assert max(charges) == 2
    assert min(charges) == -4


def test_nodes():
    """Test the conversion of mol to nodes with feature subset"""
    list_n = ["element", "formal_charge"]

    n_feat = make_features_dicts(NODE_FEATURES, list_n)

    mol = Chem.MolFromSmiles("Cc1ccccc1")
    nodes = make_nodes(mol, 1, n_feat)
    for xi in nodes:
        assert tuple(xi.numpy()) == (
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
        )

    list_n = ["element", "formal_charge", "reaction_center"]

    n_feat = make_features_dicts(NODE_FEATURES, list_n)
    nodes = make_nodes(mol, 1, n_feat)
    assert tuple(nodes[1].numpy()) == (
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        1.0,
    )

    assert tuple(nodes[0].numpy()) == (
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
    )


def test_smarts_nodes():
    """Test the conversion of mol to nodes with feature subset"""
    from pkasolver.data import preprocess

    sdf_filepaths = load_data()
    df = preprocess(sdf_filepaths["Training"])
    list_n = ["smarts"]
    print(df.iloc[0].smiles)
    n_feat = make_features_dicts(NODE_FEATURES, list_n)
    nodes = make_nodes(df.iloc[0].protonated, df.iloc[0].marvin_atom, n_feat)

    assert tuple(nodes[0]) == (
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
    )


def test_smarts_nodes_sds():
    """Test the conversion of mol to nodes with feature subset"""

    list_n = ["smarts"]
    n_feat = make_features_dicts(NODE_FEATURES, list_n)
    mol = Chem.MolFromSmiles("CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]")
    mol_nodes = make_nodes(mol, 33, n_feat)

    test_nodes = torch.zeros((mol_nodes.shape))
    test_nodes[12:17, 0] = 1
    test_nodes[0:12, 32] = 1
    test_nodes[12, 33] = 1
    test_nodes[14:17, 33] = 1

    assert torch.equal(test_nodes, mol_nodes)


def test_smarts_nodes_amoxicillin():
    """Test the conversion of mol to nodes with feature subset"""

    list_n = ["smarts"]
    n_feat = make_features_dicts(NODE_FEATURES, list_n)
    mol = Chem.MolFromSmiles(
        "CC1([C@@H](N2[C@H](S1)[C@@H](C2=O)NC(=O)[C@@H](C3=CC=C(C=C3)O)N)C(=O)O)C"
    )
    mol_nodes = make_nodes(mol, 23, n_feat)

    test_nodes = torch.zeros((mol_nodes.shape))
    test_nodes[21:24, 6] = 1
    test_nodes[16, 16] = 1
    test_nodes[19, 16] = 1
    test_nodes[3, 24] = 1
    test_nodes[6:13, 24] = 1
    test_nodes[2, 25] = 1
    test_nodes[21:24, 25] = 1
    test_nodes[12, 29] = 1
    test_nodes[20, 29] = 1
    test_nodes[0, 32] = 1
    test_nodes[2, 32] = 1
    test_nodes[4, 32] = 1
    test_nodes[6, 32] = 1
    test_nodes[12, 32] = 1
    test_nodes[24, 32] = 1
    test_nodes[3, 33] = 1
    test_nodes[5, 33] = 1
    test_nodes[8:12, 33] = 1
    test_nodes[19:24, 33] = 1
    test_nodes[9, 34] = 1
    test_nodes[19:21, 34] = 1
    test_nodes[23, 34] = 1

    assert torch.equal(test_nodes, mol_nodes)


def test_smarts_nodes_taurin():
    """Test the conversion of mol to nodes with feature subset"""

    list_n = ["smarts"]
    n_feat = make_features_dicts(NODE_FEATURES, list_n)
    mol = Chem.MolFromSmiles("C(CS(=O)(=O)O)N")
    mol_nodes = make_nodes(mol, 5, n_feat)

    test_nodes = torch.zeros((mol_nodes.shape[0], 1))
    test_nodes[1:6] = 1

    assert torch.equal(mol_nodes[:, 1:2], test_nodes)


def test_edges_generation():
    import torch

    """ Test the conversion of edge indizes and features with feature subset """
    list_e = ["bond_type", "is_conjugated"]

    e_feat = make_features_dicts(EDGE_FEATURES, list_e)

    mol = Chem.MolFromSmiles("Cc1ccccc1")
    edge_index, edge_attr = make_edges_and_attr(mol, e_feat)
    assert torch.equal(
        edge_index,
        torch.tensor(
            [
                [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 1],
                [1, 0, 2, 1, 3, 2, 4, 3, 5, 4, 6, 5, 1, 6],
            ]
        ),
    )
    assert torch.equal(
        edge_attr,
        torch.tensor(
            [
                [1.0, 0.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 0.0, 1.0],
            ]
        ),
    )


def test_use_dataset_for_node_generation():
    """Test that the training dataset can be generated and that prot/deprot are different molecules"""
    from pkasolver.data import preprocess
    import torch

    sdf_filepaths = load_data()
    df = preprocess(sdf_filepaths["Training"])
    assert df.iloc[0].pKa == 6.21
    assert int(df.iloc[0].marvin_atom) == 10
    assert df.iloc[0].smiles == "Brc1c(NC2CC2)nc(C2CC2)nc1N1CCCCCC1"

    list_n = ["element", "formal_charge"]
    n_feat = make_features_dicts(NODE_FEATURES, list_n)

    n_prot = make_nodes(df.iloc[0].protonated, df.iloc[0].marvin_atom, n_feat)
    print(n_prot)
    n_dep = make_nodes(df.iloc[0].deprotonated, df.iloc[0].marvin_atom, n_feat)
    print(n_dep)
    assert torch.equal(n_prot, n_dep) == False


def test_generate_data_intances():
    """Test that data classes instances are created correctly"""
    from pkasolver.data import (
        mol_to_single_mol_data,
        mol_to_paired_mol_data,
        make_paired_pyg_data_from_mol,
    )
    from pkasolver.chem import create_conjugate
    import torch

    sdf_filepaths = load_data()
    suppl = Chem.ForwardSDMolSupplier(sdf_filepaths["Training"], removeHs=True)

    for idx, mol in enumerate(suppl):
        if idx == 0:
            props = mol.GetPropsAsDict()

            assert props["pKa"] == 6.21
            atom_idx = props["marvin_atom"]
            assert int(atom_idx) == 10
            assert Chem.MolToSmiles(mol) == "Brc1c(NC2CC2)nc(C2CC2)nc1N1CCCCCC1"

            list_n = ["element", "formal_charge"]
            n_feat = make_features_dicts(NODE_FEATURES, list_n)
            list_e = ["bond_type", "is_conjugated"]
            e_feat = make_features_dicts(EDGE_FEATURES, list_e)

            conj = create_conjugate(mol, atom_idx, props["pKa"])

            d1, charge1 = mol_to_single_mol_data(mol, atom_idx, n_feat, e_feat)
            d2, charge2 = mol_to_single_mol_data(conj, atom_idx, n_feat, e_feat)
            assert charge1 != charge2
            # sort mol and conj into protonated and deprotonated molecule
            if int(mol.GetAtomWithIdx(atom_idx).GetFormalCharge()) > int(
                conj.GetAtomWithIdx(atom_idx).GetFormalCharge()
            ):
                prot = mol
                deprot = conj
            else:
                prot = conj
                deprot = mol

            d1, charge1 = mol_to_single_mol_data(prot, atom_idx, n_feat, e_feat)
            d2, charge2 = mol_to_single_mol_data(deprot, atom_idx, n_feat, e_feat)

            assert charge1 == 1
            assert charge2 == 0

            d3 = mol_to_paired_mol_data(prot, deprot, atom_idx, n_feat, e_feat,)
            # all of them have the same number of nodes
            assert d1.num_nodes == d2.num_nodes == len(d3.x_p) == len(d3.x_d)
            # but different node features
            assert torch.equal(d1.x, d2.x) is False
            # they have the same connection table
            assert torch.equal(d1.edge_index, d2.edge_index)
            # but different edge features (NOTE: In the case of this molecule edge attr are the same)
            assert torch.equal(d1.edge_attr, d2.edge_attr) is True
            # try the encapsuled function
            # make_paired_pyg_data_from_mol(mol, n_feat, e_feat)
            # Try a new molecule
            ############
        elif idx == 1429:
            ############
            props = mol.GetPropsAsDict()
            atom_idx = props["marvin_atom"]
            assert atom_idx == 35
            conj = create_conjugate(mol, atom_idx, props["pKa"])
            pka = props["pKa"]
            assert np.isclose(float(pka), 6.0)
            assert np.isclose(float(props["marvin_pKa"]), 6.52)

            d1, charge1 = mol_to_single_mol_data(mol, atom_idx, n_feat, e_feat)
            d2, charge2 = mol_to_single_mol_data(conj, atom_idx, n_feat, e_feat)
            d3 = mol_to_paired_mol_data(mol, conj, atom_idx, n_feat, e_feat,)
            assert (
                Chem.MolToSmiles(mol)
                == "CCCN(CCC)C(=O)c1cc(C)cc(C(=O)N[C@@H](Cc2cc(F)cc(F)c2)[C@H](O)[C@@H]2[NH2+]CCN(Cc3ccccc3)C2=O)c1"
            )
            print(Chem.MolToSmiles(mol))
            print(Chem.MolToSmiles(conj))
            print(Chem.MolToMolBlock(conj))
            print(Chem.MolToMolBlock(mol))

            print(charge1, charge2)
            assert charge1 == 1
            assert charge2 == 0

            # all of them have the same number of nodes
            assert d1.num_nodes == d2.num_nodes == len(d3.x_p) == len(d3.x_d)
            # but different node features
            assert torch.equal(d1.x, d2.x) is False
            # they have the same connection table
            assert torch.equal(d1.edge_index, d2.edge_index)
            # but different edge features (NOTE: In the case of this molecule edge attr are the same)
            assert torch.equal(d1.edge_attr, d2.edge_attr) is True
            make_paired_pyg_data_from_mol(mol, n_feat, e_feat)


def test_generate_dataset():
    """Test that data classes instances are created correctly"""
    from pkasolver.data import (
        preprocess,
        make_pyg_dataset_from_dataframe,
    )

    # setupt dataframe and features
    sdf_filepaths = load_data()
    df = preprocess(sdf_filepaths["Training"])
    list_n = ["element", "formal_charge"]
    list_e = ["bond_type", "is_conjugated"]

    # generated PairedData set
    dataset = make_pyg_dataset_from_dataframe(df, list_n, list_e, paired=True)
    print(dataset[0])
    assert hasattr(dataset[0], "x_p")
    assert hasattr(dataset[0], "x_d")
    assert hasattr(dataset[0], "charge_prot")
    assert hasattr(dataset[0], "charge_deprot")
    assert dataset[0].num_nodes == len(dataset[0].x_p)

    # generated single Data set
    dataset = make_pyg_dataset_from_dataframe(
        df, list_n, list_e, paired=False, mode="protonated"
    )
    print(dataset[0])
    dataset = make_pyg_dataset_from_dataframe(
        df, list_n, list_e, paired=False, mode="deprotonated"
    )
    print(dataset[0])

    # start with generating datasets based on hydrogen count


def test_generate_dataloader():
    """Test that data classes instances are created correctly"""
    from pkasolver.data import (
        preprocess,
        make_pyg_dataset_from_dataframe,
    )
    from pkasolver.ml import dataset_to_dataloader

    # setupt dataframe and features
    sdf_filepaths = load_data()
    df = preprocess(sdf_filepaths["Novartis"])
    list_n = ["element", "formal_charge"]
    list_e = ["bond_type", "is_conjugated"]
    # start with generating datasets based on charge

    # generated PairedData set
    dataset = make_pyg_dataset_from_dataframe(df, list_n, list_e, paired=True)
    l = dataset_to_dataloader(dataset, batch_size=64, shuffle=False)
    next(iter(l))
