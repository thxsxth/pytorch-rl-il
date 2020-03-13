import torch
from rlil.nn import RLNetwork
from .approximation import Approximation


class QContinuous(Approximation):
    def __init__(
            self,
            model,
            optimizer,
            name='q',
            **kwargs
    ):
        model = QContinuousModule(model)
        super().__init__(
            model,
            optimizer,
            name=name,
            **kwargs
        )


class QContinuousModule(RLNetwork):
    def forward(self, states, actions_raw):
        x = torch.cat((states.features.float(), actions_raw), dim=1)
        return self.model(x).squeeze(-1) * states.mask.float()
