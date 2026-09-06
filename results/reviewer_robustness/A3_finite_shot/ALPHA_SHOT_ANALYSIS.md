# Alpha × shot-count estimator analysis

Complete independent sampling records: 5400. No quantum optimization was rerun for this grid.

The grid uses frozen O0/O3 held-out endpoint distributions, alpha in {0.02, 0.05, 0.10, 0.25, 0.50}, and 1e3/1e4/1e5 shots. Each sample is reused across alpha values within a record, providing a paired view of tail aggressiveness versus sampling cost.

## Numerical summary

- alpha=0.02, shots=1000: mean O0/O3 CVaR RMSE=0.0821651; exact ordering preservation=0.895.
- alpha=0.02, shots=10000: mean O0/O3 CVaR RMSE=0.0271791; exact ordering preservation=0.968.
- alpha=0.02, shots=100000: mean O0/O3 CVaR RMSE=0.00812966; exact ordering preservation=0.957.
- alpha=0.05, shots=1000: mean O0/O3 CVaR RMSE=0.0481084; exact ordering preservation=0.897.
- alpha=0.05, shots=10000: mean O0/O3 CVaR RMSE=0.0147831; exact ordering preservation=0.959.
- alpha=0.05, shots=100000: mean O0/O3 CVaR RMSE=0.00450183; exact ordering preservation=0.977.
- alpha=0.1, shots=1000: mean O0/O3 CVaR RMSE=0.0483929; exact ordering preservation=0.901.
- alpha=0.1, shots=10000: mean O0/O3 CVaR RMSE=0.0156977; exact ordering preservation=0.967.
- alpha=0.1, shots=100000: mean O0/O3 CVaR RMSE=0.00485944; exact ordering preservation=0.992.
- alpha=0.25, shots=1000: mean O0/O3 CVaR RMSE=0.0285352; exact ordering preservation=0.846.
- alpha=0.25, shots=10000: mean O0/O3 CVaR RMSE=0.0093436; exact ordering preservation=0.921.
- alpha=0.25, shots=100000: mean O0/O3 CVaR RMSE=0.00278318; exact ordering preservation=0.987.
- alpha=0.5, shots=1000: mean O0/O3 CVaR RMSE=0.0206795; exact ordering preservation=0.848.
- alpha=0.5, shots=10000: mean O0/O3 CVaR RMSE=0.00671723; exact ordering preservation=0.959.
- alpha=0.5, shots=100000: mean O0/O3 CVaR RMSE=0.0020804; exact ordering preservation=1.000.

This is fixed-parameter estimator evidence only. It does not establish finite-shot training, hardware, or noise robustness.
