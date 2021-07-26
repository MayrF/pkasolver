from torch_geometric.data import DataLoader
import torch
import pandas as pd

#Train/Test Split PyG Datasets

# def pyg_split(dataset,train_test_split):
#     """Take List of PyG Data oojcts and a split ratio between 0 and 1 
#     and return a list of Training data and a list of test data.
#     """    
#     split_length=int(len(dataset)*train_test_split)
#     train_dataset = dataset[:split_length]
#     test_dataset = dataset[split_length:]
#     return train_dataset, test_dataset

#PyG Dataset to Dataloader 
def dataset_to_dataloader(data, batch_size, shuffle=False):
    """Take a PyG Dataset and return a Dataloader object.
    
    batch_size must be defined.
    Optional shuffle can be enabled.
    """
    return DataLoader(data, batch_size=batch_size, shuffle=shuffle, follow_batch=['x2'])

def test_ml_model(baseline_models, X_data, y_data, dataset_name):
    res ={'Dataset':dataset_name,
          'pKa_true':y_data
         }
    for name, models in baseline_models.items():
        for mode, model in models.items(): 
            res[f'{name.upper()}_{mode}'] = model.predict(X_data[mode]).flatten()
    return pd.DataFrame(res)

def graph_predict(model, loader, device='cpu'):
    model.eval()
    for i,data in enumerate(loader):  # Iterate in batches over the training dataset.
        data.to(device=device)
        y_pred = model(x=data.x, x2=data.x2,edge_attr=data.edge_attr, edge_attr2=data.edge_attr2, data=data).reshape(-1)
        y_true = data.y
        if i == 0:
            Y_pred = y_pred 
            Y_true = y_true
        else:
            Y_true=torch.hstack((Y_true,y_true))
            Y_pred=torch.hstack((Y_pred,y_pred))
    return Y_true.detach().numpy(), Y_pred.detach().numpy()

def test_graph_model(graph_models, loader, dataset_name):
    res ={'Dataset':dataset_name,
         }
    for mode, models in graph_models.items():
        for edge, model in models.items():
            res['pKa_true'], res[f'GCN_{mode}_{edge}'] = graph_predict(model,loader)
    return pd.DataFrame(res)