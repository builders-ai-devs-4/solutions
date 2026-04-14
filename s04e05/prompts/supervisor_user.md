Solve the foodwarehouse task using the available sub-agents and control tools.

Execution rules:
- First gather understanding with Recon.
- Then determine the full demand.
- Then find destination mappings.
- Then determine creator identities and signatures.
- Then build a complete plan.
- Then execute the plan.
- Then audit the live state.
- Only if the audit passes, call api_done.
- After api_done, call scan_flag on the returned response.

Important constraints:
- One separate order per required city.
- Do not guess destination, creatorID, or signature.
- Do not call api_done before the audit passes.
- If the state is broken beyond safe repair, use api_reset and rebuild.

Your final successful result should be the extracted flag.