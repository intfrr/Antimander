import random
import numpy as np

from src.utils.articulation_points import articulationPoints
from src.connectivity import can_lose
from src.districts import district_populations, is_frontier

def fix_pop_equality(state, partition, n_districts, tolerance=.10, max_iters=10000):
    assert 0 < tolerance < 1.0
    ideal_pop = state.population / n_districts
    d_pop = district_populations(state, partition, n_districts)
    pop_max = ideal_pop * (1+tolerance)
    pop_min = ideal_pop * (1-tolerance)

    fronts = [ set() for _ in range(n_districts) ]
    for ti in range(state.n_tiles):
        if is_frontier(partition, state, ti):
            fronts[partition[ti]].add(ti)

    for i in range(max_iters):
        changes_needed = False

        for d_i, d_front in enumerate(fronts):
            too_big = d_pop[d_i] > pop_max
            too_small = d_pop[d_i] < pop_min

            if too_small or too_big:
                changes_needed = True

            for t_i in random.sample(tuple(d_front), min(5, len(d_front))):
                tile_moved = None

                # Over populated, give t_i away.
                if too_big:
                    if not can_lose(partition, state, n_districts, t_i):
                        continue
                    options = [ t for t in state.tile_neighbors[t_i] if d_i != partition[t] ]
                    assert len(options)
                    t_other = random.choice(options)
                    d_other = partition[t_other]
                    d_pop[d_i] -= state.tile_populations[t_i]
                    d_pop[d_other] += state.tile_populations[t_i]
                    partition[t_i] = d_other
                    d_front.remove(t_i)
                    fronts[d_other].add(t_i)
                    tile_moved = t_i

                # Under populated, take one.
                elif d_pop[d_i] < ideal_pop * (1-tolerance):
                    options = [ t for t in state.tile_neighbors[t_i] if d_i != partition[t] and can_lose(partition, state, n_districts, t) ]

                    if len(options):
                        t_other = random.choice(options)
                        d_other = partition[t_other]
                        d_pop[d_i] += state.tile_populations[t_other]
                        d_pop[d_other] -= state.tile_populations[t_other]
                        partition[t_other] = d_i
                        d_front.add(t_other)
                        fronts[d_other].remove(t_other)
                        tile_moved = t_other

                if tile_moved is not None:
                    for tk in state.tile_neighbors[tile_moved]:
                        d_front = fronts[partition[tk]]
                        is_front = is_frontier(partition, state, tk)
                        if is_front:
                            d_front.add(tk)
                        elif tk in d_front:
                            d_front.remove(tk)
                    # Only edit one tile per district per step.
                    break

            # for ti in range(state.n_tiles):
            #     if is_frontier(partition, state, ti):
            #         assert ti in fronts[partition[ti]], (ti, partition[ti])
            #     else:
            #         assert ti not in fronts[partition[ti]], (ti, partition[ti])

        # assert np.array_equal(d_pop, district_populations(state, partition, n_districts)), (d_pop, district_populations(state, partition, n_districts))
        if not changes_needed:
            # print(d_pop, pop_max, pop_min)
            return i

    raise ValueError('Failed to fix pop_equality.')
