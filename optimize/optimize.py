import sys, os, json, random, argparse, time
import numpy as np
import matplotlib.pyplot as plt

from pymoo.algorithms.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.factory import get_problem, get_sampling, get_crossover, get_mutation
from pymoo.model.crossover import Crossover
from pymoo.model.mutation import Mutation
from pymoo.model.problem import Problem
from pymoo.operators.crossover.util import crossover_mask
from pymoo.performance_indicator.hv import Hypervolume

from state import State
import districts
from metrics import efficiency_gap, compactness, compactness_polsby_popper
from constraints import fix_pop_equality
import mutation

metric = Hypervolume(ref_point=np.array([2.0, 2.0]))

class DistrictCross(Crossover):
    def __init__(self, **kwargs):
        super().__init__(n_parents=2, n_offsprings=2, **kwargs)
    def _do(self, problem, X, **kwargs):
        return X.copy()

class DistrictMutation(Mutation):
    def __init__(self, state, n_districts):
        super().__init__()
        self.state = state
        self.n_districts = n_districts
        total_pop = state.tile_populations.sum()
        ideal_pop = total_pop / n_districts
        self.pop_max = ideal_pop * (1+ .1)
        self.pop_min = ideal_pop * (1- .1)

    def _do(self, problem, X, **kwargs):
        t = time.time()
        X = X.copy()
        for i in range(X.shape[0]):
            mutation_rate = random.gauss(0.02, .01)
            mutation.mutate(X[i], self.n_districts, self.state, mutation_rate, self.pop_min, self.pop_max)
        return X

class DistrictProblem(Problem):
    def __init__(self, state, n_districts, **kwargs):
        super().__init__(n_var=state.n_tiles, n_obj=2, type_var=np.integer, **kwargs)
        self.state = state
        self.n_districts = n_districts

    def _calc_pareto_front(self, n_pareto_points=100):
        x = np.linspace(0, 1, n_pareto_points)
        return np.array([x, x]).T
        # return np.array([0, 0, 0])

    def _evaluate(self, X, out, *args, **kwargs):
        t = time.time()
        out['F'] = np.array([
            [ f(self.state, p, self.n_districts) for f in (compactness, efficiency_gap) ]
            for p in X
        ])
        # print(round(metric.calc(out['F']), 6))
        # print('evaluated', X.shape[0], 'in', time.time() - t)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-d', '--n_districts', default=5, type=int)
    parser.add_argument('-t', '--n_tiles', default=100, type=int)
    parser.add_argument('-p', '--pop_size', default=100, type=int)
    parser.add_argument('-g', '--n_gens', default=100, type=int)
    parser.add_argument('-o', '--out', required=True)
    args = parser.parse_args()

    state = State.makeRandom(args.n_tiles, seed=0)

    seeds = []
    while len(seeds) < args.pop_size:
        try:
            p = districts.make_random(state, args.n_districts)
            fix_pop_equality(state, p, args.n_districts, tolerance=.10, max_iters=600)
            seeds.append(p)
        except ValueError as e:
            print(e)
            pass
        except StopIteration as e:
            print(e)
            pass
    print('Created seeds')
    algorithm = NSGA2(
        pop_size=args.pop_size,
        sampling=np.array(seeds),
        crossover=DistrictCross(),
        mutation=DistrictMutation(state, args.n_districts),
    )
    # algorithm.func_display_attrs = None

    problem = DistrictProblem(state, args.n_districts)

    res = minimize(
        problem,
        algorithm,
        ('n_gen', args.n_gens),
        seed=1,
        verbose=True,
        save_history=False
    )

    with open(os.path.join(args.out, 'rundata.json'), 'w') as f:
        json.dump({
            'n_districts': args.n_districts,
            'nsga_config': {},
            'state': state.toJSON(),
            'values': res.F.tolist(),
            'solutions': res.X.tolist()
        }, f)

    plt.scatter(res.F[:, 0], res.F[:, 1])
    plt.savefig(os.path.join(args.out, 'pareto_front.png'))

    # pop_each_gen = [ a.pop for a in res.history[1:] ]
    # obj_and_feasible_each_gen = [pop[pop.get("feasible")[:,0]].get("F") for pop in pop_each_gen]
    # hv = [ metric.calc(f) for f in obj_and_feasible_each_gen ]
    # plt.plot(np.arange(len(hv)), hv, '-o')
    # plt.title("Convergence")
    # plt.xlabel("Generation")
    # plt.ylabel("Hypervolume")
    # plt.savefig(os.path.join(args.out, 'convergence.png'))
