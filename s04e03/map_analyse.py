
   

def greedy_cluster(points: list[tuple[int, int]], threshold: float = 2.5) -> list[list[tuple[int, int]]]:
    """
    Groups spatial points into clusters based on Euclidean distance.

    Greedy algorithm: for each unassigned point, creates a new cluster and adds
    all other unassigned points within distance <= threshold to it.
    The order of input points affects the result — earlier points act as cluster seeds.

    Args:
        points: List of (row, column) coordinates to group,
                e.g. coordinates of high-rise blocks on an 11x11 map.
        threshold: Maximum Euclidean distance between a seed point and a candidate
                   for the candidate to be included in the same cluster.
                   Defaults to 2.5 — covers a 2-field neighborhood in each direction.

    Returns:
        List of clusters, where each cluster is a list of (row, column) points
        belonging to that group. Each input point appears in exactly one cluster.

    Example:
        >>> blocks = [(1,1), (1,2), (2,1), (8,8), (9,8)]
        >>> greedy_cluster(blocks, threshold=2.5)
        [[(1, 1), (1, 2), (2, 1)], [(8, 8), (9, 8)]]

    Note:
        The algorithm is not symmetric — changing the order of input points
        may produce different clusters. For deterministic results, sort `points`
        before calling, e.g. sorted(points).
    """
    clusters = []
    assigned = set()
    for i, p in enumerate(points):
        if i in assigned:
            continue
        cluster = [p]
        assigned.add(i)
        for j, q in enumerate(points):
            if j not in assigned and distance(p, q) <= threshold:
                cluster.append(q)
                assigned.add(j)
        clusters.append(cluster)
    return clusters