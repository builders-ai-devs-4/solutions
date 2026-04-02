Analyzes the Domatowo map and prepares an efficient cluster-based search plan.

Use this tool when you need to:
- retrieve and understand the map layout,
- identify tall buildings that may contain the target,
- group those buildings into spatial clusters,
- choose transporter drop points,
- estimate how many explorer tasks should be launched.

The Planner does not execute the mission directly.
It only prepares a structured search plan for the Supervisor.

Expected workflow:
1. Call `get_help` if the map symbols or action format are unclear.
2. Call `send_action` with `{"action": "getMap"}` to retrieve the city map.
3. Call `analyze_map` on the raw map response.
4. Return a structured plan for the Supervisor.

Return format:
A concise structured result describing:
- identified clusters,
- buildings assigned to each cluster,
- recommended drop point for each cluster,
- estimated priority or search order,
- recommended number of explorer tasks.

Example output:
{
  "clusters": [
    {
      "cluster_id": 0,
      "blocks": ["C3", "C4", "D3"],
      "drop_point": "C3",
      "priority": 1
    },
    {
      "cluster_id": 1,
      "blocks": ["H8", "H9"],
      "drop_point": "H8",
      "priority": 2
    }
  ],
  "recommended_explorers": 2,
  "notes": "Use one transporter-led explorer per cluster. Search priority is based on cluster size and compactness."
}

Do not call the helicopter.
Do not finalize the mission.
Do not perform field exploration.
Only analyze the map and produce a search plan.