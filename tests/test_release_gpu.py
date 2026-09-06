"""Small CUDA infrastructure check; the published simulator remains NumPy CPU."""
import numpy as np
import pytest

from qroute_dilution.qaoa import apply_cost_layer, plus_state


@pytest.mark.gpu
def test_cuda_complex128_cost_layer_matches_numpy():
    torch = pytest.importorskip('torch', reason='optional CUDA infrastructure test')
    if not torch.cuda.is_available():
        pytest.skip('CUDA unavailable; scientific CPU tests do not require it')
    # Fixed inputs, no optimizer, no new scientific endpoint or backend.
    energy = np.linspace(0.0, 2.0, 256, dtype=np.float64)
    state = plus_state(8)
    expected = apply_cost_layer(state, energy, 0.375)
    observed = torch.as_tensor(state, device='cuda') * torch.exp(
        -1j * 0.375 * torch.as_tensor(energy, device='cuda'))
    torch.cuda.synchronize()
    np.testing.assert_allclose(observed.cpu().numpy(), expected, rtol=0.0, atol=1e-13)
    assert abs(float(torch.sum(torch.abs(observed) ** 2).item()) - 1.0) < 1e-13
