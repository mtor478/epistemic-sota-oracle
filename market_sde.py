import torch
import torch.nn as nn
import torch.nn.functional as F

# 📐 Invariantes Topológicas
STATE_DIM = 50       
REGIME_DIM = 128     
ACTION_DIM = 3 # USDC (Cash), WETH (Risk-On), WBTC (Store of Value)

class NeuralSDE(nn.Module):
    """
    Motor SDE Neural. 
    Mapeia os sinais FHE colapsados para um delta de alocação de capital (\Delta w).
    """
    def __init__(self, fhe_dim=64):
        super().__init__()
        self.fhe_projection = nn.Linear(fhe_dim, REGIME_DIM)
        self.policy = nn.Sequential(
            nn.Linear(REGIME_DIM + STATE_DIM, 128),
            nn.LayerNorm(128),
            nn.Mish(),
            nn.Linear(128, ACTION_DIM)
        )
        # Memória Latente do Mercado (H_t)
        self.latent_state = nn.Parameter(torch.ones(1, STATE_DIM), requires_grad=False)

    def forward(self, fhe_signals):
        """
        fhe_signals: Tensor extraído do Oráculo L2 (Decriptado no Ring 3)
        Retorna: w_{t+\Delta t} (Pesos Alvo)
        """
        # 1. Absorção Epistêmica
        fhe_emb = F.gelu(self.fhe_projection(fhe_signals.unsqueeze(0)))
        
        # 2. Concatenação de Estado
        state = torch.cat([self.latent_state, fhe_emb], dim=-1)
        
        # 3. Política de Alocação (\pi_\phi)
        logits = self.policy(state)
        target_weights = F.softmax(logits, dim=-1)
        
        # 4. Evolução da SDE (Euler-Maruyama step aproximado)
        drift = -0.01 * self.latent_state
        diffusion = 0.05 * torch.randn_like(self.latent_state)
        self.latent_state.data = self.latent_state + drift + diffusion
        
        return target_weights.squeeze(0)
