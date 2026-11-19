# Sourcing optimization methodology — allocation_milp_v1

This model minimizes hypothetical cost for an analyst-defined comparable quantity. HMRC disclosures do not supply quotations, equivalent units, available capacity or switching costs. Inputs are analyst assumptions or explicitly illustrative examples, never inferred commercial facts.

For supplier i, continuous allocation x_i and binary selection y_i minimize `Σ cost_i*x_i + Σ fixed_i*y_i`. Constraints are:

- `Σ x_i = demand`.
- `0 ≤ x_i ≤ min(capacity_i, maximum_i, demand*dependency_share)*y_i`.
- `x_i ≥ max(minimum_i, 0.0001)*y_i`.
- Ineligible suppliers have y_i=0; selected supplier count lies between the supplied bounds.

The disclosed 0.0001-unit selection floor prevents zero-allocation suppliers from satisfying a minimum supplier count. Zero demand is explicitly rejected; quantities/costs must be nonnegative, finite and within validated precision/range limits. Up to 40 candidate suppliers and a 0.01–30 second time limit bound local requests. Minimum allocation applies only when selected. All candidates must use the same explicitly named unit.

SciPy `optimize.milp` executes the HiGHS mixed-integer solver; this is not a price-sorting heuristic. The application independently checks returned constraint residuals, bounds and integrality before showing a feasible allocation. Quantity tolerance is max(1e-6, demand*1e-8); integrality tolerance is 1e-6. Solver arithmetic is floating point, separate from the exact Decimal financial scenario model. Objective display derives from returned allocations and entered prices; no HMRC savings baseline is implied. [Official SciPy MILP documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).

Status 0 is called optimal only after feasibility checks. A valid incumbent at a time limit is feasible_not_proven_optimal; a limit without a valid incumbent is limit_reached. Infeasible, unbounded, failed, unknown and failed_validation remain distinct. Capacity and eligibility explanations are sufficient diagnostics; no irreducible infeasible-set claim is made. Binding limits identify active combined capacity/maximum/dependency bounds, minimum allocations and supplier-count limits.

Independent fixtures: demand 100, supplier A cost £10/capacity 60 and B cost £20/capacity 100 yields 60/40 and £1,400. A 50% dependency cap yields 50/50 and £1,500. A £1,000 fixed cost for A yields B-only £2,000; a 55-unit B minimum yields £1,550. Tests also cover single supplier, eligibility, infeasibility, selection caps, invalid/zero demand and nonoptimal termination.

Each saved run stores model version, full assumptions/constraints, optional context/source fingerprint, solver status, allocations, objective and validation metadata. Save re-solves server-side rather than accepting client results. Copy/rerun creates a new immutable result; never silently overwrite a previous run. Recent alternatives compare modelled cost and dependency constraints. Different units or assumptions are not automatically comparable.


## Guided sourcing workflow

React now separates requirement, candidate suppliers, constraints and optimize/compare steps. Saved Strategies is a separate view. Comparisons are restricted to matching units, demand and supplier names and expose all configuration details; analysts must still assess commercial comparability. Solver mathematics, feasibility validation, tolerances and immutable run persistence are unchanged. Cost differences remain hypothetical model outputs.
