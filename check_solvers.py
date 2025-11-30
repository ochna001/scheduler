
import pulp as pl

print("Available Solvers:")
solver_list = pl.listSolvers(onlyAvailable=True)
for s in solver_list:
    print(f" - {s}")

print("\nTesting CBC...")
try:
    prob = pl.LpProblem("test", pl.LpMinimize)
    x = pl.LpVariable("x", 0, 1)
    prob += x >= 1
    prob.solve(pl.PULP_CBC_CMD(msg=False))
    print("CBC Works!")
except Exception as e:
    print(f"CBC Failed: {e}")

print("\nTesting HiGHS...")
try:
    prob = pl.LpProblem("test", pl.LpMinimize)
    x = pl.LpVariable("x", 0, 1)
    prob += x >= 1
    prob.solve(pl.getSolver('HiGHS_CMD', msg=False))
    print("HiGHS Works!")
except Exception as e:
    print(f"HiGHS Failed: {e}")
