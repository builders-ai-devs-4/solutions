Runs multiple Explorer agents in parallel, one per cluster.
Stops all explorers as soon as one confirms finding the target.
Returns the coordinates of the found target, or a list of 'not found' results if no target was located.

Args:
  tasks: list of task strings, one per cluster, e.g.:
    ['Search cluster A: tall blocks at (1,1),(1,2),(2,1). Transporter drop point: (2,1). Budget: 80pts.',
     'Search cluster B: tall blocks at (8,8),(9,8). Transporter drop point: (8,8). Budget: 80pts.']

Returns:
  dict with keys:
    found (bool): whether the target was located
    coordinates (str | None): grid coordinates if found, e.g. 'F6'
    explorer_id (int | None): which explorer found the target
    results (list[dict]): all explorer reports