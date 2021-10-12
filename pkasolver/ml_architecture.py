import copy
import pickle

import torch
from torch_geometric.nn.glob import attention
from tqdm import tqdm
import torch.nn.functional as F
from torch.nn import Linear, ModuleList, ReLU, Sequential
from torch_geometric.nn import (
    GCNConv,
    NNConv,
    global_mean_pool,
    global_max_pool,
    GlobalAttention,
)

from pkasolver.constants import DEVICE, SEED

#####################################
#####################################


def attention_pooling(num_node_features):
    return GlobalAttention(
        Sequential(
            Linear(num_node_features, num_node_features),
            ReLU(),
            Linear(num_node_features, 1),
        )
    )


#####################################
#####################################
# defining GCN for single state
#####################################
#####################################
from torch_geometric.nn.models import (
    GIN,
    GAT,
    AttentiveFP,
)


class AttentivePka(AttentiveFP):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        num_layers: int,
        out_channels: int,
        dropout: float,
        edge_dim: int,
        num_timesteps: int,
    ):

        super().__init__(
            in_channels=in_channels,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            num_timesteps=num_timesteps,
            dropout=dropout,
            edge_dim=edge_dim,
        )
        torch.manual_seed(SEED)
        self.checkpoint = {
            "epoch": 0,
            "optimizer_state_dict": "",
            "best_loss": (100, -1, -1),
            "best_states": {},
            "progress_table": {"epoch": [], "train_loss": [], "validation_loss": []},
        }

    @staticmethod
    def _return_lin(
        input_dim: int, nr_of_lin_layers: int, embeding_size: int,
    ):
        lins = []
        lins.append(Linear(input_dim, embeding_size))
        for _ in range(2, nr_of_lin_layers):
            lins.append(Linear(embeding_size, embeding_size))
        lins.append(Linear(embeding_size, 1))
        return ModuleList(lins)


class GATpKa(GAT):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        num_layers: int,
        out_channels,
        dropout,
    ):
        super().__init__(
            in_channels=in_channels,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )
        torch.manual_seed(SEED)
        self.checkpoint = {
            "epoch": 0,
            "optimizer_state_dict": "",
            "best_loss": (100, -1, -1),
            "best_states": {},
            "progress_table": {"epoch": [], "train_loss": [], "validation_loss": []},
        }

    @staticmethod
    def _return_lin(
        input_dim: int, nr_of_lin_layers: int, embeding_size: int,
    ):
        lins = []
        lins.append(Linear(input_dim, embeding_size))
        for _ in range(2, nr_of_lin_layers):
            lins.append(Linear(embeding_size, embeding_size))
        lins.append(Linear(embeding_size, 1))
        return ModuleList(lins)


class GINpKa(GIN):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        num_layers: int,
        out_channels,
        dropout,
    ):
        super().__init__(
            in_channels=in_channels,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )
        torch.manual_seed(SEED)
        self.checkpoint = {
            "epoch": 0,
            "optimizer_state_dict": "",
            "best_loss": (100, -1, -1),
            "best_states": {},
            "progress_table": {"epoch": [], "train_loss": [], "validation_loss": []},
        }

    @staticmethod
    def _return_lin(
        input_dim: int, nr_of_lin_layers: int, embeding_size: int,
    ):
        lins = []
        lins.append(Linear(input_dim, embeding_size))
        for _ in range(2, nr_of_lin_layers):
            lins.append(Linear(embeding_size, embeding_size))
        lins.append(Linear(embeding_size, 1))
        return ModuleList(lins)


class GCN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(SEED)
        self.checkpoint = {
            "epoch": 0,
            "optimizer_state_dict": "",
            "best_loss": (100, -1, -1),
            "best_states": {},
            "progress_table": {"epoch": [], "train_loss": [], "validation_loss": []},
        }

    @staticmethod
    def _return_lin(
        input_dim: int, nr_of_lin_layers: int, embeding_size: int,
    ):
        lins = []
        lins.append(Linear(input_dim, embeding_size))
        for _ in range(2, nr_of_lin_layers):
            lins.append(Linear(embeding_size, embeding_size))
        lins.append(Linear(embeding_size, 1))
        return ModuleList(lins)

    @staticmethod
    def _return_conv(num_node_features, nr_of_layers, embeding_size):
        convs = []
        convs.append(GCNConv(num_node_features, embeding_size))
        for _ in range(1, nr_of_layers):
            convs.append(GCNConv(embeding_size, embeding_size))
        return ModuleList(convs)

    @staticmethod
    def _return_nnconv(
        num_node_features, num_edge_features, nr_of_layers, embeding_size
    ):

        convs = []
        nn1 = Sequential(
            Linear(num_edge_features, embeding_size),
            ReLU(),
            Linear(embeding_size, num_node_features * embeding_size),
        )
        nn2 = Sequential(
            Linear(num_edge_features, embeding_size),
            ReLU(),
            Linear(embeding_size, embeding_size * embeding_size),
        )
        convs.append(NNConv(num_node_features, embeding_size, nn=nn1))
        for _ in range(1, nr_of_layers):
            convs.append(NNConv(embeding_size, embeding_size, nn=nn2))
        return ModuleList(convs)


#####################################
# tie in classes
# forward function
#####################################
class GCNSingleForward:
    def _forward(self, x, edge_index, x_batch):
        # move batch to device
        x_batch = x_batch.to(device=DEVICE)

        if self.attention:
            # if attention=True, pool
            x_att = self.pool(x, x_batch)

        # run through conv layers
        for i in range(len(self.convs)):
            if i < len(self.convs) - 1:
                x = F.relu(self.convs[i](x, edge_index))
            else:
                x = self.convs[i](x, edge_index)

        # set dimensions to zero
        x = F.dropout(x, p=0.5, training=self.training)

        # global max pooling
        x = global_mean_pool(x, x_batch)  # [batch_size, hidden_channels]

        # if attention=True append attention layer
        if self.attention:
            x = torch.cat((x, x_att), 1)

        # run through linear layer
        for i in range(len(self.lins)):
            if i < len(self.lins) - 1:
                x = F.relu(self.lins[i](x))
            else:
                x = self.lins[i](x)
        return x


class GCNPairOneConvForward:
    def _forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        x_p_batch = data.x_p_batch.to(device=DEVICE)
        x_d_batch = data.x_d_batch.to(device=DEVICE)

        # using only a single conv

        for i in range(len(self.convs)):
            if i < len(self.lins_p) - 1:
                x_p = F.relu(self.convs[i](x_p, data.edge_index_p))
            else:
                x_p = self.convs[i](x_p, data.edge_index_p)

        for i in range(len(self.convs)):
            if i < len(self.lins_d) - 1:
                x_d = F.relu(self.convs[i](x_d, data.edge_index_p))
            else:
                x_d = self.convs[i](x_d, data.edge_index_p)

        x_p = global_mean_pool(x_p, x_p_batch)  # [batch_size, hidden_channels]
        x_d = global_mean_pool(x_d, x_d_batch)

        x_p = F.dropout(x_p, p=0.5, training=self.training)
        x_d = F.dropout(x_d, p=0.5, training=self.training)

        for i in range(len(self.lins_p)):
            if i < len(self.lins_p) - 1:
                x_p = F.relu(self.lins_p[i](x_p))
            else:
                x_p = self.lins_p[i](x_p)

        for i in range(len(self.lins_d)):
            if i < len(self.lins_d) - 1:
                x_d = F.relu(self.lins_d[i](x_d))
            else:
                x_d = F.relu(self.lins_d[i](x_d))

        return x_p + x_d


class GCNPairTwoConvForward:
    def _forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        x_p_batch = data.x_p_batch.to(device=DEVICE)
        x_d_batch = data.x_d_batch.to(device=DEVICE)

        if self.attention:
            x_p_att = self.pool(x_p, x_p_batch)
            x_d_att = self.pool(x_d, x_d_batch)

        for i in range(len(self.convs_p)):
            if i < len(self.convs_p) - 1:
                x_p = F.relu(self.convs_p[i](x_p, data.edge_index_p))
            else:
                x_p = self.convs_p[i](x_p, data.edge_index_p)

        for i in range(len(self.convs_d)):
            if i < len(self.convs_d) - 1:
                x_d = F.relu(self.convs_d[i](x_d, data.edge_index_d))
            else:
                x_d = self.convs_d[i](x_d, data.edge_index_d)

        x_p = global_mean_pool(x_p, x_p_batch)  # [batch_size, hidden_channels]
        x_d = global_mean_pool(x_d, x_d_batch)

        if self.attention:
            x = torch.cat((x_p, x_d, x_p_att, x_d_att), 1)
        else:
            x = torch.cat([x_p, x_d], 1)

        x = F.dropout(x, p=0.5, training=self.training)
        for i in range(len(self.lins)):
            if i < len(self.lins) - 1:
                x = F.relu(self.lins[i](x))
            else:
                x = self.lins[i](x)
        return x


class NNConvSingleForward:
    def _forward(self, x, x_batch, edge_attr, edge_index):

        x_batch = x_batch.to(device=DEVICE)
        if self.attention:
            x_att = self.pool(x, x_batch)

        for i in range(len(self.convs)):
            if i < len(self.convs) - 1:
                x = F.relu(self.convs[i](x, edge_index, edge_attr))
            else:
                x = self.convs[i](x, edge_index, edge_attr)

        x = global_mean_pool(x, x_batch)  # [batch_size, hidden_channels]

        if self.attention:
            x = torch.cat((x, x_att), 1)

        x = F.dropout(x, p=0.5, training=self.training)

        for i in range(len(self.lins)):
            if i < len(self.lins) - 1:
                x = F.relu(self.lins[i](x))
            else:
                x = self.lins[i](x)
        return x


class NNConvPairForward:
    def _forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):

        x_p_batch, x_d_batch = (
            data.x_p_batch.to(device=DEVICE),
            data.x_d_batch.to(device=DEVICE),
        )
        x_p_att = self.pool(x_p, x_p_batch)
        x_d_att = self.pool(x_d, x_d_batch)

        for i in range(len(self.convs_d)):
            if i < len(self.convs_d) - 1:
                x_d = F.relu(self.convs_d[i](x_d, data.edge_index_d, edge_attr_d))
            else:
                x_d = self.convs_d[i](x_d, data.edge_index_d, edge_attr_d)

        for i in range(len(self.convs_p)):
            if i < len(self.convs_p) - 1:
                x_p = F.relu(self.convs_p[i](x_p, data.edge_index_p, edge_attr_p))
            else:
                x_p = self.convs_p[i](x_p, data.edge_index_p, edge_attr_p)

        x_p = global_mean_pool(x_p, x_p_batch)  # [batch_size, hidden_channels]
        x_d = global_mean_pool(x_d, x_d_batch)

        if self.attention:
            x = torch.cat((x_p, x_d, x_p_att, x_d_att), 1)
        else:
            x = torch.cat((x_p, x_d), 1)

        x = F.dropout(x, p=0.5, training=self.training)
        for i in range(len(self.lins)):
            if i < len(self.lins) - 1:
                x = F.relu(self.lins[i](x))
            else:
                x = self.lins[i](x)

        return x


class NNConvSingleArchitecture(GCN):
    def __init__(
        self, num_node_features, num_edge_features, nr_of_layers=3, embeding_size=96
    ):
        super().__init__()
        self.pool = attention_pooling(num_node_features)

        self.convs = self._return_nnconv(
            num_node_features,
            num_edge_features,
            nr_of_layers=nr_of_layers,
            embeding_size=embeding_size,
        )
        if self.attention:
            input_dim = embeding_size + num_node_features
        else:
            input_dim = embeding_size

        self.lins = GCN._return_lin(
            input_dim=input_dim, nr_of_lin_layers=2, embeding_size=embeding_size,
        )


class GCNSingleArchitecture(GCN):
    def __init__(self, num_node_features, nr_of_layers: int, embeding_size: int):
        super().__init__()
        self.pool = attention_pooling(num_node_features)

        self.convs = self._return_conv(
            num_node_features, nr_of_layers=nr_of_layers, embeding_size=embeding_size
        )

        if self.attention:
            input_dim = embeding_size + num_node_features
        else:
            input_dim = embeding_size

        self.lins = GCN._return_lin(
            input_dim=input_dim, nr_of_lin_layers=2, embeding_size=embeding_size,
        )


class GCNPairArchitecture(GCN):
    def __init__(
        self, num_node_features, nr_of_layers: int = 3, embeding_size: int = 96
    ):
        super().__init__()

        self.pool = attention_pooling(num_node_features,)

        self.convs_p = self._return_conv(
            num_node_features, nr_of_layers=nr_of_layers, embeding_size=embeding_size
        )
        self.convs_d = self._return_conv(
            num_node_features, nr_of_layers=nr_of_layers, embeding_size=embeding_size
        )
        if self.attention:
            input_dim = embeding_size * 2 + 2 * num_node_features
        else:
            input_dim = embeding_size * 2

        self.lins = GCN._return_lin(
            input_dim=input_dim, nr_of_lin_layers=2, embeding_size=embeding_size,
        )

        self.pool = attention_pooling(num_node_features)


class GCNPairArchitectureV2(GCN):
    def __init__(
        self, num_node_features, nr_of_layers: int = 3, embeding_size: int = 96
    ):
        super().__init__()

        self.pool = attention_pooling(num_node_features)

        self.convs = self._return_conv(
            num_node_features, nr_of_layers=nr_of_layers, embeding_size=embeding_size
        )

        if self.attention:
            input_dim = embeding_size
        else:
            input_dim = embeding_size

        self.lins_d = GCN._return_lin(
            input_dim=input_dim, nr_of_lin_layers=2, embeding_size=embeding_size,
        )
        self.lins_p = GCN._return_lin(
            input_dim=input_dim, nr_of_lin_layers=2, embeding_size=embeding_size,
        )

        self.pool = attention_pooling(num_node_features)


class NNConvPairArchitecture(GCN):
    def __init__(
        self,
        num_node_features,
        num_edge_features,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
    ):
        super().__init__()

        self.pool = attention_pooling(num_node_features)

        self.convs_d = GCN._return_nnconv(
            num_node_features,
            num_edge_features,
            nr_of_layers=nr_of_layers,
            embeding_size=embeding_size,
        )
        self.convs_p = GCN._return_nnconv(
            num_node_features,
            num_edge_features,
            nr_of_layers=nr_of_layers,
            embeding_size=embeding_size,
        )
        if self.attention:
            input_dim = 2 * embeding_size + (2 * num_node_features)
        else:
            input_dim = 2 * embeding_size

        self.lins = GCN._return_lin(
            input_dim=input_dim, nr_of_lin_layers=2, embeding_size=embeding_size,
        )


#####################################
#####################################
# Combining everything
#####################################
#####################################
class GATProt(GATpKa):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        hidden_channels: int = 32,
        num_layers: int = 3,
        out_channels=32,
        dropout=0.5,
        attention=False,
    ):
        super().__init__(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )
        print(f"Attention pooling: {attention}")
        self.lins = GATpKa._return_lin(
            input_dim=out_channels, nr_of_lin_layers=2, embeding_size=64
        )

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        x_p_batch = data.x_p_batch.to(device=DEVICE)

        x = super().forward(x=x_p, edge_index=data.edge_index_p)
        # global mean pooling
        x = global_mean_pool(x, x_p_batch)  # [batch_size, hidden_channels]
        # run through linear layer
        for i in range(len(self.lins)):
            if i < len(self.lins) - 1:
                x = F.relu(self.lins[i](x))
            else:
                x = self.lins[i](x)
        return x


class AttentiveProt(AttentivePka):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        hidden_channels: int = 32,
        num_layers: int = 3,
        num_timesteps: int = 10,
        out_channels=32,
        dropout=0.5,
        attention=False,
    ):
        super().__init__(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
            edge_dim=num_edge_features,
            num_timesteps=num_timesteps,
        )
        print(f"Attention pooling: {attention}")
        self.lins = AttentivePka._return_lin(
            input_dim=out_channels, nr_of_lin_layers=2, embeding_size=64
        )

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        x_p_batch = data.x_p_batch.to(device=DEVICE)

        x = super().forward(
            x=x_p, edge_attr=edge_attr_p, edge_index=data.edge_index_p, batch=x_p_batch
        )
        # global mean pooling
        # x = global_mean_pool(x, x_p_batch)  # [batch_size, hidden_channels]
        # run through linear layer
        # for i in range(len(self.lins)):
        #    if i < len(self.lins) - 1:
        #        x = F.relu(self.lins[i](x))
        #    else:
        #        x = self.lins[i](x)
        return x


class GINProt(GINpKa):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        hidden_channels: int = 32,
        num_layers: int = 3,
        out_channels=32,
        dropout=0.5,
        attention=False,
    ):
        super().__init__(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )
        print(f"Attention pooling: {attention}")
        self.lins = GINpKa._return_lin(
            input_dim=out_channels, nr_of_lin_layers=2, embeding_size=64
        )

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        x_p_batch = data.x_p_batch.to(device=DEVICE)

        x = super().forward(x=x_p, edge_index=data.edge_index_p)
        # global mean pooling
        x = global_mean_pool(x, x_p_batch)  # [batch_size, hidden_channels]
        # run through linear layer
        for i in range(len(self.lins)):
            if i < len(self.lins) - 1:
                x = F.relu(self.lins[i](x))
            else:
                x = self.lins[i](x)
        return x


class GATPair(GATpKa):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        hidden_channels: int = 32,
        num_layers: int = 3,
        out_channels=32,
        dropout=0.5,
        attention=False,
    ):
        super().__init__(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )
        print(f"Attention pooling: {attention}")
        self.lins = GATpKa._return_lin(
            input_dim=out_channels, nr_of_lin_layers=2, embeding_size=64
        )

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        def _forward(x, edge_index, x_batch, func):
            x = func(x=x, edge_index=edge_index)
            # global mean pooling
            x = global_mean_pool(x, x_batch)  # [batch_size, hidden_channels]
            # run through linear layer
            for i in range(len(self.lins)):
                if i < len(self.lins) - 1:
                    x = F.relu(self.lins[i](x))
                else:
                    x = self.lins[i](x)
            return x

        func = super().forward
        x_p_batch = data.x_p_batch.to(device=DEVICE)
        x_d_batch = data.x_d_batch.to(device=DEVICE)

        x_p = _forward(x_p, data.edge_index_p, x_p_batch, func)
        x_d = _forward(x_d, data.edge_index_d, x_d_batch, func)
        return x_p + x_d


class GINPairV1(GINpKa):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        hidden_channels: int = 32,
        num_layers: int = 3,
        out_channels=32,
        dropout=0.5,
        attention=False,
    ):

        super().__init__(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )
        GIN_p = GINpKa(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )
        GIN_d = GINpKa(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )

        print(f"Attention pooling: {attention}")
        self.lins = GINpKa._return_lin(
            input_dim=out_channels, nr_of_lin_layers=2, embeding_size=64
        )
        self.GIN_p = GIN_p
        self.GIN_d = GIN_d

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        def _forward(x, edge_index, x_batch, func):
            x = func(x=x, edge_index=edge_index)
            # global mean pooling
            x = global_mean_pool(x, x_batch)  # [batch_size, hidden_channels]
            # run through linear layer
            for i in range(len(self.lins)):
                if i < len(self.lins) - 1:
                    x = F.relu(self.lins[i](x))
                else:
                    x = self.lins[i](x)
            return x

        x_p_batch = data.x_p_batch.to(device=DEVICE)
        x_d_batch = data.x_d_batch.to(device=DEVICE)

        x_p = _forward(x_p, data.edge_index_p, x_p_batch, self.GIN_p.forward)
        x_d = _forward(x_d, data.edge_index_d, x_d_batch, self.GIN_d.forward)
        return x_p + x_d


class GINPairV2(GINpKa):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        hidden_channels: int = 32,
        num_layers: int = 3,
        out_channels=32,
        dropout=0.5,
        attention=False,
    ):

        super().__init__(
            in_channels=num_node_features,
            out_channels=out_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
        )

        print(f"Attention pooling: {attention}")
        self.lins_d = GINpKa._return_lin(
            input_dim=out_channels, nr_of_lin_layers=3, embeding_size=64
        )
        self.lins_p = GINpKa._return_lin(
            input_dim=out_channels, nr_of_lin_layers=3, embeding_size=64
        )

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        def _forward(x, edge_index, x_batch, func, lins):
            x = func(x=x, edge_index=edge_index)
            # global mean pooling
            x = global_mean_pool(x, x_batch)  # [batch_size, hidden_channels]
            # run through linear layer
            for i in range(len(lins)):
                if i < len(lins) - 1:
                    x = F.relu(lins[i](x))
                else:
                    x = lins[i](x)
            return x

        x_p_batch = data.x_p_batch.to(device=DEVICE)
        x_d_batch = data.x_d_batch.to(device=DEVICE)

        x_p = _forward(x_p, data.edge_index_p, x_p_batch, super().forward, self.lins_p)
        x_d = _forward(x_d, data.edge_index_d, x_d_batch, super().forward, self.lins_d)
        return x_p / x_d


class GCNProt(GCNSingleArchitecture, GCNSingleForward):
    def __init__(
        self,
        num_node_features,
        num_edge_features,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
        attention=False,
    ):
        self.attention = attention
        super().__init__(num_node_features, nr_of_layers, embeding_size)
        print(f"Attention pooling: {self.attention}")

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        return self._forward(x_p, data.edge_index_p, data.x_p_batch)


class GCNDeprot(GCNSingleArchitecture, GCNSingleForward):
    def __init__(
        self,
        num_node_features,
        num_edge_features,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
        attention=False,
    ):
        self.attention = attention
        super().__init__(num_node_features, nr_of_layers, embeding_size)
        self.pool = attention_pooling(num_node_features)
        print(f"Attention pooling: {self.attention}")

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        return self._forward(x_d, data.edge_index_d, data.x_d_batch)


class NNConvProt(NNConvSingleArchitecture, NNConvSingleForward):
    def __init__(
        self,
        num_node_features,
        num_edge_features,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
        attention=False,
    ):
        self.attention = attention
        print(f"Attention pooling: {self.attention}")

        super().__init__(
            num_node_features, num_edge_features, nr_of_layers, embeding_size
        )
        self.pool = attention_pooling(num_node_features)

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        return self._forward(x_p, data.x_p_batch, edge_attr_p, data.edge_index_p)


class NNConvDeprot(NNConvSingleArchitecture, NNConvSingleForward):
    def __init__(
        self,
        num_node_features,
        num_edge_features,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
        attention=False,
    ):
        self.attention = attention
        print(f"Attention pooling: {self.attention}")
        super().__init__(
            num_node_features, num_edge_features, nr_of_layers, embeding_size
        )
        self.pool = attention_pooling(num_node_features)

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        return self._forward(x_d, data.x_d_batch, edge_attr_d, data.edge_index_d)


#####################################
# for pairs
#####################################


class GCNPairTwoConv(GCNPairArchitecture, GCNPairTwoConvForward):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
        attention: bool = False,
    ):
        self.attention = attention
        super().__init__(num_node_features, nr_of_layers, embeding_size)
        print(f"Attention pooling: {self.attention}")

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        return self._forward(x_p, x_d, edge_attr_p, edge_attr_d, data)


class GCNPairSingleConv(GCNPairArchitectureV2, GCNPairOneConvForward):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
        attention: bool = False,
    ):
        self.attention = attention
        super().__init__(num_node_features, nr_of_layers, embeding_size)
        print(f"Attention pooling: {self.attention}")

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        return self._forward(x_p, x_d, edge_attr_p, edge_attr_d, data)


class NNConvPair(NNConvPairArchitecture, NNConvPairForward):
    def __init__(
        self,
        num_node_features: int,
        num_edge_features: int,
        nr_of_layers: int = 3,
        embeding_size: int = 96,
        attention: bool = False,
    ):
        self.attention = attention
        super().__init__(
            num_node_features, num_edge_features, nr_of_layers, embeding_size
        )
        print(f"Attention pooling: {self.attention}")

    def forward(self, x_p, x_d, edge_attr_p, edge_attr_d, data):
        return self._forward(x_p, x_d, edge_attr_p, edge_attr_d, data)


#####################################
#####################################
#####################################
#####################################
# Functions for training and testing of GCN models

calculate_mse = torch.nn.MSELoss()
calculate_mae = torch.nn.L1Loss()  # that's the MAE Loss


def gcn_train(model, loader, optimizer):
    model.train()
    for data in loader:  # Iterate in batches over the training dataset.
        out = model(
            x_p=data.x_p,
            x_d=data.x_d,
            edge_attr_p=data.edge_attr_p,
            edge_attr_d=data.edge_attr_d,
            data=data,
        )
        loss = calculate_mse(out.flatten(), data.y)  # Compute the loss.
        loss.backward()  # Derive gradients.
        optimizer.step()  # Update parameters based on gradients.
        optimizer.zero_grad()  # Clear gradients.


def gcn_test(model, loader):
    model.eval()
    loss = torch.Tensor([0]).to(device=DEVICE)
    for data in loader:  # Iterate in batches over the training dataset.
        out = model(
            x_p=data.x_p,
            x_d=data.x_d,
            edge_attr_p=data.edge_attr_p,
            edge_attr_d=data.edge_attr_d,
            data=data,
        )  # Perform a single forward pass.
        loss += calculate_mae(out.flatten(), data.y).detach()
    return round(
        float(loss / len(loader)), 3
    )  # MAE loss of batches can be summed and divided by the number of batches


def save_checkpoint(model, optimizer, epoch, train_loss, validation_loss, path):
    performance = model.checkpoint
    # increment epoch
    performance["epoch"] = epoch + 1
    # save performance of best model evaluated on validation set
    if performance["best_loss"][0] > validation_loss:
        performance["best_loss"] = (
            validation_loss,
            epoch,
            copy.deepcopy(model.state_dict()),
        )
        performance["best_states"][epoch] = (
            validation_loss,
            copy.deepcopy(model.state_dict()),
        )
    performance["optimizer_state"] = optimizer.state_dict()
    performance["progress_table"]["epoch"].append(epoch)
    performance["progress_table"]["train_loss"].append(train_loss)
    performance["progress_table"]["validation_loss"].append(validation_loss)
    with open(path, "wb") as pickle_file:
        pickle.dump(model, pickle_file)


def gcn_full_training(
    model, train_loader, val_loader, optimizer, path: str = "", NUM_EPOCHS: int = 1_000
) -> dict:
    pbar = tqdm(range(model.checkpoint["epoch"], NUM_EPOCHS + 1), desc="Epoch: ")
    results = {}
    results["training-set"] = []
    results["validation-set"] = []
    for epoch in pbar:
        if epoch != 0:
            gcn_train(model, train_loader, optimizer)
        if epoch % 20 == 0:
            train_loss = gcn_test(model, train_loader)
            val_loss = gcn_test(model, val_loader)
            pbar.set_description(
                f"Train MAE: {train_loss:.4f}, Validation MAE: {val_loss:.4f}"
            )
            results["training-set"].append(train_loss)
            results["validation-set"].append(val_loss)
            if path:
                save_checkpoint(model, optimizer, epoch, train_loss, val_loss, path)

    return results
