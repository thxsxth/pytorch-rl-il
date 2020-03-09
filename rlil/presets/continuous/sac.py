import torch
from torch.optim import Adam
from torch.optim.lr_scheduler import CosineAnnealingLR
from rlil.agents import SAC
from rlil.approximation import QContinuous, PolyakTarget, VNetwork
from rlil.utils.writer import DummyWriter
from rlil.policies.soft_deterministic import SoftDeterministicPolicy
from rlil.memory import ExperienceReplayBuffer
from .models import fc_q, fc_v, fc_soft_policy


def sac(
        # pretrained policy path
        policy_path=None,
        # Common settings
        device="cpu",
        discount_factor=0.98,
        last_frame=2e6,
        # Adam optimizer settings
        lr_q=1e-3,
        lr_v=1e-3,
        lr_pi=1e-4,
        # Training settings
        minibatch_size=100,
        update_frequency=2,
        polyak_rate=0.005,
        # Replay Buffer settings
        replay_start_size=5000,
        replay_buffer_size=1e6,
        # Exploration settings
        temperature_initial=0.1,
        lr_temperature=1e-5,
        entropy_target_scaling=1.,
):
    """
    SAC continuous control preset.

    Args:
        policy_path (str): Path to the pretrained policy state_dict.pt
        device (str): The device to load parameters and buffers onto for this agent..
        discount_factor (float): Discount factor for future rewards.
        last_frame (int): Number of frames to train.
        lr_q (float): Learning rate for the Q networks.
        lr_v (float): Learning rate for the state-value networks.
        lr_pi (float): Learning rate for the policy network.
        minibatch_size (int): Number of experiences to sample in each training update.
        update_frequency (int): Number of timesteps per training update.
        polyak_rate (float): Speed with which to update the target network towards the online network.
        replay_start_size (int): Number of experiences in replay buffer when training begins.
        replay_buffer_size (int): Maximum number of experiences to store in the replay buffer.
        temperature_initial (float): Initial value of the temperature parameter.
        lr_temperature (float): Learning rate for the temperature. Should be low compared to other learning rates.
        entropy_target_scaling (float): The target entropy will be -(entropy_target_scaling * env.action_space.shape[0])
    """
    def _sac(env, writer=DummyWriter()):
        final_anneal_step = (last_frame - replay_start_size) // update_frequency

        q_1_model = fc_q(env).to(device)
        q_1_optimizer = Adam(q_1_model.parameters(), lr=lr_q)
        q_1 = QContinuous(
            q_1_model,
            q_1_optimizer,
            scheduler=CosineAnnealingLR(
                q_1_optimizer,
                final_anneal_step
            ),
            writer=writer,
            name='q_1'
        )

        q_2_model = fc_q(env).to(device)
        q_2_optimizer = Adam(q_2_model.parameters(), lr=lr_q)
        q_2 = QContinuous(
            q_2_model,
            q_2_optimizer,
            scheduler=CosineAnnealingLR(
                q_2_optimizer,
                final_anneal_step
            ),
            writer=writer,
            name='q_2'
        )

        v_model = fc_v(env).to(device)
        v_optimizer = Adam(v_model.parameters(), lr=lr_v)
        v = VNetwork(
            v_model,
            v_optimizer,
            scheduler=CosineAnnealingLR(
                v_optimizer,
                final_anneal_step
            ),
            target=PolyakTarget(polyak_rate),
            writer=writer,
            name='v',
        )

        policy_model = fc_soft_policy(env).to(device)
        if policy_path:
            policy_model.load_state_dict(torch.load(policy_path, map_location=device))
        policy_optimizer = Adam(policy_model.parameters(), lr=lr_pi)
        policy = SoftDeterministicPolicy(
            policy_model,
            policy_optimizer,
            env.action_space,
            scheduler=CosineAnnealingLR(
                policy_optimizer,
                final_anneal_step
            ),
            writer=writer
        )

        replay_buffer = ExperienceReplayBuffer(
            replay_buffer_size
        )

        return SAC(
            policy,
            q_1,
            q_2,
            v,
            replay_buffer,
            temperature_initial=temperature_initial,
            entropy_target=(-env.action_space.shape[0] * entropy_target_scaling),
            lr_temperature=lr_temperature,
            replay_start_size=replay_start_size,
            discount_factor=discount_factor,
            update_frequency=update_frequency,
            minibatch_size=minibatch_size,
            writer=writer,
            device=device
        )
    return _sac
